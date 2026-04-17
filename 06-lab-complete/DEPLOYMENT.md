# Deployment Information

| Thông tin | |
| --- | --- |
| **Họ và tên** | Đặng Văn Minh |
| **MSSV** | 2A202600027 |
| **Platform** | Railway |
| **Public URL** | [dangvanminh-2a202600027-production.up.railway.app](https://dangvanminh-2a202600027-production.up.railway.app) |
| **Chat UI** | [/chat](https://dangvanminh-2a202600027-production.up.railway.app/chat) |
| **Ngày deploy** | 17/04/2026 |

---

## Environment Variables đã set trên Railway

| Variable | Giá trị |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `AGENT_API_KEY` | *(set, không public)* |
| `REDIS_URL` | *(Railway Redis internal URL)* |
| `JWT_SECRET` | *(set, không public)* |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `DAILY_BUDGET_USD` | `5.0` |

---

## Test Commands (Production)

### 1. Health check

```bash
curl https://dangvanminh-2a202600027-production.up.railway.app/health
```

Expected response:

```json
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

### 2. Readiness check

```bash
curl https://dangvanminh-2a202600027-production.up.railway.app/ready
```

Expected: `{"ready": true}`

### 3. Authentication required (expect 401)

```bash
curl -X POST https://dangvanminh-2a202600027-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "test"}'
```

Expected: `{"detail": "Invalid or missing API key. Include header: X-API-Key: <key>"}`

### 4. Gọi API với key hợp lệ (expect 200)

```bash
curl -X POST https://dangvanminh-2a202600027-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?", "user_id": "user1"}'
```

Expected:

```json
{
  "question": "What is Docker?",
  "answer": "...",
  "model": "mock-llm",
  "timestamp": "2026-04-17T10:35:00+00:00",
  "user_id": "user1"
}
```

### 5. Conversation history (stateless test)

```bash
# Request 1
curl -X POST https://dangvanminh-2a202600027-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "My name is Alice", "user_id": "conv-test"}'

# Request 2 — agent nhớ context từ Redis
curl -X POST https://dangvanminh-2a202600027-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is my name?", "user_id": "conv-test"}'
```

### 6. Rate limiting (expect 429 sau request thứ 11)

```bash
for i in {1..15}; do
  echo -n "Request $i: "
  curl -s -o /dev/null -w "%{http_code}" \
    -X POST https://dangvanminh-2a202600027-production.up.railway.app/ask \
    -H "X-API-Key: my-secret-key-123" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"test $i\", \"user_id\": \"ratetest\"}"
  echo ""
done
```

Expected output:

```text
Request 1:  200
Request 2:  200
...
Request 10: 200
Request 11: 429
Request 12: 429
...
```

---

## Test Commands (Local)

```bash
cd 06-lab-complete
cp .env.example .env.local
# Điền AGENT_API_KEY vào .env.local

# Chạy full stack
docker compose up

# Test qua Nginx (port 80)
curl http://localhost/health
curl http://localhost/ready

curl -X POST http://localhost/ask \
  -H "X-API-Key: my-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "local-test"}'

# Scale lên 3 instances
docker compose up --scale agent=3

# Xem instance nào xử lý (load balancing)
curl -I http://localhost/health | grep X-Served-By
```

---

## Screenshots

| | |
| --- | --- |
| Railway Dashboard | ![Dashboard](Screenshots/dashboard_railway.png) |
| Test kết quả | ![Test](Screenshots/test_url.png) |
