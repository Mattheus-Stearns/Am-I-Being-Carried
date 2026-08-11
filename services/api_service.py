# services/api_service.py
import requests
import os
import json
from config import Config

def fetch_player_data(platform, username):
    """Fetch player data from API"""
    api_key = Config.API_KEY
    
    if not api_key:
        print("❌ API_KEY not configured")
        return None, 'API_KEY not configured', 500
    
    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"🔍 Fetching: {platform}/{username}")
    
    headers = {
        "X-API-Key": api_key,
        "API-Snapshot-Version": "6"
    }
    
    try:
        response = requests.get(
            "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_sessions",
            headers=headers,
            params={
                "platform": platform,
                "username": username
            },
            timeout=30
        )
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"📊 Response type: {type(data)}")
                print(f"📊 Response keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                print(f"📊 Full response (first 1000 chars): {json.dumps(data, indent=2)[:1000]}")
                
                # Check for the actual data structure
                if 'data' in data:
                    actual_data = data['data']
                    print(f"📊 Found 'data' key with items: {'items' in actual_data}")
                    if 'items' in actual_data:
                        item_count = len(actual_data['items'])
                        print(f"📊 Items count: {item_count}")
                        if item_count > 0:
                            return actual_data, None, 200
                        else:
                            print("⚠️ Items array is empty!")
                            return None, f'No data found for {username} on {platform}', 422
                    else:
                        print("⚠️ No 'items' in data.data")
                        return None, 'Invalid response structure', 422
                elif 'items' in data:
                    item_count = len(data['items'])
                    print(f"📊 Items count: {item_count}")
                    if item_count > 0:
                        return data, None, 200
                    else:
                        print("⚠️ Items array is empty!")
                        return None, f'No data found for {username} on {platform}', 422
                else:
                    print("⚠️ No 'items' in response")
                    return None, 'Invalid response structure', 422
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                return None, 'Invalid JSON response', 502
        else:
            print(f"❌ API error: {response.status_code} - {response.text[:200]}")
            return None, f'API error: {response.status_code}', response.status_code
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None, str(e), 500