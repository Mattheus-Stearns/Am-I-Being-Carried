# utils/helpers.py
from flask import request
import hashlib

def get_client_ip():
    """Get client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return ip
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def hash_string(string):
    """Hash a string for consistent keys"""
    return hashlib.sha256(string.encode()).hexdigest()[:16]

def get_steam_error_message(username):
    """Generate a special error message for Steam users"""
    steam_profile_url = f"https://steamcommunity.com/id/{username}"
    
    return {
        "message": f'Player "{username}" not found on Steam.',
        "suggestion": f"""
            <div class="steam-error-help">
                <p>If you're sure this is the correct Steam profile, try:</p>
                <ol>
                    <li>Checking the <strong>custom URL</strong> on their Steam profile</li>
                    <li>Using their <strong>Steam ID (17-digit number)</strong> instead</li>
                    <li>Verifying they have played <strong>competitive Rocket League</strong> matches</li>
                </ol>
                <p class="mt-2">
                    <i class="fas fa-info-circle"></i> 
                    Steam profile URL format: 
                    <code>https://steamcommunity.com/id/{username}</code>
                </p>
                <a href="{steam_profile_url}" target="_blank" class="btn btn-sm btn-outline-primary mt-1">
                    <i class="fas fa-external-link-alt"></i> Check on Steam
                </a>
            </div>
        """,
        "show_steam_help": True
    }