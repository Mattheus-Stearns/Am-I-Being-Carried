# rocket_league_ml/data_pipeline/replay_processor.py

import os
import sys
import pandas as pd
import numpy as np
from typing import Optional, List
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.ball_tracking_parser import BallTrackingParser
from data_pipeline.data_storage import DataStorage

class ReplayProcessor:
    """Process replay files and extract ML-ready features using ball tracking parser"""
    
    def __init__(self, 
                 raw_dir: str = "data/raw", 
                 features_dir: str = "data/features",
                 quiet: bool = True):
        self.raw_dir = raw_dir
        self.features_dir = features_dir
        self.quiet = quiet
        self.parser = BallTrackingParser()
        
        os.makedirs(features_dir, exist_ok=True)
    
    def process_replay(self, replay_path: str) -> Optional[pd.DataFrame]:
        """Process a single replay file"""
        
        try:
            replay_id = Path(replay_path).stem
            if not self.quiet:
                print(f"📁 Processing: {replay_id}")
            
            # Parse with ball tracking parser
            df = self.parser.parse_replay_with_metadata(replay_path)
            
            if df.empty:
                if not self.quiet:
                    print(f"❌ No data for: {replay_id}")
                return None
            
            # Resample to 1-second intervals
            df = self._resample_to_seconds(df)
            
            # Create derived features
            df = self._add_derived_features(df)
            
            # Remove any duplicate columns before saving
            df = df.loc[:, ~df.columns.duplicated()]
            
            # Save processed data
            features_path = os.path.join(self.features_dir, f"{replay_id}_features.parquet")
            df.to_parquet(features_path, index=False)
            
            if not self.quiet:
                print(f"✅ Processed {replay_id}: {len(df)} rows, {len(df.columns)} columns")
            return df
            
        except Exception as e:
            if not self.quiet:
                print(f"❌ Error processing {replay_path}: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def _resample_to_seconds(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample data to 1-second intervals"""
        
        if 'time' not in df.columns:
            return df
        
        # Round time to nearest second
        df['time_rounded'] = np.floor(df['time'])
        
        # Group by second and take mean for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        meta_cols = ['replay_id', 'match_date', 'playlist', 'season', 'target_win', 
                    'team0_score', 'team1_score', 'duration', 'ball_actor_id']
        text_cols = [col for col in df.columns if col in meta_cols or df[col].dtype == 'object']
        
        # Don't include the original 'time' column in aggregation
        agg_dict = {}
        for col in numeric_cols:
            if col not in ['time', 'time_rounded'] and col not in meta_cols:
                agg_dict[col] = 'mean'
        
        for col in text_cols:
            if col in df.columns:
                agg_dict[col] = 'first'
        
        df_resampled = df.groupby('time_rounded').agg(agg_dict).reset_index()
        df_resampled.rename(columns={'time_rounded': 'time'}, inplace=True)
        
        return df_resampled
    
    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived features like ball speed"""
        
        # Make a copy
        df = df.copy()
        
        # Ball speed
        if all(col in df.columns for col in ['ball_vel_x', 'ball_vel_y', 'ball_vel_z']):
            df['ball_speed'] = np.sqrt(
                df['ball_vel_x']**2 + 
                df['ball_vel_y']**2 + 
                df['ball_vel_z']**2
            )
        
        return df
    
    def process_all_replays(self) -> List[str]:
        """Process all replay files in the raw directory"""
        
        processed_files = []
        
        if not os.path.exists(self.raw_dir):
            if not self.quiet:
                print(f"❌ Raw directory not found: {self.raw_dir}")
            return processed_files
        
        replay_files = [f for f in os.listdir(self.raw_dir) 
                       if f.endswith('.replay') and not f.startswith('.')]
        
        if not self.quiet:
            print(f"\n📊 Found {len(replay_files)} replay files to process")
        
        if not replay_files:
            return processed_files
        
        for replay_file in replay_files:
            replay_path = os.path.join(self.raw_dir, replay_file)
            replay_id = Path(replay_file).stem
            
            features_path = os.path.join(self.features_dir, f"{replay_id}_features.parquet")
            if os.path.exists(features_path):
                if not self.quiet:
                    print(f"⏭️ Skipping {replay_id} (already processed)")
                processed_files.append(features_path)
                continue
            
            df = self.process_replay(replay_path)
            if df is not None:
                processed_files.append(features_path)
        
        if not self.quiet:
            print(f"\n✅ Processed {len(processed_files)} replays")
        return processed_files