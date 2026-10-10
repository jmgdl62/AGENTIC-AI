#!/bin/bash
# Start the marketing agent's web app automatically on macOS.
#
# Installs a LaunchAgent that starts the web app when you log in and restarts it if it stops.
# The page is then always at http://127.0.0.1:8000, and only this Mac can reach it.
#
# Usage (from the AGENTIC-AI folder):
#   bash scripts/mac_autostart.sh install     # set up and start now
#   bash scripts/mac_autostart.sh status      # is it running?
#   bash scripts/mac_autostart.sh restart     # restart after changing .env or pulling new code
#   bash scripts/mac_autostart.sh uninstall   # stop it and remove the auto-start

set -euo pipefail

LABEL="com.agentic-ai.marketing-agent"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$PROJECT_DIR/logs"
UVICORN="$PROJECT_DIR/.venv/bin/uvicorn"
PORT=8000
DOMAIN="gui/$(id -u)"

if [ "$(uname)" != "Darwin" ]; then
  echo "This script is for macOS only." >&2
  exit 1
fi

install() {
  if [ ! -x "$UVICORN" ]; then
    echo "Can't find $UVICORN." >&2
    echo "Set up the project first (see README.md): python3 -m venv .venv, then" >&2
    echo "source .venv/bin/activate and pip install -r requirements.txt." >&2
    exit 1
  fi
  if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "Can't find $PROJECT_DIR/.env. Copy .env.example to .env and add your keys first." >&2
    exit 1
  fi

  mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$UVICORN</string>
    <string>web_app:app</string>
    <string>--host</string>
    <string>127.0.0.1</string>
    <string>--port</string>
    <string>$PORT</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>30</integer>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/web_app.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/web_app.log</string>
</dict>
</plist>
EOF

  # Replace any earlier copy, then start it.
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  launchctl bootstrap "$DOMAIN" "$PLIST"
  echo "Installed. The web app starts now and every time you log in."
  echo "Open http://127.0.0.1:$PORT (give it a few seconds the first time)."
  echo "Logs: $LOG_DIR/web_app.log"
}

uninstall() {
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Stopped and removed. The web app no longer starts on its own."
}

restart() {
  launchctl kickstart -k "$DOMAIN/$LABEL"
  echo "Restarted. Open http://127.0.0.1:$PORT"
}

status() {
  if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
    launchctl print "$DOMAIN/$LABEL" | grep -E "^\s*(state|pid|last exit code) =" || true
    if curl -fs -o /dev/null "http://127.0.0.1:$PORT/"; then
      echo "The page is up at http://127.0.0.1:$PORT"
    else
      echo "The page isn't answering yet. Check $LOG_DIR/web_app.log"
    fi
  else
    echo "Not installed. Run: bash scripts/mac_autostart.sh install"
  fi
}

case "${1:-}" in
  install) install ;;
  uninstall) uninstall ;;
  restart) restart ;;
  status) status ;;
  *) echo "Usage: bash scripts/mac_autostart.sh install|status|restart|uninstall" >&2; exit 1 ;;
esac
