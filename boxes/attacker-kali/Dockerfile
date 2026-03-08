FROM kalilinux/kali-rolling:latest

LABEL maintainer="pwnlab" \
      description="PwnLab Kali Linux attacker image"

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap nikto sqlmap hydra \
    metasploit-framework \
    wordlists \
    dirb \
    curl wget \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["/bin/bash"]
