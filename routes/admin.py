# routes/admin.py
from flask import render_template, jsonify
from . import admin_bp
from models import Feedback, Donation, APICallLog
from extensions import db

@admin_bp.route('/feedback')
def view_feedback():
    """Admin view for feedback"""
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template('admin/feedback.html', feedbacks=feedbacks)

@admin_bp.route('/donations')
def view_donations():
    """Admin view for donations"""
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    return render_template('admin/donations.html', donations=donations)