FROM ubuntu:20.04

LABEL maintainer="pwnlab" \
      description="PwnLab Metasploitable Lite - deliberately vulnerable"

ENV DEBIAN_FRONTEND=noninteractive

# Install deliberately vulnerable services
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    vsftpd \
    telnetd \
    xinetd \
    apache2 \
    php \
    php-mysql \
    mysql-server \
    && rm -rf /var/lib/apt/lists/*

# Setup vulnerable SSH (weak config)
RUN mkdir -p /var/run/sshd && \
    echo 'root:toor' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Vulnerable vsftpd (anon enabled)
COPY vsftpd.conf /etc/vsftpd.conf

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 21 22 23 80 3306

CMD ["/start.sh"]
