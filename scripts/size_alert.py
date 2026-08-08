#!/usr/bin/env python
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from datetime import datetime

def check_db_size():
    with app.app_context():
        size_mb = db.session.execute(
            "SELECT pg_database_size(current_database()) / 1024 / 1024"
        ).scalar()
        
        alerts = []
        
        if size_mb > 10000:  # 10 GB
            alerts.append("CRITICAL: Database size exceeded 10 GB")
        elif size_mb > 1000:  # 1 GB
            alerts.append("WARNING: Database size exceeded 1 GB")
        elif size_mb > 100:  # 100 MB
            alerts.append("INFO: Database size exceeded 100 MB")
        
        if alerts:
            print(f"\nDatabase Size Alert: {size_mb:.2f} MB")
            for alert in alerts:
                print(f"  {alert}")
            
            # Send email or log alert
            # You could add email notification here
            
        return size_mb

if __name__ == "__main__":
    check_db_size()