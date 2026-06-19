#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Career Forge — one-command launcher (macOS / Linux)
# Creates a virtual env, installs dependencies, checks your .env, and starts the
# Streamlit app at http://localhost:8501
# Usage:  bash run.sh   (or: chmod +x run.sh && ./run.sh)
# ──────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

echo "🔥 Career Forge launcher"
echo "────────────────────────"

# 1. Python check
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 not found. Install Python 3.9+ from https://www.python.org/downloads/"
  exit 1
fi

# 2. Virtual environment
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment (.venv)..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 3. Dependencies (only installs/upgrades when requirements change)
echo "📥 Installing dependencies (first run may take a minute)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 4. .env / API key check
if [ ! -f ".env" ]; then
  echo "📝 No .env found — creating one from the template."
  cp .env.example .env
fi
if ! grep -q "GOOGLE_API_KEY=.\+" .env || grep -q "your_google_api_key_here" .env; then
  echo ""
  echo "⚠️  Add your Google API key before the AI features will work:"
  echo "    1. Get a free key at https://aistudio.google.com/app/apikey"
  echo "    2. Open the .env file in this folder and set:"
  echo "         GOOGLE_API_KEY=\"your_actual_key\""
  echo "    (The deterministic ATS score works without a key; AI tabs need one.)"
  echo ""
  read -r -p "Press Enter to launch anyway, or Ctrl+C to add the key first..."
fi

# 5. Launch
echo "🚀 Starting Career Forge at http://localhost:8501  (Ctrl+C to stop)"
streamlit run app.py
