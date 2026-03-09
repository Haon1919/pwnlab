#!/bin/bash
# BlaqLiq attacker base entrypoint

echo "╔══════════════════════════════════════════════════╗"
echo "║          BlaqLiq Attacker Container               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Session ID: ${SESSION_ID:-unknown}"
echo "Mode:       ${MODE:-standard}"
echo ""

# Print target info if not blackbox
if [ -n "$TARGET_DVWA_IP" ]; then
    echo "Target (dvwa): $TARGET_DVWA_IP"
fi
if [ -n "$TARGET_WEBGOAT_IP" ]; then
    echo "Target (webgoat): $TARGET_WEBGOAT_IP"
fi

echo ""
echo "Happy hacking! Remember: authorized targets only."
echo ""

exec "$@"
