# dataframe.py

import pandas as pd
import numpy as np
import re
from collections import defaultdict

def build_telemetry_dataframe(replay_data, replay_date):
    """
    Fully automatic parser with boost statistics tracking.
    """
    objects_pool = replay_data.get("objects", [])
    frames = replay_data.get("network_frames", {}).get("frames", [])
    
    # Relationship registries
    actor_attributes = defaultdict(set)
    actor_strings = {}
    actor_unique_ids = {}
    actor_display_names = defaultdict(list)
    actor_rigidbody_data = defaultdict(list)
    actor_byte_data = defaultdict(list)
    actor_activeactor_refs = defaultdict(set)
    actor_custom_names = {}
    actor_object_types = {}
    
    print(f"\n================== DYNAMIC SCANNING ==================")
    print(f"Processing {len(frames)} frames with {len(objects_pool)} object definitions")
    
    # PASS 1: Collect ALL data
    print("Scanning all frames for discovery...")
    
    for frame_idx, frame in enumerate(frames):
        for updated_actor in frame.get("updated_actors", []):
            act_id = updated_actor["actor_id"]
            attr_id = updated_actor["object_id"]
            attr_payload = updated_actor.get("attribute")
            
            if attr_payload is None or attr_id >= len(objects_pool):
                continue
                
            attr_name = objects_pool[attr_id]
            actor_attributes[act_id].add(attr_name)
            
            # Store custom_name
            if "custom_name" in attr_payload:
                custom_name = attr_payload.get("custom_name", "")
                if custom_name:
                    actor_custom_names[act_id] = custom_name
            
            # Store ActorType
            if "ActorType" in attr_payload:
                actor_type = attr_payload.get("ActorType", "")
                if actor_type:
                    actor_object_types[act_id] = actor_type
            
            # Store strings
            if "String" in attr_payload:
                raw_value = attr_payload.get("String", "")
                if raw_value and len(raw_value) > 1:
                    clean_value = raw_value.replace('"', '').strip()
                    actor_strings[act_id] = clean_value
                    
                    # Check if this is a unique ID (hex string)
                    if re.match(r'^[0-9a-fA-F]+$', clean_value.replace('-', '')) and len(clean_value) >= 30:
                        actor_unique_ids[act_id] = clean_value
                    else:
                        # This is a display name
                        technical_patterns = ['default', 'object', 'none', 'null', 'actor', 
                                             'player_', 'unknown', 'undefined', 'class', 'function', 'script']
                        if len(clean_value) > 2 and not any(p in clean_value.lower() for p in technical_patterns):
                            actor_display_names[act_id].append(clean_value)
            
            # Store RigidBody data
            if "RigidBody" in attr_payload:
                rb = attr_payload["RigidBody"]
                if isinstance(rb, dict):
                    loc = rb.get("location")
                    vel = rb.get("linear_velocity")
                    
                    pos = (0, 0, 0)
                    if isinstance(loc, dict):
                        pos = (loc.get("x", 0), loc.get("y", 0), loc.get("z", 0))
                    
                    vel_tuple = (0, 0, 0)
                    if isinstance(vel, dict):
                        vel_tuple = (vel.get("x", 0), vel.get("y", 0), vel.get("z", 0))
                    
                    actor_rigidbody_data[act_id].append({
                        'frame': frame_idx,
                        'time': frame.get("time", 0),
                        'pos': pos,
                        'vel': vel_tuple
                    })
            
            # Store Byte data (boost)
            if "Byte" in attr_payload:
                byte_val = attr_payload.get("Byte", 0)
                actor_byte_data[act_id].append({
                    'frame': frame_idx,
                    'time': frame.get("time", 0),
                    'value': byte_val
                })
            
            # Store ActiveActor references
            if "ActiveActor" in attr_payload:
                target = attr_payload["ActiveActor"]
                if isinstance(target, dict) and "actor" in target:
                    target_id = target["actor"]
                    if isinstance(target_id, int):
                        actor_activeactor_refs[act_id].add(target_id)
    
    # PASS 2: Identify Players
    player_actors = {}
    
    def is_real_player_name(name):
        """Returns True if the name looks like a real player name."""
        if re.match(r'^Player\s*\d+$', name, re.IGNORECASE):
            return False
        technical = ['default', 'object', 'none', 'null', 'unknown', 'undefined']
        if any(t in name.lower() for t in technical):
            return False
        return any(c.isalpha() for c in name) and len(name) > 1
    
    for act_id, names in actor_display_names.items():
        if not names:
            continue
        
        real_names = [n for n in names if is_real_player_name(n)]
        player_names = [n for n in names if not is_real_player_name(n)]
        
        preferred_name = real_names[0] if real_names else names[0]
        unique_id = actor_unique_ids.get(act_id, None)
        
        player_actors[act_id] = {
            'name': preferred_name,
            'all_names': names,
            'unique_id': unique_id,
            'id_type': 'real_name' if real_names else 'generic'
        }
        
        print(f"✅ Player: Actor {act_id} -> '{preferred_name}'")
    
    if not player_actors:
        for act_id, unique_id in actor_unique_ids.items():
            player_actors[act_id] = {
                'name': unique_id[:8],
                'unique_id': unique_id,
                'id_type': 'unique_id'
            }
            print(f"✅ Player (by ID): Actor {act_id} -> '{unique_id[:8]}...'")
    
    # PASS 3: Identify Ball - Using Multiple Methods
    print("\n🔍 Searching for ball...")
    ball_actor_ids = set()
    
    # METHOD 1: Check custom_name for "ball"
    print("  Method 1: Checking custom_name for 'ball'...")
    for act_id, custom_name in actor_custom_names.items():
        if 'ball' in custom_name.lower():
            print(f"    ✅ Ball found by custom_name: Actor {act_id} -> '{custom_name}'")
            ball_actor_ids.add(act_id)
    
    # METHOD 2: Check ActorType for ball-related types
    print("  Method 2: Checking ActorType for ball...")
    for act_id, actor_type in actor_object_types.items():
        if 'ball' in actor_type.lower():
            print(f"    ✅ Ball found by ActorType: Actor {act_id} -> '{actor_type}'")
            ball_actor_ids.add(act_id)
    
    # METHOD 3: Check object attributes for ball references
    print("  Method 3: Checking object attributes for ball...")
    for act_id, attrs in actor_attributes.items():
        attrs_str = ' '.join(attrs).lower()
        if 'ball' in attrs_str:
            # Make sure it's not a player (players might have "ball" in their attributes)
            if act_id not in player_actors:
                print(f"    ✅ Ball found by attributes: Actor {act_id}")
                ball_actor_ids.add(act_id)
    
    # METHOD 4: Check for specific ball object types in the pool
    print("  Method 4: Checking object pool for ball types...")
    ball_object_indices = set()
    for idx, obj_name in enumerate(objects_pool):
        if 'ball' in obj_name.lower():
            ball_object_indices.add(idx)
    
    for act_id, attrs in actor_attributes.items():
        if act_id not in player_actors:
            for idx in ball_object_indices:
                if idx in attrs or str(idx) in attrs:
                    ball_actor_ids.add(act_id)
                    break
    
    # METHOD 5: Movement-based fallback
    if not ball_actor_ids:
        print("  Method 5: Fallback - using movement patterns...")
        ball_candidates = {}
        
        for act_id in actor_rigidbody_data:
            if act_id in player_actors:
                continue
            if act_id in actor_byte_data:
                continue
            
            data = actor_rigidbody_data[act_id]
            if len(data) < 10:
                continue
            
            total_dist = 0
            max_speed = 0
            z_values = []
            
            for i in range(1, len(data)):
                prev_pos = data[i-1]['pos']
                curr_pos = data[i]['pos']
                dist = ((curr_pos[0] - prev_pos[0])**2 + 
                       (curr_pos[1] - prev_pos[1])**2 + 
                       (curr_pos[2] - prev_pos[2])**2) ** 0.5
                total_dist += dist
                
                vel = data[i]['vel']
                speed = (vel[0]**2 + vel[1]**2 + vel[2]**2) ** 0.5
                if speed > max_speed:
                    max_speed = speed
                
                z_values.append(curr_pos[2])
            
            if z_values:
                z_range = max(z_values) - min(z_values)
                avg_z = sum(z_values) / len(z_values)
            else:
                z_range = 0
                avg_z = 0
            
            ball_candidates[act_id] = {
                'total_dist': total_dist,
                'max_speed': max_speed,
                'z_range': z_range,
                'avg_z': avg_z,
                'data_points': len(data)
            }
        
        sorted_candidates = sorted(ball_candidates.items(), 
                                  key=lambda x: (x[1]['total_dist'] + x[1]['z_range'] * 2), 
                                  reverse=True)
        
        for act_id, stats in sorted_candidates[:3]:
            if stats['total_dist'] > 100 and stats['z_range'] > 50:
                print(f"    ✅ Ball found by movement: Actor {act_id}")
                ball_actor_ids.add(act_id)
    
    # Print final ball actors
    if ball_actor_ids:
        print(f"\n  ✅ Ball actors found: {sorted(ball_actor_ids)}")
    else:
        print("  ❌ No ball found! Ball data will be zeros.")
    
    # PASS 4: Identify ALL cars for each player
    player_cars = defaultdict(list)
    unique_id_to_player = {}
    for act_id, player_info in player_actors.items():
        if player_info['unique_id']:
            unique_id_to_player[player_info['unique_id']] = player_info['name']
    
    print(f"\n🏎️ Finding cars for each player...")
    
    for act_id in actor_rigidbody_data:
        if act_id not in ball_actor_ids and act_id in actor_byte_data:
            if len(actor_rigidbody_data[act_id]) > 5:
                player_name = None
                
                if act_id in actor_activeactor_refs:
                    for ref_id in actor_activeactor_refs[act_id]:
                        if ref_id in player_actors:
                            player_name = player_actors[ref_id]['name']
                            break
                
                if not player_name:
                    for ref_actor, refs in actor_activeactor_refs.items():
                        if act_id in refs and ref_actor in player_actors:
                            player_name = player_actors[ref_actor]['name']
                            break
                
                if not player_name and act_id in actor_unique_ids:
                    car_unique_id = actor_unique_ids[act_id]
                    if car_unique_id in unique_id_to_player:
                        player_name = unique_id_to_player[car_unique_id]
                
                if player_name:
                    player_cars[player_name].append({
                        'car_id': act_id,
                        'first_frame': actor_rigidbody_data[act_id][0]['frame'],
                        'last_frame': actor_rigidbody_data[act_id][-1]['frame'],
                        'first_time': actor_rigidbody_data[act_id][0]['time'],
                        'last_time': actor_rigidbody_data[act_id][-1]['time'],
                        'data_points': len(actor_rigidbody_data[act_id])
                    })
    
    # PASS 5: Stitch cars together
    print(f"\n🏎️ Stitching cars for each player...")
    
    car_to_player = {}
    for player_name, car_list in player_cars.items():
        for car_info in car_list:
            car_to_player[car_info['car_id']] = player_name
        
        car_list.sort(key=lambda x: x['first_time'])
        
        print(f"  {player_name}: {len(car_list)} cars")
        for i, car in enumerate(car_list):
            print(f"    Car {car['car_id']}: {car['first_time']:.1f}s - {car['last_time']:.1f}s ({car['data_points']} frames)")
    
    # PASS 6: Find Boost relationships
    boost_to_car = {}
    for boost_actor, target_ids in actor_activeactor_refs.items():
        for target_id in target_ids:
            if target_id in car_to_player and boost_actor in actor_byte_data:
                boost_to_car[boost_actor] = target_id
                break
    
    # PASS 7: Detect game start
    print("\n⏱️ Detecting game start...")
    game_start_frame = 0
    game_start_time = 0.0
    found_movement = False
    
    all_cars = set(car_to_player.keys())
    for frame_idx, frame in enumerate(frames):
        if found_movement:
            break
        time_stamp = frame.get("time", 0.0)
        
        for updated_actor in frame.get("updated_actors", []):
            act_id = updated_actor["actor_id"]
            if act_id not in all_cars:
                continue
                
            attr_payload = updated_actor.get("attribute")
            if attr_payload is None:
                continue
                
            if "RigidBody" in attr_payload:
                rb = attr_payload["RigidBody"]
                if isinstance(rb, dict):
                    lin_vel = rb.get("linear_velocity")
                    if isinstance(lin_vel, dict):
                        vel_mag = abs(lin_vel.get("x", 0)) + abs(lin_vel.get("y", 0)) + abs(lin_vel.get("z", 0))
                        if vel_mag > 10:
                            game_start_frame = frame_idx
                            game_start_time = time_stamp
                            found_movement = True
                            print(f"🏁 First movement at frame {frame_idx}, time {time_stamp:.3f}s")
                            break
    
    if not found_movement:
        print("⚠️ No movement detected, using 6-second offset...")
        for frame_idx, frame in enumerate(frames):
            if frame.get("time", 0.0) >= 6.0:
                game_start_frame = frame_idx
                game_start_time = frame.get("time", 0.0)
                break
    
    print(f"🎮 Game start: Frame {game_start_frame}, Time {game_start_time:.3f}s")
    
    # PASS 8: Build Telemetry Dataframe
    print("\n🏎️ Building telemetry dataframe with boost statistics...")
    current_state = {}
    telemetry_records = []
    
    all_cars_set = set(car_to_player.keys())
    all_boost = set(boost_to_car.keys())
    tracked_actors = all_cars_set | ball_actor_ids | all_boost
    
    print(f"  Tracking {len(tracked_actors)} actors: {len(all_cars_set)} cars, {len(ball_actor_ids)} ball(s), {len(all_boost)} boost")
    
    player_current_car = {player: None for player in set(car_to_player.values())}
    player_last_active = {player: -1 for player in set(car_to_player.values())}
    
    car_time_ranges = {}
    for car_id in all_cars_set:
        if car_id in actor_rigidbody_data and len(actor_rigidbody_data[car_id]) > 0:
            car_time_ranges[car_id] = {
                'first': actor_rigidbody_data[car_id][0]['frame'],
                'last': actor_rigidbody_data[car_id][-1]['frame'],
                'first_time': actor_rigidbody_data[car_id][0]['time'],
                'last_time': actor_rigidbody_data[car_id][-1]['time']
            }
    
    # Track the current active ball actor across frames
    current_ball_actor = None
    
    for frame_idx, frame in enumerate(frames):
        time_stamp = frame.get("time", 0.0)
        adjusted_time = time_stamp - game_start_time
        
        if adjusted_time < 0:
            adjusted_time = 0.0
        
        # Update current_state with all tracked actors
        for updated_actor in frame.get("updated_actors", []):
            act_id = updated_actor["actor_id"]
            if act_id not in tracked_actors:
                continue
                
            attr_payload = updated_actor.get("attribute")
            if attr_payload is None:
                continue
            
            if "RigidBody" in attr_payload:
                rb = attr_payload["RigidBody"]
                if isinstance(rb, dict):
                    loc = rb.get("location")
                    if isinstance(loc, dict):
                        current_state[f"pos_x_{act_id}"] = loc.get("x", 0.0)
                        current_state[f"pos_y_{act_id}"] = loc.get("y", 0.0)
                        current_state[f"pos_z_{act_id}"] = loc.get("z", 0.0)
                    
                    lin_vel = rb.get("linear_velocity")
                    if isinstance(lin_vel, dict):
                        current_state[f"vel_x_{act_id}"] = lin_vel.get("x", 0.0)
                        current_state[f"vel_y_{act_id}"] = lin_vel.get("y", 0.0)
                        current_state[f"vel_z_{act_id}"] = lin_vel.get("z", 0.0)
            
            if "Byte" in attr_payload:
                byte_val = attr_payload.get("Byte", 0)
                current_state[f"byte_{act_id}"] = byte_val
        
        # Determine which car each player is using
        for player_name, car_list in player_cars.items():
            current_car = None
            
            for car_info in car_list:
                car_id = car_info['car_id']
                if car_id in car_time_ranges:
                    car_range = car_time_ranges[car_id]
                    if car_range['first'] <= frame_idx <= car_range['last']:
                        current_car = car_id
                        break
            
            if current_car is not None:
                player_current_car[player_name] = current_car
                player_last_active[player_name] = frame_idx
        
        # Build the row
        row = {"frame": frame_idx, "time": adjusted_time}
        
        # Player data
        for player_name, current_car in player_current_car.items():
            clean_name = re.sub(r'[^a-zA-Z0-9]', '_', player_name)
            clean_name = clean_name.lstrip('_')
            if not clean_name:
                clean_name = f"Player_{current_car}"
            
            if current_car is not None:
                row[f"{clean_name}_pos_x"] = current_state.get(f"pos_x_{current_car}", np.nan)
                row[f"{clean_name}_pos_y"] = current_state.get(f"pos_y_{current_car}", np.nan)
                row[f"{clean_name}_pos_z"] = current_state.get(f"pos_z_{current_car}", np.nan)
                row[f"{clean_name}_vel_x"] = current_state.get(f"vel_x_{current_car}", 0.0)
                row[f"{clean_name}_vel_y"] = current_state.get(f"vel_y_{current_car}", 0.0)
                row[f"{clean_name}_vel_z"] = current_state.get(f"vel_z_{current_car}", 0.0)
                
                # Boost data
                boost_found = False
                for boost_id, linked_car_id in boost_to_car.items():
                    if linked_car_id == current_car:
                        boost_val = current_state.get(f"byte_{boost_id}", 0)
                        row[f"{clean_name}_boost"] = (boost_val / 255.0) * 100.0
                        boost_found = True
                        break
                
                if not boost_found:
                    boost_val = current_state.get(f"byte_{current_car}", 0)
                    row[f"{clean_name}_boost"] = (boost_val / 255.0) * 100.0
            else:
                row[f"{clean_name}_pos_x"] = np.nan
                row[f"{clean_name}_pos_y"] = np.nan
                row[f"{clean_name}_pos_z"] = np.nan
                row[f"{clean_name}_vel_x"] = 0.0
                row[f"{clean_name}_vel_y"] = 0.0
                row[f"{clean_name}_vel_z"] = 0.0
                row[f"{clean_name}_boost"] = 0.0
        
        # Ball data - FIND THE ACTIVE BALL ACTOR FOR THIS FRAME
        ball_pos_x = 0.0
        ball_pos_y = 0.0
        ball_pos_z = 0.0
        ball_vel_x = 0.0
        ball_vel_y = 0.0
        ball_vel_z = 0.0
        
        # Check all ball actors to find the active one for this frame
        active_ball_found = False
        for ball_id in ball_actor_ids:
            # Check if this ball actor has position data in current_state
            pos_x = current_state.get(f"pos_x_{ball_id}", None)
            if pos_x is not None and not np.isnan(pos_x):
                # This ball actor has data in this frame
                ball_pos_x = pos_x
                ball_pos_y = current_state.get(f"pos_y_{ball_id}", 0.0)
                ball_pos_z = current_state.get(f"pos_z_{ball_id}", 0.0)
                ball_vel_x = current_state.get(f"vel_x_{ball_id}", 0.0)
                ball_vel_y = current_state.get(f"vel_y_{ball_id}", 0.0)
                ball_vel_z = current_state.get(f"vel_z_{ball_id}", 0.0)
                current_ball_actor = ball_id  # Update the current ball actor
                active_ball_found = True
                break
        
        # If no ball actor has data in this frame, keep previous values
        # (This handles the case where the ball is deleted/recreated)
        # But we should still try to find the new ball actor in the next frame
        if not active_ball_found:
            # Check if any ball actor has data that we missed
            for ball_id in ball_actor_ids:
                pos_x = current_state.get(f"pos_x_{ball_id}", None)
                if pos_x is not None and not np.isnan(pos_x):
                    # Found a ball actor with data
                    ball_pos_x = pos_x
                    ball_pos_y = current_state.get(f"pos_y_{ball_id}", 0.0)
                    ball_pos_z = current_state.get(f"pos_z_{ball_id}", 0.0)
                    ball_vel_x = current_state.get(f"vel_x_{ball_id}", 0.0)
                    ball_vel_y = current_state.get(f"vel_y_{ball_id}", 0.0)
                    ball_vel_z = current_state.get(f"vel_z_{ball_id}", 0.0)
                    current_ball_actor = ball_id
                    active_ball_found = True
                    break
        
        row["Ball_pos_x"] = ball_pos_x
        row["Ball_pos_y"] = ball_pos_y
        row["Ball_pos_z"] = ball_pos_z
        row["Ball_vel_x"] = ball_vel_x
        row["Ball_vel_y"] = ball_vel_y
        row["Ball_vel_z"] = ball_vel_z
        
        telemetry_records.append(row)
    
    df = pd.DataFrame(telemetry_records)
    
    if not df.empty:
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        df.fillna(0, inplace=True)
    
    # Calculate boost statistics for each player
    print(f"\n📊 {replay_date} Boost Statistics:")
    print("-" * 60)
    for player_name in player_cars.keys():
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', player_name)
        clean_name = clean_name.lstrip('_')
        
        if f"{clean_name}_boost" in df.columns:
            boost_col = df[f"{clean_name}_boost"]
            
            avg_boost = boost_col.mean()
            max_boost = boost_col.max()
            min_boost = boost_col.min()
            boost_usage = boost_col.diff().abs().sum()
            
            high_boost_time = (boost_col > 80).sum() / len(df) * 100
            low_boost_time = (boost_col < 20).sum() / len(df) * 100
            
            print(f"  {player_name}:")
            print(f"    Avg Boost: {avg_boost:.1f}%")
            print(f"    Max Boost: {max_boost:.1f}%")
            print(f"    Min Boost: {min_boost:.1f}%")
            print(f"    Boost Usage: {boost_usage:.0f}% (total change)")
            print(f"    Time with >80% boost: {high_boost_time:.1f}%")
            print(f"    Time with <20% boost: {low_boost_time:.1f}%")
    
    print("-" * 60)
    
    print(f"\n✅ Generated dataframe with boost statistics:")
    print(f"  - Rows: {len(df)}")
    print(f"  - Columns: {len(df.columns)}")
    if not df.empty:
        print(f"  - Duration: {df['time'].max():.2f}s")
        print(f"  - Players: {list(player_cars.keys())}")
        print(f"  - Total cars stitched: {len(all_cars_set)}")
        print(f"  - Ball actors: {list(ball_actor_ids)}")
        print(f"  - Columns: {df.columns.tolist()}")
    
    return df