from flask_sqlalchemy import SQLAlchemy

# Initialize extensions
db = SQLAlchemy()

def init_app(app):
    """Initialize Flask extensions with the app instance."""
    db.init_app(app)