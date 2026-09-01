import os
import json
import pandas as pd
from typing import Optional, List
import sys

# Add parent directory to path to import your replay analyzer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from replay_analyzer.parse import parse_replay_to_dict
from replay_analyzer.dataframe import build_telemetry_dataframe
from replay_analyzer.graph import calculate_advanced_boost_stats
from feature_extractor import FeatureExtractor

class ReplayProcessor:
    """Process replay files and extract ML-ready features"""
    
    def __init__(self, raw_dir: str = "data/raw", 
                 processed_dir: str = "data/processed",
                 features_dir: str = "data/features"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.features_dir = features_dir
        self.feature_extractor = FeatureExtractor()
        
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(features_dir, exist_ok=True)
        
    def process_replay(self, replay_path: str, game_mode: str = "3v3") -> Optional[pd.DataFrame]:
        """Process a single replay file"""
        
        try:
            print(f" Processing: {replay_path}")
            
            # Parse the replay using your existing parser
            parsed_data = parse_replay_to_dict(replay_path)
            if not parsed_data:
                print(f" Failed to parse: {replay_path}")
                return None
                
            # Get replay metadata
            replay_id = os.path.basename(replay_path).replace('.replay', '')
            metadata_path = replay_path.replace('.replay', '_metadata.json')
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            # Extract date for naming
            properties = parsed_data.get("properties", {})
            date_str = properties.get("Date", "unknown_date")
            date_str = date_str.replace(' ', '_').replace('-', '_')
            
            # Build telemetry dataframe using your existing code
            df_telemetry = build_telemetry_dataframe(parsed_data, date_str)
            
            if df_telemetry.empty:
                print(f" No telemetry data for: {replay_path}")
                return None
                
            # Extract features for ML
            df_features = self.feature_extractor.extract_features(
                df_telemetry, game_mode
            )
            
            # Add match metadata
            df_features['replay_id'] = replay_id
            df_features['match_date'] = date_str
            
            # Add target variable from metadata (who won?)
            blue_score = metadata.get("blue", {}).get("score", 0)
            orange_score = metadata.get("orange", {}).get("score", 0)
            
            if blue_score > orange_score:
                df_features['target_win'] = 1  # Blue won
            elif orange_score > blue_score:
                df_features['target_win'] = 0  # Orange won
            else:
                df_features['target_win'] = None  # Tie?
            
            # Save processed data
            processed_path = os.path.join(
                self.processed_dir, 
                f"{replay_id}_processed.parquet"
            )
            df_telemetry.to_parquet(processed_path, index=False)
            
            # Save features
            features_path = os.path.join(
                self.features_dir,
                f"{replay_id}_features.parquet"
            )
            df_features.to_parquet(features_path, index=False)
            
            print(f" Processed: {replay_id}")
            print(f"   - {len(df_telemetry)} telemetry rows")
            print(f"   - {len(df_features)} feature rows")
            
            return df_features
            
        except Exception as e:
            print(f" Error processing {replay_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def process_all_replays(self, game_mode: str = "3v3") -> List[str]:
        """Process all replay files in the raw directory"""
        
        processed_files = []
        replay_files = [f for f in os.listdir(self.raw_dir) 
                       if f.endswith('.replay') and not f.startswith('.')]
        
        print(f" Found {len(replay_files)} replay files to process")
        
        for replay_file in replay_files:
            replay_path = os.path.join(self.raw_dir, replay_file)
            
            # Check if already processed
            replay_id = replay_file.replace('.replay', '')
            features_path = os.path.join(
                self.features_dir,
                f"{replay_id}_features.parquet"
            )
            
            if os.path.exists(features_path):
                print(f"️ Skipping {replay_id} (already processed)")
                processed_files.append(features_path)
                continue
                
            df = self.process_replay(replay_path, game_mode)
            if df is not None:
                processed_files.append(features_path)
                
        print(f"\n Processed {len(processed_files)} replays")
        return processed_files