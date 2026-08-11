# services/cache_service.py
from extensions import redis_client, db
from models import PlayerProfile
from datetime import datetime, timezone, timedelta
import json
from flask import session

WHITELIST_KEY = 'authorized_ips'

def get_cached_data(platform, username):
    """Get cached data from Redis or database"""
    # Try session first
    session_data = session.get('api_data')
    session_platform = session.get('platform')
    session_username = session.get('username')
    
    if session_data and session_platform == platform and session_username == username:
        return session_data
    
    # Try database
    profile = PlayerProfile.query.filter_by(
        platform=platform,
        username=username
    ).first()
    
    if profile:
        # ============================================
        # FIX: Use timezone-aware datetime for comparison
        # ============================================
        # Get current UTC time (aware)
        now = datetime.now(timezone.utc)
        
        # Ensure updated_at is timezone-aware
        if profile.updated_at.tzinfo is None:
            updated_at = profile.updated_at.replace(tzinfo=timezone.utc)
        else:
            updated_at = profile.updated_at
        
        time_since_update = now - updated_at
        
        if time_since_update < timedelta(hours=24):
            return profile.data
    
    
    return None

def save_cached_data(platform, username, data):
    """Save data to cache"""
    # Update database
    profile = PlayerProfile.query.filter_by(
        platform=platform,
        username=username
    ).first()
    
    if profile:
        profile.data = data
        profile.updated_at = datetime.now(timezone.utc)
        profile.last_accessed = datetime.now(timezone.utc)
        profile.api_call_count += 1
    else:
        profile = PlayerProfile(
            platform=platform,
            username=username,
            data=data,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc)
        )
        db.session.add(profile)
    
    db.session.commit()
    return True

def load_authorized_ips():
    """Load authorized IPs from config into Redis"""
    from config import Config
    
    ips = Config.AUTHORIZED_IPS
    
    if not redis_client:
        print("⚠️ Redis not available. Cannot load authorized IPs.")
        return ips
    
    try:
        redis_client.delete(WHITELIST_KEY)
        if ips:
            redis_client.sadd(WHITELIST_KEY, *ips)
            print(f"✅ Loaded {len(ips)} authorized IPs")
            print(f"   IPs: {ips}")
        else:
            print("ℹ️ No authorized IPs found")
    except Exception as e:
        print(f"❌ Failed to load authorized IPs: {e}")
    
    return ips

def is_ip_authorized(ip):
    """Check if IP is authorized"""
    if not ip or not redis_client:
        return False
    try:
        return redis_client.sismember(WHITELIST_KEY, ip)
    except Exception:
        return False

def log_api_call(platform, username, success, response_code, error_message=None, response_size=0):
    """Log API call to database"""
    from models import APICallLog
    from utils.helpers import get_client_ip
    
    try:
        log = APICallLog(
            platform=platform,
            username=username,
            success=success,
            response_code=response_code,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc),
            response_size=response_size,
            ip_address=get_client_ip()
        )
        db.session.add(log)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Failed to log API call: {e}")
        db.session.rollback()
        return False