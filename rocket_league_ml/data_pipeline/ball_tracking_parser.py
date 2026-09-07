# rocket_league_ml/data_pipeline/ball_tracking_parser.py

import subtr_actor
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path
import json
import re
from collections import defaultdict

class BallTrackingParser:
    """
    Parse Rocket League replays by tracking actors by their class.
    Specifically tracks TAGame.Ball_TA for proper ball tracking.
    """
    
    def __init__(self):
        self.ball_actor_cache = {}  # Cache for ball properties
        self.current_ball_id = None
        self.ball_data = []
        
    def parse_replay(self, replay_path: str) -> pd.DataFrame:
        """Parse a replay file and track the ball properly"""
        
        print(f"🔍 Parsing replay: {replay_path}")
        
        with open(replay_path, 'rb') as f:
            replay_bytes = f.read()
        
        result = subtr_actor.parse_replay(replay_bytes)
        
        if result is None:
            print("❌ Failed to parse replay")
            return pd.DataFrame()
        
        frames = result.get("network_frames", {}).get("frames", [])
        objects_pool = result.get("objects", [])
        
        print(f"📊 Processing {len(frames)} frames")
        
        # Track ball actors by their class
        ball_actors = {}  # actor_id -> class_name
        ball_actor_history = defaultdict(list)  # actor_id -> list of (frame, props)
        current_ball_actor = None
        
        # Pass 1: Identify all ball actors by their class
        print("🔍 Identifying ball actors by class...")
        
        for frame_idx, frame in enumerate(frames):
            for updated_actor in frame.get("updated_actors", []):
                act_id = updated_actor["actor_id"]
                attr_id = updated_actor["object_id"]
                
                if attr_id >= len(objects_pool):
                    continue
                
                # Get the actor's class/object name
                obj_name = objects_pool[attr_id]
                
                # Check if this is a ball actor
                if "TAGame.Ball_TA" in obj_name:
                    ball_actors[act_id] = obj_name
                    # print(f"  ✅ Found ball actor: {act_id} (class: {obj_name})")
                    
                    # Store when this actor was first seen
                    if act_id not in ball_actor_history:
                        ball_actor_history[act_id].append(("created", frame_idx, frame.get("time", 0)))
        
        print(f"🏀 Found {len(ball_actors)} ball actors")
        
        # Pass 2: Track ball actor lifecycle and extract data
        print("📊 Tracking ball actor lifecycle...")
        
        # Track when ball actors are deleted
        for frame_idx, frame in enumerate(frames):
            for updated_actor in frame.get("updated_actors", []):
                act_id = updated_actor["actor_id"]
                attr_payload = updated_actor.get("attribute")
                
                # Check if this actor is being deleted
                if attr_payload and "Deleted" in attr_payload:
                    if act_id in ball_actors:
                        ball_actor_history[act_id].append(("deleted", frame_idx, frame.get("time", 0)))
                        # print(f"  🗑️ Ball actor {act_id} deleted at frame {frame_idx}")
        
        # Print ball actor lifecycle summary
        print("\n📋 Ball Actor Lifecycle:")
        for actor_id, events in ball_actor_history.items():
            created = None
            deleted = None
            for event, frame, time in events:
                if event == "created":
                    created = time
                elif event == "deleted":
                    deleted = time
            if created:
                print(f"  Actor {actor_id}: created at {created:.2f}s, deleted at {deleted:.2f}s" if deleted else f"  Actor {actor_id}: created at {created:.2f}s (still active)")
        
        # Pass 3: Extract ball data from each frame
        print("\n📊 Extracting ball data...")
        
        ball_data = []
        current_ball_actor = None
        
        for frame_idx, frame in enumerate(frames):
            time_stamp = frame.get("time", 0.0)
            ball_pos_x = None
            ball_pos_y = None
            ball_pos_z = None
            ball_vel_x = None
            ball_vel_y = None
            ball_vel_z = None
            
            # Check if any ball actor is active in this frame
            for updated_actor in frame.get("updated_actors", []):
                act_id = updated_actor["actor_id"]
                attr_payload = updated_actor.get("attribute")
                
                if act_id not in ball_actors:
                    continue
                
                # Check if this actor is being deleted
                if attr_payload and "Deleted" in attr_payload:
                    if current_ball_actor == act_id:
                        current_ball_actor = None
                    continue
                
                # Check for RigidBody data
                if attr_payload and "RigidBody" in attr_payload:
                    rb = attr_payload["RigidBody"]
                    if isinstance(rb, dict):
                        loc = rb.get("location")
                        vel = rb.get("linear_velocity")
                        
                        if isinstance(loc, dict):
                            ball_pos_x = loc.get("x", 0.0)
                            ball_pos_y = loc.get("y", 0.0)
                            ball_pos_z = loc.get("z", 0.0)
                            current_ball_actor = act_id
                        
                        if isinstance(vel, dict):
                            ball_vel_x = vel.get("x", 0.0)
                            ball_vel_y = vel.get("y", 0.0)
                            ball_vel_z = vel.get("z", 0.0)
            
            # If we have ball data, store it
            if ball_pos_x is not None:
                ball_data.append({
                    'frame': frame_idx,
                    'time': time_stamp,
                    'ball_actor_id': current_ball_actor,
                    'ball_pos_x': ball_pos_x,
                    'ball_pos_y': ball_pos_y,
                    'ball_pos_z': ball_pos_z,
                    'ball_vel_x': ball_vel_x or 0.0,
                    'ball_vel_y': ball_vel_y or 0.0,
                    'ball_vel_z': ball_vel_z or 0.0
                })
        
        # Create DataFrame
        df = pd.DataFrame(ball_data)
        
        if df.empty:
            print("❌ No ball data extracted!")
            return df
        
        print(f"✅ Extracted {len(df)} frames with ball data")
        
        # Show ball actor transitions
        print("\n🔄 Ball Actor Transitions:")
        actor_changes = df['ball_actor_id'].drop_duplicates()
        for actor_id in actor_changes:
            count = (df['ball_actor_id'] == actor_id).sum()
            first_frame = df[df['ball_actor_id'] == actor_id]['frame'].iloc[0]
            last_frame = df[df['ball_actor_id'] == actor_id]['frame'].iloc[-1]
            first_time = df[df['ball_actor_id'] == actor_id]['time'].iloc[0]
            last_time = df[df['ball_actor_id'] == actor_id]['time'].iloc[-1]
            print(f"  Actor {actor_id}: frames {first_frame}-{last_frame} ({first_time:.2f}s - {last_time:.2f}s), {count} frames")
        
        # Show ball movement stats
        print("\n📊 Ball Movement Stats:")
        if 'ball_pos_x' in df.columns:
            nonzero = ((df['ball_pos_x'] != 0) | (df['ball_pos_y'] != 0)).sum()
            total = len(df)
            print(f"  Non-zero positions: {nonzero}/{total} ({nonzero/total*100:.1f}%)")
            print(f"  X range: {df['ball_pos_x'].min():.2f} to {df['ball_pos_x'].max():.2f}")
            print(f"  Y range: {df['ball_pos_y'].min():.2f} to {df['ball_pos_y'].max():.2f}")
            print(f"  Z range: {df['ball_pos_z'].min():.2f} to {df['ball_pos_z'].max():.2f}")
        
        return df
    
    def parse_replay_with_metadata(self, replay_path: str) -> pd.DataFrame:
        """Parse a replay and also include metadata about ball actor lifecycles"""
        
        df = self.parse_replay(replay_path)
        
        if df.empty:
            return df
        
        # Add metadata
        replay_id = Path(replay_path).stem
        df['replay_id'] = replay_id
        
        # Try to load metadata from JSON file
        metadata_path = replay_path.replace('.replay', '.metadata.json')
        if Path(metadata_path).exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Add metadata columns
            df['team0_score'] = metadata.get('team0_score', 0)
            df['team1_score'] = metadata.get('team1_score', 0)
            df['target_win'] = 1 if metadata.get('winner') == 0 else 0
            df['duration'] = metadata.get('duration', 0)
        
        return df