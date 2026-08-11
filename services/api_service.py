# services/api_service.py
import requests
import os
import time
import json
from config import Config

def fetch_player_data(platform, username):
    """Fetch player data from API with improved error handling"""
    api_key = Config.API_KEY
    if not api_key:
        return None, 'API_KEY not configured', 500
    
    import urllib.parse
    encoded_username = urllib.parse.quote(username)
    
    # Validate platform
    valid_platforms = ['epic', 'steam', 'psn', 'xbox', 'switch']
    if platform not in valid_platforms:
        return None, f'Invalid platform: {platform}', 422
    
    try:
        response = requests.get(
            "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_sessions",
            headers={
                "X-API-Key": api_key,
                "API-Snapshot-Version": "6",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            params={
                "platform": platform,
                "username": encoded_username
            },
            timeout=30
        )
        
        # Handle response
        if response.status_code == 200:
            try:
                data = response.json()
                if 'items' in data:
                    return data, None, 200
                else:
                    return None, 'Invalid response format', 422
            except json.JSONDecodeError:
                return None, 'Invalid JSON response', 502
                
        elif response.status_code == 422:
            return None, f'Player not found on {platform}', 422
            
        elif response.status_code == 429:
            return None, 'Rate limit exceeded', 429
            
        elif response.status_code in [502, 503, 504]:
            return None, f'API server error: {response.status_code}', response.status_code
            
        else:
            return None, f'API returned {response.status_code}', response.status_code
            
    except requests.exceptions.Timeout:
        return None, 'Request timeout', 408
        
    except requests.exceptions.ConnectionError:
        return None, 'Connection error', 503
        
    except Exception as e:
        return None, str(e), 500