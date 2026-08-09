#!/usr/bin/env python
"""
Analytics Script for APICallLog
Track user counts, region analytics, and API usage statistics
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db, APICallLog
from datetime import datetime, timedelta, timezone
from collections import Counter
import json
import click
import geoip2.database
from geoip2.errors import AddressNotFoundError

# Configure GeoIP database path
GEOIP_DB_PATH = Path(__file__).parent.parent / 'ip_2_geo_db' / 'GeoLite2-City.mmdb'

class Analytics:
    def __init__(self):
        self.app = app
        self.db = db
        self.geoip_reader = None
        self._init_geoip()
    
    def _init_geoip(self):
        """Initialize GeoIP reader"""
        try:
            if GEOIP_DB_PATH.exists():
                self.geoip_reader = geoip2.database.Reader(str(GEOIP_DB_PATH))
                print(f"GeoIP database loaded from: {GEOIP_DB_PATH}")
            else:
                print(f"Warning: GeoIP database not found at {GEOIP_DB_PATH}")
                print(f"Please download GeoLite2-City.mmdb to ip_2_geo_db/")
                self.geoip_reader = None
        except Exception as e:
            print(f"Warning: Failed to load GeoIP database: {e}")
            self.geoip_reader = None
    
    def get_region_from_ip(self, ip_address):
        """Get region from IP address using GeoIP"""
        if not self.geoip_reader:
            return 'Other'
        
        # Handle local/private IPs
        if ip_address.startswith('127.') or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
            return 'Other'
        
        try:
            response = self.geoip_reader.city(ip_address)
            continent = response.continent.code if response.continent else None
            
            # Map continent codes to your regions
            region_map = {
                'NA': 'NA',      # North America
                'SA': 'SAM',     # South America
                'EU': 'EU',      # Europe
                'AF': 'Other',   # Africa
                'AS': 'ASIA',    # Asia
                'OC': 'OCE',     # Oceania
                'AN': 'Other'    # Antarctica
            }
            return region_map.get(continent, 'Other')
        except AddressNotFoundError:
            return 'Other'
        except Exception as e:
            print(f"Error getting region for IP {ip_address}: {e}")
            return 'Other'
    
    def _detect_region_from_username(self, username):
        """Detect region from username patterns"""
        if not username:
            return 'Other'
        
        username_lower = username.lower()
        
        region_patterns = {
            'NA': ['na_', '_na', 'north', 'america', 'us_', '_us', 'ca_', '_ca', 'usa', 'canada'],
            'EU': ['eu_', '_eu', 'europe', 'uk_', '_uk', 'de_', '_de', 'fr_', '_fr', 'germany', 'france'],
            'OCE': ['oce_', '_oce', 'au_', '_au', 'nz_', '_nz', 'australia', 'newzealand'],
            'SAM': ['sam_', '_sam', 'br_', '_br', 'brazil', 'arg_', '_arg', 'latam', 'southamerica'],
            'ME': ['me_', '_me', 'middleeast', 'uae', 'dubai', 'ksa', 'middle_east'],
            'ASIA': ['asia', 'jp_', '_jp', 'kr_', '_kr', 'cn_', '_cn', 'sg_', '_sg', 'japan', 'korea', 'china']
        }
        
        for region_name, patterns in region_patterns.items():
            for pattern in patterns:
                if pattern in username_lower:
                    return region_name
        
        return 'Other'
    
    def _detect_region_from_platform(self, platform):
        """Fallback: detect region from platform"""
        # This is a simple default mapping for global platforms
        platform_regions = {
            'epic': 'Other',   # Global platform
            'steam': 'Other',  # Global platform
            'psn': 'Other',    # Global platform
            'xbox': 'Other',   # Global platform
            'switch': 'Other'  # Global platform
        }
        return platform_regions.get(platform, 'Other')
    
    def _detect_regions(self, logs):
        """Detect regions using GeoIP or fallback methods"""
        regions = {
            'NA': {'total': 0, 'users': set()},
            'EU': {'total': 0, 'users': set()},
            'OCE': {'total': 0, 'users': set()},
            'SAM': {'total': 0, 'users': set()},
            'ME': {'total': 0, 'users': set()},
            'ASIA': {'total': 0, 'users': set()},
            'Other': {'total': 0, 'users': set()}
        }
        
        for log in logs:
            user_key = f"{log.platform}_{log.username}"
            region = 'Other'
            
            # Try GeoIP first (if we have IP address)
            if hasattr(log, 'ip_address') and log.ip_address:
                region = self.get_region_from_ip(log.ip_address)
            
            # Fallback: username patterns
            if region == 'Other' and hasattr(log, 'username') and log.username:
                region = self._detect_region_from_username(log.username)
            
            # Final fallback: platform-based
            if region == 'Other' and hasattr(log, 'platform'):
                region = self._detect_region_from_platform(log.platform)
            
            regions[region]['total'] += 1
            regions[region]['users'].add(user_key)
        
        # Convert sets to counts
        for region in regions:
            regions[region]['user_count'] = len(regions[region]['users'])
            del regions[region]['users']
        
        return regions
    
    def get_user_count(self, days=30):
        """Get unique user count for the last N days"""
        with self.app.app_context():
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            users = self.db.session.query(
                APICallLog.platform, 
                APICallLog.username
            ).filter(
                APICallLog.timestamp >= cutoff
            ).distinct().all()
            
            return len(users)
    
    def get_user_stats(self, days=30):
        """Get detailed user statistics"""
        with self.app.app_context():
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            logs = APICallLog.query.filter(
                APICallLog.timestamp >= cutoff
            ).all()
            
            if not logs:
                return None
            
            platform_counts = Counter()
            user_list = set()
            platform_users = {}
            
            for log in logs:
                key = f"{log.platform}_{log.username}"
                user_list.add(key)
                platform_counts[log.platform] += 1
                
                if log.platform not in platform_users:
                    platform_users[log.platform] = set()
                platform_users[log.platform].add(log.username)
            
            successful = sum(1 for log in logs if log.success)
            failed = len(logs) - successful
            
            regions = self._detect_regions(logs)
            
            return {
                'total_requests': len(logs),
                'unique_users': len(user_list),
                'successful_requests': successful,
                'failed_requests': failed,
                'success_rate': round((successful / len(logs)) * 100, 2) if logs else 0,
                'platform_stats': dict(platform_counts),
                'platform_user_counts': {k: len(v) for k, v in platform_users.items()},
                'region_stats': regions,
                'total_users': len(user_list)
            }
    
    def get_daily_stats(self, days=30):
        """Get daily statistics for the last N days"""
        with self.app.app_context():
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            daily_stats = {}
            
            for day in range(days):
                date = datetime.now(timezone.utc) - timedelta(days=day)
                date_str = date.strftime('%Y-%m-%d')
                
                day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                day_logs = APICallLog.query.filter(
                    APICallLog.timestamp >= day_start,
                    APICallLog.timestamp < day_end
                ).all()
                
                if day_logs:
                    unique_users = set()
                    for log in day_logs:
                        unique_users.add(f"{log.platform}_{log.username}")
                    
                    daily_stats[date_str] = {
                        'requests': len(day_logs),
                        'unique_users': len(unique_users),
                        'successful': sum(1 for log in day_logs if log.success),
                        'failed': sum(1 for log in day_logs if not log.success)
                    }
                else:
                    daily_stats[date_str] = {
                        'requests': 0,
                        'unique_users': 0,
                        'successful': 0,
                        'failed': 0
                    }
            
            return daily_stats
    
    def get_top_users(self, limit=10, days=30):
        """Get top users by request count"""
        with self.app.app_context():
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            logs = APICallLog.query.filter(
                APICallLog.timestamp >= cutoff
            ).all()
            
            user_counts = Counter()
            for log in logs:
                key = f"{log.platform}/{log.username}"
                user_counts[key] += 1
            
            return user_counts.most_common(limit)
    
    def get_error_stats(self, days=30):
        """Get error statistics"""
        with self.app.app_context():
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            errors = APICallLog.query.filter(
                APICallLog.timestamp >= cutoff,
                APICallLog.success == False
            ).all()
            
            error_counts = Counter()
            for error in errors:
                error_counts[error.error_message or 'Unknown Error'] += 1
            
            return dict(error_counts)


# ============================================
# CLI Commands
# ============================================

@click.group()
def cli():
    """Analytics CLI for APICallLog"""
    pass

@cli.command()
@click.option('--days', '-d', default=30, help='Number of days to analyze')
def stats(days):
    """Show overall statistics"""
    analytics = Analytics()
    stats_data = analytics.get_user_stats(days)
    
    if not stats_data:
        print(f"\nNo data found for the last {days} days")
        return
    
    print(f"\n{'='*60}")
    print(f"ANALYTICS - Last {days} Days")
    print(f"{'='*60}")
    print(f"\nTotal Requests:    {stats_data['total_requests']}")
    print(f"Unique Users:      {stats_data['unique_users']}")
    print(f"Successful:        {stats_data['successful_requests']}")
    print(f"Failed:           {stats_data['failed_requests']}")
    print(f"Success Rate:     {stats_data['success_rate']}%")
    
    print(f"\n{'='*60}")
    print("PLATFORM STATISTICS")
    print(f"{'='*60}")
    for platform, count in stats_data['platform_stats'].items():
        user_count = stats_data['platform_user_counts'].get(platform, 0)
        print(f"  {platform.upper():10} -> {count:4} requests, {user_count:4} users")
    
    print(f"\n{'='*60}")
    print("REGION STATISTICS")
    print(f"{'='*60}")
    for region, data in stats_data['region_stats'].items():
        print(f"  {region:10} -> {data['total']:4} requests, {data['user_count']:4} users")
    
    print(f"\n{'='*60}")

@cli.command()
@click.option('--days', '-d', default=7, help='Number of days to show')
def daily(days):
    """Show daily statistics"""
    analytics = Analytics()
    daily_stats = analytics.get_daily_stats(days)
    
    print(f"\n{'='*60}")
    print(f"DAILY STATS - Last {days} Days")
    print(f"{'='*60}\n")
    
    # Sort by date (newest first)
    for date, stats in sorted(daily_stats.items(), reverse=True):
        if stats['requests'] > 0:
            print(f"{date}:")
            print(f"  Requests:    {stats['requests']}")
            print(f"  Users:       {stats['unique_users']}")
            print(f"  Successful:  {stats['successful']}")
            print(f"  Failed:      {stats['failed']}")
            print()

@cli.command()
@click.option('--days', '-d', default=30, help='Number of days to analyze')
@click.option('--limit', '-l', default=10, help='Number of top users to show')
def topusers(days, limit):
    """Show top users by request count"""
    analytics = Analytics()
    top_users = analytics.get_top_users(limit, days)
    
    print(f"\n{'='*60}")
    print(f"TOP {limit} USERS - Last {days} Days")
    print(f"{'='*60}\n")
    
    for i, (user, count) in enumerate(top_users, 1):
        print(f"{i:2}. {user:30} -> {count:4} requests")

@cli.command()
@click.option('--days', '-d', default=30, help='Number of days to analyze')
def errors(days):
    """Show error statistics"""
    analytics = Analytics()
    errors = analytics.get_error_stats(days)
    
    print(f"\n{'='*60}")
    print(f"ERROR STATISTICS - Last {days} Days")
    print(f"{'='*60}\n")
    
    if not errors:
        print("No errors found!")
        return
    
    for error, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
        print(f"  {count:3}x -> {error[:50]}...")

@cli.command()
def totalusers():
    """Show total unique users all time"""
    with app.app_context():
        users = db.session.query(
            APICallLog.platform, 
            APICallLog.username
        ).distinct().all()
        
        platform_counts = Counter()
        for platform, username in users:
            platform_counts[platform] += 1
        
        print(f"\n{'='*60}")
        print("TOTAL UNIQUE USERS (All Time)")
        print(f"{'='*60}")
        print(f"\nTotal Users: {len(users)}")
        print(f"\nBy Platform:")
        for platform, count in platform_counts.items():
            print(f"  {platform.upper():10} -> {count:4} users")
        print(f"\n{'='*60}")

@cli.command()
@click.option('--format', '-f', default='table', type=click.Choice(['table', 'json']))
def export(format):
    """Export analytics data"""
    analytics = Analytics()
    stats_data = analytics.get_user_stats(365)  # Last year
    
    if format == 'json':
        print(json.dumps(stats_data, indent=2, default=str))
    else:
        # Table format
        print(f"\n{'='*60}")
        print("EXPORT DATA")
        print(f"{'='*60}")
        print(f"Total Users:     {stats_data['total_users']}")
        print(f"Total Requests:  {stats_data['total_requests']}")
        print(f"Success Rate:    {stats_data['success_rate']}%")
        print(f"\nPlatforms:")
        for platform, count in stats_data['platform_stats'].items():
            user_count = stats_data['platform_user_counts'].get(platform, 0)
            print(f"  {platform}: {count} requests, {user_count} users")

if __name__ == "__main__":
    cli()