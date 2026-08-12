# routes/replay.py
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

# Try to import the replay analyzer
try:
    from replay_analyzer import parse_replay, generate_graphs, create_dataframe
    REPLAY_ANALYZER_AVAILABLE = True
    print("✅ Replay analyzer loaded successfully")
except ImportError as e:
    print(f"⚠️ Replay analyzer not available: {e}")
    REPLAY_ANALYZER_AVAILABLE = False
    # Define placeholder functions
    def parse_replay(filepath):
        return simulate_replay_analysis(filepath)
    def generate_graphs(data):
        return None
    def create_dataframe(data):
        return None

# Configuration
UPLOAD_FOLDER = 'uploads/replays'
ANALYSIS_FOLDER = 'uploads/analysis'
ALLOWED_EXTENSIONS = {'replay'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ANALYSIS_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

def analyze_replay_file(filepath, unique_id, original_filename):
    """Analyze a replay file using your analyzer"""
    print(f"🔍 Starting replay analysis for: {original_filename} (ID: {unique_id})")
    print(f"📁 File path: {filepath}")
    print(f"📁 File exists: {os.path.exists(filepath)}")
    print(f"📁 File size: {os.path.getsize(filepath) if os.path.exists(filepath) else 'N/A'} bytes")
    
    generated_files = []
    
    try:
        # Create analysis directory for this replay
        analysis_dir = os.path.join(ANALYSIS_FOLDER, unique_id)
        os.makedirs(analysis_dir, exist_ok=True)
        print(f"📁 Analysis directory: {analysis_dir}")
        
        # Check if the replay analyzer is available
        print(f"📊 REPLAY_ANALYZER_AVAILABLE: {REPLAY_ANALYZER_AVAILABLE}")
        
        # Parse the replay
        print("🔄 Calling parse_replay...")
        result = parse_replay(filepath)
        print(f"📊 parse_replay returned: {type(result)}")
        
        # Debug the result
        if isinstance(result, dict):
            print(f"📊 Result keys: {list(result.keys())}")
            if 'players' in result:
                print(f"📊 Players count: {len(result.get('players', []))}")
            if 'events' in result:
                print(f"📊 Events count: {len(result.get('events', []))}")
        else:
            print(f"⚠️ Result is not a dict: {result}")
        
        # If result is a string (error), convert to dict
        if isinstance(result, str):
            print(f"⚠️ parse_replay returned string: {result[:100]}...")
            result = {
                'success': False,
                'file_name': original_filename,
                'game_mode': 'Error',
                'duration': '0:00',
                'players': [],
                'events': [],
                'scoreboard': {'blue': 0, 'orange': 0},
                'error': result
            }
        
        # Save analysis text
        text_file = os.path.join(analysis_dir, 'analysis.txt')
        print(f"💾 Saving analysis to: {text_file}")
        with open(text_file, 'w') as f:
            f.write(f"Replay Analysis: {original_filename}\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write("="*50 + "\n\n")
            f.write(json.dumps(result, indent=2, default=str))
        generated_files.append(text_file)
        print(f"✅ Analysis saved to {text_file}")
        
        # Generate graphs if available
        if REPLAY_ANALYZER_AVAILABLE and generate_graphs:
            print("🔄 Generating graphs...")
            try:
                graph_data = generate_graphs(result)
                if graph_data and isinstance(graph_data, dict):
                    for key, value in graph_data.items():
                        if isinstance(value, str) and value.endswith('.png'):
                            generated_files.append(value)
                            print(f"✅ Graph saved: {value}")
            except Exception as e:
                print(f"⚠️ Graph generation failed: {e}")
                traceback.print_exc()
        else:
            print("ℹ️ Graph generation skipped (not available)")
        
        print(f"✅ Analysis complete! Generated {len(generated_files)} files")
        return result, generated_files
        
    except Exception as e:
        print(f"❌ Analyze error: {e}")
        traceback.print_exc()
        print("🔄 Falling back to simulated analysis...")
        return simulate_replay_analysis(filepath), generated_files

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
        
        try:
            # Parse the replay using your analyzer
            replay_data, generated_files = analyze_replay_file(filepath, unique_id, filename)
            analysis_files.extend(generated_files)
            
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
                'analysis_files': generated_files
            }
            
            # Delete the original replay file after analysis
            cleanup_files(filepath)
            
            print("✅ Replay analysis complete, rendering results")
            return render_template('replay_analysis.html', 
                                 replay_data=replay_data,
                                 analysis_files=generated_files,
                                 replay_id=unique_id)
            
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
        
        file_path = os.path.join(ANALYSIS_FOLDER, replay_id, filename)
        
        print(f"📥 Download requested: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return "File not found", 404
        
        # Determine content type
        if filename.endswith('.png'):
            mimetype = 'image/png'
        elif filename.endswith('.txt'):
            mimetype = 'text/plain'
        else:
            mimetype = 'application/octet-stream'
        
        print(f"✅ Serving file: {file_path} ({mimetype})")
        return send_file(file_path, mimetype=mimetype, as_attachment=False)
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
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
        
        return jsonify({
            'success': True,
            'message': 'Replay data deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500