#!/usr/bin/env python
"""
Populate username suggestions from existing successful searches
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from extensions import db
from app import app
from models import PlayerProfile, APICallLog, UsernameSuggestion
from services.suggestion_service import add_successful_username

def populate_from_logs():
    """Populate suggestions from successful API call logs"""
    with app.app_context():
        # Get successful API calls
        successful_calls = APICallLog.query.filter_by(
            success=True
        ).all()
        
        count = 0
        for log in successful_calls:
            if log.username and log.platform:
                # Check if already exists
                existing = UsernameSuggestion.query.filter_by(
                    platform=log.platform,
                    username=log.username.lower()
                ).first()
                
                if not existing:
                    add_successful_username(log.platform, log.username)
                    count += 1
        
        print(f"✅ Added {count} new username suggestions")
        
        # Show stats
        total = UsernameSuggestion.query.count()
        print(f"Total suggestions in database: {total}")

if __name__ == "__main__":
    populate_from_logs()