# Deployment Information

## Public URL
https://dangvanminh-2a202600027-production.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://dangvanminh-2a202600027-production.up.railway.app/health
# Expected: {"status": "ok", "environment": "production", ...}
```

### API Test — No key (expect 401)
```bash
curl -X POST https://dangvanminh-2a202600027-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello", "user_id": "test"}'
# Expected: {"detail": "Invalid or missing API key..."}
```

### API Test — With key (expect 200)
```bash
curl -X POST https://dangvanminh-2a202600027-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "My name is Alice", "user_id": "user1"}'
```

### Rate Limit Test (expect 429 after 10 requests)
```bash
for i in {1..15}; do
  echo -n "Request $i: "
  curl -s -o /dev/null -w "%{http_code}" \
    -X POST https://dangvanminh-2a202600027-production.up.railway.app/ask \
    -H "X-API-Key: my-secret-key-123" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"test\", \"user_id\": \"ratetest\"}"
  echo ""
done
```

## Environment Variables Set
- `ENVIRONMENT` = production
- `AGENT_API_KEY` = (set)
- `RATE_LIMIT_PER_MINUTE` = 10
- `REDIS_URL` = (Railway Redis internal URL)
- `JWT_SECRET` = (set)

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
