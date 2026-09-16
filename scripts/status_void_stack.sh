#!/data/data/com.termux/files/usr/bin/bash
set -u
printf '%s\n' '===== VOID STACK STATUS ====='
printf 'Router9: '
if curl -fsS --max-time 2 http://127.0.0.1:20127/api/health >/dev/null 2>&1; then echo ONLINE; else echo OFFLINE; fi
printf 'VOID API: '
if curl -fsS --max-time 2 http://127.0.0.1:8787/health >/dev/null 2>&1; then echo ONLINE; else echo OFFLINE; fi
printf 'Processes:\n'
ps -A -o pid=,args= 2>/dev/null | grep -E 'next start|python server.py|python -m void.telegram_bot' | grep -v grep || true
