import requests
import os
import json
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

class BallChasingDownloader:
    """Download replay files from BallChasing.com API"""
    
    def __init__(self, api_key: str, output_dir: str = "data/raw"):
        self.api_key = api_key
        self.base_url = "https://ballchasing.com/api"
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": api_key,
            "Content-Type": "application/json"
        })
        os.makedirs(output_dir, exist_ok=True)
        
    def search_replays(self, 
                       game_mode: str = "3v3",  # "2v2", "3v3", "1v1"
                       min_rank: int = None,    # 0-21 (Unranked to SSL)
                       max_rank: int = None,
                       min_date: str = None,    # "2024-01-01"
                       max_date: str = None,
                       limit: int = 10,
                       page: int = 1) -> List[Dict]:
        """Search for replays matching criteria"""
        
        params = {
            "playlist": game_mode,
            "limit": min(limit, 100),  # API max is 100 per page
            "page": page
        }
        
        # Add rank filters
        rank_map = {
            "Unranked": 0, "Bronze I": 1, "Bronze II": 2, "Bronze III": 3,
            "Silver I": 4, "Silver II": 5, "Silver III": 6,
            "Gold I": 7, "Gold II": 8, "Gold III": 9,
            "Platinum I": 10, "Platinum II": 11, "Platinum III": 12,
            "Diamond I": 13, "Diamond II": 14, "Diamond III": 15,
            "Champion I": 16, "Champion II": 17, "Champion III": 18,
            "Grand Champion I": 19, "Grand Champion II": 20,
            "Grand Champion III": 21, "Supersonic Legend": 22
        }
        
        # API uses rank names, not numbers
        if min_rank is not None:
            # Convert min_rank to rank name - we'll search by season rank
            pass
            
        try:
            response = self.session.get(
                f"{self.base_url}/replays",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return data.get("list", [])
            
        except requests.exceptions.RequestException as e:
            print(f" Error searching replays: {e}")
            return []
    
    def download_replay(self, replay_id: str, output_path: str = None) -> Optional[str]:
        """Download a single replay file"""
        
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"{replay_id}.replay")
            
        try:
            # First get the replay info
            info_response = self.session.get(
                f"{self.base_url}/replays/{replay_id}"
            )
            info_response.raise_for_status()
            replay_info = info_response.json()
            
            # Download the actual replay file
            download_url = replay_info.get("file", {}).get("link")
            if not download_url:
                print(f" No download link for replay {replay_id}")
                return None
                
            # Download the file
            file_response = requests.get(download_url, stream=True)
            file_response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            print(f" Downloaded: {replay_id} -> {output_path}")
            
            # Save metadata alongside the replay
            metadata_path = output_path.replace('.replay', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(replay_info, f, indent=2)
                
            return output_path
            
        except Exception as e:
            print(f" Error downloading {replay_id}: {e}")
            return None
    
    def download_replays_batch(self, 
                              game_mode: str = "3v3",
                              count: int = 10,
                              rank_filter: str = None) -> List[str]:
        """Download multiple replays matching criteria"""
        
        downloaded = []
        page = 1
        
        while len(downloaded) < count:
            # Search for replays
            replays = self.search_replays(
                game_mode=game_mode,
                limit=min(100, count - len(downloaded)),
                page=page
            )
            
            if not replays:
                print(f"️ No more replays found on page {page}")
                break
                
            # Download each replay
            for replay in replays:
                if len(downloaded) >= count:
                    break
                    
                replay_id = replay.get("id")
                if replay_id:
                    # Check if already downloaded
                    existing_path = os.path.join(
                        self.output_dir, f"{replay_id}.replay"
                    )
                    if os.path.exists(existing_path):
                        print(f"️ Skipping {replay_id} (already downloaded)")
                        downloaded.append(existing_path)
                        continue
                        
                    # Download the replay
                    file_path = self.download_replay(replay_id)
                    if file_path:
                        downloaded.append(file_path)
                        
                    # Rate limiting - don't hammer the API
                    time.sleep(1)
                    
            page += 1
            
        print(f"\n Downloaded {len(downloaded)} replays")
        return downloaded