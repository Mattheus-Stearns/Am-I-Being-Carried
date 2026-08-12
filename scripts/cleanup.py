#!/usr/bin/env python
"""
Database cleanup script - remove old data
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extensions import db
from app import app
from datetime import datetime, timedelta, timezone
import click

@click.command()
@click.option('--days', default=90, help='Keep data for N days (default: 90)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
def cleanup(days, dry_run):
    """Clean up old data from the database"""
    with app.app_context():
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        print(f"\n{'='*60}")
        print("DATABASE CLEANUP")
        print(f"{'='*60}")
        print(f"Keeping data newer than: {cutoff_date.strftime('%Y-%m-%d')}")
        print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete)'}")
        
        # Check what would be deleted
        print("\nRecords to delete:")
        print("-" * 60)
        
        # API Call Logs
        old_logs = db.session.execute(
            "SELECT COUNT(*) FROM api_call_logs WHERE timestamp < :cutoff",
            {'cutoff': cutoff_date}
        ).scalar()
        print(f"  API Call Logs: {old_logs} records")
        
        # Sessions (if you have a sessions table with timestamp)
        old_sessions = db.session.execute(
            "SELECT COUNT(*) FROM sessions WHERE created_at < :cutoff",
            {'cutoff': cutoff_date}
        ).scalar() if 'sessions' in get_table_names() else 0
        print(f"  Sessions: {old_sessions} records")
        
        # Feedback (keep forever, but you might want to archive old ones)
        old_feedback = db.session.execute(
            "SELECT COUNT(*) FROM feedback WHERE created_at < :cutoff AND is_read = true",
            {'cutoff': cutoff_date - timedelta(days=365)}
        ).scalar() if 'feedback' in get_table_names() else 0
        print(f"  Read Feedback (older than 1 year): {old_feedback} records")
        
        if not dry_run:
            confirm = input(f"\nDelete {old_logs} API call logs and {old_sessions} sessions? (y/N): ")
            if confirm.lower() == 'y':
                # Delete old API logs
                db.session.execute(
                    "DELETE FROM api_call_logs WHERE timestamp < :cutoff",
                    {'cutoff': cutoff_date}
                )
                
                # Delete old sessions
                if 'sessions' in get_table_names():
                    db.session.execute(
                        "DELETE FROM sessions WHERE created_at < :cutoff",
                        {'cutoff': cutoff_date}
                    )
                
                # Delete old read feedback
                if 'feedback' in get_table_names():
                    db.session.execute(
                        "DELETE FROM feedback WHERE created_at < :cutoff AND is_read = true",
                        {'cutoff': cutoff_date - timedelta(days=365)}
                    )
                
                db.session.commit()
                print(f"\n Cleanup complete!")
                
                # Show new size
                new_size = db.session.execute(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                ).scalar()
                print(f"New database size: {new_size}")
            else:
                print("Cleanup cancelled.")
        else:
            print(f"\nDRY RUN: Would delete {old_logs} API logs, {old_sessions} sessions")

def get_table_names():
    with app.app_context():
        result = db.session.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        return [row[0] for row in result]

if __name__ == "__main__":
    cleanup()