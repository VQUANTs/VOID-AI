#!/data/data/com.termux/files/usr/bin/bash
set -u
LOG_DIR="${VOID_LOG_DIR:-$HOME/.void-stack}"
for f in "$LOG_DIR"/*.pid; do
    [ -f "$f" ] || continue
    pid="$(cat "$f" 2>/dev/null || true)"
    if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; fi
    rm -f "$f"
done
# Also stop matching child processes if PID files are stale.
ps -A -o pid=,args= 2>/dev/null | awk '/python server\.py|python -m void\.telegram_bot|next start/ && !/awk/ {print $1}' | while read -r pid; do
    kill "$pid" 2>/dev/null || true
done
printf '%s\n' "[VOID] stack stop requested"
