#!/usr/bin/env python
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.replay_processor import ReplayProcessor
from data_pipeline.data_storage import DataStorage
import argparse

def main():
    parser = argparse.ArgumentParser(description="Process Rocket League replays for ML")
    parser.add_argument("--game-mode", default="3v3", choices=["1v1", "2v2", "3v3"],
                       help="Game mode")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory with .replay files")
    parser.add_argument("--processed-dir", default="data/processed", help="Output directory")
    parser.add_argument("--features-dir", default="data/features", help="Features directory")
    
    args = parser.parse_args()
    
    # Process all replays
    processor = ReplayProcessor(
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        features_dir=args.features_dir
    )
    processed = processor.process_all_replays(game_mode=args.game_mode)
    
    # Combine into single dataset
    if processed:
        storage = DataStorage(args.features_dir)
        df = storage.combine_feature_files()
        storage.save_dataset(df, f"rocket_league_{args.game_mode.replace('v', 'v')}")
        
        print(f"\n Final dataset: {len(df)} rows, {len(df.columns)} columns")
        print(f"   Target distribution: {df['target_win'].value_counts().to_dict()}")

if __name__ == "__main__":
    main()