# Importing key Libraries

import os
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import json
import requests
from datetime import datetime, timedelta

load_dotenv()

# Configure application
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.secret_key = os.getenv("SECRET_KEY")

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
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
    timestamp = db.Column(db.DateTime, default=datetime.now(datetime.timezone.utc))
    response_size = db.Column(db.Integer)  # Size of response in bytes

# Create tables when the app starts
with app.app_context():
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
    api_data = session.get('api_data')
    platform = session.get('platform')
    username = session.get('username')
    from_cache = session.get('from_cache', False)
    last_updated = session.get('last_updated')
    
    if not api_data:
        flash('No data found. Please perform a search first.', 'warning')
        return redirect(url_for('index'))
    
    return render_template('results.html', 
                         data=api_data,
                         platform=platform,
                         username=username,
                         from_cache=from_cache,
                         last_updated=last_updated)


@app.route('/api/query', methods=['POST'])
def query_api():
    """Handle API query with session caching"""
    try:
        req_data = request.get_json()
        platform = req_data.get('platform_id', '').strip().lower()
        username = req_data.get('username', '').strip()
        force_refresh = req_data.get('force_refresh', False)  # Optional: force refresh
        
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
            time_since_update = datetime.utcnow() - existing_profile.updated_at
            cache_duration = timedelta(hours=24)
            
            if time_since_update < cache_duration:
                # Update last accessed time
                existing_profile.last_accessed = datetime.utcnow()
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
            "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_profile",
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
                existing_profile.updated_at = datetime.utcnow()
                existing_profile.last_accessed = datetime.utcnow()
                existing_profile.api_call_count += 1
                existing_profile.session_id = session.sid if hasattr(session, 'sid') else None
            else:
                new_profile = PlayerProfile(
                    platform=platform,
                    username=username,
                    data=data,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    last_accessed=datetime.utcnow(),
                    session_id=session.sid if hasattr(session, 'sid') else None
                )
                db.session.add(new_profile)
            
            db.session.commit()
            
            # Store in session
            session['api_data'] = data
            session['platform'] = platform
            session['username'] = username
            session['from_cache'] = False
            session['last_updated'] = datetime.utcnow().isoformat()
            
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
            "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_profile",
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
                existing_profile.updated_at = datetime.utcnow()
                existing_profile.api_call_count += 1
            else:
                new_profile = PlayerProfile(
                    platform=platform,
                    username=username,
                    data=data,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    session_id=session.sid if hasattr(session, 'sid') else None
                )
                db.session.add(new_profile)
            
            db.session.commit()
            
            # Update session
            session['api_data'] = data
            session['from_cache'] = False
            session['last_updated'] = datetime.utcnow().isoformat()
            
            return jsonify({
                'success': True,
                'data': data,
                'message': 'Data refreshed successfully',
                'from_cache': False
            })
        else:
            return jsonify({
                'success': False,
                'message': f'API Error: {response.status_code}'
            })
            
    except Exception as e:
        app.logger.error(f"Error in refresh_data: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/clear_session', methods=['POST'])
def clear_session_data():
    """Clear session data"""
    session.pop('api_data', None)
    session.pop('platform', None)
    session.pop('username', None)
    session.pop('from_cache', None)
    session.pop('last_updated', None)
    
    return jsonify({'success': True, 'message': 'Session data cleared'})