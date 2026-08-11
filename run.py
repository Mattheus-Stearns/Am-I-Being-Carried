#!/usr/bin/env python
"""
Unified script runner
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py <script> [args]")
        print("\nAvailable scripts:")
        print("  analytics stats [--days N]")
        print("  analytics daily [--days N]")
        print("  analytics topusers [--days N] [--limit N]")
        print("  analyze_failures")
        print("  cleanup [--days N] [--dry-run]")
        print("  cleanup_replays")
        print("  check_db")
        print("  monitor")
        print("  size_alert")
        print("  vacuum")
        print("  archive")
        print("  view_feedback")
        print("  populate_suggestions")
        sys.exit(1)
    
    script = sys.argv[1]
    args = sys.argv[2:]
    
    if script == "analytics":
        from scripts.analytics import cli
        cli(args)
    elif script == "cleanup":
        from scripts.cleanup import cleanup
        cleanup()
    elif script == "cleanup_replays":
        from scripts.cleanup_replays import cleanup_old_files
        cleanup_old_files()
    elif script == "check_db":
        from scripts.check_db import check_db_size
        check_db_size()
    elif script == "monitor":
        from scripts.monitor import monitor_growth
        monitor_growth()
    elif script == "size_alert":
        from scripts.size_alert import check_db_size
        check_db_size()
    elif script == "vacuum":
        from scripts.vacuum import vacuum_database
        vacuum_database()
    elif script == "archive":
        from scripts.archive import archive_old_data
        archive_old_data()
    elif script == "view_feedback":
        from scripts.view_feedback import view_feedback
        view_feedback()
    elif script == "analyze_failures":
        from scripts.analyze_failures import analyze_failures
        analyze_failures()
    elif script == "populate_suggestions":
        from scripts.populate_suggestions import populate_from_logs
        populate_from_logs()
    else:
        print(f"Unknown script: {script}")