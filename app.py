# Importing key Libraries

import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta, timezone, time
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

load_dotenv()

# Configure application
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.secret_key = os.getenv("SECRET_KEY")

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
        print(f"✅ Loaded {len(ips)} authorized IPs from .env")
        print(f"   IPs: {ips}")
    else:
        print("⚠️ No authorized IPs found in .env")
    
    return ips

def is_ip_authorized(ip):
    """Check if IP is authorized"""
    if not ip:
        return False
    return redis_client.sismember(WHITELIST_KEY, ip)

def get_client_ip():
    """Get client IP behind nginx"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

# Initialize rate limiter with Redis
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="redis://localhost:6379/0",
    default_limits=["100 per minute"],
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
        'error': 'Rate limit exceeded',
        'message': '2 per 1 hour',
        'retry_after': None
    }), 429

# Initialize and connect your server-side session database
db = SQLAlchemy()
app.config["SESSION_TYPE"] = "sqlalchemy"
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config["SESSION_SQLALCHEMY"] = db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SESSION_SQLALCHEMY_TABLE"] = "sessions"  # Automatically creates this table in Postgres

db.init_app(app)
Session(app)

# Database Models
class PlayerProfile(db.Model):
    __tablename__ = 'player_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_accessed = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    api_call_count = db.Column(db.Integer, default=1)
    session_id = db.Column(db.String(255))  # Store session ID for tracking
    
    __table_args__ = (
        db.UniqueConstraint('platform', 'username', name='unique_player'),
    )

class APICallLog(db.Model):
    """Optional: Track API calls for monitoring"""
    __tablename__ = 'api_call_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))
    username = db.Column(db.String(100))
    success = db.Column(db.Boolean, default=True)
    response_code = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    response_size = db.Column(db.Integer)  # Size of response in bytes

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
    
    return render_template(
        'results.html',
        data=data,
        recent_matches=recent_matches,
        match_summary=match_summary,
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
@limiter.limit("2 per hour")
def query_api():
    """Handle API query with session caching"""
    try:
        req_data = request.get_json()
        platform = req_data.get('platform_id', '').strip().lower()
        username = req_data.get('username', '').strip()
        force_refresh = req_data.get('force_refresh', True)
        
        # DEBUG: Log current session state
        print(f"🔍 Session before query: {dict(session)}")
        print(f"📝 Request: platform={platform}, username={username}, force_refresh={force_refresh}")
        
        if not platform or not username:
            return jsonify({'success': False, 'message': 'Missing platform or username'})
        
        # Check if we have data in session first (faster than DB query)
        session_data = session.get('api_data')
        session_platform = session.get('platform')
        session_username = session.get('username')
        
        # If session has data and it matches the current search and not forcing refresh
        if session_data and session_platform == platform and session_username == username and not force_refresh:
            app.logger.info(f"Serving data from session for {platform}:{username}")
            return jsonify({
                'success': True,
                'data': session_data,
                'message': f'Retrieved data from session cache',
                'from_cache': True,
                'cached_at': session.get('last_updated')
            })
        
        # Check database for cached data
        existing_profile = PlayerProfile.query.filter_by(
            platform=platform,
            username=username
        ).first()
        
        # If data exists in database and not forcing refresh
        if existing_profile and not force_refresh:
            # Check if data is recent (e.g., less than 24 hours old)
            time_since_update = datetime.now(timezone.utc) - existing_profile.updated_at
            cache_duration = timedelta(hours=24)
            
            if time_since_update < cache_duration:
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
                return jsonify({
                    'success': True,
                    'data': existing_profile.data,
                    'message': f'Retrieved cached data for {username} on {platform}',
                    'from_cache': True,
                    'cached_at': existing_profile.updated_at.isoformat()
                })
        
        # If we get here, we need to make a fresh API call
        app.logger.info(f"Making fresh API call for {platform}:{username}")
        
        api_key = os.getenv("API_KEY")
        if not api_key:
            return jsonify({'success': False, 'message': 'Server configuration error'})
        
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
        
        if response.status_code == 200:
            data = response.json()
            
            # Save to database
            if existing_profile:
                existing_profile.data = data
                existing_profile.updated_at = datetime.now(timezone.utc)
                existing_profile.last_accessed = datetime.now(timezone.utc)
                existing_profile.api_call_count += 1
                existing_profile.session_id = session.sid if hasattr(session, 'sid') else None
            else:
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
            
            # Store in session
            session['api_data'] = data
            session['platform'] = platform
            session['username'] = username
            session['from_cache'] = False
            session['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            return jsonify({
                'success': True,
                'data': data,
                'message': f'Successfully fetched fresh data for {username} on {platform}',
                'from_cache': False
            })
        else:
            return jsonify({
                'success': False,
                'message': f'API Error: {response.status_code}'
            })
            
    except Exception as e:
        app.logger.error(f"Error in query_api: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Force refresh data for current session"""
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
            return jsonify({'success': False, 'message': 'Server configuration error'})
        
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
            
            return jsonify({
            'success': True,
            'message': 'Data fetched successfully',
            'data': session['api_data']
        })
        
    except Exception as e:
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