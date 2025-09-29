#!/usr/bin/env python3
"""
Pichanga Manager - Backward Compatibility Module

This module provides backward compatibility by importing the refactored application.
The main application logic has been moved to a proper Flask application factory pattern.

For the new structure, use:
    python run.py

This file is kept for backward compatibility only.
"""

import warnings
from app import create_app

# Show deprecation warning
warnings.warn(
    "Using app.py directly is deprecated. Please use 'python run.py' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Create application instance for backward compatibility
app = create_app()

# Import all models for backward compatibility
from app.models import Player, Match, MatchAttendance, Payment
from app.extensions import db

if __name__ == '__main__':
    print("⚠️  Warning: Using app.py directly is deprecated.")
    print("✅ Please use 'python run.py' for the new structure.")
    print("🚀 Starting application anyway for backward compatibility...\n")
    
    app.run(debug=True, port=8080, host='127.0.0.1')

