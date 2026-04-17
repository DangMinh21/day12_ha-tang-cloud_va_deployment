import time
from datetime import datetime
import redis as redis_lib
from fastapi import HTTPException, Depends
from app.config import settings
from app.auth import verify_api_key

COST_PER_REQUEST = 0.001  # $0.001 mỗi request (mock estimate)
MONTHLY_BUDGET = 10.0     # $10/tháng

def get_redis():
    if settings.redis_url:
        return redis_lib.from_url(settings.redis_url, decode_responses=True)
    return None

def check_budget(api_key: str = Depends(verify_api_key)):
    r = get_redis()
    if r is None:
        return  # skip if no Redis (dev mode)

    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{api_key[:8]}:{month_key}"

    current = float(r.get(key) or 0)
    if current + COST_PER_REQUEST > MONTHLY_BUDGET:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly budget ${MONTHLY_BUDGET} exceeded. Resets next month.",
        )

    r.incrbyfloat(key, COST_PER_REQUEST)
    r.expire(key, 33 * 24 * 3600)  # 33 days TTL
