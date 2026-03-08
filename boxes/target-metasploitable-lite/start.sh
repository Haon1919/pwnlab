#!/bin/bash
service ssh start
service vsftpd start
service apache2 start
service mysql start

echo "Metasploitable Lite services started"
tail -f /dev/null
