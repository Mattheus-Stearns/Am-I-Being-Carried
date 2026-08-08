#!/usr/bin/env python
from app import app, db
from datetime import datetime, timedelta, timezone
import json
import os

def archive_old_data():
    with app.app_context():
        archive_dir = 'archives'
        os.makedirs(archive_dir, exist_ok=True)
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        
        # Archive API logs
        result = db.session.execute("""
            SELECT * FROM api_call_logs 
            WHERE timestamp < :cutoff
        """, {'cutoff': cutoff})
        
        rows = result.fetchall()
        if rows:
            archive_file = f"{archive_dir}/api_logs_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
            
            # Convert to dicts
            data = [dict(row._mapping) for row in rows]
            
            # Save to JSON
            with open(archive_file, 'w') as f:
                json.dump(data, f, default=str, indent=2)
            
            # Delete archived data
            db.session.execute(
                "DELETE FROM api_call_logs WHERE timestamp < :cutoff",
                {'cutoff': cutoff}
            )
            db.session.commit()
            
            print(f"Archived {len(data)} records to {archive_file}")
            print(f"Compressed size: {os.path.getsize(archive_file) / 1024 / 1024:.2f} MB")
        else:
            print("No data to archive")

if __name__ == "__main__":
    archive_old_data()