import pytest
from app.services.wargame_engine import (
    score_to_level,
    parse_iptables_line,
    parse_fail2ban_line,
    parse_auditd_line,
    match_detection_rules,
    LEVEL_THRESHOLDS
)

def test_score_to_level():
    assert score_to_level(0) == "clean"
    assert score_to_level(9) == "clean"
    assert score_to_level(10) == "warning"
    assert score_to_level(39) == "warning"
    assert score_to_level(40) == "detected"
    assert score_to_level(99) == "detected"
    assert score_to_level(100) == "busted"
    assert score_to_level(150) == "busted"

def test_parse_iptables_line():
    line = "Mar  8 12:00:00 kernel: [12345.6789] PWNLAB-DETECT: IN=eth0 OUT= MAC=... SRC=10.100.1.100 DST=10.100.1.10 LEN=60 TOS=0x00 PREC=0x00 TTL=64 ID=12345 DF PROTO=TCP SPT=54321 DPT=80 WINDOW=65535 RES=0x00 SYN URGP=0"
    event = parse_iptables_line(line)
    
    assert event is not None
    assert event["type"] == "iptables_log"
    assert event["src_ip"] == "10.100.1.100"
    assert event["dst_port"] == 80
    
    # Non-matching line
    assert parse_iptables_line("Some other log line") is None

def test_parse_fail2ban_line():
    line = "2026-03-08 12:00:00,000 fail2ban.actions [123]: NOTICE [sshd] Ban 10.100.1.100"
    event = parse_fail2ban_line(line)
    
    assert event is not None
    assert event["type"] == "fail2ban_ban"
    assert event["src_ip"] == "10.100.1.100"
    assert event["jail"] == "sshd"
    
    # Non-matching line
    assert parse_fail2ban_line("Some other log line") is None

def test_parse_auditd_line():
    line = 'type=EXECVE msg=audit(1234567890.123:456): argc=3 a0="sh" a1="-c" a2="id" key="shell_spawn" exe="/bin/sh"'
    event = parse_auditd_line(line)
    
    assert event is not None
    assert event["type"] == "auditd"
    assert event["key"] == "shell_spawn"
    assert event["exe"] == "/bin/sh"
    
    # Non-matching line
    assert parse_auditd_line("type=SYSCALL msg=audit(1234567890.123:456): arch=c000003e syscall=59 success=yes") is not None

def test_match_detection_rules():
    rules = {
        "port_scan": {
            "backend": "iptables",
            "severity": "warning"
        },
        "brute_force": {
            "backend": "fail2ban",
            "severity": "detected"
        },
        "shell_spawn": {
            "backend": "auditd",
            "severity": "busted",
            "trigger": "/bin/sh"
        }
    }
    
    # Match iptables
    event1 = {"type": "iptables_log"}
    assert match_detection_rules(event1, rules) == "warning"
    
    # Match fail2ban
    event2 = {"type": "fail2ban_ban"}
    assert match_detection_rules(event2, rules) == "detected"
    
    # Match auditd by key
    event3 = {"type": "auditd", "key": "shell_spawn", "exe": "/bin/bash"}
    assert match_detection_rules(event3, rules) == "busted"
    
    # Match auditd by exe
    event4 = {"type": "auditd", "key": "other_key", "exe": "/bin/sh"}
    assert match_detection_rules(event4, rules) == "busted"
    
    # No match
    event5 = {"type": "unknown"}
    assert match_detection_rules(event5, rules) is None
