#!/bin/bash
# Monitor fail2ban for bans and emit JSONL events

STATUS_FILE="/tmp/blaqliq-fail2ban-seen"
touch "$STATUS_FILE"

if ! command -v fail2ban-client &>/dev/null; then
    exit 0
fi

# Get list of jails
JAILS=$(fail2ban-client status 2>/dev/null | grep "Jail list" | sed 's/.*:\s*//' | tr ',' '\n' | tr -d ' ') || exit 0

for jail in $JAILS; do
    [ -z "$jail" ] && continue

    banned=$(fail2ban-client status "$jail" 2>/dev/null | grep "Banned IP list" | sed 's/.*:\s*//' | tr ' ' '\n') || continue

    while read -r ip; do
        [ -z "$ip" ] && continue
        key="${jail}:${ip}"
        if ! grep -qF "$key" "$STATUS_FILE" 2>/dev/null; then
            echo "$key" >> "$STATUS_FILE"
            printf '{"type":"fail2ban_ban","jail":"%s","src_ip":"%s","ts":"%s"}\n' \
                "$jail" "$ip" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        fi
    done <<< "$banned"
done
