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
import time
import re
import requests
from services.suggestion_service import (
    record_username_search, 
    get_correction_suggestion,
    add_successful_username
)

# ============================================
# HELPER FUNCTIONS
# ============================================

def is_likely_valid_username(username):
    """
    Validate username format and check if it's likely a real player
    Prevents 422 errors by catching invalid usernames early
    """
    if not username:
        return False
    
    # Basic format validation
    if len(username) < 2 or len(username) > 100:
        return False
    
    # Check for common invalid/test patterns
    invalid_patterns = [
        r'^test', r'^demo', r'^user\d+$', r'^player\d+$',
        r'^anonymous$', r'^guest$', r'^unknown$', r'^none$',
        r'^admin$', r'^root$', r'^example$'
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, username.lower()):
            return False
    
    return True

def get_user_friendly_error(error_code, status_code, message, username, platform):
    """Convert API errors to user-friendly messages"""
    errors = {
        'PLAYER_NOT_FOUND': {
            'message': f'Player "{username}" not found on {platform}.',
            'suggestion': 'Verify the username is correct and matches the selected platform.'
        },
        'INVALID_USERNAME': {
            'message': f'The username "{username}" appears to be invalid.',
            'suggestion': 'Check for typos and try again.'
        },
        'RATE_LIMITED': {
            'message': 'Too many requests. Please wait a moment.',
            'suggestion': f'Try again in a few minutes.'
        },
        'API_ERROR': {
            'message': 'The stats service is temporarily unavailable.',
            'suggestion': 'Please try again in a few minutes.'
        },
        'TIMEOUT': {
            'message': 'The request took too long to complete.',
            'suggestion': 'Please try again.'
        }
    }
    
    # Map status codes to error types
    if status_code == 404 or status_code == 422:
        return errors['PLAYER_NOT_FOUND']
    elif status_code == 429:
        return errors['RATE_LIMITED']
    elif status_code in [502, 503, 504, 408]:
        return errors['API_ERROR']
    elif status_code == 408:
        return errors['TIMEOUT']
    else:
        return {
            'message': message or 'An error occurred.',
            'suggestion': 'Please try again or contact support.'
        }

# ============================================
# ROUTES
# ============================================

@api_bp.route('/query', methods=['POST'])
@limiter.limit("1 per 5 minutes")
def query_api():
    """Handle API query with session caching and improved error handling"""
    try:
        req_data = request.get_json()
        if not req_data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
            
        platform = req_data.get('platform_id', '').strip().lower()
        username = req_data.get('username', '').strip()
        force_refresh = req_data.get('force_refresh', True)
        
        # ============================================
        # 1. VALIDATION - Prevent 422 errors
        # ============================================
        
        # Validate platform
        is_valid, error_msg = validate_platform(platform)
        if not is_valid:
            log_api_call(platform, username, False, 400, error_msg)
            return jsonify({
                'success': False, 
                'message': error_msg,
                'error_code': 'INVALID_PLATFORM'
            }), 400
        
        # Validate username format
        is_valid, error_msg = validate_username(username)
        if not is_valid:
            log_api_call(platform, username, False, 400, error_msg)
            return jsonify({
                'success': False, 
                'message': error_msg,
                'error_code': 'INVALID_USERNAME'
            }), 400
        
        # Additional check for likely valid usernames
        if not is_likely_valid_username(username):
            error_msg = 'This username does not appear to be valid. Please check the spelling.'
            log_api_call(platform, username, False, 400, error_msg)
            return jsonify({
                'success': False, 
                'message': error_msg,
                'error_code': 'UNLIKELY_USERNAME',
                'suggestion': 'Try searching for the player on Rocket League Tracker Network first.'
            }), 400
        
        # ============================================
        # 2. SESSION CACHE CHECK
        # ============================================
        
        session_data = session.get('api_data')
        session_platform = session.get('platform')
        session_username = session.get('username')
        
        if session_data and session_platform == platform and session_username == username and not force_refresh:
            log_api_call(platform, username, True, 200, None, len(str(session_data)))
            return jsonify({
                'success': True,
                'data': session_data,
                'message': 'Retrieved data from session cache',
                'from_cache': True
            })
        
        # ============================================
        # 3. DATABASE CACHE CHECK
        # ============================================
        
        cached_data = get_cached_data(platform, username)
        if cached_data and not force_refresh:
            log_api_call(platform, username, True, 200, None, len(str(cached_data)))
            return jsonify({
                'success': True,
                'data': cached_data,
                'message': 'Retrieved cached data',
                'from_cache': True
            })
        
        # ============================================
        # 4. API CALL WITH RETRY LOGIC
        # ============================================
        
        # Retry configuration for different error types
        retry_configs = [
            {'delay': 1, 'max_retries': 2},   # Quick retry for transient errors
            {'delay': 5, 'max_retries': 1},   # Longer wait before final retry
        ]
        
        last_error = None
        last_status_code = 500
        data = None
        
        for retry_group in retry_configs:
            for attempt in range(retry_group['max_retries']):
                try:
                    # Fetch fresh data
                    data, error, status_code = fetch_player_data(platform, username)
                    
                    if status_code == 200 and data:
                        # Success - save to cache
                        save_cached_data(platform, username, data)
                        
                        # Store in session
                        session['api_data'] = data
                        session['platform'] = platform
                        session['username'] = username
                        session['from_cache'] = False
                        session['last_updated'] = datetime.now(timezone.utc).isoformat()
                        
                        log_api_call(platform, username, True, 200, None, len(str(data)))
                        
                        return jsonify({
                            'success': True,
                            'data': data,
                            'message': 'Data fetched successfully',
                            'from_cache': False
                        })
                    
                    # ============================================
                    # 5. HANDLE SPECIFIC STATUS CODES
                    # ============================================
                    
                    if status_code == 422:
                        # Invalid username/platform - don't retry
                        record_username_search(platform, username, False)
                        
                        # Get "Did you mean?" suggestion
                        suggestion = get_correction_suggestion(platform, username)
                        
                        response_data = {
                            'success': False,
                            'error_code': 'PLAYER_NOT_FOUND'
                        }
                        
                        if suggestion:
                            # ✅ Return suggestion as an object
                            response_data['suggestion'] = {
                                'username': str(suggestion.get('display_name', '')),
                                'search_count': int(suggestion.get('search_count', 0)),
                                'success_rate': f"{suggestion.get('success_count', 0)}/{suggestion.get('search_count', 1)}"
                            }
                            response_data['message'] = f'Player "{username}" not found. Did you mean "{suggestion["display_name"]}"?'
                            print(f"✅ Added suggestion: {suggestion['display_name']}")
                        else:
                            # ✅ No suggestion found - give helpful message
                            response_data['message'] = f'Player "{username}" not found on {platform}. Please check the spelling and platform.'
                        
                        return jsonify(response_data), 404
                    
                    elif status_code == 429:
                        # Rate limited - wait and retry
                        log_api_call(platform, username, False, status_code, error)
                        
                        if attempt < retry_group['max_retries'] - 1:
                            time.sleep(retry_group['delay'] * (attempt + 1))
                            continue
                        else:
                            error_info = get_user_friendly_error('RATE_LIMITED', status_code, error, username, platform)
                            return jsonify({
                                'success': False,
                                'message': error_info['message'],
                                'suggestion': error_info.get('suggestion'),
                                'error_code': 'RATE_LIMITED'
                            }), 429
                    
                    elif status_code in [502, 503, 504, 408]:
                        # Server errors - retry
                        log_api_call(platform, username, False, status_code, error)
                        last_error = error
                        last_status_code = status_code
                        
                        if attempt < retry_group['max_retries'] - 1:
                            time.sleep(retry_group['delay'] * (attempt + 1))
                            continue
                        else:
                            error_info = get_user_friendly_error('API_ERROR', status_code, error, username, platform)
                            return jsonify({
                                'success': False,
                                'message': error_info['message'],
                                'suggestion': error_info.get('suggestion'),
                                'error_code': 'API_ERROR',
                                'status_code': status_code
                            }), 503
                    
                    else:
                        # Other errors
                        log_api_call(platform, username, False, status_code, error)
                        last_error = error
                        last_status_code = status_code
                        
                except requests.exceptions.Timeout:
                    error_msg = 'Request timed out'
                    log_api_call(platform, username, False, 408, error_msg)
                    last_error = error_msg
                    last_status_code = 408
                    
                    if attempt < retry_group['max_retries'] - 1:
                        time.sleep(retry_group['delay'])
                        continue
                    
                except requests.exceptions.ConnectionError:
                    error_msg = 'Connection error'
                    log_api_call(platform, username, False, 503, error_msg)
                    last_error = error_msg
                    last_status_code = 503
                    
                    if attempt < retry_group['max_retries'] - 1:
                        time.sleep(retry_group['delay'])
                        continue
                    
                except Exception as e:
                    error_msg = str(e)
                    log_api_call(platform, username, False, 500, error_msg)
                    last_error = error_msg
                    last_status_code = 500
                    
                    if attempt < retry_group['max_retries'] - 1:
                        time.sleep(retry_group['delay'])
                        continue
        
        # ============================================
        # 6. ALL RETRIES EXHAUSTED
        # ============================================
        
        error_info = get_user_friendly_error('API_ERROR', last_status_code, last_error, username, platform)
        log_api_call(platform, username, False, last_status_code, last_error)
        
        return jsonify({
            'success': False,
            'message': error_info['message'],
            'suggestion': error_info.get('suggestion'),
            'error_code': 'API_ERROR',
            'status_code': last_status_code
        }), 503
            
    except Exception as e:
        print(f"Error in query_api: {e}")
        import traceback
        traceback.print_exc()
        
        log_api_call(
            platform=platform if 'platform' in locals() else 'unknown',
            username=username if 'username' in locals() else 'unknown',
            success=False,
            response_code=500,
            error_message=str(e)
        )
        
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'error_code': 'INTERNAL_ERROR'
        }), 500

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
        
        log_api_call(platform, username, True, 200, 'Refresh triggered')
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared. Please search again.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/clear_session', methods=['POST'])
def clear_session():
    """Clear the current session data"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Session cleared successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

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
        
        log_api_call('feedback', data.get('email', 'anonymous'), True, 200, 'Feedback submitted')
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!'
        })
        
    except Exception as e:
        print(f"Feedback error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500