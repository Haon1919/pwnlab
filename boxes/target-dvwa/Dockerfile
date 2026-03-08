FROM vulnerables/web-dvwa:latest

LABEL maintainer="pwnlab" \
      description="PwnLab DVWA target"

# DVWA already fully configured in base image
# Override to make it immediately exploitable (security=low)
COPY dvwa-config.inc.php /var/www/html/config/config.inc.php.dist

EXPOSE 80

CMD ["/main.sh"]
