import os
import redis.asyncio as aioredis
from django.conf import settings

REDIS_URL = getattr(settings, 'REDIS_URL', '')

redis_client = aioredis.from_url(
    REDIS_URL,
    decode_responses=True,
)