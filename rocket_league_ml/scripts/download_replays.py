#!/usr/bin/env python
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.ballchasing_downloader import BallChasingDownloader
import argparse

def main():
    parser = argparse.ArgumentParser(description="Download Rocket League replays from BallChasing.com")
    parser.add_argument("--api-key", required=True, help="Your BallChasing.com API key")
    parser.add_argument("--game-mode", default="3v3", choices=["1v1", "2v2", "3v3"], 
                       help="Game mode to download")
    parser.add_argument("--count", type=int, default=10, help="Number of replays to download")
    parser.add_argument("--output-dir", default="data/raw", help="Output directory")
    
    args = parser.parse_args()
    
    downloader = BallChasingDownloader(args.api_key, args.output_dir)
    downloaded = downloader.download_replays_batch(
        game_mode=args.game_mode,
        count=args.count
    )
    
    print(f"\n Downloaded {len(downloaded)} replays to {args.output_dir}")

if __name__ == "__main__":
    main()