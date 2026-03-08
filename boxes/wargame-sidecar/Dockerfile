FROM debian:bookworm-slim

LABEL maintainer="pwnlab" \
      description="PwnLab wargame detection sidecar"

RUN apt-get update && apt-get install -y --no-install-recommends \
    iptables \
    fail2ban \
    auditd \
    auditctl \
    iproute2 \
    procps \
    bash \
    python3 \
    && rm -rf /var/lib/apt/lists/*

COPY iptables-logger.sh /usr/local/bin/iptables-logger.sh
COPY fail2ban-monitor.sh /usr/local/bin/fail2ban-monitor.sh
COPY auditd-monitor.sh /usr/local/bin/auditd-monitor.sh
COPY sidecar.sh /usr/local/bin/sidecar.sh
COPY pwnlab.conf /etc/fail2ban/jail.d/pwnlab.conf

RUN chmod +x /usr/local/bin/*.sh

VOLUME ["/events"]

CMD ["/usr/local/bin/sidecar.sh"]
