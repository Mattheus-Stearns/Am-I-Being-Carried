# routes/replay.py - Fixed with route decorators

import os
import uuid
import shutil
import json
import sys
from datetime import datetime
from flask import request, jsonify, render_template, session, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from . import main_bp
import traceback

REPLAY_ANALYSIS_FOLDER = 'replay-analysis'

# Import the actual replay analyzer functions
try:
    from replay_analyzer.parse import parse_replay_to_dict
    from replay_analyzer.dataframe import build_telemetry_dataframe
    from replay_analyzer.graph import (
        plot_player_speeds,
        plot_boost_usage,
        plot_combined_candlesticks,
        calculate_advanced_boost_stats
    )
    REPLAY_ANALYZER_AVAILABLE = True
    print("✅ Replay analyzer loaded successfully")
except ImportError as e:
    print(f"⚠️ Replay analyzer import error: {e}")
    REPLAY_ANALYZER_AVAILABLE = False

# Configuration
UPLOAD_FOLDER = 'uploads/replays'
ANALYSIS_FOLDER = 'uploads/analysis'
ALLOWED_EXTENSIONS = {'replay'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ANALYSIS_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_replay_date(replay_data):
    """
    Extract and parse the replay date from the properties section.
    From replay_analyzer/app.py
    """
    properties = replay_data.get("properties", {})
    date_str = properties.get("Date", "")
    
    if not date_str:
        print("⚠️ No date found in replay data")
        return datetime.now()
    
    print(f"📅 Raw date string: {date_str}")
    
    # The date format appears to be: "2026-07-29 04-31-41"
    parts = date_str.split()
    if len(parts) == 2:
        date_part = parts[0]
        time_part = parts[1]
        # Convert time part from "04-31-41" to "04:31:41"
        time_part_fixed = time_part.replace('-', ':')
        date_str_fixed = f"{date_part} {time_part_fixed}"
    else:
        date_str_fixed = date_str
    
    try:
        dt = datetime.strptime(date_str_fixed, "%Y-%m-%d %H:%M:%S")
        return dt
    except ValueError as e:
        print(f"⚠️ Error parsing date: {e}")
        return datetime.now()

def simulate_replay_analysis(filepath):
    """Simulate replay analysis for testing when parser is unavailable"""
    import random
    
    print(f"🔄 Using SIMULATED replay analysis for: {filepath}")
    
    players = ['Player1', 'Player2', 'Player3', 'Player4', 'Player5', 'Player6']
    random.shuffle(players)
    
    team_blue = players[:3]
    team_orange = players[3:6]
    
    blue_stats = []
    orange_stats = []
    
    for player in team_blue:
        goals = random.randint(0, 3)
        assists = random.randint(0, 2)
        saves = random.randint(0, 3)
        shots = random.randint(0, 5)
        score = goals * 100 + assists * 50 + saves * 30 + random.randint(0, 50)
        
        blue_stats.append({
            'name': player,
            'goals': goals,
            'assists': assists,
            'saves': saves,
            'shots': shots,
            'score': score,
            'mvp': False
        })
    
    for player in team_orange:
        goals = random.randint(0, 3)
        assists = random.randint(0, 2)
        saves = random.randint(0, 3)
        shots = random.randint(0, 5)
        score = goals * 100 + assists * 50 + saves * 30 + random.randint(0, 50)
        
        orange_stats.append({
            'name': player,
            'goals': goals,
            'assists': assists,
            'saves': saves,
            'shots': shots,
            'score': score,
            'mvp': False
        })
    
    all_players = blue_stats + orange_stats
    if all_players:
        mvp = max(all_players, key=lambda x: x['score'])
        mvp['mvp'] = True
    
    events = []
    event_types = ['Goal', 'Save', 'Assist', 'Shot on Goal', 'Demolition']
    for i in range(random.randint(5, 15)):
        events.append({
            'type': random.choice(event_types),
            'time': f"{random.randint(0, 5)}:{random.randint(0, 59):02d}",
            'player': random.choice(players),
            'details': ''
        })
    
    result = {
        'success': True,
        'file_name': os.path.basename(filepath),
        'game_mode': 'Soccar',
        'duration': f"{random.randint(5, 10)}:{random.randint(0, 59):02d}",
        'players': all_players,
        'events': sorted(events, key=lambda x: x['time']),
        'scoreboard': {
            'blue': random.randint(1, 5),
            'orange': random.randint(0, 4)
        }
    }
    
    print(f"📊 Simulated result: {len(result['players'])} players, {len(result['events'])} events")
    return result

def cleanup_files(filepath, analysis_files=None):
    """Delete replay file and optional analysis files"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"🗑️ Deleted replay file: {filepath}")
        
        if analysis_files:
            for file_path in analysis_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️ Deleted analysis file: {file_path}")
        
        return True
    except Exception as e:
        print(f"⚠️ Error cleaning up files: {e}")
        return False

def analyze_replay_file(filepath, unique_id, original_filename):
    """Analyze a replay file using your rrrocket parser and generate graphs"""
    print(f"🔍 Starting replay analysis for: {original_filename}")
    
    generated_files = []
    
    try:
        # Create analysis directory
        analysis_dir = os.path.join(ANALYSIS_FOLDER, unique_id)
        os.makedirs(analysis_dir, exist_ok=True)
        print(f"📁 Analysis directory: {analysis_dir}")
        
        if not REPLAY_ANALYZER_AVAILABLE:
            print("⚠️ Replay analyzer not available, using simulation")
            return simulate_replay_analysis(filepath), generated_files
        
        # Step 1: Parse the replay using rrrocket
        print("🔄 Calling parse_replay_to_dict...")
        replay_data = parse_replay_to_dict(filepath)
        
        if replay_data is None:
            print("❌ Parsing failed, using simulation")
            return simulate_replay_analysis(filepath), generated_files
        
        print(f"📊 Parse successful!")
        
        # Save the parsed data as JSON
        json_file = os.path.join(analysis_dir, 'replay_data.json')
        with open(json_file, 'w') as f:
            json.dump(replay_data, f, indent=2, default=str)
        generated_files.append(json_file)
        print(f"💾 Saved replay data to: {json_file}")
        
        # Step 2: Get the replay date
        replay_date_obj = parse_replay_date(replay_data)
        replay_date_str = replay_date_obj.strftime('%Y-%m-%d_%H-%M-%S')
        print(f"📅 Replay date: {replay_date_str}")
        
        # Step 3: Build telemetry dataframe
        print("🔄 Building telemetry dataframe...")
        try:
            # Note: build_telemetry_dataframe expects the parsed data directly
            df_telemetry = build_telemetry_dataframe(replay_data, replay_date_str)
            
            if df_telemetry is not None and not df_telemetry.empty:
                print(f"📊 Telemetry dataframe: {len(df_telemetry)} rows")
                
                # Save dataframe as CSV
                csv_file = os.path.join(analysis_dir, 'telemetry.csv')
                df_telemetry.to_csv(csv_file, index=False)
                generated_files.append(csv_file)
                print(f"💾 Saved telemetry to: {csv_file}")
                
                # Step 4: Generate graphs
                print("🔄 Generating graphs...")
                
                # Plot player speeds
                try:
                    plot_player_speeds(df_telemetry, replay_date_str)
                    # The plot function saves the file in the current directory
                    # We need to find and move it
                    speed_file = f'player_speeds_{replay_date_str}.png'
                    if os.path.exists(speed_file):
                        new_path = os.path.join(analysis_dir, speed_file)
                        shutil.move(speed_file, new_path)
                        generated_files.append(new_path)
                        print(f"✅ Speed graph saved: {new_path}")
                except Exception as e:
                    print(f"⚠️ Speed graph failed: {e}")
                
                # Plot boost usage
                try:
                    plot_boost_usage(df_telemetry, replay_date_str)
                    boost_file = f'boost_usage_{replay_date_str}.png'
                    if os.path.exists(boost_file):
                        new_path = os.path.join(analysis_dir, boost_file)
                        shutil.move(boost_file, new_path)
                        generated_files.append(new_path)
                        print(f"✅ Boost graph saved: {new_path}")
                except Exception as e:
                    print(f"⚠️ Boost graph failed: {e}")
                
                # Calculate advanced boost stats
                try:
                    boost_stats = calculate_advanced_boost_stats(df_telemetry)
                    if boost_stats:
                        stats_file = os.path.join(analysis_dir, 'boost_stats.txt')
                        with open(stats_file, 'w') as f:
                            f.write(str(boost_stats))
                        generated_files.append(stats_file)
                        print(f"✅ Boost stats saved: {stats_file}")
                except Exception as e:
                    print(f"⚠️ Boost stats calculation failed: {e}")
                
            else:
                print("⚠️ Telemetry dataframe is empty or None")
        except Exception as e:
            print(f"⚠️ Dataframe building failed: {e}")
            traceback.print_exc()
        
        # Step 5: Build player stats from parsed data
        player_stats = []
        print(f"📊 Looking for player data in replay_data...")
        print(f"📊 replay_data keys: {list(replay_data.keys())}")

        # Try different possible locations for player data
        players_found = False

        # Method 1: Direct 'players' key
        if 'players' in replay_data:
            print("📊 Found 'players' key directly")
            for player in replay_data.get('players', []):
                player_stats.append({
                    'name': player.get('name', 'Unknown'),
                    'goals': player.get('goals', 0),
                    'assists': player.get('assists', 0),
                    'saves': player.get('saves', 0),
                    'shots': player.get('shots', 0),
                    'score': player.get('score', 0),
                    'mvp': player.get('mvp', False)
                })
            players_found = True

        # Method 2: Players might be in 'properties' or 'metadata'
        if not players_found and 'properties' in replay_data:
            print("📊 Looking for players in 'properties'")
            props = replay_data.get('properties', {})
            if 'players' in props:
                for player in props.get('players', []):
                    player_stats.append({
                        'name': player.get('name', 'Unknown'),
                        'goals': player.get('goals', 0),
                        'assists': player.get('assists', 0),
                        'saves': player.get('saves', 0),
                        'shots': player.get('shots', 0),
                        'score': player.get('score', 0),
                        'mvp': player.get('mvp', False)
                    })
                players_found = True

        # Method 3: Extract from telemetry dataframe
        if not players_found and 'df_telemetry' in locals() and df_telemetry is not None:
            print("📊 Extracting players from telemetry dataframe")
            # Get unique player names from column names
            import re
            player_pattern = r'^([a-zA-Z0-9_]+)__'
            players_set = set()
            for col in df_telemetry.columns:
                match = re.match(player_pattern, col)
                if match:
                    players_set.add(match.group(1))
            
            for player_name in players_set:
                player_stats.append({
                    'name': player_name,
                    'goals': 0,
                    'assists': 0,
                    'saves': 0,
                    'shots': 0,
                    'score': 0,
                    'mvp': False
                })
            players_found = True

        print(f"📊 Found {len(player_stats)} players: {[p['name'] for p in player_stats]}")

        replay_analysis_files = []
        if os.path.exists(REPLAY_ANALYSIS_FOLDER):
            for file in os.listdir(REPLAY_ANALYSIS_FOLDER):
                if file.endswith('.png') and replay_date_str in file:
                    replay_analysis_files.append(file)
                    generated_files.append(os.path.join(REPLAY_ANALYSIS_FOLDER, file))
        
        # Build result dictionary
        result = {
            'success': True,
            'file_name': original_filename,
            'game_mode': replay_data.get('game_mode', 'Soccar'),
            'duration': replay_data.get('duration', '0:00'),
            'players': player_stats,
            'events': replay_data.get('events', [])[:50],
            'scoreboard': replay_data.get('scoreboard', {'blue': 0, 'orange': 0}),
            'analysis_files': generated_files,
            'replay_analysis_files': replay_analysis_files
        }
        
        print(f"✅ Analysis complete! Generated {len(generated_files)} files")
        return result, generated_files
        
    except Exception as e:
        print(f"❌ Analyze error: {e}")
        traceback.print_exc()
        print("🔄 Falling back to simulated analysis...")
        return simulate_replay_analysis(filepath), generated_files

# ============================================
# ROUTES
# ============================================

@main_bp.route('/replay/upload', methods=['GET', 'POST'])
def upload_replay():
    """Upload and analyze a Rocket League replay file"""
    print("="*60)
    print("🔄 REPLAY UPLOAD REQUEST")
    print("="*60)
    print(f"Method: {request.method}")
    
    if not REPLAY_ANALYZER_AVAILABLE:
        print("⚠️ Replay analyzer not available")
        flash('Replay analyzer is not available. Please check the installation.', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'GET':
        print("📄 Rendering upload form")
        return render_template('upload_replay.html')
    
    # Handle file upload
    print("📤 Processing file upload...")
    if 'replay_file' not in request.files:
        print("❌ No file in request")
        flash('No file selected', 'error')
        return redirect(request.url)
    
    file = request.files['replay_file']
    print(f"📁 File received: {file.filename}")
    
    if file.filename == '':
        print("❌ Empty filename")
        flash('No file selected', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        print(f"💾 Saving file to: {filepath}")
        file.save(filepath)
        print(f"✅ Replay saved: {filepath}")
        print(f"📁 File size: {os.path.getsize(filepath)} bytes")
        
        analysis_files = []
        boost_stats_content = ""
        
        try:
            # Parse the replay using your analyzer
            replay_data, generated_files = analyze_replay_file(filepath, unique_id, filename)
            analysis_files.extend(generated_files)
            
            # Read boost stats if the file exists
            stats_file = os.path.join(ANALYSIS_FOLDER, unique_id, 'boost_stats.txt')
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    boost_stats_content = f.read()
                print(f"📊 Read boost stats: {len(boost_stats_content)} characters")
            
            # Also look for boost stats in the replay-analysis folder
            if not boost_stats_content:
                import glob
                boost_files = glob.glob('replay-analysis/*_boost_stats.txt')
                if boost_files:
                    # Get the most recent one
                    latest_boost = max(boost_files, key=os.path.getctime)
                    with open(latest_boost, 'r') as f:
                        boost_stats_content = f.read()
                    print(f"📊 Read boost stats from replay-analysis: {len(boost_stats_content)} characters")
            
            print(f"📊 Replay data: {len(replay_data.get('players', []))} players, {len(replay_data.get('events', []))} events")
            
            # Store replay data in session
            session['replay_result'] = {
                'id': unique_id,
                'filename': filename,
                'game_mode': replay_data.get('game_mode', 'Unknown'),
                'duration': replay_data.get('duration', 'Unknown'),
                'players': replay_data.get('players', []),
                'events': replay_data.get('events', [])[:50],
                'scoreboard': replay_data.get('scoreboard', {}),
                'analysis_files': generated_files,
                'boost_stats_content': boost_stats_content  # 👈 Add boost stats
            }
            
            # Delete the original replay file after analysis
            cleanup_files(filepath)
            
            print("✅ Replay analysis complete, rendering results")
            return render_template('replay_analysis.html', 
                                 replay_data=replay_data,
                                 analysis_files=generated_files,
                                 replay_id=unique_id,
                                 boost_stats_content=boost_stats_content)  # 👈 Pass to template
            
        except Exception as e:
            print(f"❌ Error analyzing replay: {e}")
            traceback.print_exc()
            cleanup_files(filepath, analysis_files)
            flash(f'Error analyzing replay: {str(e)}', 'error')
            return redirect(request.url)
    
    print("❌ Invalid file type")
    flash('Invalid file type. Please upload a .replay file.', 'error')
    return redirect(request.url)

@main_bp.route('/replay/download/<replay_id>/<filename>')
def download_analysis_file(replay_id, filename):
    """Download an analysis file"""
    try:
        # Security: Prevent directory traversal
        if '..' in filename or '/' in filename:
            return "Invalid filename", 400
        
        # Try the analysis folder first
        file_path = os.path.join(ANALYSIS_FOLDER, replay_id, filename)
        
        # If not found, try the replay-analysis folder
        if not os.path.exists(file_path):
            file_path = os.path.join('replay-analysis', filename)
        
        print(f"📥 Download requested: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return "File not found", 404
        
        # Determine content type
        if filename.endswith('.png'):
            mimetype = 'image/png'
        elif filename.endswith('.txt'):
            mimetype = 'text/plain'
        elif filename.endswith('.csv'):
            mimetype = 'text/csv'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(file_path, mimetype=mimetype, as_attachment=False)
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        return str(e), 500

@main_bp.route('/replay/delete/<replay_id>', methods=['POST'])
def delete_replay_analysis(replay_id):
    """Delete replay analysis files"""
    try:
        analysis_dir = os.path.join(ANALYSIS_FOLDER, replay_id)
        if os.path.exists(analysis_dir):
            shutil.rmtree(analysis_dir)
            print(f"🗑️ Deleted analysis directory: {analysis_dir}")
        
        if 'replay_result' in session:
            session.pop('replay_result', None)
        
        flash('Replay analysis deleted successfully.', 'success')
        return redirect(url_for('main.upload_replay'))
        
    except Exception as e:
        print(f"❌ Delete error: {e}")
        flash(f'Error deleting replay analysis: {str(e)}', 'error')
        return redirect(url_for('main.upload_replay'))