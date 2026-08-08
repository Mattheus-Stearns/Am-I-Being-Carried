#!/usr/bin/env python
"""
Check database size and table sizes
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import text

def check_db_size():
    with app.app_context():
        print("\n" + "="*60)
        print("DATABASE SIZE REPORT")
        print("="*60)
        
        # Get database size
        result = db.session.execute(text("""
            SELECT 
                pg_size_pretty(pg_database_size(current_database())) AS total_size
        """))
        total = result.fetchone()
        
        print(f"\nTotal Database Size: {total.total_size}")
        
        # Get per-table sizes
        print("\nTable Sizes:")
        print("-" * 60)
        
        result = db.session.execute(text("""
            SELECT 
                table_name,
                pg_size_pretty(pg_total_relation_size('"' || table_name || '"')) AS size,
                pg_total_relation_size('"' || table_name || '"') / 1024 / 1024 AS size_mb
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY pg_total_relation_size('"' || table_name || '"') DESC
        """))
        
        total_tables_mb = 0
        for row in result:
            print(f"  {row.table_name:25} -> {row.size:15} ({row.size_mb or 0} MB)")
            total_tables_mb += row.size_mb or 0
        
        print("-" * 60)
        print(f"  {'Total Tables':25} -> {total_tables_mb:.2f} MB")

if __name__ == "__main__":
    check_db_size()