#!/bin/bash
# iptables logging setup and collection for PwnLab detection

CHAIN="PWNLAB-DETECT"
LOG_FILE="/var/log/pwnlab-iptables.log"

case "$1" in
    setup)
        # Create logging chain
        iptables -N "$CHAIN" 2>/dev/null || true
        iptables -F "$CHAIN" 2>/dev/null || true

        # Log all new connections to the chain
        iptables -I INPUT -m state --state NEW -j "$CHAIN" 2>/dev/null || true

        # Log with PWNLAB-DETECT prefix
        iptables -A "$CHAIN" -j LOG --log-prefix "PWNLAB-DETECT " --log-level 4 2>/dev/null || true
        iptables -A "$CHAIN" -j RETURN 2>/dev/null || true

        echo "[iptables-logger] Rules installed"
        ;;

    collect)
        # Read kernel log for PWNLAB-DETECT entries
        if [ -f /var/log/kern.log ]; then
            # Get new entries since last check
            grep "PWNLAB-DETECT" /var/log/kern.log 2>/dev/null | tail -50 | while read -r line; do
                # Parse and emit as JSONL
                SRC=$(echo "$line" | grep -oP 'SRC=\K\S+' || echo "unknown")
                DPT=$(echo "$line" | grep -oP 'DPT=\K\d+' || echo "0")
                printf '{"type":"iptables_log","src_ip":"%s","dst_port":%s,"raw":"%s","ts":"%s"}\n' \
                    "$SRC" "$DPT" "${line//\"/\'}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
            done
        fi

        # Alternative: read from dmesg
        dmesg 2>/dev/null | grep "PWNLAB-DETECT" | tail -20 | while read -r line; do
            SRC=$(echo "$line" | grep -oP 'SRC=\K\S+' || echo "unknown")
            DPT=$(echo "$line" | grep -oP 'DPT=\K\d+' || echo "0")
            printf '{"type":"iptables_log","src_ip":"%s","dst_port":%s,"raw":"%s","ts":"%s"}\n' \
                "$SRC" "$DPT" "${line//\"/\'}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        done
        ;;
esac
