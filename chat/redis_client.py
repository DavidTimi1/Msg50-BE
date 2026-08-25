import logging
import redis.asyncio as aioredis
from django.conf import settings

logger = logging.getLogger(__name__)

REDIS_URL = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')

try:
    pool = aioredis.ConnectionPool.from_url(
        REDIS_URL,
        decode_responses=True,
        max_connections=20,
        socket_timeout=5,
        retry_on_timeout=True
    )
    redis_client = aioredis.Redis(connection_pool=pool)
except Exception as e:
    logger.error(f"Failed to initialize Redis ConnectionPool: {e}")
    redis_client = None