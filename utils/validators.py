# utils/validators.py
import re

VALID_PLATFORMS = ['epic', 'steam', 'psn', 'xbox', 'switch']

def validate_platform(platform):
    """Validate platform"""
    if not platform:
        return False, 'Platform is required'
    if platform not in VALID_PLATFORMS:
        return False, f"Invalid platform. Must be one of: {', '.join(VALID_PLATFORMS)}"
    return True, None

def validate_username(username):
    """Validate username"""
    if not username:
        return False, 'Username is required'
    if len(username) < 2:
        return False, 'Username must be at least 2 characters'
    if len(username) > 100:
        return False, 'Username must be less than 100 characters'
    if not re.match(r'^[a-zA-Z0-9_.\- ]+$', username):
        return False, 'Username contains invalid characters'
    return True, None