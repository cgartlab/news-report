#!/usr/bin/env bash
# edge-cdp.sh — launch Edge (or Chrome/Chromium) with a local proxy and a CDP
# debug port for news-report module 06 (X-Browser). See SKILL.md「模块 06」.
#
# Usage (Linux / macOS):
#   ./bin/edge-cdp.sh                 # defaults: proxy 127.0.0.1:7897, port 9222
#   PROXY=http://127.0.0.1:7890 ./bin/edge-cdp.sh
#   PORT=9223 ./bin/edge-cdp.sh
#   ./bin/edge-cdp.sh --stop          # stop the CDP instance on this port
set -euo pipefail

PROXY="${PROXY:-http://127.0.0.1:7897}"
PORT="${PORT:-9222}"
START_URL="${START_URL:-https://x.com}"
USER_DATA_DIR="${USER_DATA_DIR:-$HOME/.local/share/edge-cdp-profile}"

if [[ "${1:-}" == "--stop" ]]; then
  PID=$(lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$PID" ]]; then
    kill "$PID"
    echo "stopped CDP instance on port $PORT (pid $PID)"
  else
    echo "nothing listening on port $PORT"
  fi
  exit 0
fi

# Pick a Chromium-family browser.
BROWSER=""
for b in \
  "$(command -v microsoft-edge)" \
  "$(command -v msedge)" \
  "$(command -v google-chrome)" \
  "$(command -v chromium)" \
  "$(command -v brave-browser)" \
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
  if [[ -n "$b" && -x "$b" ]]; then BROWSER="$b"; break; fi
done
if [[ -z "$BROWSER" ]]; then
  echo "error: no Edge/Chrome/Chromium found" >&2
  exit 1
fi

if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "already listening on $PORT — no-op"
  exit 0
fi

mkdir -p "$USER_DATA_DIR"

"$BROWSER" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$USER_DATA_DIR" \
  --proxy-server="$PROXY" \
  --no-first-run \
  --no-default-browser-check \
  "$START_URL" \
  >/dev/null 2>&1 &
disown

sleep 3
if curl -fsS "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "OK: CDP = http://127.0.0.1:$PORT"
else
  echo "error: browser launched but CDP port $PORT did not answer" >&2
  exit 1
fi
