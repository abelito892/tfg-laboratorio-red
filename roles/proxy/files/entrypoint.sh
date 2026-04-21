#!/bin/bash
# Entrypoint proxy01 — espera fw01 y syslog01, configura rutas, arranca rsyslog + nginx

# Esperar a que fw01 esté disponible (ICMP)
echo "Esperando a fw01 (172.21.0.2)..."
until ping -c1 -W2 172.21.0.2 >/dev/null 2>&1; do
    sleep 2
done
echo "fw01 disponible."

# Esperar a que syslog01 esté disponible en mgmt_net
echo "Esperando a syslog01 (172.22.0.10)..."
until bash -c "cat < /dev/null > /dev/tcp/172.22.0.10/514" 2>/dev/null; do
    sleep 2
done
rsyslogd
sleep 1

# Configurar rutas estáticas hacia WAN y LAN a través de fw01
ip route add 172.20.0.0/24 via 172.21.0.2 2>/dev/null || true
ip route add 192.168.100.0/24 via 172.21.0.2 2>/dev/null || true

exec nginx -g "daemon off;"
