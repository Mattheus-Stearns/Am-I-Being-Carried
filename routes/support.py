# routes/support.py
from flask import render_template, jsonify, request
import stripe
import os
from . import support_bp
from models import Donation
from extensions import db
from config import Config

@support_bp.route('/donate', methods=['GET', 'POST'])
def donate():
    """Donation page with Stripe"""
    if request.method == 'GET':
        return render_template('donate.html', 
                             stripe_publishable_key=Config.STRIPE_PUBLISHABLE_KEY)
    
    try:
        data = request.json
        amount = data.get('amount')
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        
        if not amount or float(amount) < 1:
            return jsonify({'success': False, 'message': 'Minimum donation is $1.00'}), 400
        
        # Create payment intent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(float(amount) * 100),
            currency='usd',
            metadata={
                'name': name or 'Anonymous',
                'email': email,
                'message': message
            },
            receipt_email=email if email else None,
            description='Donation to Am I Being Carried?'
        )
        
        # Save to database
        donation = Donation(
            name=name,
            email=email,
            amount=amount,
            message=message,
            stripe_payment_id=payment_intent.id,
            status='pending'
        )
        db.session.add(donation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'client_secret': payment_intent.client_secret,
            'payment_intent_id': payment_intent.id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500