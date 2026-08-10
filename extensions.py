# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
import redis
import os
import hashlib
from flask import session, request

# Database
db = SQLAlchemy()

# Rate Limiter
limiter = Limiter(
    key_func=lambda: get_remote_address(),
    default_limits=["100 per day", "20 per hour"],
    storage_uri="memory://",
)

# Migrate
migrate = Migrate()

# Redis
redis_client = None
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True,
        socket_connect_timeout=5
    )
    redis_client.ping()
    print("✅ Redis connected")
except:
    print("⚠️ Redis not available")