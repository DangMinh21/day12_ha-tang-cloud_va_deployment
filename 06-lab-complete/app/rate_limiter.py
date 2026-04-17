import time
import redis as redis_lib
from fastapi import HTTPException, Depends
from app.config import settings
from app.auth import verify_api_key

def get_redis():
    if settings.redis_url:
        return redis_lib.from_url(settings.redis_url, decode_responses=True)
    return None

def check_rate_limit(api_key: str = Depends(verify_api_key)):
    r = get_redis()
    now = time.time()
    window = 60
    limit = settings.rate_limit_per_minute

    if r is None:
        return  # skip if no Redis (dev mode)

    key = f"rate:{api_key[:8]}"
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    results = pipe.execute()

    count = results[2]
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} req/min",
            headers={"Retry-After": "60"},
        )
