# Importing key Libraries

import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, url_for
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta, timezone, time
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import re
import json
import stripe
from models import PlayerProfile, APICallLog, Feedback, Donation
from flask_migrate import Migrate
from database import db
from helper import calculate_carried_score

load_dotenv()

# Configure application
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.secret_key = os.getenv("SECRET_KEY")
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Redis connection
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)

WHITELIST_KEY = 'authorized_ips'

def load_authorized_ips():
    """Load authorized IPs from .env into Redis"""
    # Get IPs from .env
    ips_string = os.getenv('AUTHORIZED_IPS', '')
    ips = [ip.strip() for ip in ips_string.split(',') if ip.strip()]
    
    # Clear existing
    redis_client.delete(WHITELIST_KEY)
    
    # Add IPs to Redis
    if ips:
        redis_client.sadd(WHITELIST_KEY, *ips)
        print(f" Loaded {len(ips)} authorized IPs from .env")
        print(f"   IPs: {ips}")
    else:
        print(" No authorized IPs found in .env")
    
    return ips

def is_ip_authorized(ip):
    """Check if IP is authorized"""
    if not ip:
        return False
    return redis_client.sismember(WHITELIST_KEY, ip)

def get_client_ip():
    """Get client IP address from request"""
    # Check for forwarded IP (if behind proxy/nginx)
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return ip
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

# Initialize rate limiter with Redis
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="redis://localhost:6379/0",
    default_limits=["100 per day", "20 per hour"],
)

# Exempt authorized IPs from rate limiting
@limiter.request_filter
def ip_authorized_filter():
    client_ip = get_client_ip()
    return is_ip_authorized(client_ip)

# Error handler for rate limit
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'success': False,
        'message': 'Rate limit exceeded. Please wait 5 minutes before making another request.',
        'retry_after': 300  # 5 minutes in seconds
    }), 429

# Initialize and connect your server-side session databasex
app.config["SESSION_TYPE"] = "sqlalchemy"
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config["SESSION_SQLALCHEMY"] = db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SESSION_SQLALCHEMY_TABLE"] = "sessions"  # Automatically creates this table in Postgres

db.init_app(app)
Session(app)
migrate = Migrate(app, db)

# Create tables when the app starts
with app.app_context():
    load_authorized_ips()
    try:
        db.create_all()
        print("Database tables created/verified successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")


# Routes

@app.route('/')
def index():
    """Home page with search form"""
    # Clear any previous session data when visiting home
    # But keep the last search info for display
    return render_template('index.html')

@app.route('/results')
def results():
    """Display results page"""
    # Check if we have data in session
    data = session.get('api_data')
    platform = session.get('platform')
    username = session.get('username')
    from_cache = session.get('from_cache', False)
    last_updated = session.get('last_updated', None)
    
    # If we have session data from the request
    if not data and request.args.get('data'):
        import json
        data = json.loads(request.args.get('data'))
    
    # Process matches - extract all competitive matches
    all_matches = []
    competitive_playlists = [
        'Ranked Duel 1v1',
        'Ranked Doubles 2v2',
        'Ranked Standard 3v3'
    ]
    
    # IMPORTANT: Extract items from the nested structure
    # The data might be in data['data']['items'] or data['items']
    items = []
    if data:
        if 'data' in data and 'items' in data['data']:
            # Nested structure: {"data": {"items": [...]}}
            items = data['data']['items']
        elif 'items' in data:
            # Direct structure: {"items": [...]}
            items = data['items']
        else:
            # Try to find items anywhere
            for key, value in data.items():
                if key == 'items' or (isinstance(value, dict) and 'items' in value):
                    items = value.get('items', [])
                    break
    
    print(f"Found {len(items)} items to process")  # Debug
    
    if items:
        # Iterate through all sessions (items)
        for session_item in items:
            for match in session_item.get('matches', []):
                playlist = match.get('metadata', {}).get('playlist', '')
                is_grouped = match.get('metadata', {}).get('isGrouped', False)
                
                # Only include individual competitive matches (not grouped summaries)
                if playlist in competitive_playlists and not is_grouped:
                    # Extract stats
                    stats = match.get('stats', {})
                    
                    # Get values safely
                    def get_value(stats_dict, key):
                        val = stats_dict.get(key, {})
                        if isinstance(val, dict):
                            return val.get('value')
                        return val
                    
                    match_data = {
                        'playlist': playlist,
                        'result': match.get('metadata', {}).get('result', 'unknown'),
                        'date_collected': match.get('metadata', {}).get('dateCollected', ''),
                        'goals': get_value(stats, 'goals'),
                        'assists': get_value(stats, 'assists'),
                        'saves': get_value(stats, 'saves'),
                        'shots': get_value(stats, 'shots'),
                        'mvps': get_value(stats, 'mvps'),
                        'matches_played': get_value(stats, 'matchesPlayed'),
                        'wins': get_value(stats, 'wins'),
                    }
                    
                    # Get rating information
                    rating_stats = stats.get('rating', {})
                    if isinstance(rating_stats, dict):
                        match_data['rating'] = rating_stats.get('value')
                        # Get rating metadata
                        rating_metadata = rating_stats.get('metadata', {})
                        match_data['rating_delta'] = rating_metadata.get('ratingDelta')
                        match_data['tier'] = rating_metadata.get('tier')
                        match_data['division'] = rating_metadata.get('division')
                        match_data['icon_url'] = rating_metadata.get('iconUrl')
                    else:
                        match_data['rating'] = None
                        match_data['rating_delta'] = None
                        match_data['tier'] = None
                        match_data['division'] = None
                        match_data['icon_url'] = rating_metadata.get('iconUrl')
                    
                    all_matches.append(match_data)
        
        # Sort by date (most recent first)
        all_matches.sort(
            key=lambda x: x['date_collected'] if x['date_collected'] else '',
            reverse=True
        )
        
        # Get last 25 matches
        recent_matches = all_matches[:25]
        
        # Calculate summary statistics
        total_matches = len(recent_matches)
        
        # Determine wins based on result
        def is_win(result):
            if result:
                result_lower = result.lower()
                return 'victory' in result_lower or 'win' in result_lower
            return False
        
        wins = sum(1 for m in recent_matches if is_win(m['result']))
        losses = sum(1 for m in recent_matches if not is_win(m['result']) and m['result'])
        
        total_goals = sum(m.get('goals') or 0 for m in recent_matches)
        total_assists = sum(m.get('assists') or 0 for m in recent_matches)
        total_saves = sum(m.get('saves') or 0 for m in recent_matches)
        total_shots = sum(m.get('shots') or 0 for m in recent_matches)
        total_mvps = sum(m.get('mvps') or 0 for m in recent_matches)
        
        win_rate = round((wins / total_matches * 100) if total_matches > 0 else 0)
        
        match_summary = {
            'total_matches': total_matches,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_goals': total_goals,
            'total_assists': total_assists,
            'total_saves': total_saves,
            'total_shots': total_shots,
            'total_mvps': total_mvps,
            'avg_goals': round(total_goals / total_matches, 1) if total_matches > 0 else 0,
            'avg_assists': round(total_assists / total_matches, 1) if total_matches > 0 else 0,
            'avg_saves': round(total_saves / total_matches, 1) if total_matches > 0 else 0,
            'avg_shots': round(total_shots / total_matches, 1) if total_matches > 0 else 0,
        }
    else:
        recent_matches = []
        match_summary = {
            'total_matches': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'total_goals': 0,
            'total_assists': 0,
            'total_saves': 0,
            'total_shots': 0,
            'total_mvps': 0,
            'avg_goals': 0,
            'avg_assists': 0,
            'avg_saves': 0,
            'avg_shots': 0,
        }
    
    # Debug info to see what matches were found
    print(f"Found {len(all_matches)} total matches, showing {len(recent_matches)} recent")
    
    # After calculating match_summary, calculate carried score
    carried_score = calculate_carried_score(match_summary, recent_matches)
    
    # Determine "carried" category
    if carried_score >= 80:
        carried_label = "Heavy Carry"
        carried_color = "danger"
        carried_icon = "fa-bullseye"
        carried_description = "You're being significantly carried by your teammates. Focus on improving mechanics and positioning."
    elif carried_score >= 60:
        carried_label = "Sometimes Carried"
        carried_color = "warning"
        carried_icon = "fa-exclamation-triangle"
        carried_description = "You're getting carried some games. Work on consistency and team play."
    elif carried_score >= 40:
        carried_label = "Balanced"
        carried_color = "info"
        carried_icon = "fa-balance-scale"
        carried_description = "You're contributing fairly to your wins. Keep improving!"
    elif carried_score >= 20:
        carried_label = "Contributor"
        carried_color = "success"
        carried_icon = "fa-thumbs-up"
        carried_description = "You're pulling your weight in most games. Good job!"
    else:
        carried_label = "Carrying Others"
        carried_color = "primary"
        carried_icon = "fa-trophy"
        carried_description = "You're the one doing the carrying! Keep up the great work!"
    
    return render_template(
        'results.html',
        data=data,
        recent_matches=recent_matches,
        match_summary=match_summary,
        carried_score=carried_score,
        carried_label=carried_label,
        carried_color=carried_color,
        carried_icon=carried_icon,
        carried_description=carried_description,
        username=username,
        platform=platform,
        from_cache=from_cache,
        last_updated=last_updated,
        total_matches_found=len(all_matches),
        debug_items_found=len(items)
    )

# Custom filter for date formatting
@app.template_filter('format_date')
def format_date(date_string):
    if not date_string:
        return 'N/A'
    try:
        date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return date_obj.strftime('%Y-%m-%d %H:%M')
    except:
        return date_string[:16] if date_string else 'N/A'

@app.route('/api/query', methods=['POST'])
@limiter.limit("1 per 5 minutes")
def query_api():
    """Handle API query with session caching"""
    start_time = datetime.now(timezone.utc)
    platform = None
    username = None
    
    print("=" * 60)
    print("QUERY_API CALLED")
    print("=" * 60)
    
    try:
        req_data = request.get_json()
        platform = req_data.get('platform_id', '').strip().lower()
        username = req_data.get('username', '').strip()
        force_refresh = req_data.get('force_refresh', True)
        
        print(f"Platform: {platform}")
        print(f"Username: {username}")
        print(f"Force Refresh: {force_refresh}")
        
        # ============================================
        # 1. INPUT VALIDATION - Prevent 422 errors
        # ============================================
        
        # Check missing fields
        if not platform or not username:
            error_msg = 'Missing platform or username'
            print(f"ERROR: {error_msg}")
            
            # Log validation error
            try:
                log = APICallLog(
                    platform=platform or 'unknown',
                    username=username or 'unknown',
                    success=False,
                    response_code=400,
                    error_message=error_msg,
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log validation error: {log_error}")
            
            return jsonify({
                'success': False, 
                'message': error_msg,
                'error_code': 'MISSING_FIELDS'
            }), 400
        
        # Validate platform
        valid_platforms = ['epic', 'steam', 'psn', 'xbox', 'switch']
        if platform not in valid_platforms:
            error_msg = f"Invalid platform: '{platform}'. Must be one of: {', '.join(valid_platforms)}"
            print(f"ERROR: {error_msg}")
            
            # Log validation error
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=400,
                    error_message=error_msg,
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log validation error: {log_error}")
            
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_code': 'INVALID_PLATFORM',
                'valid_platforms': valid_platforms
            }), 400
        
        # Validate username format
        if len(username) < 2:
            error_msg = 'Username must be at least 2 characters long'
            print(f"ERROR: {error_msg}")
            
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=400,
                    error_message=error_msg,
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log validation error: {log_error}")
            
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_code': 'USERNAME_TOO_SHORT'
            }), 400
        
        if len(username) > 100:
            error_msg = 'Username must be less than 100 characters'
            print(f"ERROR: {error_msg}")
            
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=400,
                    error_message=error_msg,
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log validation error: {log_error}")
            
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_code': 'USERNAME_TOO_LONG'
            }), 400
        
        # Validate username characters (no special characters that might break API)
        import re
        if not re.match(r'^[a-zA-Z0-9_.\- ]+$', username):
            error_msg = 'Username contains invalid characters. Only letters, numbers, underscores, hyphens, dots, and spaces are allowed.'
            print(f"ERROR: {error_msg}")
            
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=400,
                    error_message=error_msg,
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log validation error: {log_error}")
            
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_code': 'INVALID_USERNAME_CHARS'
            }), 400
        
        # ============================================
        # 2. SESSION CACHE CHECK
        # ============================================
        
        print(f"Session before query: {dict(session)}")
        
        # Check if we have data in session first (faster than DB query)
        session_data = session.get('api_data')
        session_platform = session.get('platform')
        session_username = session.get('username')
        
        print(f"Session data exists: {session_data is not None}")
        print(f"Session platform: {session_platform}")
        print(f"Session username: {session_username}")
        
        # If session has data and it matches the current search and not forcing refresh
        if session_data and session_platform == platform and session_username == username and not force_refresh:
            print("Serving from SESSION cache")
            app.logger.info(f"Serving data from session for {platform}:{username}")
            
            # LOG SESSION HIT
            try:
                print("Attempting to log session hit...")
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=True,
                    response_code=200,
                    error_message=None,
                    timestamp=datetime.now(timezone.utc),
                    response_size=len(json.dumps(session_data)) if session_data else 0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
                print(f"SUCCESS: Logged session hit for {platform}/{username}")
            except Exception as log_error:
                print(f"FAILED: Failed to log session hit: {log_error}")
                db.session.rollback()
            
            return jsonify({
                'success': True,
                'data': session_data,
                'message': f'Retrieved data from session cache',
                'from_cache': True,
                'cached_at': session.get('last_updated')
            })
        
        # ============================================
        # 3. DATABASE CACHE CHECK
        # ============================================
        
        print("Checking database for cached data...")
        existing_profile = PlayerProfile.query.filter_by(
            platform=platform,
            username=username
        ).first()
        
        print(f"Existing profile found: {existing_profile is not None}")
        
        # If data exists in database and not forcing refresh
        if existing_profile and not force_refresh:
            print("Database profile found, checking age...")
            # Check if data is recent (e.g., less than 24 hours old)
            time_since_update = datetime.now(timezone.utc) - existing_profile.updated_at
            cache_duration = timedelta(hours=24)
            
            print(f"Time since update: {time_since_update}")
            print(f"Cache duration: {cache_duration}")
            
            if time_since_update < cache_duration:
                print("Serving from DATABASE cache")
                # Update last accessed time
                existing_profile.last_accessed = datetime.now(timezone.utc)
                existing_profile.session_id = session.sid if hasattr(session, 'sid') else None
                db.session.commit()
                
                # Store in session
                session['api_data'] = existing_profile.data
                session['platform'] = platform
                session['username'] = username
                session['from_cache'] = True
                session['last_updated'] = existing_profile.updated_at.isoformat()
                
                app.logger.info(f"Serving data from database for {platform}:{username}")
                
                # LOG DATABASE HIT
                try:
                    print("Attempting to log database hit...")
                    log = APICallLog(
                        platform=platform,
                        username=username,
                        success=True,
                        response_code=200,
                        error_message=None,
                        timestamp=datetime.now(timezone.utc),
                        response_size=len(json.dumps(existing_profile.data)) if existing_profile.data else 0,
                        ip_address=get_client_ip()
                    )
                    db.session.add(log)
                    db.session.commit()
                    print(f"SUCCESS: Logged database hit for {platform}/{username}")
                except Exception as log_error:
                    print(f"FAILED: Failed to log database hit: {log_error}")
                    db.session.rollback()
                
                return jsonify({
                    'success': True,
                    'data': existing_profile.data,
                    'message': f'Retrieved cached data for {username} on {platform}',
                    'from_cache': True,
                    'cached_at': existing_profile.updated_at.isoformat()
                })
        
        # ============================================
        # 4. FRESH API CALL WITH RETRY LOGIC
        # ============================================
        
        print("Making FRESH API call...")
        app.logger.info(f"Making fresh API call for {platform}:{username}")
        
        api_key = os.getenv("API_KEY")
        print(f"API Key present: {api_key is not None}")
        
        if not api_key:
            print("ERROR: API_KEY missing")
            # LOG API KEY ERROR
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=500,
                    error_message='Server configuration error - API_KEY missing',
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
                print("Logged API key error")
            except Exception as log_error:
                print(f"Failed to log API key error: {log_error}")
            
            return jsonify({'success': False, 'message': 'Server configuration error'}), 500
        
        # URL encode username for API request
        import urllib.parse
        encoded_username = urllib.parse.quote(username)
        
        # Retry logic for transient errors (429, 502, 503, 504)
        max_retries = 3
        retry_delays = [1, 2, 5]  # Increasing delays
        response = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                print(f"API request attempt {attempt + 1}/{max_retries}")
                
                response = requests.get(
                    "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_sessions",
                    headers={
                        "X-API-Key": api_key,
                        "API-Snapshot-Version": "6",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    params={
                        "platform": platform,
                        "username": encoded_username
                    },
                    timeout=30
                )
                
                print(f"API Response Status: {response.status_code}")
                
                # If successful or client error (422, 404), don't retry
                if response.status_code == 200:
                    break
                elif response.status_code in [400, 404, 422]:
                    # Client errors - don't retry
                    break
                elif response.status_code in [429, 502, 503, 504]:
                    # Rate limited or server errors - retry
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        print(f"Status {response.status_code}. Retrying in {delay} seconds...")
                        time.sleep(delay)
                        continue
                    else:
                        break
                else:
                    # Other status codes
                    break
                    
            except requests.exceptions.Timeout:
                print(f"Request timeout (attempt {attempt + 1}/{max_retries})")
                last_error = "Request timeout"
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
                else:
                    response = None
                    break
                    
            except requests.exceptions.ConnectionError:
                print(f"Connection error (attempt {attempt + 1}/{max_retries})")
                last_error = "Connection error"
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
                else:
                    response = None
                    break
                    
            except Exception as e:
                print(f"Request error: {e}")
                last_error = str(e)
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
                else:
                    response = None
                    break
        
        # ============================================
        # 5. HANDLE API RESPONSE
        # ============================================
        
        # If no response after retries
        if response is None:
            error_msg = last_error or 'API request failed after retries'
            print(f"API call FAILED: {error_msg}")
            
            # LOG FAILED API CALL
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=500,
                    error_message=error_msg,
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
                print(f"Logged failed API call for {platform}/{username}")
            except Exception as log_error:
                print(f"Failed to log API call: {log_error}")
                db.session.rollback()
            
            return jsonify({
                'success': False,
                'message': f'API request failed: {error_msg}',
                'error_code': 'API_REQUEST_FAILED'
            }), 500
        
        response_size = len(response.content) if response.content else 0
        
        if response.status_code == 200:
            print("API call SUCCESSFUL")
            data = response.json()
            
            # Check if data contains valid session data
            if not data.get('items'):
                print("WARNING: API returned success but no items found")
                # This is a valid response but no data for this user
            
            # Save to database
            if existing_profile:
                print("Updating existing profile...")
                existing_profile.data = data
                existing_profile.updated_at = datetime.now(timezone.utc)
                existing_profile.last_accessed = datetime.now(timezone.utc)
                existing_profile.api_call_count += 1
                existing_profile.session_id = session.sid if hasattr(session, 'sid') else None
            else:
                print("Creating new profile...")
                new_profile = PlayerProfile(
                    platform=platform,
                    username=username,
                    data=data,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    last_accessed=datetime.now(timezone.utc),
                    session_id=session.sid if hasattr(session, 'sid') else None
                )
                db.session.add(new_profile)
            
            db.session.commit()
            print("Database updated successfully")
            
            # Store in session
            session['api_data'] = data
            session['platform'] = platform
            session['username'] = username
            session['from_cache'] = False
            session['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            # LOG SUCCESSFUL API CALL
            try:
                print("Attempting to log API success...")
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=True,
                    response_code=response.status_code,
                    error_message=None,
                    timestamp=datetime.now(timezone.utc),
                    response_size=response_size,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
                print(f"SUCCESS: Logged successful API call for {platform}/{username}")
            except Exception as log_error:
                print(f"FAILED: Failed to log API call: {log_error}")
                print(f"Error details: {log_error.__class__.__name__}: {str(log_error)}")
                db.session.rollback()
            
            return jsonify({
                'success': True,
                'data': data,
                'message': f'Successfully fetched fresh data for {username} on {platform}',
                'from_cache': False
            })
        
        elif response.status_code == 422:
            # Invalid request - user error
            error_msg = f'Invalid username or platform. Please check your input.'
            print(f"API call FAILED: {error_msg}")
            
            # LOG FAILED API CALL
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=response.status_code,
                    error_message=f'API returned 422: {response.text[:200]}',
                    timestamp=datetime.now(timezone.utc),
                    response_size=response_size,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log API call: {log_error}")
                db.session.rollback()
            
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_code': 'INVALID_USERNAME',
                'platform': platform,
                'username': username,
                'suggestion': 'Check if the username is correct and try again'
            }), 404
        
        elif response.status_code == 429:
            # Rate limited
            retry_after = int(response.headers.get('Retry-After', 60))
            error_msg = f'API rate limit exceeded. Please wait {retry_after} seconds.'
            print(f"API call FAILED: {error_msg}")
            
            # LOG FAILED API CALL
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=response.status_code,
                    error_message=f'Rate limited. Retry-After: {retry_after}s',
                    timestamp=datetime.now(timezone.utc),
                    response_size=response_size,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log API call: {log_error}")
                db.session.rollback()
            
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_code': 'RATE_LIMITED',
                'retry_after': retry_after
            }), 429
        
        elif response.status_code in [502, 503, 504]:
            # Server errors
            error_msg = f'The API service is temporarily unavailable. Please try again later.'
            print(f"API call FAILED: {error_msg}")
            
            # LOG FAILED API CALL
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=response.status_code,
                    error_message=f'API server error: {response.status_code}',
                    timestamp=datetime.now(timezone.utc),
                    response_size=response_size,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log API call: {log_error}")
                db.session.rollback()
            
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_code': 'API_SERVER_ERROR',
                'status_code': response.status_code
            }), response.status_code
        
        else:
            # Unknown error
            error_msg = f'API error: {response.status_code}'
            print(f"API call FAILED: {error_msg}")
            
            # LOG FAILED API CALL
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=response.status_code,
                    error_message=f'API returned {response.status_code}: {response.text[:200]}',
                    timestamp=datetime.now(timezone.utc),
                    response_size=response_size,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log API call: {log_error}")
                db.session.rollback()
            
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_code': 'API_UNKNOWN_ERROR',
                'status_code': response.status_code
            }), response.status_code
            
    except Exception as e:
        print(f"EXCEPTION in query_api: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # LOG UNEXPECTED ERROR
        try:
            log = APICallLog(
                platform=platform or 'unknown',
                username=username or 'unknown',
                success=False,
                response_code=500,
                error_message=f'Unexpected error: {str(e)}',
                timestamp=datetime.now(timezone.utc),
                response_size=0,
                ip_address=get_client_ip()
            )
            db.session.add(log)
            db.session.commit()
            print(f"Logged unexpected error: {str(e)}")
        except Exception as log_error:
            print(f"Failed to log error: {log_error}")
            db.session.rollback()
        
        app.logger.error(f"Error in query_api: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': 'An unexpected error occurred. Please try again.',
            'error_code': 'INTERNAL_ERROR'
        }), 500

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Force refresh data for current session"""
    platform = None
    username = None
    
    try:
        req_data = request.get_json()
        platform = req_data.get('platform_id', '').strip().lower()
        username = req_data.get('username', '').strip()
        
        if not platform or not username:
            return jsonify({'success': False, 'message': 'Missing platform or username'})
        
        # Force refresh by making a new API call
        app.logger.info(f"Forcing refresh for {platform}:{username}")
        
        api_key = os.getenv("API_KEY")
        if not api_key:
            # LOG API KEY ERROR
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=500,
                    error_message='Server configuration error - API_KEY missing',
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log API key error: {log_error}")
            
            return jsonify({'success': False, 'message': 'Server configuration error'})
        
        try:
            response = requests.get(
                "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_sessions",
                headers={
                    "X-API-Key": api_key,
                    "API-Snapshot-Version": "6"
                },
                params={
                    "platform": platform,
                    "username": username
                },
                timeout=30
            )
            
            response_size = len(response.content) if response.content else 0
            
            if response.status_code == 200:
                data = response.json()
                
                # Update database
                existing_profile = PlayerProfile.query.filter_by(
                    platform=platform,
                    username=username
                ).first()
                
                if existing_profile:
                    existing_profile.data = data
                    existing_profile.updated_at = datetime.now(timezone.utc)
                    existing_profile.api_call_count += 1
                else:
                    new_profile = PlayerProfile(
                        platform=platform,
                        username=username,
                        data=data,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                        session_id=session.sid if hasattr(session, 'sid') else None
                    )
                    db.session.add(new_profile)
                
                db.session.commit()
                
                # Update session
                session['api_data'] = data
                session['from_cache'] = False
                session['last_updated'] = datetime.now(timezone.utc).isoformat()
                
                # LOG REFRESH SUCCESS
                try:
                    log = APICallLog(
                        platform=platform,
                        username=username,
                        success=True,
                        response_code=response.status_code,
                        error_message=None,
                        timestamp=datetime.now(timezone.utc),
                        response_size=response_size,
                        ip_address=get_client_ip()
                    )
                    db.session.add(log)
                    db.session.commit()
                    print(f"Logged refresh for {platform}/{username}")
                except Exception as log_error:
                    print(f"Failed to log refresh: {log_error}")
                    db.session.rollback()
                
                return jsonify({
                    'success': True,
                    'message': 'Data fetched successfully',
                    'data': session['api_data']
                })
            else:
                # LOG REFRESH FAILED
                try:
                    log = APICallLog(
                        platform=platform,
                        username=username,
                        success=False,
                        response_code=response.status_code,
                        error_message=f'Refresh API returned {response.status_code}',
                        timestamp=datetime.now(timezone.utc),
                        response_size=response_size,
                        ip_address=get_client_ip()
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception as log_error:
                    print(f"Failed to log refresh failure: {log_error}")
                
                return jsonify({
                    'success': False,
                    'message': f'API Error: {response.status_code}'
                }), response.status_code
                
        except requests.exceptions.Timeout:
            # LOG TIMEOUT
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=408,
                    error_message='Refresh request timed out',
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log timeout: {log_error}")
            
            return jsonify({
                'success': False,
                'message': 'Refresh request timed out. Please try again.'
            }), 408
            
        except Exception as e:
            # LOG REFRESH ERROR
            try:
                log = APICallLog(
                    platform=platform,
                    username=username,
                    success=False,
                    response_code=500,
                    error_message=f'Refresh error: {str(e)}',
                    timestamp=datetime.now(timezone.utc),
                    response_size=0,
                    ip_address=get_client_ip()
                )
                db.session.add(log)
                db.session.commit()
            except Exception as log_error:
                print(f"Failed to log refresh error: {log_error}")
            
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
            
    except Exception as e:
        # LOG UNEXPECTED ERROR
        try:
            log = APICallLog(
                platform=platform or 'unknown',
                username=username or 'unknown',
                success=False,
                response_code=500,
                error_message=f'Unexpected refresh error: {str(e)}',
                timestamp=datetime.now(timezone.utc),
                response_size=0,
                ip_address=get_client_ip()
            )
            db.session.add(log)
            db.session.commit()
        except Exception as log_error:
            print(f"Failed to log unexpected error: {log_error}")
        
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Session management
@app.route('/api/clear_session', methods=['POST'])
def clear_session():
    session.clear()
    return jsonify({'success': True, 'message': 'Session cleared'})

@app.route('/api/session_status')
def session_status():
    """Check if session has data"""
    return jsonify({
        'has_data': bool(session.get('api_data')),
        'platform': session.get('platform'),
        'username': session.get('username'),
        'last_query': session.get('last_query_time')
    })

# Email validation helper
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('message'):
            return jsonify({
                'success': False,
                'message': 'Message is required'
            }), 400
        
        # Validate email if provided
        email = data.get('email', '').strip()
        if email and not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400
        
        # Create feedback entry
        feedback = Feedback(
            name=data.get('name', '').strip(),
            email=email,
            rating=data.get('rating', 0),
            message=data['message'].strip(),
            page_url=data.get('page_url', ''),
            user_agent=request.headers.get('User-Agent', ''),
            ip_address=request.remote_addr
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!'
        }), 200
        
    except Exception as e:
        print(f"Feedback error: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to submit feedback. Please try again.'
        }), 500

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    """Donation page with Stripe integration"""
    if request.method == 'GET':
        return render_template('donate.html', 
                             stripe_publishable_key=STRIPE_PUBLISHABLE_KEY)
    
    # POST request - Process donation
    try:
        data = request.json
        amount = data.get('amount')
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        is_anonymous = data.get('is_anonymous', False)
        show_on_wall = data.get('show_on_wall', False)
        
        # Validate amount
        if not amount or float(amount) < 1:
            return jsonify({
                'success': False,
                'message': 'Minimum donation is $1.00'
            }), 400
        
        # Validate email
        if email and not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400
        
        # Create Stripe customer
        customer = stripe.Customer.create(
            name=name if name else None,
            email=email if email else None,
            metadata={
                'name': name or 'Anonymous',
                'message': message,
                'is_anonymous': str(is_anonymous),
                'show_on_wall': str(show_on_wall)
            }
        )
        
        # Create payment intent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(float(amount) * 100),  # Convert to cents
            currency='usd',
            customer=customer.id,
            metadata={
                'name': name or 'Anonymous',
                'email': email or '',
                'message': message,
                'is_anonymous': str(is_anonymous)
            },
            receipt_email=email if email else None,
            description='Donation to Am I Being Carried?',
            statement_descriptor='Am I Being Carried?',
            payment_method_types=['card']
        )
        
        # Save to database
        donation = Donation(
            name=name,
            email=email,
            amount=amount,
            message=message,
            stripe_payment_id=payment_intent.id,
            stripe_customer_id=customer.id,
            status='pending',
            is_anonymous=is_anonymous,
            show_on_wall=show_on_wall
        )
        db.session.add(donation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'client_secret': payment_intent.client_secret,
            'payment_intent_id': payment_intent.id
        })
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        return jsonify({
            'success': False,
            'message': 'Payment processing error. Please try again.'
        }), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500

@app.route('/api/donation/success', methods=['POST'])
def donation_success():
    """Handle successful donation confirmation"""
    try:
        data = request.json
        payment_intent_id = data.get('payment_intent_id')
        
        if not payment_intent_id:
            return jsonify({'success': False, 'message': 'Missing payment intent ID'}), 400
        
        # Verify payment with Stripe
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if payment_intent.status == 'succeeded':
            # Update donation record
            donation = Donation.query.filter_by(
                stripe_payment_id=payment_intent_id
            ).first()
            
            if donation:
                donation.status = 'succeeded'
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Thank you for your support!',
                    'donation_id': donation.id
                })
        
        return jsonify({'success': False, 'message': 'Payment not confirmed'}), 400
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': 'Error processing confirmation'}), 500

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    import traceback
    
    try:
        # Get the raw payload
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature', '')
        content_type = request.headers.get('Content-Type', '')
        
        # Debug logging
        print("="*60)
        print("WEBHOOK RECEIVED")
        print("="*60)
        print(f"Content-Type: {content_type}")
        print(f"Signature present: {bool(sig_header)}")
        print(f"Payload length: {len(payload)}")
        print(f"Payload preview: {payload[:200]}...")
        
        # If no payload, return error
        if not payload:
            print("❌ Empty payload")
            return jsonify({'error': 'Empty payload'}), 400
        
        # ============================================
        # TEST MODE: No signature header
        # ============================================
        if not sig_header:
            print("⚠️ Test webhook - no signature header")
            print(f"Test data: {payload}")
            
            # Try to parse as JSON
            try:
                data = json.loads(payload)
                print(f"Test webhook data: {data}")
                
                # Check if it's our test webhook
                if data.get('type') == 'test':
                    return jsonify({
                        'status': 'success',
                        'message': 'Test webhook received',
                        'test': True
                    }), 200
                
                # Handle test payment_intent
                if data.get('id') and data.get('id').startswith('pi_'):
                    print(f"Test payment intent: {data.get('id')}")
                    return jsonify({
                        'status': 'success',
                        'message': 'Test payment intent received',
                        'payment_intent_id': data.get('id')
                    }), 200
                    
            except json.JSONDecodeError:
                print("Not valid JSON - test mode")
            
            # Always return success for test webhooks
            return jsonify({'status': 'success', 'test': True}), 200
        
        # ============================================
        # PRODUCTION MODE: Verify signature
        # ============================================
        # Make sure webhook secret is set
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not webhook_secret:
            print("❌ STRIPE_WEBHOOK_SECRET not set in environment")
            return jsonify({'error': 'Webhook secret not configured'}), 500
        
        print(f"Webhook secret present: {webhook_secret[:10]}...")
        
        # Verify the signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            print(f"✅ Webhook verified: {event['type']}")
            
        except ValueError as e:
            print(f"❌ Invalid webhook payload: {e}")
            print(f"Payload: {payload[:500]}")
            return jsonify({'error': 'Invalid payload'}), 400
            
        except stripe.error.SignatureVerificationError as e:
            print(f"❌ Invalid webhook signature: {e}")
            print(f"Signature header: {sig_header[:50]}...")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # ============================================
        # HANDLE EVENTS
        # ============================================
        try:
            event_type = event['type']
            print(f"Processing event: {event_type}")
            
            if event_type == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                payment_id = payment_intent['id']
                amount = payment_intent.get('amount', 0) / 100
                currency = payment_intent.get('currency', 'usd')
                customer_id = payment_intent.get('customer')
                metadata = payment_intent.get('metadata', {})
                
                print(f"💰 Payment successful: {payment_id}")
                print(f"   Amount: {amount} {currency.upper()}")
                print(f"   Customer: {customer_id}")
                print(f"   Metadata: {metadata}")
                
                # Update donation record
                try:
                    donation = Donation.query.filter_by(
                        stripe_payment_id=payment_id
                    ).first()
                    
                    if donation:
                        donation.status = 'succeeded'
                        donation.stripe_customer_id = customer_id
                        db.session.commit()
                        print(f"✅ Donation {donation.id} marked as succeeded")
                    else:
                        print(f"⚠️ Donation not found for payment: {payment_id}")
                        # Create a donation record if it doesn't exist (fallback)
                        new_donation = Donation(
                            name=metadata.get('name', 'Anonymous'),
                            email=metadata.get('email', ''),
                            amount=amount,
                            currency=currency,
                            message=metadata.get('message', ''),
                            stripe_payment_id=payment_id,
                            stripe_customer_id=customer_id,
                            status='succeeded',
                            is_anonymous=metadata.get('is_anonymous') == 'True',
                            show_on_wall=metadata.get('show_on_wall') == 'True'
                        )
                        db.session.add(new_donation)
                        db.session.commit()
                        print(f"✅ Created new donation record for {payment_id}")
                        
                except Exception as e:
                    print(f"❌ Error updating donation: {e}")
                    db.session.rollback()
            
            elif event_type == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                payment_id = payment_intent['id']
                print(f"❌ Payment failed: {payment_id}")
                
                try:
                    donation = Donation.query.filter_by(
                        stripe_payment_id=payment_id
                    ).first()
                    
                    if donation:
                        donation.status = 'failed'
                        db.session.commit()
                        print(f"❌ Donation {donation.id} marked as failed")
                except Exception as e:
                    print(f"❌ Error updating donation: {e}")
                    db.session.rollback()
            
            elif event_type == 'checkout.session.completed':
                print(f"🛒 Checkout completed")
                
            elif event_type == 'customer.subscription.created':
                print(f"📋 Subscription created")
            
            else:
                print(f"ℹ️ Unhandled event type: {event_type}")
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            print(f"❌ Error handling event: {e}")
            traceback.print_exc()
            # Return 200 to prevent Stripe from retrying
            return jsonify({'status': 'success', 'error': str(e)}), 200
        
    except Exception as e:
        print(f"❌ Unexpected webhook error: {e}")
        traceback.print_exc()
        # Return 200 to prevent Stripe from retrying
        return jsonify({'status': 'success'}), 200