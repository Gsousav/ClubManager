#!/usr/bin/env python3
"""
Pichanga Manager - Main Application Entry Point

This is the main entry point for the Pichanga Manager application.
Run this file to start the development server.

Usage:
    python run.py
    
Environment Variables:
    FLASK_ENV: Set to 'development', 'production', or 'testing' (default: 'development')
    DATABASE_URL: Custom database URL (optional)
    SECRET_KEY: Custom secret key (optional)
"""

import os
from app import create_app

# Create application instance
app = create_app()

if __name__ == '__main__':
    # Only run the development server when called directly
    # In production, use a proper WSGI server like Gunicorn
    app.run(
        debug=app.config.get('DEBUG', True),
        port=int(os.environ.get('PORT', 8080)),
        host=os.environ.get('HOST', '127.0.0.1')
    ) 