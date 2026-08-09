#!/usr/bin/env python
"""
Analyze failed API requests
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db, APICallLog
from datetime import datetime, timedelta
from collections import Counter

def analyze_failures():
    with app.app_context():
        print("\n" + "="*60)
        print("FAILED REQUESTS ANALYSIS")
        print("="*60)
        
        # Get all failed requests in last 30 days
        cutoff = datetime.utcnow() - timedelta(days=30)
        failures = APICallLog.query.filter(
            APICallLog.success == False,
            APICallLog.timestamp >= cutoff
        ).all()
        
        print(f"\nTotal Failed Requests: {len(failures)}")
        
        if not failures:
            print("No failures found!")
            return
        
        # Group by error message
        print("\nErrors by Type:")
        print("-" * 60)
        error_counts = Counter()
        for f in failures:
            error_counts[f.error_message or 'Unknown Error'] += 1
        
        for error, count in error_counts.most_common():
            print(f"  {count:3}x -> {error[:80]}")
        
        # Group by platform
        print("\nFailures by Platform:")
        print("-" * 60)
        platform_counts = Counter()
        for f in failures:
            platform_counts[f.platform or 'unknown'] += 1
        
        for platform, count in platform_counts.most_common():
            print(f"  {platform:10} -> {count:3} failures")
        
        # Show recent failures
        print("\nRecent Failures (Last 5):")
        print("-" * 60)
        for f in failures[:5]:
            print(f"\n  {f.platform}/{f.username}")
            print(f"    Code: {f.response_code}")
            print(f"    Error: {f.error_message or 'No error message'}")
            print(f"    Time: {f.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check for patterns
        print("\nPattern Analysis:")
        print("-" * 60)
        
        # Check if failures are from specific users
        user_failures = Counter()
        for f in failures:
            key = f"{f.platform}/{f.username}"
            user_failures[key] += 1
        
        if user_failures:
            print("Users with most failures:")
            for user, count in user_failures.most_common(5):
                print(f"  {user}: {count} failures")
        
        # Check if failures are from specific time periods
        hour_counts = Counter()
        for f in failures:
            hour_counts[f.timestamp.hour] += 1
        
        if hour_counts:
            print("\nFailures by hour of day:")
            for hour in sorted(hour_counts.keys()):
                print(f"  {hour:02d}:00 - {hour:02d}:59 -> {hour_counts[hour]} failures")

if __name__ == "__main__":
    analyze_failures()