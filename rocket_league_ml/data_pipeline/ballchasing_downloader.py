# data_pipeline/ballchasing_downloader.py

import requests
import os
import json
import time
from typing import List, Dict, Optional
from datetime import datetime

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
        
        # Map game modes to API playlist STRINGS (from documentation)
        self.playlist_map = {
            "1v1": "ranked-duels",
            "2v2": "ranked-doubles", 
            "3v3": "ranked-standard",
            "1v1_unranked": "unranked-duels",
            "2v2_unranked": "unranked-doubles",
            "3v3_unranked": "unranked-standard",
            "hoops": "hoops",
            "rumble": "rumble",
            "dropshot": "dropshot",
            "snowday": "snowday",
            "tournament": "tournament"
        }
        
        # Map ranks to API rank strings
        self.rank_map = {
            "unranked": "unranked",
            "bronze_1": "bronze-1",
            "bronze_2": "bronze-2",
            "bronze_3": "bronze-3",
            "silver_1": "silver-1",
            "silver_2": "silver-2",
            "silver_3": "silver-3",
            "gold_1": "gold-1",
            "gold_2": "gold-2",
            "gold_3": "gold-3",
            "platinum_1": "platinum-1",
            "platinum_2": "platinum-2",
            "platinum_3": "platinum-3",
            "diamond_1": "diamond-1",
            "diamond_2": "diamond-2",
            "diamond_3": "diamond-3",
            "champion_1": "champion-1",
            "champion_2": "champion-2",
            "champion_3": "champion-3",
            "grand_champion_1": "grand-champion",
            "grand_champion_2": "grand-champion",
            "grand_champion_3": "grand-champion",
            "supersonic_legend": "grand-champion"
        }
    
    def search_replays(self, 
                       game_mode: str = None,
                       min_rank: str = None,
                       max_rank: str = None,
                       season: str = None,
                       min_date: str = None,
                       max_date: str = None,
                       sort_by: str = "replay-date",
                       sort_dir: str = "desc",
                       limit: int = 100,
                       page: int = 1) -> List[Dict]:
        """
        Search for replays matching criteria
        """
        params = {}
        
        if game_mode and game_mode in self.playlist_map:
            params["playlist"] = self.playlist_map[game_mode]
        if min_rank:
            params["min-rank"] = self.rank_map.get(min_rank, min_rank)
        if max_rank:
            params["max-rank"] = self.rank_map.get(max_rank, max_rank)
        if season:
            params["season"] = season
        if min_date:
            params["replay-date-after"] = min_date
        if max_date:
            params["replay-date-before"] = max_date
        if sort_by:
            params["sort-by"] = sort_by
        if sort_dir:
            params["sort-dir"] = sort_dir
        
        params["limit"] = min(limit, 200)
        params["page"] = page
        
        try:
            print(f"🔍 Searching page {page}")
            response = self.session.get(
                f"{self.base_url}/replays",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if "list" in data:
                replays = data["list"]
                print(f"📊 Found {len(replays)} replays on page {page}")
                return replays
            elif isinstance(data, list):
                print(f"📊 Found {len(data)} replays on page {page}")
                return data
            else:
                print(f"⚠️ Unexpected response format")
                return []
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error searching replays: {e}")
            return []
    
    def download_replay(self, replay_id: str, output_path: str = None) -> Optional[str]:
        """Download a single replay file using the /file endpoint"""
        
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"{replay_id}.replay")
        
        if os.path.exists(output_path):
            print(f"⏭️ {replay_id} already downloaded")
            return output_path
        
        try:
            # Use the CORRECT /file endpoint
            download_url = f"{self.base_url}/replays/{replay_id}/file"
            
            print(f"⬇️ Downloading {replay_id}...")
            file_response = self.session.get(
                download_url,
                stream=True,
                timeout=60
            )
            file_response.raise_for_status()
            
            total_size = int(file_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"   Progress: {progress:.1f}%", end='\r')
            
            print(f"\n✅ Downloaded: {replay_id}")
            self._save_metadata(replay_id)
            return output_path
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading {replay_id}: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def _save_metadata(self, replay_id: str):
        """Fetch and save metadata for a replay"""
        
        metadata_path = os.path.join(self.output_dir, f"{replay_id}_metadata.json")
        
        try:
            response = self.session.get(
                f"{self.base_url}/replays/{replay_id}",
                timeout=30
            )
            response.raise_for_status()
            replay_info = response.json()
            
            clean_metadata = {
                "id": replay_info.get("id"),
                "date": replay_info.get("date"),
                "duration": replay_info.get("duration"),
                "playlist": replay_info.get("playlist"),
                "playlist_name": replay_info.get("playlist_name"),
                "season": replay_info.get("season"),
                "map": replay_info.get("map"),
                "uploader": replay_info.get("uploader", {}).get("name"),
                "teams": {
                    "blue": {
                        "score": replay_info.get("blue", {}).get("score", 0),
                        "players": []
                    },
                    "orange": {
                        "score": replay_info.get("orange", {}).get("score", 0),
                        "players": []
                    }
                }
            }
            
            for team in ["blue", "orange"]:
                team_data = replay_info.get(team, {})
                players = team_data.get("players", [])
                for player in players:
                    clean_metadata["teams"][team]["players"].append({
                        "name": player.get("name"),
                        "platform": player.get("platform"),
                        "id": player.get("id"),
                        "car": player.get("car"),
                        "stats": {
                            "goals": player.get("stats", {}).get("goals", 0),
                            "assists": player.get("stats", {}).get("assists", 0),
                            "saves": player.get("stats", {}).get("saves", 0),
                            "shots": player.get("stats", {}).get("shots", 0),
                            "score": player.get("stats", {}).get("score", 0),
                            "mvp": player.get("stats", {}).get("mvp", False)
                        }
                    })
            
            with open(metadata_path, 'w') as f:
                json.dump(clean_metadata, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Could not save metadata: {e}")
    
    def download_replays_batch(self, 
                              game_mode: str = None,
                              count: int = 10,
                              min_rank: str = None,
                              max_rank: str = None,
                              season: str = None,
                              min_date: str = None,
                              max_date: str = None) -> List[str]:
        """Download multiple replays matching criteria"""
        
        downloaded = []
        page = 1
        max_pages = 50
        seen_ids = set()
        
        print(f"\n📊 Starting batch download:")
        print(f"   Game Mode: {game_mode if game_mode else 'Any'}")
        print(f"   Target: {count} replays")
        if min_rank:
            print(f"   Min Rank: {min_rank}")
        if max_rank:
            print(f"   Max Rank: {max_rank}")
        if season:
            print(f"   Season: {season}")
        print()
        
        while len(downloaded) < count and page <= max_pages:
            replays = self.search_replays(
                game_mode=game_mode,
                min_rank=min_rank,
                max_rank=max_rank,
                season=season,
                min_date=min_date,
                max_date=max_date,
                limit=min(100, count * 2),
                page=page
            )
            
            if not replays:
                print(f"⚠️ No more replays found on page {page}")
                break
            
            new_replays = []
            for replay in replays:
                replay_id = replay.get("id")
                if replay_id and replay_id not in seen_ids:
                    seen_ids.add(replay_id)
                    new_replays.append(replay)
            
            if not new_replays:
                page += 1
                continue
            
            print(f"📊 Found {len(new_replays)} new replays to check")
            
            for replay in new_replays:
                if len(downloaded) >= count:
                    break
                
                replay_id = replay.get("id")
                if not replay_id:
                    continue
                
                existing_path = os.path.join(self.output_dir, f"{replay_id}.replay")
                if os.path.exists(existing_path):
                    print(f"⏭️ {replay_id} already downloaded")
                    downloaded.append(existing_path)
                    continue
                
                # Try to download using the /file endpoint
                file_path = self.download_replay(replay_id)
                if file_path:
                    downloaded.append(file_path)
                    print(f"✅ Downloaded {len(downloaded)}/{count} replays")
                
                time.sleep(0.3)
            
            page += 1
        
        print(f"\n📊 Summary: Downloaded {len(downloaded)} replays to {self.output_dir}")
        return downloaded
    
    def get_total_available(self, 
                           game_mode: str = None,
                           min_rank: str = None,
                           max_rank: str = None,
                           season: str = None) -> int:
        """Get the total number of available replays matching criteria"""
        
        params = {"limit": 1, "count": 1}
        
        if game_mode and game_mode in self.playlist_map:
            params["playlist"] = self.playlist_map[game_mode]
        if min_rank:
            params["min-rank"] = self.rank_map.get(min_rank, min_rank)
        if max_rank:
            params["max-rank"] = self.rank_map.get(max_rank, max_rank)
        if season:
            params["season"] = season
        
        try:
            response = self.session.get(
                f"{self.base_url}/replays",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("count", 0)
        except Exception as e:
            print(f"❌ Error getting total count: {e}")
            return 0