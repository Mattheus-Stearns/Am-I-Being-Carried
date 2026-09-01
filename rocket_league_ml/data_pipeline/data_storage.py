import pandas as pd
import os
import glob
from typing import List, Optional

class DataStorage:
    """Store and load processed replay data"""
    
    def __init__(self, features_dir: str = "data/features"):
        self.features_dir = features_dir
        
    def save_dataset(self, df: pd.DataFrame, name: str = "rocket_league_dataset"):
        """Save combined dataset for ML training"""
        
        # Save full dataset
        path = os.path.join(self.features_dir, f"{name}.parquet")
        df.to_parquet(path, index=False)
        print(f" Saved dataset: {path}")
        
        # Also save a sample file for inspection
        sample_path = os.path.join(self.features_dir, f"{name}_sample.csv")
        df.head(1000).to_csv(sample_path, index=False)
        
        return path
    
    def load_dataset(self, name: str = "rocket_league_dataset") -> Optional[pd.DataFrame]:
        """Load a previously saved dataset"""
        
        path = os.path.join(self.features_dir, f"{name}.parquet")
        if os.path.exists(path):
            return pd.read_parquet(path)
        return None
    
    def combine_feature_files(self, pattern: str = "*_features.parquet") -> pd.DataFrame:
        """Combine all feature files into a single DataFrame"""
        
        file_pattern = os.path.join(self.features_dir, pattern)
        files = glob.glob(file_pattern)
        
        if not files:
            print(f" No files found matching: {file_pattern}")
            return pd.DataFrame()
            
        print(f" Combining {len(files)} feature files...")
        
        dfs = []
        for file in files:
            df = pd.read_parquet(file)
            dfs.append(df)
            
        combined = pd.concat(dfs, ignore_index=True)
        print(f" Combined dataset: {len(combined)} rows, {len(combined.columns)} columns")
        
        return combined