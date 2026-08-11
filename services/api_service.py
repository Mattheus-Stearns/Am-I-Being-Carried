# services/api_service.py
import requests
import os
import json
from config import Config

def fetch_player_data(platform, username):
    """Fetch player data from API"""
    api_key = Config.API_KEY
    if not api_key:
        return None, 'API_KEY not configured', 500
    
    # ============================================
    # DEBUG: Log exactly what we're sending
    # ============================================
    print("="*60)
    print("🔍 API REQUEST DEBUG")
    print("="*60)
    print(f"Platform: {platform}")
    print(f"Username: {username}")
    
    # Build the URL with params
    url = "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_sessions"
    params = {
        "platform": platform,
        "username": username
    }
    headers = {
        "X-API-Key": api_key,
        "API-Snapshot-Version": "6",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"Headers: {headers}")
    print("="*60)
    
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body (first 500 chars): {response.text[:500]}")
        print("="*60)
        
        # Handle response
        if response.status_code == 200:
            try:
                data = response.json()
                if 'items' in data:
                    return data, None, 200
                else:
                    return None, 'No items in response', 422
            except json.JSONDecodeError:
                return None, 'Invalid JSON response', 502
        else:
            return None, f'API returned {response.status_code}', response.status_code
            
    except Exception as e:
        print(f"Exception: {e}")
        return None, str(e), 500