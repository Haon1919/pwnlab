FROM debian:bookworm-slim

LABEL maintainer="pwnlab" \
      description="PwnLab attacker base image"

ARG TOOL_PROFILE=web

# Install base tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget netcat-traditional nmap \
    python3 python3-pip \
    bash vim nano \
    iproute2 iputils-ping \
    dnsutils \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Web profile tools
RUN if [ "$TOOL_PROFILE" = "web" ] || [ "$TOOL_PROFILE" = "full" ]; then \
    apt-get update && apt-get install -y --no-install-recommends \
        nikto \
        dirb \
        sqlmap \
    && rm -rf /var/lib/apt/lists/*; \
    fi

# Network profile tools
RUN if [ "$TOOL_PROFILE" = "network" ] || [ "$TOOL_PROFILE" = "full" ]; then \
    apt-get update && apt-get install -y --no-install-recommends \
        hydra \
        medusa \
        masscan \
        tcpdump \
    && rm -rf /var/lib/apt/lists/*; \
    fi

# Crypto profile tools
RUN if [ "$TOOL_PROFILE" = "crypto" ] || [ "$TOOL_PROFILE" = "full" ]; then \
    apt-get update && apt-get install -y --no-install-recommends \
        openssl \
        hashcat \
        john \
    && rm -rf /var/lib/apt/lists/*; \
    fi

RUN pip3 install --no-cache-dir requests pwntools 2>/dev/null || pip3 install --no-cache-dir requests

WORKDIR /workspace

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
