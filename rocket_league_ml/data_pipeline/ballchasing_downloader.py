# rocket_league_ml/data_pipeline/ballchasing_downloader.py

import os
import time
import json
from typing import List, Dict, Optional
from datetime import datetime
import requests

class BallChasingDownloader:
    """Download replay files from BallChasing.com using direct API calls"""
    
    def __init__(self, api_key: str, output_dir: str = "data/raw"):
        self.api_key = api_key
        self.output_dir = output_dir
        self.base_url = "https://ballchasing.com/api"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": api_key,
            "Content-Type": "application/json"
        })
        
        os.makedirs(output_dir, exist_ok=True)
        
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
        
        self.rank_map = {
            "unranked": "Unranked",
            "bronze_1": "Bronze I",
            "bronze_2": "Bronze II",
            "bronze_3": "Bronze III",
            "silver_1": "Silver I",
            "silver_2": "Silver II",
            "silver_3": "Silver III",
            "gold_1": "Gold I",
            "gold_2": "Gold II",
            "gold_3": "Gold III",
            "platinum_1": "Platinum I",
            "platinum_2": "Platinum II",
            "platinum_3": "Platinum III",
            "diamond_1": "Diamond I",
            "diamond_2": "Diamond II",
            "diamond_3": "Diamond III",
            "champion_1": "Champion I",
            "champion_2": "Champion II",
            "champion_3": "Champion III",
            "grand_champion_1": "Grand Champion I",
            "grand_champion_2": "Grand Champion II",
            "grand_champion_3": "Grand Champion III",
            "supersonic_legend": "Supersonic Legend",
            "gc1": "Grand Champion I",
            "gc2": "Grand Champion II",
            "gc3": "Grand Champion III",
            "ssl": "Supersonic Legend"
        }
    
    def search_replays(self, 
                       game_mode: str = None,
                       min_rank: str = None,
                       max_rank: str = None,
                       season: int = None,
                       min_date: str = None,
                       max_date: str = None,
                       count: int = 100,
                       page: int = 1) -> List[Dict]:
        """Search for replays using direct API calls"""
        
        try:
            params = {}
            
            if game_mode and game_mode in self.playlist_map:
                params["playlist"] = self.playlist_map[game_mode]
            
            if min_rank:
                params["min-rank"] = self.rank_map.get(min_rank, min_rank)
            if max_rank:
                params["max-rank"] = self.rank_map.get(max_rank, max_rank)
            
            if season:
                params["season"] = str(season)
            
            if min_date:
                params["replay-date-after"] = min_date
            if max_date:
                params["replay-date-before"] = max_date
            
            params["count"] = min(count, 200)
            params["page"] = page
            
            print(f"🔍 Searching page {page} with params: {params}")
            
            response = self.session.get(
                f"{self.base_url}/replays",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            replay_list = []
            if "list" in data:
                for replay in data["list"]:
                    replay_dict = {
                        "id": replay.get("id", ""),
                        "date": replay.get("date", ""),
                        "duration": replay.get("duration", 0),
                        "playlist": replay.get("playlist", ""),
                        "playlist_name": replay.get("playlist_name", ""),
                        "season": replay.get("season", ""),
                        "map": replay.get("map", ""),
                        "uploader": replay.get("uploader", {}).get("name", ""),
                        "blue": {
                            "score": replay.get("blue", {}).get("goals", 0),
                            "players": []
                        },
                        "orange": {
                            "score": replay.get("orange", {}).get("goals", 0),
                            "players": []
                        }
                    }
                    
                    for team in ["blue", "orange"]:
                        team_data = replay.get(team, {})
                        players = team_data.get("players", [])
                        for player in players:
                            replay_dict[team]["players"].append({
                                "name": player.get("name", "Unknown"),
                                "platform": player.get("platform", None),
                                "id": player.get("id", None),
                                "car": player.get("car", None),
                                "stats": {
                                    "goals": player.get("stats", {}).get("goals", 0),
                                    "assists": player.get("stats", {}).get("assists", 0),
                                    "saves": player.get("stats", {}).get("saves", 0),
                                    "shots": player.get("stats", {}).get("shots", 0),
                                    "score": player.get("stats", {}).get("score", 0),
                                    "mvp": player.get("stats", {}).get("mvp", False)
                                }
                            })
                    
                    replay_list.append(replay_dict)
            
            total = data.get("count", len(replay_list))
            print(f"📊 Found {len(replay_list)} replays on page {page} (Total available: {total})")
            return replay_list
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error searching replays: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text[:200]}")
            return []
    
    def download_replay(self, replay_id: str, output_path: str = None) -> Optional[str]:
        """Download a single replay file - NO metadata file created"""
        
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"{replay_id}.replay")
        
        if os.path.exists(output_path):
            print(f"⏭️ {replay_id} already downloaded")
            return output_path
        
        try:
            print(f"⬇️ Downloading {replay_id}...")
            
            response = self.session.get(
                f"{self.base_url}/replays/{replay_id}/file",
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"✅ Downloaded: {replay_id}")
            # DO NOT create metadata file here - we'll create it separately
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading {replay_id}: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def download_replays_batch(self, 
                              game_mode: str = None,
                              count: int = 10,
                              min_rank: str = None,
                              max_rank: str = None,
                              season: int = None,
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
                count=min(100, count * 2),
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
                print(f"⚠️ No new replays on page {page}")
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
                
                file_path = self.download_replay(replay_id)
                if file_path:
                    downloaded.append(file_path)
                    print(f"✅ Downloaded {len(downloaded)}/{count} replays")
                
                time.sleep(0.5)
            
            page += 1
        
        print(f"\n📊 Summary: Downloaded {len(downloaded)} replays to {self.output_dir}")
        return downloaded
    
    def get_total_available(self, 
                           game_mode: str = None,
                           min_rank: str = None,
                           max_rank: str = None,
                           season: int = None) -> int:
        """Get the total number of available replays matching criteria"""
        
        try:
            params = {}
            
            if game_mode and game_mode in self.playlist_map:
                params["playlist"] = self.playlist_map[game_mode]
            if min_rank:
                params["min-rank"] = self.rank_map.get(min_rank, min_rank)
            if max_rank:
                params["max-rank"] = self.rank_map.get(max_rank, max_rank)
            if season:
                params["season"] = str(season)
            
            params["count"] = 1
            
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