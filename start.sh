#!/bin/bash
# Start the marketing agent's web app.
#
# Run this every time you want to use the agent:
#   ./start.sh
# Or double-click "Start Agentic AI.command" in Finder.
#
# The first run sets everything up (Python environment and packages). Later runs just start it.
# The page opens in your browser at http://127.0.0.1:8000. Press Ctrl+C to stop it.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJECT_DIR/.venv"
PORT="${PORT:-8000}"
URL="http://127.0.0.1:$PORT"

cd "$PROJECT_DIR"

open_browser() {
  if command -v open >/dev/null 2>&1; then
    open "$1"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" >/dev/null 2>&1
  fi
}

# Already running (for example from scripts/mac_autostart.sh)? Just open the page.
if curl -fs -o /dev/null "$URL/api/reports" 2>/dev/null; then
  echo "The agent is already running at $URL. Opening it."
  open_browser "$URL"
  exit 0
fi

# Find Python 3.10 or newer.
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Python 3.10 or newer is required. Install it from https://www.python.org/downloads/" >&2
  exit 1
fi

# Create the Python environment the first time.
if [ ! -x "$VENV/bin/python" ]; then
  echo "Setting up the Python environment (first run only)..."
  "$PYTHON" -m venv "$VENV"
fi

# Install packages when requirements.txt is new or has changed.
REQ_HASH="$(cksum requirements.txt | cut -d' ' -f1)"
if [ "$(cat "$VENV/.requirements-hash" 2>/dev/null)" != "$REQ_HASH" ]; then
  echo "Installing packages..."
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r requirements.txt
  echo "$REQ_HASH" > "$VENV/.requirements-hash"
fi

# Check the API keys.
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env. Open it, add your ANTHROPIC_API_KEY and FIRECRAWL_API_KEY, then run this again:"
  echo "  $PROJECT_DIR/.env"
  open_browser "$PROJECT_DIR/.env" || true
  exit 1
fi
for key in ANTHROPIC_API_KEY FIRECRAWL_API_KEY; do
  value="$(grep -E "^$key=" .env | tail -n1 | cut -d= -f2- | tr -d '"'"'"' ')"
  if [ -z "$value" ] || [[ "$value" == *"..." ]]; then
    echo "$key is missing in .env. Add your real key, then run this again:" >&2
    echo "  $PROJECT_DIR/.env" >&2
    exit 1
  fi
done

# Something else on the port?
if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is used by another program. Try: PORT=8001 ./start.sh" >&2
  exit 1
fi

# Open the browser once the server answers.
(
  for _ in $(seq 1 30); do
    if curl -fs -o /dev/null "$URL/api/reports" 2>/dev/null; then
      open_browser "$URL"
      exit 0
    fi
    sleep 1
  done
) &

echo "Starting the agent at $URL (press Ctrl+C to stop)..."
exec "$VENV/bin/uvicorn" web_app:app --host 127.0.0.1 --port "$PORT"
