# Pichanga Manager

Internal cricket club management system for tracking players, matches, and payments.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Gsousav/ClubManager
cd ClubManager

# Run the app 
./run_cricket_manager.sh
```

## Project Structure

```
ClubManager/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory 
│   ├── extensions.py            # Flask extensions (database, etc.)
│   ├── models/                  # Database models
│   │   ├── __init__.py         # Model exports
│   │   ├── player.py           # Player model with balance calculations
│   │   ├── match.py            # Match & MatchAttendance models
│   │   └── payment.py          # Payment model
│   ├── blueprints/             # Route blueprints (organized by feature)
│   │   ├── __init__.py         # Blueprint exports
│   │   ├── main.py             # Dashboard and general routes
│   │   ├── players.py          # Player management routes
│   │   ├── matches.py          # Match management routes
│   │   └── payments.py         # Payment management routes
│   └── utils/                  # Utility functions
│       ├── __init__.py         # Utility exports
│       ├── database.py         # Database migration logic
│       └── imports.py          # Excel import functionality
├── static/                      # CSS, JavaScript, images
├── templates/                   # HTML templates
├── data/                       # Database storage
├── config.py                   # Configuration management
├── run.py                      # Main entry point (recommended)
├── app.py                      # Legacy entry point (backward compatibility)
├── run_cricket_manager.sh      # Launch script
└── requirements.txt            # Python dependencies
```

### Entry Points

**Recommended (New Structure):**
```bash
python run.py              # Direct Python execution
./run_cricket_manager.sh   # Production-ready with Gunicorn
```

**Legacy (Backward Compatibility):**
```bash
python app.py             # Shows deprecation warning
```

## Requirements

- Python 3.12+ (macOS/Linux)
- Internet connection (first run only)

## Troubleshooting

- **Python not found:** Install from python.org
- **Permission denied:** Run `chmod +x run_cricket_manager.sh`
- **Port in use:** Script auto-kills existing processes

## Data

Database stored in `data/cricket.db` - **backup regularly!**

Stop with `Ctrl+C` 
