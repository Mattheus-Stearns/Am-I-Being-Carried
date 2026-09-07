# rocket_league_ml/data_pipeline/data_storage.py

import pandas as pd
import os
import glob
from typing import Optional, List

class DataStorage:
    """Store and load processed replay data"""
    
    def __init__(self, features_dir: str = "data/features"):
        self.features_dir = features_dir
        
    def combine_feature_files(self, pattern: str = "*_features.parquet") -> pd.DataFrame:
        """Combine all feature files into a single DataFrame"""
        
        # Check if directory exists
        if not os.path.exists(self.features_dir):
            print(f"❌ Features directory not found: {self.features_dir}")
            return pd.DataFrame()
        
        file_pattern = os.path.join(self.features_dir, pattern)
        files = glob.glob(file_pattern)
        
        if not files:
            print(f"❌ No files found matching: {file_pattern}")
            return pd.DataFrame()
        
        print(f"📊 Combining {len(files)} feature files...")
        
        dfs = []
        for file in files:
            try:
                df = pd.read_parquet(file)
                dfs.append(df)
            except Exception as e:
                print(f"⚠️ Could not read {file}: {e}")
        
        if not dfs:
            return pd.DataFrame()
        
        combined = pd.concat(dfs, ignore_index=True)
        print(f"✅ Combined dataset: {len(combined)} rows, {len(combined.columns)} columns")
        return combined
    
    def save_dataset(self, df: pd.DataFrame, name: str = "rocket_league_dataset"):
        """Save combined dataset for ML training"""
        
        # Check if directory exists
        if not os.path.exists(self.features_dir):
            os.makedirs(self.features_dir, exist_ok=True)
        
        # Save full dataset
        path = os.path.join(self.features_dir, f"{name}.parquet")
        df.to_parquet(path, index=False)
        print(f"✅ Saved dataset: {path}")
        
        # Save sample for inspection
        sample_path = os.path.join(self.features_dir, f"{name}_sample.csv")
        df.head(1000).to_csv(sample_path, index=False)
        print(f"✅ Saved sample: {sample_path}")
        
        return path
    
    def load_dataset(self, name: str = "rocket_league_dataset") -> Optional[pd.DataFrame]:
        """Load a previously saved dataset"""
        
        path = os.path.join(self.features_dir, f"{name}.parquet")
        if os.path.exists(path):
            return pd.read_parquet(path)
        return None