from datetime import datetime, timezone
from app import db

class PlayerProfile(db.Model):
    __tablename__ = 'player_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_accessed = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    api_call_count = db.Column(db.Integer, default=1)
    session_id = db.Column(db.String(255))  # Store session ID for tracking
    
    __table_args__ = (
        db.UniqueConstraint('platform', 'username', name='unique_player'),
    )

class APICallLog(db.Model):
    """Optional: Track API calls for monitoring"""
    __tablename__ = 'api_call_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))
    username = db.Column(db.String(100))
    success = db.Column(db.Boolean, default=True)
    response_code = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    response_size = db.Column(db.Integer)  # Size of response in bytes
    ip_address = db.Column(db.String(45))
    region = db.Column(db.String(10)) 

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    rating = db.Column(db.Integer)  # 1-5 stars
    message = db.Column(db.Text, nullable=False)
    page_url = db.Column(db.String(255))
    user_agent = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Feedback {self.id}: {self.message[:30]}>'

class Donation(db.Model):
    __tablename__ = 'donations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    amount = db.Column(db.Numeric(10, 2))  # Donation amount in USD
    currency = db.Column(db.String(3), default='usd')
    message = db.Column(db.Text)
    stripe_payment_id = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(255))
    status = db.Column(db.String(50), default='pending')  # pending, succeeded, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_anonymous = db.Column(db.Boolean, default=False)
    show_on_wall = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Donation {self.id}: ${self.amount} from {self.name or "Anonymous"}>'