# rocket_league_ml/scripts/download_replays.py

import os
import sys
import json
import time
from pathlib import Path

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
ml_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(ml_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, ml_dir)

from data_pipeline.ballchasing_downloader import BallChasingDownloader
from replay_analyzer.parse import parse_replay_to_dict
import argparse

def get_api_key():
    """
    Get the API key from api-key.txt in the scripts directory
    """
    api_key_file = os.path.join(script_dir, 'api-key.txt')
    
    if os.path.exists(api_key_file):
        with open(api_key_file, 'r') as f:
            api_key = f.read().strip()
            if api_key:
                return api_key
    
    return None

def cleanup_fake_metadata(raw_dir: str):
    """
    Remove BallChasing-generated _metadata.json files
    """
    raw_path = Path(raw_dir)
    fake_metadata_files = list(raw_path.glob("*_metadata.json"))
    
    if fake_metadata_files:
        print(f"\n🧹 Cleaning up {len(fake_metadata_files)} fake metadata files...")
        for file in fake_metadata_files:
            try:
                os.remove(file)
                print(f"  Removed: {file.name}")
            except Exception as e:
                print(f"  ⚠️ Could not remove {file.name}: {e}")
        print()

def extract_metadata_from_replay(replay_path: str) -> dict:
    """
    Extract metadata from a .replay file using the existing parser
    """
    # Parse the replay using your existing parser
    parsed_data = parse_replay_to_dict(replay_path)
    
    if not parsed_data:
        return None
    
    # Extract metadata from the parsed data
    properties = parsed_data.get("properties", {})
    
    # Get team scores
    team0_score = properties.get("Team0Score", 0)
    team1_score = properties.get("Team1Score", 0)
    
    # Get player stats
    player_stats = properties.get("PlayerStats", [])
    
    # Extract player information
    players = []
    for player in player_stats:
        players.append({
            'name': player.get('Name', 'Unknown'),
            'team': player.get('Team', 0),
            'goals': player.get('Goals', 0),
            'assists': player.get('Assists', 0),
            'saves': player.get('Saves', 0),
            'shots': player.get('Shots', 0),
            'score': player.get('Score', 0),
            'mvp': player.get('bMVP', False)
        })
    
    # Get goal events
    goals = properties.get("Goals", [])
    
    # Determine winner
    winner = None
    if team0_score > team1_score:
        winner = 0  # Team 0 won
    elif team1_score > team0_score:
        winner = 1  # Team 1 won
    else:
        winner = -1  # Tie or unknown
    
    # Build metadata dict
    metadata = {
        'replay_id': Path(replay_path).stem,
        'team0_score': team0_score,
        'team1_score': team1_score,
        'winner': winner,
        'team_size': properties.get('TeamSize', 0),
        'duration': properties.get('TotalSecondsPlayed', 0),
        'date': properties.get('Date', ''),
        'playlist': properties.get('Playlist', ''),
        'season': properties.get('Season', ''),
        'players': players,
        'goal_count': len(goals),
        'goals': goals,
    }
    
    return metadata

def process_replay_metadata(replay_path: str, force: bool = False) -> bool:
    """
    Process a single replay file and create its metadata file
    Returns True if successful, False otherwise
    """
    metadata_path = replay_path.replace('.replay', '.metadata.json')
    
    # Skip if metadata already exists and we're not forcing
    if os.path.exists(metadata_path) and not force:
        return True
    
    # Extract metadata
    metadata = extract_metadata_from_replay(replay_path)
    
    if metadata is None:
        return False
    
    # Save metadata to JSON file
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return True

def main():
    # Get default API key from file
    default_api_key = get_api_key()
    
    parser = argparse.ArgumentParser(description="Download Rocket League replays from BallChasing.com")
    parser.add_argument("--api-key", 
                       default=default_api_key,
                       help="Your BallChasing.com API key (default: read from scripts/api-key.txt)")
    parser.add_argument("--game-mode", choices=["1v1", "2v2", "3v3", "hoops", "rumble", "dropshot", "snowday"],
                       help="Game mode to download")
    parser.add_argument("--count", type=int, default=10, help="Number of replays to download")
    parser.add_argument("--min-rank", choices=[
        "unranked", "bronze_1", "bronze_2", "bronze_3",
        "silver_1", "silver_2", "silver_3",
        "gold_1", "gold_2", "gold_3",
        "platinum_1", "platinum_2", "platinum_3",
        "diamond_1", "diamond_2", "diamond_3",
        "champion_1", "champion_2", "champion_3",
        "grand_champion_1", "grand_champion_2", "grand_champion_3",
        "supersonic_legend",
        "gc1", "gc2", "gc3", "ssl"
    ], help="Minimum rank to download")
    parser.add_argument("--max-rank", choices=[
        "unranked", "bronze_1", "bronze_2", "bronze_3",
        "silver_1", "silver_2", "silver_3",
        "gold_1", "gold_2", "gold_3",
        "platinum_1", "platinum_2", "platinum_3",
        "diamond_1", "diamond_2", "diamond_3",
        "champion_1", "champion_2", "champion_3",
        "grand_champion_1", "grand_champion_2", "grand_champion_3",
        "supersonic_legend",
        "gc1", "gc2", "gc3", "ssl"
    ], help="Maximum rank to download")
    parser.add_argument("--season", type=int, help="Rocket League season number")
    parser.add_argument("--min-date", help="Minimum date (YYYY-MM-DD)")
    parser.add_argument("--max-date", help="Maximum date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default="data/raw", help="Output directory")
    parser.add_argument("--scored-only", action="store_true", 
                       help="Only keep replays that have score data (analyzed from file)")
    parser.add_argument("--force-metadata", action="store_true",
                       help="Force overwrite existing metadata files")
    
    args = parser.parse_args()
    
    # Check if API key is provided
    if not args.api_key:
        print("❌ No API key found. Please either:")
        print("   1. Create scripts/api-key.txt with your API key")
        print("   2. Pass --api-key YOUR_API_KEY")
        return
    
    # Step 1: Clean up any existing fake metadata files
    cleanup_fake_metadata(args.output_dir)
    
    # Step 2: Download replays
    downloader = BallChasingDownloader(args.api_key, args.output_dir)
    
    print(f"\n📥 Downloading replays...")
    
    # Check if we have any replays to download
    if args.min_rank or args.max_rank:
        total = downloader.get_total_available(
            game_mode=args.game_mode,
            min_rank=args.min_rank,
            max_rank=args.max_rank,
            season=args.season
        )
        print(f"📊 Total replays available: {total}")
        
        if total == 0:
            print("❌ No replays found matching your criteria.")
            return
        
        downloaded = downloader.download_replays_batch(
            game_mode=args.game_mode,
            count=min(args.count, total),
            min_rank=args.min_rank,
            max_rank=args.max_rank,
            season=args.season,
            min_date=args.min_date,
            max_date=args.max_date
        )
    else:
        downloaded = downloader.download_replays_batch(
            game_mode=args.game_mode,
            count=args.count
        )
    
    print(f"✅ Downloaded {len(downloaded)} replays")
    
    if not downloaded:
        print("❌ No replays downloaded.")
        return
    
    # Step 3: Extract metadata from each replay
    print(f"\n📊 Extracting metadata from downloaded replays...")
    
    analyzed_files = []
    scored_files = []
    no_score_files = []
    
    for replay_path in downloaded:
        replay_id = Path(replay_path).stem
        success = process_replay_metadata(replay_path, args.force_metadata)
        
        if success:
            analyzed_files.append(replay_path)
            
            # Check if it has scores
            metadata_path = replay_path.replace('.replay', '.metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                if metadata.get('team0_score', 0) > 0 or metadata.get('team1_score', 0) > 0:
                    scored_files.append(replay_path)
                    print(f"  ✅ {replay_id}: {metadata['team0_score']}-{metadata['team1_score']}")
                else:
                    no_score_files.append(replay_path)
                    print(f"  ⚠️ {replay_id}: No scores found")
        else:
            print(f"  ❌ {replay_id}: Failed to extract metadata")
    
    # Step 4: Optionally remove unscored replays
    if args.scored_only and no_score_files:
        print(f"\n🗑️ Removing {len(no_score_files)} replays without scores...")
        for replay_path in no_score_files:
            try:
                os.remove(replay_path)
                print(f"  Removed: {Path(replay_path).name}")
                # Also remove metadata file if it exists
                metadata_path = replay_path.replace('.replay', '.metadata.json')
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
            except Exception as e:
                print(f"  ⚠️ Could not remove {replay_path}: {e}")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"  Total downloaded: {len(downloaded)}")
    print(f"  Successfully analyzed: {len(analyzed_files)}")
    print(f"  With scores: {len(scored_files)}")
    print(f"  Without scores: {len(no_score_files)}")
    if args.scored_only:
        print(f"  Kept (with scores): {len(scored_files)}")
    
    print(f"\n✅ Done!")

if __name__ == "__main__":
    main()