# Cricket Club Manager

Internal cricket club management system for tracking players, matches, and payments.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Gsousav/ClubManager
cd cricket-club-manager

# Run the app (handles everything automatically)
./run_cricket_manager.sh
```

Access at: **http://127.0.0.1:8080**

## What It Does

- 👥 Manage players (members & non-members)  
- 🏏 Track matches and attendance
- 💰 Record payments (cash/bank/membership)
- 📊 Generate overdue reports
- 📋 Excel import/export

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
