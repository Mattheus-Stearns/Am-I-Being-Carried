# routes/__init__.py
from flask import Blueprint

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')
webhook_bp = Blueprint('webhook', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
support_bp = Blueprint('support', __name__)

def register_blueprints(app):
    """Register all blueprints with the app"""
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(support_bp)

# Import routes (must be after blueprint creation)
from . import main, api, webhook, admin, support, replay