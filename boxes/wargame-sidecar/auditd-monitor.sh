#!/bin/bash
# Monitor auditd for shell spawns and emit JSONL events

OFFSET_FILE="/tmp/pwnlab-auditd-offset"
AUDIT_LOG="/var/log/audit/audit.log"

[ ! -f "$AUDIT_LOG" ] && exit 0

LAST_LINE=0
if [ -f "$OFFSET_FILE" ]; then
    LAST_LINE=$(cat "$OFFSET_FILE")
fi

TOTAL_LINES=$(wc -l < "$AUDIT_LOG")
echo "$TOTAL_LINES" > "$OFFSET_FILE"

if [ "$TOTAL_LINES" -le "$LAST_LINE" ]; then
    exit 0
fi

tail -n +"$((LAST_LINE + 1))" "$AUDIT_LOG" | grep -E 'key="shell_spawn_by_webserver"' | while read -r line; do
    EXE=$(echo "$line" | grep -oP 'exe="\K[^"]+' || echo "unknown")
    KEY=$(echo "$line" | grep -oP 'key="\K[^"]+' || echo "unknown")
    printf '{"type":"auditd","key":"%s","exe":"%s","raw":"%s","ts":"%s"}\n' \
        "$KEY" "$EXE" "${line//\"/\'}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
done
