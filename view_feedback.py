#!/usr/bin/env python
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Feedback

def view_feedback():
    with app.app_context():
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
        
        print("\n" + "="*80)
        print(f"FEEDBACK ({len(feedbacks)} entries)")
        print("="*80)
        
        for f in feedbacks:
            print(f"\n ID: {f.id}")
            print(f"Name: {f.name or 'Anonymous'}")
            print(f"Email: {f.email or 'N/A'}")
            print(f"Rating: {f.rating}/5" if f.rating else "Star Rating: N/A")
            print(f"Date: {f.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Read: {'Y' if f.is_read else 'X'}")
            print(f"Page: {f.page_url or 'N/A'}")
            print(f"IP: {f.ip_address or 'N/A'}")
            print("-"*40)
            print(f"Message:\n{f.message}")
            print("-"*40)
        
        print("\n" + "="*80)
        print(f"Total: {len(feedbacks)} | Unread: {len([f for f in feedbacks if not f.is_read])}")

if __name__ == "__main__":
    view_feedback()