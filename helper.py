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
