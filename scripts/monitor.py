#!/usr/bin/env python
"""
Monitor database growth over time
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extensions import db
from app import app
from sqlalchemy import text
from datetime import datetime, timedelta
import json
import os

def monitor_growth():
    with app.app_context():
        print("\n" + "="*60)
        print("DATABASE GROWTH MONITOR")
        print("="*60)
        
        # Current size
        result = db.session.execute(text("""
            SELECT 
                pg_database_size(current_database()) / 1024 / 1024 AS size_mb,
                pg_size_pretty(pg_database_size(current_database())) AS size_pretty
        """))
        row = result.fetchone()
        print(f"\nCurrent Size: {row.size_pretty} ({row.size_mb} MB)")
        
        # Growth by day (last 30 days)
        result = db.session.execute(text("""
            SELECT 
                date_trunc('day', timestamp) as day,
                COUNT(*) as records,
                SUM(response_size) / 1024 / 1024 as total_mb
            FROM api_call_logs
            WHERE timestamp > NOW() - INTERVAL '30 days'
            GROUP BY date_trunc('day', timestamp)
            ORDER BY day DESC
        """))
        
        print("\nGrowth by Day (Last 30 Days):")
        print("-" * 60)
        for row in result:
            print(f"  {row.day.strftime('%Y-%m-%d')}: {row.records} records, {row.total_mb or 0:.2f} MB")
        
        # Oldest data
        result = db.session.execute(text("""
            SELECT 
                MIN(timestamp) as oldest,
                MAX(timestamp) as newest,
                COUNT(*) as total
            FROM api_call_logs
        """))
        row = result.fetchone()
        if row:
            print(f"\nOldest Record: {row.oldest}")
            print(f"Newest Record: {row.newest}")
            print(f"Total Records: {row.total}")

if __name__ == "__main__":
    monitor_growth()