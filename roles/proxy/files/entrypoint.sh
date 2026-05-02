#!/bin/bash
echo "Esperando a fw01 (172.21.0.2)..."
until ping -c1 -W2 172.21.0.2 >/dev/null 2>&1; do
    sleep 2
done
echo "fw01 disponible."

echo "Esperando a syslog01 (172.22.0.10)..."
until bash -c "cat < /dev/null > /dev/tcp/172.22.0.10/514" 2>/dev/null; do
    sleep 2
done
rsyslogd
sleep 1

ip route add 172.20.0.0/24 via 172.21.0.2 2>/dev/null || true
ip route add 192.168.100.0/24 via 172.21.0.2 2>/dev/null || true

echo "Iniciando reenvio de logs a syslog01..."
tail -F -n0 /var/log/nginx/proxy01_access.log | while IFS= read -r line; do
  logger -n 172.22.0.10 -P 514 --udp "proxy01: $line"
done &
disown

exec nginx -g "daemon off;"
