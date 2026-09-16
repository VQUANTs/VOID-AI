#!/data/data/com.termux/files/usr/bin/bash
set -u

VOID_HOME="${VOID_HOME:-$HOME/VOID-AI}"
ROUTER9_DIR="${ROUTER9_DIR:-$HOME/VOID-ROUTER-LAB/9router}"
ROUTER9_URL="${VOID_ROUTER_BASE_URL:-http://127.0.0.1:20127/v1}"
ROUTER9_HEALTH="http://127.0.0.1:20127/api/health"
LOG_DIR="${VOID_LOG_DIR:-$HOME/.void-stack}"
mkdir -p "$LOG_DIR"

cd "$VOID_HOME"

is_running() {
    ps -A -o args= 2>/dev/null | grep -F "$1" | grep -v grep >/dev/null 2>&1
}

wait_router9() {
    for _ in $(seq 1 60); do
        if curl -fsS --max-time 2 "$ROUTER9_HEALTH" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

echo "[VOID] Starting Router9..."
if curl -fsS --max-time 2 "$ROUTER9_HEALTH" >/dev/null 2>&1; then
    echo "[VOID] Router9 already online."
elif [ -d "$ROUTER9_DIR" ]; then
    if ! is_running "next start" && ! is_running "npm run start"; then
        (
            cd "$ROUTER9_DIR" || exit 1
            PORT=20127 HOSTNAME=127.0.0.1 npm run start
        ) >>"$LOG_DIR/router9.log" 2>&1 &
        echo $! >"$LOG_DIR/router9.pid"
    fi
    if ! wait_router9; then
        echo "[VOID] ERROR: Router9 did not become ready."
        echo "[VOID] Check $LOG_DIR/router9.log"
        exit 1
    fi
else
    echo "[VOID] ERROR: Router9 directory not found: $ROUTER9_DIR"
    exit 1
fi

export VOID_ROUTER_BASE_URL="$ROUTER9_URL"

start_if_missing() {
    local pattern="$1"
    local command="$2"
    local logfile="$3"
    if is_running "$pattern"; then
        echo "[VOID] Already running: $pattern"
    else
        nohup bash -lc "cd '$VOID_HOME' && $command" >>"$LOG_DIR/$logfile" 2>&1 &
        echo $! >"$LOG_DIR/${logfile%.log}.pid"
        echo "[VOID] Started: $pattern"
    fi
}

start_if_missing "python server.py" "python server.py" "api.log"
start_if_missing "python -m void.telegram_bot" "TELEGRAM_MODE=polling python -m void.telegram_bot" "telegram.log"

echo "[VOID] Stack is running."
echo "[VOID] Browser: http://127.0.0.1:8787/"
echo "[VOID] Logs: $LOG_DIR"
