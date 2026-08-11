#!/usr/bin/env python
"""
Cleanup old replay analysis files
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

ANALYSIS_FOLDER = 'uploads/analysis'
MAX_AGE_DAYS = 7  # Keep files for 7 days

def cleanup_old_files():
    """Delete analysis files older than MAX_AGE_DAYS"""
    with app.app_context():
        if not os.path.exists(ANALYSIS_FOLDER):
            print("No analysis folder found")
            return
        
        cutoff = datetime.now() - timedelta(days=MAX_AGE_DAYS)
        deleted_count = 0
        
        for item in os.listdir(ANALYSIS_FOLDER):
            item_path = os.path.join(ANALYSIS_FOLDER, item)
            
            # Check if it's a directory (replay_id folder)
            if os.path.isdir(item_path):
                # Get creation time
                created = datetime.fromtimestamp(os.path.getctime(item_path))
                
                if created < cutoff:
                    # Delete the folder and all contents
                    import shutil
                    shutil.rmtree(item_path)
                    deleted_count += 1
                    print(f"🗑️ Deleted old analysis: {item}")
        
        print(f"✅ Cleanup complete. Deleted {deleted_count} old analyses.")

if __name__ == "__main__":
    cleanup_old_files()