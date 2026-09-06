# rocket_league_ml/data_pipeline/replay_processor.py

import os
import sys
import json
import contextlib
import io
import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from datetime import datetime

# Fix: Go up three levels to reach the project root where replay_analyzer lives
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from replay_analyzer.parse import parse_replay_to_dict
from replay_analyzer.dataframe import build_telemetry_dataframe

class ReplayProcessor:
    """Process replay files and extract ML-ready features"""
    
    def __init__(self, raw_dir: str = "data/raw", 
                 processed_dir: str = "data/processed",
                 features_dir: str = "data/features",
                 quiet: bool = True):
        # Store paths as-is - don't modify them
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.features_dir = features_dir
        self.quiet = quiet
        
        # Create directories if they don't exist
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.features_dir, exist_ok=True)
        
    def _suppress_output(self):
        """Context manager to suppress stdout and stderr"""
        if self.quiet:
            return contextlib.redirect_stdout(io.StringIO())
        else:
            return contextlib.nullcontext()
        
    def process_replay(self, replay_path: str, game_mode: str = "1v1") -> Optional[pd.DataFrame]:
        """Process a single replay file and return feature DataFrame"""
        
        try:
            replay_id = os.path.basename(replay_path).replace('.replay', '')
            if not self.quiet:
                print(f"📁 Processing: {replay_id}")
            
            # Parse replay using your existing parser - suppress stdout
            with self._suppress_output():
                parsed_data = parse_replay_to_dict(replay_path)
            
            if not parsed_data:
                if not self.quiet:
                    print(f"❌ Failed to parse: {replay_path}")
                return None
            
            # Get date from metadata
            properties = parsed_data.get("properties", {})
            date_str = properties.get("Date", "unknown_date")
            date_str = date_str.replace(' ', '_').replace('-', '_')
            
            # Build telemetry dataframe using your existing code - suppress stdout
            with self._suppress_output():
                df_telemetry = build_telemetry_dataframe(parsed_data, date_str)
            
            if df_telemetry.empty:
                if not self.quiet:
                    print(f"❌ No telemetry data for: {replay_id}")
                return None
            
            # Extract features at 1-second intervals
            df_features = self._extract_features(df_telemetry, game_mode)
            
            # Add match metadata
            df_features['replay_id'] = replay_id
            df_features['match_date'] = date_str
            
            # Add target variable from metadata
            metadata_path = replay_path.replace('.replay', '_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                blue_score = metadata.get("teams", {}).get("blue", {}).get("score", 0)
                orange_score = metadata.get("teams", {}).get("orange", {}).get("score", 0)
                df_features['target_win'] = 1 if blue_score > orange_score else 0
            else:
                df_features['target_win'] = 0
            
            # Ensure target_win is int
            df_features['target_win'] = df_features['target_win'].astype(int)
            
            # Save processed data
            features_path = os.path.join(self.features_dir, f"{replay_id}_features.parquet")
            df_features.to_parquet(features_path, index=False)
            
            if not self.quiet:
                print(f"✅ Processed {replay_id}: {len(df_features)} rows, {len(df_features.columns)} columns")
            return df_features
            
        except Exception as e:
            if not self.quiet:
                print(f"❌ Error processing {replay_path}: {e}")
            return None
    
    def _extract_features(self, df_telemetry: pd.DataFrame, game_mode: str = "1v1") -> pd.DataFrame:
        """Extract features at 1-second intervals from telemetry"""
        
        # Identify players
        players = self._identify_players(df_telemetry)
        
        # Resample to 1-second intervals
        df_snapshots = self._resample_to_seconds(df_telemetry)
        
        # Extract features for each snapshot using .iloc to avoid Series issues
        features_list = []
        for idx in range(len(df_snapshots)):
            row = df_snapshots.iloc[idx]
            snapshot = self._extract_snapshot_features(row, players)
            features_list.append(snapshot)
        
        df_features = pd.DataFrame(features_list)
        
        # Ensure all numeric columns are proper float types
        for col in df_features.columns:
            if col not in ['replay_id', 'match_date', 'target_win']:
                df_features[col] = pd.to_numeric(df_features[col], errors='coerce').fillna(0.0)
        
        return df_features
    
    def _identify_players(self, df: pd.DataFrame) -> List[str]:
        """Extract player names from column headers"""
        players = set()
        for col in df.columns:
            if '_vel_x' in col and not col.startswith('Ball'):
                player = col.replace('_vel_x', '')
                players.add(player)
        return sorted(players)
    
    def _resample_to_seconds(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample telemetry data to 1-second intervals"""
        
        if 'time' not in df.columns:
            return df
        
        # Ensure time is float
        df['time'] = pd.to_numeric(df['time'], errors='coerce').fillna(0.0)
        
        # Round time to nearest second
        df['time_rounded'] = np.floor(df['time'])
        
        # Group by second and take mean for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        agg_dict = {col: 'mean' for col in numeric_cols if col != 'time_rounded'}
        
        df_resampled = df.groupby('time_rounded').agg(agg_dict).reset_index()
        df_resampled.rename(columns={'time_rounded': 'time'}, inplace=True)
        
        return df_resampled
    
    def _extract_snapshot_features(self, row: pd.Series, players: List[str]) -> Dict:
        """Extract all features for a single snapshot - using .iloc to get scalar values"""
        
        # Helper to safely get scalar value from Series
        def safe_get(series, key, default=0.0):
            val = series.get(key, default)
            if isinstance(val, pd.Series):
                # If it's a Series, take the first value
                return float(val.iloc[0]) if len(val) > 0 else float(default)
            try:
                return float(val)
            except (ValueError, TypeError):
                return float(default)
        
        features = {'time': safe_get(row, 'time', 0.0)}
        
        # Ball features
        features['ball_x'] = safe_get(row, 'Ball_pos_x', 0.0)
        features['ball_y'] = safe_get(row, 'Ball_pos_y', 0.0)
        features['ball_z'] = safe_get(row, 'Ball_pos_z', 0.0)
        features['ball_vx'] = safe_get(row, 'Ball_vel_x', 0.0)
        features['ball_vy'] = safe_get(row, 'Ball_vel_y', 0.0)
        features['ball_vz'] = safe_get(row, 'Ball_vel_z', 0.0)
        features['ball_speed'] = np.sqrt(
            features['ball_vx']**2 + 
            features['ball_vy']**2 + 
            features['ball_vz']**2
        )
        
        # Player features
        for i, player in enumerate(players, 1):
            prefix = f"p{i}_"
            
            # Position
            features[f"{prefix}pos_x"] = safe_get(row, f"{player}_pos_x", 0.0)
            features[f"{prefix}pos_y"] = safe_get(row, f"{player}_pos_y", 0.0)
            features[f"{prefix}pos_z"] = safe_get(row, f"{player}_pos_z", 0.0)
            
            # Velocity
            features[f"{prefix}vel_x"] = safe_get(row, f"{player}_vel_x", 0.0)
            features[f"{prefix}vel_y"] = safe_get(row, f"{player}_vel_y", 0.0)
            features[f"{prefix}vel_z"] = safe_get(row, f"{player}_vel_z", 0.0)
            
            # Speed
            features[f"{prefix}speed"] = np.sqrt(
                features[f"{prefix}vel_x"]**2 + 
                features[f"{prefix}vel_y"]**2 + 
                features[f"{prefix}vel_z"]**2
            )
            
            # Boost
            features[f"{prefix}boost"] = safe_get(row, f"{player}_boost", 0.0)
            
            # Distance to ball
            dx = features[f"{prefix}pos_x"] - features['ball_x']
            dy = features[f"{prefix}pos_y"] - features['ball_y']
            dz = features[f"{prefix}pos_z"] - features['ball_z']
            features[f"{prefix}dist_to_ball"] = np.sqrt(dx**2 + dy**2 + dz**2)
        
        return features
    
    def process_all_replays(self, game_mode: str = "1v1") -> List[str]:
        """Process all replay files in the raw directory"""
        
        processed_files = []
        
        # Check if raw directory exists
        if not os.path.exists(self.raw_dir):
            if not self.quiet:
                print(f"❌ Raw directory not found: {self.raw_dir}")
            return processed_files
        
        replay_files = [f for f in os.listdir(self.raw_dir) 
                       if f.endswith('.replay') and not f.startswith('.')]
        
        if not self.quiet:
            print(f"\n📊 Found {len(replay_files)} replay files to process")
        
        if not replay_files:
            if not self.quiet:
                print("❌ No .replay files found in the raw directory")
            return processed_files
        
        for replay_file in replay_files:
            replay_path = os.path.join(self.raw_dir, replay_file)
            replay_id = replay_file.replace('.replay', '')
            
            # Check if already processed
            features_path = os.path.join(self.features_dir, f"{replay_id}_features.parquet")
            if os.path.exists(features_path):
                if not self.quiet:
                    print(f"⏭️ Skipping {replay_id} (already processed)")
                processed_files.append(features_path)
                continue
            
            df = self.process_replay(replay_path, game_mode)
            if df is not None:
                processed_files.append(features_path)
        
        if not self.quiet:
            print(f"\n✅ Processed {len(processed_files)} replays")
        return processed_files