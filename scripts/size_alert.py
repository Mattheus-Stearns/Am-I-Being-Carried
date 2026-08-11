#!/usr/bin/env python
"""
Check database size and alert if it's getting too large
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import text

def check_db_size():
    """Check database size and alert if too large"""
    with app.app_context():
        # Use text() for raw SQL
        result = db.session.execute(
            text("SELECT pg_database_size(current_database()) / 1024 / 1024")
        )
        size_mb = result.scalar()
        
        alerts = []
        
        if size_mb > 10000:  # 10 GB
            alerts.append("CRITICAL: Database size exceeded 10 GB")
        elif size_mb > 1000:  # 1 GB
            alerts.append("WARNING: Database size exceeded 1 GB")
        elif size_mb > 100:  # 100 MB
            alerts.append("INFO: Database size exceeded 100 MB")
        
        if alerts:
            print(f"\n📊 Database Size Alert: {size_mb:.2f} MB")
            for alert in alerts:
                print(f"  {alert}")
        else:
            print(f"\n✅ Database size is healthy: {size_mb:.2f} MB")
            
        return size_mb

if __name__ == "__main__":
    check_db_size()