# Day 12 Lab - Mission Answers

> **Student Name:** _________________________  
> **Student ID:** _________________________  
> **Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (trong `01-localhost-vs-production/develop/app.py`)

1. [Điền anti-pattern 1 — ví dụ: hardcoded API key]
2. [Điền anti-pattern 2]
3. [Điền anti-pattern 3]
4. [Điền anti-pattern 4]
5. [Điền anti-pattern 5]

### Exercise 1.2: Chạy basic version

- Kết quả khi chạy `python app.py`: [Mô tả ngắn]
- Kết quả curl test: [Paste output]

### Exercise 1.3: Comparison table

| Feature | Basic (develop) | Advanced (production) | Tại sao quan trọng? |
|---------|-----------------|----------------------|---------------------|
| Config | Hardcode trong code | Đọc từ env vars | [Giải thích] |
| Health check | Không có | Có `/health` endpoint | [Giải thích] |
| Logging | `print()` | Structured JSON logging | [Giải thích] |
| Shutdown | Đột ngột (kill) | Graceful — hoàn thành request trước | [Giải thích] |
| Secrets | Lộ trong code | Ẩn trong `.env`, không commit | [Giải thích] |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions (`02-docker/develop/Dockerfile`)

1. **Base image là gì?** [Trả lời]
2. **Working directory là gì?** [Trả lời]
3. **Tại sao COPY requirements.txt trước khi copy code?** [Trả lời]
4. **CMD vs ENTRYPOINT khác nhau thế nào?** [Trả lời]

### Exercise 2.2: Build và run

```
# Paste output của: docker images my-agent:develop
```

- Image size: [X] MB

### Exercise 2.3: Multi-stage build

- Stage 1 làm gì? [Trả lời]
- Stage 2 làm gì? [Trả lời]
- Tại sao image nhỏ hơn? [Trả lời]

| Image | Size |
|-------|------|
| my-agent:develop | [X] MB |
| my-agent:advanced | [Y] MB |
| Chênh lệch | [Z]% |

### Exercise 2.4: Docker Compose architecture diagram

```
[Vẽ diagram — ví dụ:]
Client → Nginx (port 80) → Agent (port 8000) → Redis (port 6379)
```

Services được start:
- [Service 1]: [Vai trò]
- [Service 2]: [Vai trò]
- [Service 3]: [Vai trò]

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **Public URL:** https://[your-app].railway.app
- **Screenshot:** [Link ảnh trong repo hoặc mô tả]
- **Health check test:**
```bash
# Paste output của: curl https://your-app.railway.app/health
```

### Exercise 3.2: So sánh config files

| Thuộc tính | `railway.toml` | `render.yaml` |
|-----------|----------------|---------------|
| Start command | [Điền] | [Điền] |
| Port config | [Điền] | [Điền] |
| Env vars | [Điền] | [Điền] |

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

- API key được check ở đâu trong code? [Trả lời]
- Điều gì xảy ra nếu sai key (status code)? [Trả lời]
- Làm sao rotate key không cần redeploy? [Trả lời]

**Test results:**
```bash
# Không có key → 401:
[Paste output]

# Có key → 200:
[Paste output]
```

### Exercise 4.2: JWT authentication

- JWT flow hoạt động như thế nào? [Mô tả ngắn]
- Token được lấy qua endpoint nào? [Trả lời]

### Exercise 4.3: Rate limiting

- Algorithm được dùng? [Token bucket / Sliding window / ...]
- Limit: [X] requests/minute
- Khi hit limit, status code trả về: [Trả lời]

**Test result (gọi 20 lần liên tiếp):**
```
[Paste output hoặc mô tả kết quả]
```

### Exercise 4.4: Cost guard implementation

**Approach của tôi:**
[Giải thích logic bạn implement — tracking bằng gì, reset khi nào, giới hạn bao nhiêu]

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health and readiness checks

```bash
# curl /health:
[Paste output]

# curl /ready:
[Paste output]
```

Sự khác biệt giữa `/health` và `/ready`: [Giải thích]

### Exercise 5.2: Graceful shutdown

- Signal nào được handle? [Trả lời]
- Điều gì xảy ra khi nhận signal đó? [Trả lời]
- Test result: [Mô tả quan sát]

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

Tại sao stateless quan trọng khi scale? [Giải thích]

### Exercise 5.4: Load balancing

```bash
# docker compose up --scale agent=3 output:
[Mô tả hoặc paste logs]
```

### Exercise 5.5: Stateless test

- Conversation có còn sau khi kill 1 instance không? [Có/Không]
- Lý do: [Giải thích]
