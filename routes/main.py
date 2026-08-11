# routes/main.py
from flask import render_template, session, request, jsonify
from . import main_bp
from models import PlayerProfile, APICallLog, Feedback
from extensions import db
from datetime import datetime, timezone
import json

def calculate_carried_score(match_summary, recent_matches):
    """
    Calculate a "carried" score from 0-100% based on performance metrics.
    Higher score = more likely being carried.
    """
    # Extract metrics
    total_matches = match_summary['total_matches']
    win_rate = match_summary['win_rate']
    total_mvps = match_summary['total_mvps']
    total_goals = match_summary['total_goals']
    total_assists = match_summary['total_assists']
    total_saves = match_summary['total_saves']
    total_shots = match_summary['total_shots']
    
    # Calculate average per match
    avg_goals = total_goals / total_matches if total_matches > 0 else 0
    avg_assists = total_assists / total_matches if total_matches > 0 else 0
    avg_saves = total_saves / total_matches if total_matches > 0 else 0
    avg_shots = total_shots / total_matches if total_matches > 0 else 0
    
    # Calculate shot accuracy
    shot_accuracy = (total_goals / total_shots * 100) if total_shots > 0 else 0
    
    # MVP Rate (percentage of matches where player got MVP)
    mvp_rate = (total_mvps / total_matches * 100) if total_matches > 0 else 0
    
    # --- CARRY DETECTION ALGORITHM ---
    
    # 1. WIN RATE SCORE (0-40 points)
    # High win rate with low individual performance = suspicious
    if win_rate >= 90:
        win_score = 40  # Very suspicious
    elif win_rate >= 75:
        win_score = 30
    elif win_rate >= 60:
        win_score = 20
    elif win_rate >= 50:
        win_score = 10
    else:
        win_score = 0  # Losing a lot = not being carried
    
    # 2. MVP RATE SCORE (0-25 points)
    # Low MVP rate while winning a lot = carried
    if mvp_rate <= 10:
        mvp_score = 25  # Almost never MVP
    elif mvp_rate <= 20:
        mvp_score = 18
    elif mvp_rate <= 30:
        mvp_score = 12
    elif mvp_rate <= 40:
        mvp_score = 6
    else:
        mvp_score = 0  # Often MVP = not carried
    
    # 3. GOALS PER MATCH SCORE (0-15 points)
    # Low goals while winning = carried
    if avg_goals <= 0.5:
        goals_score = 15  # Very few goals
    elif avg_goals <= 1.0:
        goals_score = 10
    elif avg_goals <= 1.5:
        goals_score = 6
    elif avg_goals <= 2.0:
        goals_score = 3
    else:
        goals_score = 0  # Scoring a lot = not carried
    
    # 4. SAVES PER MATCH SCORE (0-10 points)
    # Low saves while winning = defensive carried
    if avg_saves <= 1.0:
        saves_score = 10
    elif avg_saves <= 2.0:
        saves_score = 6
    elif avg_saves <= 3.0:
        saves_score = 3
    else:
        saves_score = 0  # Good defense = not carried
    
    # 5. SHOT ACCURACY SCORE (0-10 points)
    # Low accuracy = worse performance = more carried
    if shot_accuracy <= 30:
        accuracy_score = 10
    elif shot_accuracy <= 45:
        accuracy_score = 6
    elif shot_accuracy <= 55:
        accuracy_score = 3
    else:
        accuracy_score = 0  # Good accuracy = not carried
    
    # 6. SHOTS PER MATCH SCORE (0-10 points)
    # Low shots = not contributing = carried
    if avg_shots <= 1.0:
        shots_score = 10
    elif avg_shots <= 2.0:
        shots_score = 6
    elif avg_shots <= 3.0:
        shots_score = 3
    else:
        shots_score = 0  # Taking shots = trying = not carried
    
    # 7. ASSISTS PER MATCH SCORE (0-5 points)
    # Low assists with high win rate = carried (not setting up teammates)
    if avg_assists <= 0.3:
        assists_score = 5
    elif avg_assists <= 0.5:
        assists_score = 3
    elif avg_assists <= 0.8:
        assists_score = 1
    else:
        assists_score = 0
    
    # 8. PERFORMANCE INDEX (0-5 points)
    # Bonus/Malus based on overall performance vs win rate
    performance_index = 0
    
    # If high win rate but poor performance = carried
    if win_rate > 70 and mvp_rate < 20 and avg_goals < 1.0:
        performance_index = 5  # Definitely carried
    
    # If high win rate and good performance = not carried
    if win_rate > 70 and mvp_rate > 40 and avg_goals > 2.0:
        performance_index = -5  # Carrying others
    
    # If losing a lot but good performance = not carried
    if win_rate < 40 and avg_goals > 1.5 and mvp_rate > 30:
        performance_index = -10  # Carrying but losing
    
    # Calculate total raw score (max 120 points)
    raw_score = (
        win_score +
        mvp_score +
        goals_score +
        saves_score +
        accuracy_score +
        shots_score +
        assists_score +
        performance_index
    )
    
    # Normalize to 0-100
    # Max theoretical score = 120 (all max values)
    # Min theoretical score = -10 (worst performance bonus)
    raw_score = max(0, min(120, raw_score))  # Clamp between 0-120
    carried_score = round((raw_score / 120) * 100)  # Convert to percentage
    
    # Edge Cases & Adjustments
    # If very few matches played, reduce confidence
    if total_matches < 5:
        carried_score = round(carried_score * 0.5)  # Less confidence
    
    # If player has extremely high stats, lower carried score
    if avg_goals > 3.0 and avg_assists > 1.5 and win_rate > 70:
        carried_score = min(carried_score, 30)  # Not carried, they're good
    
    return carried_score

@main_bp.route('/')
def index():
    """Homepage"""
    return render_template('index.html')

@main_bp.route('/results')
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


@main_bp.route('/support')
def support():
    """Support page"""
    return render_template('support.html')

@main_bp.route('/thanks')
def thanks():
    """Thank you page after donation"""
    return render_template('thanks.html')