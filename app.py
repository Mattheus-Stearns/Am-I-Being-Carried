# app.py
from flask import Flask
from config import Config
from extensions import db, limiter, migrate
from routes import register_blueprints
from services.cache_service import load_authorized_ips
import stripe
from datetime import datetime, timezone
import os
from flask_session import Session

def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)

    session_dir = app.config.get('SESSION_FILE_DIR', './flask_session')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir, mode=0o755, exist_ok=True)
    
    Session(app)
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    
    # Stripe
    stripe.api_key = Config.STRIPE_SECRET_KEY
    
    # Register blueprints
    register_blueprints(app)
    
    # ============================================
    # REGISTER TEMPLATE FILTERS HERE
    # ============================================
    
    @app.template_filter('format_date')
    def format_date(date_string):
        """Format date string for display"""
        if not date_string:
            return 'N/A'
        try:
            # Handle different date formats
            if 'Z' in date_string:
                date_string = date_string.replace('Z', '+00:00')
            date_obj = datetime.fromisoformat(date_string)
            return date_obj.strftime('%Y-%m-%d %H:%M')
        except:
            return date_string[:16] if date_string else 'N/A'
    
    @app.template_filter('time_ago')
    def time_ago(date_string):
        """Convert date to 'X time ago' format"""
        if not date_string:
            return 'N/A'
        try:
            if 'Z' in date_string:
                date_string = date_string.replace('Z', '+00:00')
            date_obj = datetime.fromisoformat(date_string)
            now = datetime.now(timezone.utc)
            diff = now - date_obj
            
            seconds = diff.total_seconds()
            if seconds < 60:
                return 'just now'
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f'{hours} hour{"s" if hours > 1 else ""} ago'
            elif seconds < 604800:
                days = int(seconds / 86400)
                return f'{days} day{"s" if days > 1 else ""} ago'
            else:
                return date_obj.strftime('%Y-%m-%d')
        except:
            return date_string
    
    @app.template_filter('truncate')
    def truncate(text, length=50):
        """Truncate text to specified length"""
        if not text:
            return ''
        if len(text) <= length:
            return text
        return text[:length] + '...'
    
    @app.template_filter('pluralize')
    def pluralize(count, singular, plural=None):
        """Pluralize a word based on count"""
        if not plural:
            plural = singular + 's'
        return singular if count == 1 else plural

    @app.template_filter('basename')
    def basename_filter(filepath):
        """Get basename from filepath"""
        return os.path.basename(filepath) if filepath else ''
    
    # Load authorized IPs
    with app.app_context():
        load_authorized_ips()
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)