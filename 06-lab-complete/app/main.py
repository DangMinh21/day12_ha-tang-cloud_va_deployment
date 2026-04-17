"""
Production AI Agent — Kết hợp tất cả Day 12 concepts

Checklist:
  ✅ Config từ environment (12-factor)
  ✅ Structured JSON logging
  ✅ API Key authentication
  ✅ Rate limiting
  ✅ Cost guard
  ✅ Input validation (Pydantic)
  ✅ Health check + Readiness probe
  ✅ Graceful shutdown
  ✅ Security headers
  ✅ CORS
  ✅ Error handling
"""
import os
import time
import signal
import logging
import json
from datetime import datetime, timezone
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings

from fastapi.responses import HTMLResponse

# Mock LLM (thay bằng OpenAI/Anthropic khi có API key)
# from utils.mock_llm import ask as llm_ask
if settings.openai_api_key:
    from utils.real_llm import ask as llm_ask
else:
    from utils.mock_llm import ask as llm_ask


# Auth
from app.auth import verify_api_key

# Rate limiter
from app.rate_limiter import check_rate_limit

# Cost Gaurd
from app.cost_guard import check_budget

# Redis
import redis as redis_lib
def get_redis():
    if settings.redis_url:
        return redis_lib.from_url(settings.redis_url, decode_responses=True)
    return None

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# ─────────────────────────────────────────────────────────
# Simple In-memory Rate Limiter
# ─────────────────────────────────────────────────────────
# _rate_windows: dict[str, deque] = defaultdict(deque)

# def check_rate_limit(key: str):
#     now = time.time()
#     window = _rate_windows[key]
#     while window and window[0] < now - 60:
#         window.popleft()
#     if len(window) >= settings.rate_limit_per_minute:
#         raise HTTPException(
#             status_code=429,
#             detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
#             headers={"Retry-After": "60"},
#         )
#     window.append(now)

# ─────────────────────────────────────────────────────────
# Simple Cost Guard
# ─────────────────────────────────────────────────────────
_daily_cost = 0.0
_cost_reset_day = time.strftime("%Y-%m-%d")

# def check_and_record_cost(input_tokens: int, output_tokens: int):
#     global _daily_cost, _cost_reset_day
#     today = time.strftime("%Y-%m-%d")
#     if today != _cost_reset_day:
#         _daily_cost = 0.0
#         _cost_reset_day = today
#     if _daily_cost >= settings.daily_budget_usd:
#         raise HTTPException(503, "Daily budget exhausted. Try tomorrow.")
#     cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
#     _daily_cost += cost

# ─────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────
# api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# def verify_api_key(api_key: str = Security(api_key_header)) -> str:
#     if not api_key or api_key != settings.agent_api_key:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid or missing API key. Include header: X-API-Key: <key>",
#         )
#     return api_key

# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    time.sleep(0.1)  # simulate init
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # response.headers.pop("server", None)
        if "server" in response.headers:
            del response.headers["server"]

        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Your question for the agent")
    user_id: str = Field(default="anonymous", max_length=64, description="User ID")

class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str
    user_id: str

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }

@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
    _rate: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget),
):
    """
    Send a question to the AI agent.

    **Authentication:** Include header `X-API-Key: <your-key>`
    """
    r = get_redis()
    history_key = f"history:{body.user_id}"

    # Lấy history từ Redis
    history = []
    if r:
        raw = r.lrange(history_key, -10, -1)  # 10 messages gần nhất
        history = [msg for msg in raw]

    # Gọi LLM (mock)
    context = "\n".join(history[-4:]) if history else ""
    full_question = f"{context}\nUser: {body.question}" if context else body.question
    # answer = llm_ask(full_question)
    if settings.openai_api_key:
        answer = llm_ask(body.question, history=history)
    else:
        answer = llm_ask(full_question)


    # Lưu vào Redis
    if r:
        r.rpush(history_key, f"User: {body.question}")
        r.rpush(history_key, f"Agent: {answer}")
        r.expire(history_key, 24 * 3600)  # 24h TTL

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "q_len": len(body.question),
    }))

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_id=body.user_id,
    )



@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Platform restarts container if this fails."""
    status = "ok"
    checks = {"llm": "mock" if not settings.openai_api_key else "openai"}
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Load balancer stops routing here if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "daily_cost_usd": round(_daily_cost, 4),
        "daily_budget_usd": settings.daily_budget_usd,
        "budget_used_pct": round(_daily_cost / settings.daily_budget_usd * 100, 1),
    }

from fastapi.responses import HTMLResponse

@app.get("/chat", response_class=HTMLResponse, tags=["Demo"])
def chat_ui():
    api_key = settings.agent_api_key
    return f"""<!DOCTYPE html>
<html>
<head>
  <title>AI Agent Demo</title>
  <style>
    body {{ font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; }}
    #messages {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px;
                height: 400px; overflow-y: auto; margin-bottom: 12px; background: #fafafa; }}
    .user {{ text-align: right; margin: 8px 0; }}
    .user span {{ background: #0070f3; color: white; padding: 8px 12px;
                 border-radius: 12px 12px 2px 12px; display: inline-block; max-width: 80%; }}
    .agent {{ text-align: left; margin: 8px 0; }}
    .agent span {{ background: #e5e5e5; padding: 8px 12px;
                  border-radius: 12px 12px 12px 2px; display: inline-block; max-width: 80%; }}
    #input-row {{ display: flex; gap: 8px; }}
    input {{ flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }}
    button {{ padding: 10px 20px; background: #0070f3; color: white;
              border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }}
    button:disabled {{ background: #999; }}
  </style>
</head>
<body>
  <h2>AI Agent Demo</h2>
  <div id="messages"></div>
  <div id="input-row">
    <input id="q" placeholder="Nhập câu hỏi..." onkeydown="if(event.key==='Enter')send()">
    <button id="btn" onclick="send()">Gửi</button>
  </div>
  <script>
    const API_KEY = "{api_key}";
    const USER_ID = "demo-" + Math.random().toString(36).slice(2,8);

    async function send() {{
      const input = document.getElementById("q");
      const btn = document.getElementById("btn");
      const question = input.value.trim();
      if (!question) return;

      addMessage(question, "user");
      input.value = "";
      btn.disabled = true;

      try {{
        const res = await fetch("/ask", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json", "X-API-Key": API_KEY }},
          body: JSON.stringify({{ question, user_id: USER_ID }})
        }});
        const data = await res.json();
        addMessage(res.ok ? data.answer : (data.detail || "Error"), "agent");
      }} catch(e) {{
        addMessage("Connection error", "agent");
      }}
      btn.disabled = false;
      input.focus();
    }}

    function addMessage(text, role) {{
      const div = document.getElementById("messages");
      div.innerHTML += `<div class="${{role}}"><span>${{text}}</span></div>`;
      div.scrollTop = div.scrollHeight;
    }}
  </script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
