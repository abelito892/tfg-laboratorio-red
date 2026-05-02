#!/bin/bash
rm -f /run/squid.pid

echo "Iniciando reenvio de logs squid a syslog01..."
tail -F -n0 /var/log/squid/access.log | while IFS= read -r line; do
  logger -n 172.22.0.10 -P 514 --udp "squid01: $line"
done &
disown

exec squid -NYCd 1
