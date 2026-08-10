# routes/webhook.py
from flask import request, jsonify
import stripe
import os
import json
from . import webhook_bp
from models import Donation
from extensions import db
from config import Config

@webhook_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    import traceback
    
    try:
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')
        
        # Debug logging
        print("="*60)
        print("WEBHOOK RECEIVED")
        print("="*60)
        print(f"Signature present: {bool(sig_header)}")
        
        # Test mode - no signature
        if not sig_header:
            print("Test webhook - no signature")
            try:
                data = json.loads(payload)
                if data.get('type') == 'test':
                    return jsonify({'status': 'success', 'test': True}), 200
            except:
                pass
            return jsonify({'status': 'success', 'test': True}), 200
        
        # Production mode - verify signature
        webhook_secret = Config.STRIPE_WEBHOOK_SECRET
        if not webhook_secret:
            print("Webhook secret not configured")
            return jsonify({'error': 'Webhook secret not configured'}), 500
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        print(f"Webhook verified: {event['type']}")
        
        # Handle events
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            payment_id = payment_intent['id']
            
            donation = Donation.query.filter_by(
                stripe_payment_id=payment_id
            ).first()
            
            if donation:
                donation.status = 'succeeded'
                db.session.commit()
                print(f"✅ Donation {donation.id} succeeded")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        traceback.print_exc()
        return jsonify({'status': 'success'}), 200  # Always return 200 to prevent retries