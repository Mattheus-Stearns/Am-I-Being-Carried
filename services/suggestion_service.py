# services/suggestion_service.py
from models import UsernameSuggestion
from extensions import db
from datetime import datetime, timezone
from difflib import get_close_matches
import re

def record_username_search(platform, username, success):
    """
    Record a username search attempt
    - If success, increment success_count and search_count
    - If failure, just increment search_count (for learning)
    """
    try:
        # Clean username
        cleaned_username = clean_username(username)
        
        # Find or create suggestion entry
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
        
        # Update counts
        suggestion.search_count += 1
        if success:
            suggestion.success_count += 1
            # If this is a successful search, update the display name
            # (username might have different casing)
            if cleaned_username != username:
                suggestion.display_name = username
        suggestion.last_searched = datetime.now(timezone.utc)
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error recording username search: {e}")
        db.session.rollback()
        return False

def clean_username(username):
    """Clean username for storage (lowercase, remove special chars for matching)"""
    if not username:
        return ''
    # Convert to lowercase
    cleaned = username.lower()
    # Remove common prefixes/suffixes
    cleaned = re.sub(r'^[_\-\s]+', '', cleaned)
    cleaned = re.sub(r'[_\-\s]+$', '', cleaned)
    return cleaned

def get_suggestions(platform, username, limit=5, min_confidence=0.5):
    """
    Get username suggestions based on:
    1. Common typos (Levenshtein distance)
    2. Most successful searches
    3. Popular usernames
    """
    suggestions = []
    cleaned_input = clean_username(username)
    
    if not cleaned_input or len(cleaned_input) < 2:
        return []
    
    # 1. Get close matches from successful searches (using Levenshtein distance)
    all_suggestions = UsernameSuggestion.query.filter_by(
        platform=platform
    ).filter(
        UsernameSuggestion.success_count > 0,
        UsernameSuggestion.search_count > 1
    ).all()
    
    # Build list of usernames for fuzzy matching
    username_list = [s.username for s in all_suggestions]
    
    # Find close matches
    close_matches = get_close_matches(cleaned_input, username_list, n=limit, cutoff=min_confidence)
    
    # Get full suggestion objects
    for match in close_matches:
        suggestion = next((s for s in all_suggestions if s.username == match), None)
        if suggestion:
            suggestions.append({
                'username': suggestion.username,
                'display_name': suggestion.display_name or suggestion.username,
                'search_count': suggestion.search_count,
                'success_count': suggestion.success_count,
                'score': suggestion.success_count / max(suggestion.search_count, 1),
                'type': 'fuzzy_match'
            })
    
    # 2. If no fuzzy matches, get most successful searches
    if not suggestions:
        popular = UsernameSuggestion.query.filter_by(
            platform=platform
        ).filter(
            UsernameSuggestion.success_count > 0
        ).order_by(
            UsernameSuggestion.success_count.desc()
        ).limit(limit).all()
        
        for pop in popular:
            suggestions.append({
                'username': pop.username,
                'display_name': pop.display_name or pop.username,
                'search_count': pop.search_count,
                'success_count': pop.success_count,
                'score': pop.success_count / max(pop.search_count, 1),
                'type': 'popular'
            })
    
    return suggestions

def get_correction_suggestion(platform, username):
    """
    Get a single "Did you mean?" suggestion
    Returns the best match or None
    """
    suggestions = get_suggestions(platform, username, limit=1, min_confidence=0.6)
    
    if suggestions:
        return suggestions[0]
    
    # Try with lower confidence
    suggestions = get_suggestions(platform, username, limit=1, min_confidence=0.3)
    if suggestions:
        return suggestions[0]
    
    return None

def add_successful_username(platform, username):
    """
    Manually add a successful username to the suggestions database
    """
    cleaned = clean_username(username)
    suggestion = UsernameSuggestion.query.filter_by(
        platform=platform,
        username=cleaned
    ).first()
    
    if not suggestion:
        suggestion = UsernameSuggestion(
            platform=platform,
            username=cleaned,
            display_name=username,
            search_count=1,
            success_count=1
        )
        db.session.add(suggestion)
    else:
        suggestion.search_count += 1
        suggestion.success_count += 1
        suggestion.display_name = username
        suggestion.last_searched = datetime.now(timezone.utc)
    
    db.session.commit()
    return suggestion