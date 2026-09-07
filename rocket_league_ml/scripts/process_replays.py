# rocket_league_ml/scripts/process_replays.py

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
ml_dir = os.path.dirname(script_dir)
sys.path.insert(0, ml_dir)

from data_pipeline.replay_processor import ReplayProcessor
from data_pipeline.data_storage import DataStorage
import argparse

def main():
    parser = argparse.ArgumentParser(description="Process Rocket League replays using subtr-actor")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory with .replay files")
    parser.add_argument("--features-dir", default="data/features", help="Features directory")
    parser.add_argument("--dataset-name", default="rocket_league_dataset", help="Name for combined dataset")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    
    args = parser.parse_args()
    
    processor = ReplayProcessor(
        raw_dir=args.raw_dir,
        features_dir=args.features_dir,
        quiet=args.quiet
    )
    
    processed_files = processor.process_all_replays()
    
    if processed_files:
        storage = DataStorage(args.features_dir)
        df = storage.combine_feature_files()
        
        if not df.empty:
            storage.save_dataset(df, args.dataset_name)
            
            print(f"\n📊 Final dataset stats:")
            print(f"   Rows: {len(df)}")
            print(f"   Columns: {len(df.columns)}")
            print(f"   Target distribution: {df['target_win'].value_counts().to_dict()}")
            print(f"   Time range: {df['time'].min():.1f}s - {df['time'].max():.1f}s")
    else:
        print("❌ No replays were processed.")

if __name__ == "__main__":
    main()