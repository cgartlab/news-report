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

# Port listeners can be discovered through several tools; minimal container
# images ship none of lsof, so probe for what exists rather than assuming lsof.
# Prints the listening PIDs (may be empty) and returns 0 when a listener exists.
listening_pids() {
  local port="$1" pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  elif command -v ss >/dev/null 2>&1; then
    pids=$(ss -lptnH "sport = :$port" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)
  elif command -v fuser >/dev/null 2>&1; then
    pids=$(fuser "$port"/tcp 2>/dev/null || true)
  elif [[ -r /proc/net/tcp ]]; then
    # Linux without lsof/ss/fuser: match the socket inode against /proc/*/fd.
    local inodes
    inodes=$(awk -v p="$(printf '%04X' "$port")" \
      '$2 ~ ":" p "$" && $4 == "0A" {print $10}' /proc/net/tcp /proc/net/tcp6 2>/dev/null | sort -u)
    for ino in $inodes; do
      for fd in /proc/[0-9]*/fd/*; do
        if [[ "$(readlink "$fd" 2>/dev/null)" == "socket:[$ino]" ]]; then
          pids="$pids $(basename "$(dirname "$(dirname "$fd")")")"
        fi
      done
    done
  elif command -v netstat >/dev/null 2>&1; then
    # Windows (Git Bash) and other netstat-only environments.
    pids=$(netstat -ano 2>/dev/null \
      | awk -v p=":$port" '$1 ~ /^(TCP|tcp)/ && $2 ~ p"$" && $NF ~ /^[0-9]+$/ {print $NF}' \
      | sort -u || true)
  fi
  # Collapse stray whitespace so callers can test the result with [[ -n ]].
  pids=$(printf '%s' "$pids" | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')
  printf '%s' "$pids"
}

if [[ "${1:-}" == "--stop" ]]; then
  PID=$(listening_pids "$PORT")
  if [[ -n "$PID" ]]; then
    # On Windows/Git Bash, netstat reports Windows PIDs while bash's kill()
    # expects MSYS PIDs; taskkill is the only reliable way to stop those.
    if command -v taskkill >/dev/null 2>&1 && [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* ]]; then
      # shellcheck disable=SC2086  # intentional word-splitting of the PID list
      taskkill //F //PID $(echo $PID | tr ' ' ',' ) >/dev/null 2>&1 || true
    else
      # shellcheck disable=SC2086  # intentional word-splitting of the PID list
      kill $PID 2>/dev/null || true
    fi
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

if [[ -n "$(listening_pids "$PORT")" ]]; then
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
disown 2>/dev/null || true

# Poll for readiness instead of a fixed sleep: a fixed 3s guess both wastes
# time on fast machines and fails on slow ones.
READY_TIMEOUT="${READY_TIMEOUT:-15}"
for _ in $(seq 1 "$READY_TIMEOUT"); do
  if curl -fsS "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo "OK: CDP = http://127.0.0.1:$PORT"
    exit 0
  fi
  sleep 1
done

echo "error: browser launched but CDP port $PORT did not answer within ${READY_TIMEOUT}s" >&2
exit 1
