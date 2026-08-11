# models.py
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from extensions import db

class PlayerProfile(db.Model):
    __tablename__ = 'player_profiles'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))
    username = db.Column(db.String(100))
    data = db.Column(JSON)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_accessed = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    api_call_count = db.Column(db.Integer, default=0)
    session_id = db.Column(db.String(255))

class APICallLog(db.Model):
    __tablename__ = 'api_call_logs'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))
    username = db.Column(db.String(100))
    success = db.Column(db.Boolean, default=True)
    response_code = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    response_size = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    region = db.Column(db.String(10))

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    rating = db.Column(db.Integer)
    message = db.Column(db.Text, nullable=False)
    page_url = db.Column(db.String(255))
    user_agent = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Donation(db.Model):
    __tablename__ = 'donations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    amount = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3), default='usd')
    message = db.Column(db.Text)
    stripe_payment_id = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(255))
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_anonymous = db.Column(db.Boolean, default=False)
    show_on_wall = db.Column(db.Boolean, default=False)

class UsernameSuggestion(db.Model):
    __tablename__ = 'username_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100))  # The correct/cleaned version
    search_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    last_searched = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    # Index for faster queries
    __table_args__ = (
        db.Index('idx_username_suggestions_platform_username', 'platform', 'username'),
        db.Index('idx_username_suggestions_search_count', 'search_count'),
    )
    
    def __repr__(self):
        return f'<UsernameSuggestion {self.platform}/{self.username}: {self.search_count} searches>'