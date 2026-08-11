# services/suggestion_service.py
from models import UsernameSuggestion
from extensions import db
from datetime import datetime, timezone
from difflib import get_close_matches
import re

def record_username_search(platform, username, success):
    """Record a username search attempt"""
    try:
        cleaned_username = clean_username(username)
        print(f"📝 Recording search: {platform}/{cleaned_username}, success={success}")
        
        suggestion = UsernameSuggestion.query.filter_by(
            platform=platform,
            username=cleaned_username
        ).first()
        
        if not suggestion:
            suggestion = UsernameSuggestion(
                platform=platform,
                username=cleaned_username,
                display_name=cleaned_username
            )
            db.session.add(suggestion)
        
        suggestion.search_count += 1
        if success:
            suggestion.success_count += 1
            if cleaned_username != username:
                suggestion.display_name = username
        suggestion.last_searched = datetime.now(timezone.utc)
        
        db.session.commit()
        print(f"✅ Recorded: {suggestion.search_count} searches, {suggestion.success_count} successes")
        return True
    except Exception as e:
        print(f"❌ Error recording username search: {e}")
        db.session.rollback()
        return False

def clean_username(username):
    """Clean username for storage"""
    if not username:
        return ''
    cleaned = username.lower()
    cleaned = re.sub(r'^[_\-\s]+', '', cleaned)
    cleaned = re.sub(r'[_\-\s]+$', '', cleaned)
    return cleaned

def get_suggestions(platform, username, limit=5, min_confidence=0.5):
    """Get username suggestions based on fuzzy matching"""
    cleaned_input = clean_username(username)
    print(f"🔍 Getting suggestions for: {platform}/{cleaned_input}")
    
    if not cleaned_input or len(cleaned_input) < 2:
        print("❌ Input too short")
        return []
    
    # Get all suggestions from database
    all_suggestions = UsernameSuggestion.query.filter_by(
        platform=platform
    ).filter(
        UsernameSuggestion.success_count > 0,
        UsernameSuggestion.search_count > 1
    ).all()
    
    print(f"📊 Found {len(all_suggestions)} suggestions in database")
    
    if not all_suggestions:
        print("❌ No suggestions in database")
        return []
    
    # Build list of usernames
    username_list = [s.username for s in all_suggestions]
    print(f"📋 Usernames: {username_list[:10]}...")
    
    # Find close matches
    close_matches = get_close_matches(cleaned_input, username_list, n=limit, cutoff=min_confidence)
    print(f"🎯 Close matches: {close_matches}")
    
    result = []
    for match in close_matches:
        suggestion = next((s for s in all_suggestions if s.username == match), None)
        if suggestion:
            result.append({
                'username': suggestion.username,
                'display_name': suggestion.display_name or suggestion.username,
                'search_count': suggestion.search_count,
                'success_count': suggestion.success_count,
                'score': suggestion.success_count / max(suggestion.search_count, 1),
                'type': 'fuzzy_match'
            })
    
    print(f"✅ Returning {len(result)} suggestions")
    return result

def get_correction_suggestion(platform, username):
    """Get a single 'Did you mean?' suggestion"""
    print(f"🔍 Looking for correction suggestion for {platform}/{username}")
    
    suggestions = get_suggestions(platform, username, limit=1, min_confidence=0.6)
    
    if suggestions:
        print(f"✅ Found suggestion: {suggestions[0]['display_name']}")
        return suggestions[0]
    
    # Try with lower confidence
    suggestions = get_suggestions(platform, username, limit=1, min_confidence=0.3)
    if suggestions:
        print(f"✅ Found suggestion (low confidence): {suggestions[0]['display_name']}")
        return suggestions[0]
    
    print("❌ No suggestions found")
    return None