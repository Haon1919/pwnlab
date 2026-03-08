#!/bin/bash
# PwnLab iptables detection logging rules template
# Applied by the wargame sidecar container

set -e

CHAIN="PWNLAB-DETECT"
LOG_PREFIX="PWNLAB-DETECT "

echo "[pwnlab-iptables] Setting up detection rules..."

# Create detection chain
iptables -N "$CHAIN" 2>/dev/null || iptables -F "$CHAIN"

# Log new TCP connections (port scan detection)
iptables -A "$CHAIN" -p tcp -m state --state NEW -j LOG \
    --log-prefix "${LOG_PREFIX}" \
    --log-level 4 \
    --log-tcp-options \
    --log-ip-options

# Log UDP scans
iptables -A "$CHAIN" -p udp -j LOG \
    --log-prefix "${LOG_PREFIX}" \
    --log-level 4

iptables -A "$CHAIN" -j RETURN

# Hook into INPUT chain
iptables -I INPUT 1 -j "$CHAIN"

echo "[pwnlab-iptables] Detection rules installed"

# Apply rate-based port scan detection
iptables -A INPUT -m recent --name portscan --rcheck --seconds 60 --hitcount 20 \
    -j LOG --log-prefix "PWNLAB-PORTSCAN-ALERT " || true

iptables -A INPUT -m state --state NEW -m recent --name portscan --set || true

echo "[pwnlab-iptables] Rate limiting rules installed"
