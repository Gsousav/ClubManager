#!/bin/bash
# Cricket Club Manager Launcher
# Robust script to run the Cricket Club Manager locally

set -e  # Exit on any error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to print colored output
print_status() {
    echo -e "${BLUE}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

# Function to detect OS and set browser command
detect_browser_command() {
    if command -v xdg-open &> /dev/null; then
        echo "xdg-open"  # Linux
    elif command -v open &> /dev/null; then
        echo "open"      # macOS
    elif command -v start &> /dev/null; then
        echo "start"     # Windows (Git Bash/WSL)
    else
        echo ""          # No browser command available
    fi
}

echo -e "${BLUE}🏏 Cricket Club Manager${NC}"
echo "========================="

# Check if App directory exists and is writable
if [ ! -d "$APP_DIR" ]; then
    print_error "❌ App directory not found!"
    echo "Expected location: $APP_DIR"
    exit 1
fi

if [ ! -w "$APP_DIR" ]; then
    print_error "❌ No write permission to app directory!"
    echo "Please ensure you have write access to: $APP_DIR"
    exit 1
fi

cd "$APP_DIR"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    print_error "❌ Python 3 not found. Please install Python 3.12+"
    echo "Visit: https://www.python.org/downloads/"
    echo ""
    echo "Installation commands:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
    echo "  macOS:         brew install python3"
    exit 1
fi

# Store the Python executable path to ensure consistency
PYTHON_EXEC=$(which python3)
print_status "🐍 Using Python at: $PYTHON_EXEC"

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.12"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    print_status "✅ Python $PYTHON_VERSION detected"
else
    print_error "❌ Python $PYTHON_VERSION is too old. Please install Python 3.12+"
    exit 1
fi

# Check if venv module is available
print_status "🔧 Checking venv module..."
print_status "   Testing: $PYTHON_EXEC -m venv --help"

# Test venv availability with better error handling
if "$PYTHON_EXEC" -c "import venv" 2>/dev/null; then
    print_success "✅ venv module available"
elif "$PYTHON_EXEC" -m venv --help >/dev/null 2>&1; then
    print_success "✅ venv module available"
else
    print_error "❌ Python venv module not available!"
    echo "Debugging info:"
    echo "  Python executable: $PYTHON_EXEC"
    echo "  Testing import:"
    "$PYTHON_EXEC" -c "import venv" 2>&1 || true
    echo "  Testing venv command:"
    "$PYTHON_EXEC" -m venv --help 2>&1 | head -3 || true
    echo ""
    echo "Please install venv with:"
    echo "  Ubuntu/Debian: sudo apt install python3-venv"
    echo "  CentOS/RHEL:   sudo yum install python3-venv" 
    echo "  macOS:         venv should be included with Python"
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    print_error "❌ requirements.txt not found!"
    echo "Please ensure requirements.txt exists in the project directory."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_warning "⚠️  Creating virtual environment..."
    if ! "$PYTHON_EXEC" -m venv venv; then
        print_error "❌ Failed to create virtual environment!"
        exit 1
    fi
    print_success "✅ Virtual environment created"
fi

# Activate virtual environment BEFORE any pip operations
print_status "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if activation worked
if [ -z "$VIRTUAL_ENV" ]; then
    print_error "❌ Failed to activate virtual environment!"
    exit 1
fi

# Verify we're using the correct Python inside the venv
VENV_PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_status "✅ Virtual environment active (Python $VENV_PYTHON_VERSION)"

# Now use the virtual environment's python and pip
print_status "📦 Installing dependencies..."
if ! python -m pip install --upgrade pip; then
    print_error "❌ Failed to upgrade pip!"
    exit 1
fi

if ! python -m pip install -r requirements.txt; then
    print_error "❌ Failed to install dependencies!"
    echo "Please check requirements.txt for invalid packages or network connectivity."
    exit 1
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    print_error "❌ app.py not found!"
    echo "Please ensure app.py exists in the project directory."
    exit 1
fi

# Kill any existing processes
print_status "🔧 Cleaning up existing processes..."
pkill -f "gunicorn.*app:app" 2>/dev/null || true
pkill -f "python.*app.py" 2>/dev/null || true

# Start the application
print_success "🚀 Starting Cricket Club Manager..."
echo "   Production WSGI server (gunicorn) will be available at: http://127.0.0.1:8080"
echo "   Running with 2 workers for better performance"
echo "   Press Ctrl+C to stop"
echo ""

# Run the app with gunicorn (production WSGI server)
print_status "🏃 Running application with gunicorn..."
if ! python -m gunicorn --bind 127.0.0.1:8080 --workers 2 --timeout 120 app:app; then
    print_error "❌ Application failed to start!"
    echo "Check the error messages above for details."
    exit 1
fi

# Detect and open browser after a short delay
BROWSER_CMD=$(detect_browser_command)
if [ -n "$BROWSER_CMD" ]; then
    print_status "🌐 Opening browser..."
    $BROWSER_CMD http://127.0.0.1:8080
else
    print_warning "⚠️  Could not detect browser command. Please open http://127.0.0.1:8080 manually."
fi

