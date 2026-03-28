#!/usr/bin/env bash
# Mouse Battery Monitor - Launcher (macOS / Linux)
# Creates venv if needed, installs dependencies, runs the app.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"

cd "$PROJECT_DIR"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Install / upgrade dependencies
pip install -q -r requirements.txt

# Copy example config if user config doesn't exist
if [ ! -f config/config.json ]; then
    echo "Creating config/config.json from example..."
    cp config/config.example.json config/config.json
fi

# Run
python -m app.main
