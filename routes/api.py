# routes/api.py
from flask import request, jsonify, session
from . import api_bp
from models import PlayerProfile, APICallLog, Feedback
from extensions import db, limiter
from services.api_service import fetch_player_data
from services.cache_service import get_cached_data, save_cached_data
from utils.helpers import get_client_ip
from services.cache_service import log_api_call
from utils.validators import validate_platform, validate_username
from datetime import datetime, timezone
import json

@api_bp.route('/query', methods=['POST'])
@limiter.limit("1 per 5 minutes")
def query_api():
    """Handle API query with session caching"""
    try:
        req_data = request.get_json()
        platform = req_data.get('platform_id', '').strip().lower()
        username = req_data.get('username', '').strip()
        force_refresh = req_data.get('force_refresh', True)
        
        # Validate inputs
        is_valid, error_msg = validate_platform(platform)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        is_valid, error_msg = validate_username(username)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Check cache
        cached_data = get_cached_data(platform, username)
        if cached_data and not force_refresh:
            return jsonify({
                'success': True,
                'data': cached_data,
                'message': 'Retrieved cached data',
                'from_cache': True
            })
        
        # Fetch fresh data
        data, error, status_code = fetch_player_data(platform, username)
        
        # Log the call
        log_api_call(platform, username, status_code == 200, status_code, error)
        
        if status_code == 200 and data:
            # Save to cache
            save_cached_data(platform, username, data)
            
            # Store in session
            session['api_data'] = data
            session['platform'] = platform
            session['username'] = username
            session['from_cache'] = False
            session['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            return jsonify({
                'success': True,
                'data': data,
                'message': 'Data fetched successfully',
                'from_cache': False
            })
        else:
            return jsonify({
                'success': False,
                'message': error or 'Failed to fetch data'
            }), status_code
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/refresh', methods=['POST'])
@limiter.limit("2 per 5 minutes")
def refresh_api():
    """Force refresh data"""
    try:
        req_data = request.get_json()
        platform = req_data.get('platform_id', '').strip().lower()
        username = req_data.get('username', '').strip()
        
        if not platform or not username:
            return jsonify({'success': False, 'message': 'Missing platform or username'}), 400
        
        # Clear cache
        session.pop('api_data', None)
        session.pop('platform', None)
        session.pop('username', None)
        session.pop('from_cache', None)
        session.pop('last_updated', None)
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared. Please search again.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'message': 'Message is required'}), 400
        
        feedback = Feedback(
            name=data.get('name', '').strip(),
            email=data.get('email', '').strip(),
            rating=data.get('rating', 0),
            message=message,
            page_url=data.get('page_url', ''),
            ip_address=get_client_ip()
        )
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500