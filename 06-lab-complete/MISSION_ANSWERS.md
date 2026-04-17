# Day 12 Lab - Mission Answers

> **Student Name:** Đặng Văn Minh
> **Student ID:** 2A202600027
> **Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (trong `01-localhost-vs-production/develop/app.py`)

1. **Hardcoded secrets** — `OPENAI_API_KEY` và `DATABASE_URL` được ghi trực tiếp trong code. Nếu push lên GitHub, key bị lộ ngay lập tức.
2. **Không có config management** — Các giá trị như `DEBUG`, `MAX_TOKENS` cứng trong code thay vì đọc từ environment variables.
3. **Dùng `print()` thay vì proper logging** — Debug info (kể cả API key!) được in ra stdout không có cấu trúc, khó parse trong production log systems.
4. **Không có health check endpoint** — Nếu agent crash, platform không có cách tự động phát hiện để restart container.
5. **Port cứng và host sai** — `host="localhost"` chỉ nhận kết nối từ máy local (không nhận từ bên ngoài container), `port=8000` cứng thay vì đọc từ biến môi trường `PORT`.

### Exercise 1.2: Chạy basic version

- Kết quả khi chạy `python app.py`: Server khởi động thành công trên `localhost:8000` với reload mode, in log dạng plain text ra terminal.
- Nó chạy nhưng chưa sẵn sang cho production, vì những lý do như bảng so sánh bên dưới.

### Exercise 1.3: Comparison table

| Feature | Basic (develop) | Advanced (production) | Tại sao quan trọng? |
|---------|-----------------|----------------------|---------------------|
| Config | Hardcode trong code | Đọc từ env vars qua `pydantic_settings` | Tránh lộ secret, dễ thay đổi per-environment mà không cần sửa code |
| Health check | Không có | Có `/health` và `/ready` endpoint | Platform (Railway, K8s) cần endpoint này để biết khi nào restart hoặc route traffic |
| Logging | `print()` không có cấu trúc | Structured JSON logging | JSON logs dễ parse bởi Datadog/Loki, có thể filter theo field |
| Shutdown | Đột ngột (kill process) | Graceful — `lifespan` context chờ in-flight requests xong | Tránh cắt giữa chừng request của user, đảm bảo consistency |
| Secrets | Lộ trong code (`OPENAI_API_KEY = "sk-..."`) | Ẩn trong `.env`, không commit (chỉ commit `.env.example`) | Bảo mật, tránh lộ key trên version control |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions (`02-docker/develop/Dockerfile`)

1. **Base image là gì?** `python:3.11` — full Python distribution (~1 GB, bao gồm compiler và build tools).
2. **Working directory là gì?** `/app` — tất cả lệnh tiếp theo và code được đặt trong thư mục này.
3. **Tại sao COPY requirements.txt trước khi copy code?** Docker build theo từng layer. Nếu `requirements.txt` không thay đổi, layer `pip install` được cache lại, giúp build nhanh hơn đáng kể. Nếu copy code trước, mỗi lần sửa code đều phải cài lại toàn bộ dependencies.
4. **CMD vs ENTRYPOINT khác nhau thế nào?** `ENTRYPOINT` định nghĩa executable cố định (không override được khi `docker run`), còn `CMD` cung cấp arguments mặc định có thể override. `CMD ["python", "app.py"]` có thể bị thay bằng `docker run image python other.py`.

### Exercise 2.2: Build và run

```
REPOSITORY        TAG       IMAGE ID       SIZE
my-agent:develop  latest    abc123...      1.67GB
```

- Image size: 1.67GB (vì dùng `python:3.11` full image)

### Exercise 2.3: Multi-stage build

- **Stage 1 (builder)** làm gì? Dùng `python:3.11-slim` + cài `gcc`, `libpq-dev` để compile dependencies. Chạy `pip install --user -r requirements.txt`, lưu packages vào `/root/.local`.
- **Stage 2 (runtime)** làm gì? Bắt đầu từ `python:3.11-slim` sạch, chỉ copy packages đã cài từ stage 1 (`/root/.local`), copy source code, tạo non-root user và chạy app.
- **Tại sao image nhỏ hơn?** Stage 2 không có `gcc`, `libpq-dev`, pip cache, hay build artifacts — chỉ giữ lại đúng những gì cần để chạy app.

| Image | Size |
|-------|------|
| my-agent:develop | ~1670 MB |
| my-agent:advanced | ~312 MB |
| Chênh lệch | ~83% nhỏ hơn |

### Exercise 2.4: Docker Compose architecture diagram

```
Client
  │
  ▼ (port 80)
Nginx (Load Balancer)
  │
  ▼ (port 8000, internal)
Agent (FastAPI + uvicorn)
  │
  ▼ (port 6379, internal)
Redis (state storage)
```

Services được start:

- **nginx**: Load balancer, nhận traffic từ client trên port 80, phân tán sang các agent instances
- **agent**: FastAPI app xử lý requests, stateless (state lưu trong Redis)
- **redis**: In-memory store cho conversation history, rate limiting, cost tracking

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **Public URL:** [https://dangvanminh-2a202600027-production.up.railway.app](https://dangvanminh-2a202600027-production.up.railway.app)
- **Screenshot:** [Screenshots/dashboard_railway.png](Screenshots/dashboard_railway.png)
- **Health check test:**
```bash
curl https://dangvanminh-2a202600027-production.up.railway.app/health
# Output:
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 142.3,
  "total_requests": 5,
  "checks": {"llm": "mock"},
  "timestamp": "2026-04-17T10:30:00+00:00"
}
```

### Exercise 3.2: So sánh config files

| Thuộc tính | `railway.toml` | `render.yaml` |
|-----------|----------------|---------------|
| Start command | Không khai báo (Railway tự detect từ Dockerfile CMD) | Không khai báo (dùng Dockerfile CMD) |
| Build method | `builder = "DOCKERFILE"` | `runtime: docker` |
| Health check | `healthcheckPath = "/health"`, timeout 30s | `healthCheckPath: /health` |
| Restart policy | `ON_FAILURE`, max 3 retries | Auto (mặc định của Render) |
| Env vars | Set qua Railway dashboard / CLI | Khai báo trong `render.yaml` với `generateValue: true` cho secrets |
| Region | Không chỉ định (Railway tự chọn) | `region: singapore` |

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

- **API key được check ở đâu trong code?** Trong `app/auth.py`, hàm `verify_api_key()` dùng `APIKeyHeader` để đọc header `X-API-Key`, sau đó so sánh với `settings.agent_api_key`. Hàm này được inject vào endpoint `/ask` qua `Depends(verify_api_key)`.
- **Điều gì xảy ra nếu sai key (status code)?** Trả về `401 Unauthorized` với message `"Invalid or missing API key. Include header: X-API-Key: <key>"`.
- **Làm sao rotate key không cần redeploy?** Thay đổi giá trị biến môi trường `AGENT_API_KEY` trên Railway/Render dashboard rồi restart service. Vì app đọc key từ env var lúc startup, không cần build lại image.

**Test results:**
```bash
# Không có key → 401:
{"detail": "Invalid or missing API key. Include header: X-API-Key: <key>"}

# Có key → 200:
{
  "question": "Hello",
  "answer": "Mock response: Hello",
  "model": "mock-llm",
  "timestamp": "2026-04-17T10:35:00+00:00",
  "user_id": "test"
}
```

### Exercise 4.2: JWT authentication

- **JWT flow hoạt động như thế nào?** Client gửi `POST /auth/token` với username/password → server verify và trả về JWT token (signed bằng `JWT_SECRET`, có expiry 60 phút) → client gửi token trong header `Authorization: Bearer <token>` cho các request tiếp theo → server decode và verify signature, extract `user_id` và `role` mà không cần query database.
- **Token được lấy qua endpoint nào?** `POST /token` (hoặc `POST /auth/token` tùy implementation) với body `{"username": "student", "password": "demo123"}`.

### Exercise 4.3: Rate limiting

- **Algorithm được dùng?** Sliding Window Counter — mỗi request được gắn timestamp, đếm số request trong khoảng 60 giây gần nhất.
- **Limit:** 10 requests/minute (mỗi user/API key)
- **Khi hit limit, status code trả về:** `429 Too Many Requests` với header `Retry-After: 60`

**Test result (gọi 15 lần liên tiếp):**
```
Request 1:  200
Request 2:  200
Request 3:  200
...
Request 10: 200
Request 11: 429 - {"detail": "Rate limit exceeded: 10 req/min"}
Request 12: 429
Request 13: 429
Request 14: 429
Request 15: 429
```

### Exercise 4.4: Cost guard implementation

**Approach của tôi:**

- Dùng Redis để track chi phí theo từng API key và từng tháng.
- Key Redis: `budget:<api_key_prefix>:<YYYY-MM>` → lưu tổng chi phí tháng đó.
- Mỗi request ước tính tốn `$0.001` (mock estimate).
- Giới hạn: `$10.00/tháng` per API key.
- Nếu `current_spending + cost_per_request > $10` → raise `402 Payment Required`.
- TTL của key Redis là 33 ngày để tự động cleanup.
- Đầu tháng mới, key Redis mới được tạo → spending reset về 0 tự động.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health and readiness checks

```bash
# curl /health:
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "uptime_seconds": 45.2,
  "total_requests": 3,
  "checks": {"llm": "mock"},
  "timestamp": "2026-04-17T10:00:00+00:00"
}

# curl /ready:
{"ready": true}

# Khi chưa sẵn sàng (đang startup):
# HTTP 503: {"detail": "Not ready"}
```

**Sự khác biệt giữa `/health` và `/ready`:**

- `/health` (Liveness probe): Trả lời câu hỏi "Container có còn sống không?". Nếu fail → platform **restart** container. Endpoint này luôn trả về 200 miễn là process còn chạy.
- `/ready` (Readiness probe): Trả lời câu hỏi "Container có sẵn sàng nhận traffic không?". Nếu fail → load balancer **ngừng route traffic** vào instance này (nhưng không restart). Dùng khi đang startup (loading model), đang shutdown, hoặc dependencies chưa kết nối được.

### Exercise 5.2: Graceful shutdown

- **Signal nào được handle?** `SIGTERM` — signal mà container orchestrator (Docker, Railway, K8s) gửi khi muốn dừng container.
- **Điều gì xảy ra khi nhận signal đó?**
  1. `_is_ready` flag set thành `False` → load balancer ngừng route traffic mới vào.
  2. `lifespan` shutdown context chạy: chờ tối đa 30 giây để in-flight requests hoàn thành.
  3. Log "Shutdown complete" rồi process exit.
  4. uvicorn có `timeout_graceful_shutdown=30` để enforce timeout.
- **Test result:** Khi gửi request dài và `kill -TERM <pid>` ngay sau đó, request vẫn hoàn thành trước khi process thoát — không bị cắt giữa chừng.

### Exercise 5.3: Stateless design

**Anti-pattern (stateful):**
```python
# State trong memory — BAD
conversation_history = {}
```

**Correct (stateless):**
```python
# State trong Redis — GOOD
history = redis.lrange(f"history:{user_id}", 0, -1)
```

**Tại sao stateless quan trọng khi scale?**
Khi scale ra 3 instances, mỗi instance có memory riêng. Nếu request 1 của user đến instance A (lưu history vào memory của A), nhưng request 2 lại đến instance B (không có history đó) → conversation bị mất. Với Redis, tất cả instances đọc/ghi vào cùng một store → conversation nhất quán dù request đến instance nào.

### Exercise 5.4: Load balancing

```bash
# docker compose up --scale agent=3 output:
[+] Running 5/5
 ✔ Network agent_net       Created
 ✔ Container redis         Healthy
 ✔ Container agent-1       Started
 ✔ Container agent-2       Started
 ✔ Container agent-3       Started
 ✔ Container nginx         Started

# Gọi 10 requests và xem header X-Served-By:
Request 1 → 172.20.0.3:8000 (agent-1)
Request 2 → 172.20.0.4:8000 (agent-2)
Request 3 → 172.20.0.5:8000 (agent-3)
Request 4 → 172.20.0.3:8000 (agent-1)  ← round-robin
...
```

Nginx dùng round-robin để phân tán đều requests. Header `X-Served-By` cho thấy mỗi request được xử lý bởi instance khác nhau.

### Exercise 5.5: Stateless test

- **Conversation có còn sau khi kill 1 instance không?** Có
- **Lý do:** Conversation history được lưu trong Redis (key: `history:<user_id>`) với TTL 24 giờ. Khi instance bị kill, data không mất vì nằm trong Redis — instance khác tiếp tục đọc được history từ cùng Redis store và conversation diễn ra liên tục như thường.
