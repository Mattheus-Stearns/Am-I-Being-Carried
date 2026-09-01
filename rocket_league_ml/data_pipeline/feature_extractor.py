import pandas as pd
import numpy as np
from typing import Dict, List
import re

class FeatureExtractor:
    """Extract features at 1-second intervals from telemetry data"""
    
    def __init__(self):
        self.feature_columns = []
        
    def extract_features(self, df_telemetry: pd.DataFrame, 
                        game_mode: str = "3v3") -> pd.DataFrame:
        """
        Convert telemetry data to 1-second snapshots with engineered features
        """
        
        # Identify players from columns
        players = self._identify_players(df_telemetry)
        
        # Resample to 1-second intervals
        df_snapshots = self._resample_to_seconds(df_telemetry)
        
        # Extract features for each snapshot
        features_list = []
        
        for idx, row in df_snapshots.iterrows():
            snapshot = self._extract_snapshot_features(
                row, players, game_mode
            )
            features_list.append(snapshot)
            
        df_features = pd.DataFrame(features_list)
        
        # Add the target variable (will be filled later from match outcome)
        df_features['target_win'] = None
        
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
            
        # Round time to nearest second
        df['time_rounded'] = np.floor(df['time'])
        
        # Group by second and take mean for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        agg_dict = {col: 'mean' for col in numeric_cols if col != 'time_rounded'}
        
        df_resampled = df.groupby('time_rounded').agg(agg_dict).reset_index()
        df_resampled.rename(columns={'time_rounded': 'time'}, inplace=True)
        
        return df_resampled
    
    def _extract_snapshot_features(self, row: pd.Series, 
                                   players: List[str], 
                                   game_mode: str) -> Dict:
        """Extract all features for a single snapshot"""
        
        features = {'time': row.get('time', 0)}
        
        for player in players:
            prefix = f"{player}_"
            
            # Positional features
            features[f"{prefix}pos_x"] = row.get(f"{prefix}pos_x", 0)
            features[f"{prefix}pos_y"] = row.get(f"{prefix}pos_y", 0)
            features[f"{prefix}pos_z"] = row.get(f"{prefix}pos_z", 0)
            
            # Velocity features
            features[f"{prefix}vel_x"] = row.get(f"{prefix}vel_x", 0)
            features[f"{prefix}vel_y"] = row.get(f"{prefix}vel_y", 0)
            features[f"{prefix}vel_z"] = row.get(f"{prefix}vel_z", 0)
            
            # Calculate speed (3D velocity magnitude)
            vx = features[f"{prefix}vel_x"]
            vy = features[f"{prefix}vel_y"]
            vz = features[f"{prefix}vel_z"]
            features[f"{prefix}speed"] = np.sqrt(vx**2 + vy**2 + vz**2)
            
            # Boost features
            features[f"{prefix}boost"] = row.get(f"{prefix}boost", 0)
            
            # Distance to ball
            ball_x = row.get('Ball_pos_x', 0)
            ball_y = row.get('Ball_pos_y', 0)
            ball_z = row.get('Ball_pos_z', 0)
            
            px = features[f"{prefix}pos_x"]
            py = features[f"{prefix}pos_y"]
            pz = features[f"{prefix}pos_z"]
            
            dist_to_ball = np.sqrt(
                (px - ball_x)**2 + 
                (py - ball_y)**2 + 
                (pz - ball_z)**2
            )
            features[f"{prefix}dist_to_ball"] = dist_to_ball
            
        # Ball features
        features['ball_x'] = row.get('Ball_pos_x', 0)
        features['ball_y'] = row.get('Ball_pos_y', 0)
        features['ball_z'] = row.get('Ball_pos_z', 0)
        features['ball_vx'] = row.get('Ball_vel_x', 0)
        features['ball_vy'] = row.get('Ball_vel_y', 0)
        features['ball_vz'] = row.get('Ball_vel_z', 0)
        features['ball_speed'] = np.sqrt(
            features['ball_vx']**2 + 
            features['ball_vy']**2 + 
            features['ball_vz']**2
        )
        
        # Team features (for 2v2/3v3)
        if game_mode in ['2v2', '3v3']:
            self._add_team_features(features, players)
            
        return features
    
    def _add_team_features(self, features: Dict, players: List[str]):
        """Add team-level features (average positions, spacing, etc.)"""
        
        # This assumes players are split into blue/orange teams
        # You'll need to determine team assignments from the replay data
        # For now, we'll use a placeholder
        
        blue_players = []  # Need to determine from replay
        orange_players = []
        
        # For now, just split evenly
        half = len(players) // 2
        blue_players = players[:half]
        orange_players = players[half:]
        
        # Average position of each team
        for team, team_players in [('blue', blue_players), ('orange', orange_players)]:
            if team_players:
                avg_x = np.mean([features.get(f"{p}_pos_x", 0) for p in team_players])
                avg_y = np.mean([features.get(f"{p}_pos_y", 0) for p in team_players])
                avg_z = np.mean([features.get(f"{p}_pos_z", 0) for p in team_players])
                
                features[f"{team}_avg_x"] = avg_x
                features[f"{team}_avg_y"] = avg_y
                features[f"{team}_avg_z"] = avg_z
                
                # Team spacing (average distance between teammates)
                distances = []
                for i in range(len(team_players)):
                    for j in range(i+1, len(team_players)):
                        p1 = team_players[i]
                        p2 = team_players[j]
                        dist = np.sqrt(
                            (features.get(f"{p1}_pos_x", 0) - features.get(f"{p2}_pos_x", 0))**2 +
                            (features.get(f"{p1}_pos_y", 0) - features.get(f"{p2}_pos_y", 0))**2 +
                            (features.get(f"{p1}_pos_z", 0) - features.get(f"{p2}_pos_z", 0))**2
                        )
                        distances.append(dist)
                
                features[f"{team}_spacing"] = np.mean(distances) if distances else 0