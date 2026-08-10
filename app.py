# app.py
from flask import Flask
from config import Config
from extensions import db, limiter, migrate, redis_client
from routes import register_blueprints
from services.cache_service import load_authorized_ips
import stripe

def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    
    # Stripe
    stripe.api_key = Config.STRIPE_SECRET_KEY
    
    # Register blueprints
    register_blueprints(app)
    
    # Load authorized IPs
    with app.app_context():
        load_authorized_ips()
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)