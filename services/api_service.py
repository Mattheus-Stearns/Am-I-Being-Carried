# services/api_service.py
import requests
import os
import time
from config import Config

def fetch_player_data(platform, username):
    """Fetch player data from API with retry logic"""
    api_key = Config.API_KEY
    if not api_key:
        return None, 'API_KEY not configured', 500
    
    import urllib.parse
    encoded_username = urllib.parse.quote(username)
    
    max_retries = 3
    retry_delays = [1, 2, 5]
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_sessions",
                headers={
                    "X-API-Key": api_key,
                    "API-Snapshot-Version": "6"
                },
                params={
                    "platform": platform,
                    "username": encoded_username
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json(), None, 200
            elif response.status_code in [429, 502, 503, 504]:
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
                return None, f'API error: {response.status_code}', response.status_code
            else:
                return None, f'API error: {response.status_code}', response.status_code
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue
            return None, 'Request timeout', 408
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue
            return None, str(e), 500
    
    return None, 'Max retries exceeded', 500