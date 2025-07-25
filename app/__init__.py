import os
from flask import Flask
from config import config
from app.extensions import db, init_app
from app.utils.database import initialize_database

def create_app(config_name=None):
    """Application factory function."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_app(app)
    
    # Register blueprints
    from app.blueprints import main_bp, players_bp, matches_bp, payments_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(players_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(payments_bp)
    
    # Initialize database and run migrations
    initialize_database(app)
    
    return app 