#!/bin/bash
# PwnLab wargame detection sidecar main script

set -e

EVENTS_FILE="/events/events.jsonl"
SESSION_ID="${SESSION_ID:-unknown}"
POLL_INTERVAL=5

echo "[sidecar] Starting PwnLab detection sidecar for session: $SESSION_ID"

# Setup iptables logging rules
echo "[sidecar] Setting up iptables logging..."
/usr/local/bin/iptables-logger.sh setup || echo "[sidecar] iptables setup failed (may need NET_ADMIN cap)"

# Start fail2ban if available
if command -v fail2ban-server &>/dev/null; then
    echo "[sidecar] Starting fail2ban..."
    fail2ban-server -b || echo "[sidecar] fail2ban start failed"
fi

# Start auditd if available
if command -v auditd &>/dev/null; then
    echo "[sidecar] Starting auditd..."
    auditd -b || echo "[sidecar] auditd start failed"
    # Load pwnlab rules
    auditctl -w /bin/sh -p x -k shell_spawn_by_webserver 2>/dev/null || true
    auditctl -w /bin/bash -p x -k shell_spawn_by_webserver 2>/dev/null || true
fi

touch "$EVENTS_FILE"

echo "[sidecar] Starting detection loop (interval: ${POLL_INTERVAL}s)"

while true; do
    # Collect iptables events
    /usr/local/bin/iptables-logger.sh collect >> "$EVENTS_FILE" 2>/dev/null || true

    # Collect fail2ban events
    /usr/local/bin/fail2ban-monitor.sh >> "$EVENTS_FILE" 2>/dev/null || true

    # Collect auditd events
    /usr/local/bin/auditd-monitor.sh >> "$EVENTS_FILE" 2>/dev/null || true

    sleep "$POLL_INTERVAL"
done
