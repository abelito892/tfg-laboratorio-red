#!/bin/bash

echo "[client01] Esperando a que la red este disponible..."
sleep 3

echo "[client01] Solicitando IP a dhcp01..."
udhcpc -i eth0 -q -n -t 10 2>/dev/null || true

echo "[client01] Configurando proxy hacia squid01..."
export http_proxy="http://192.168.100.40:3128"
export https_proxy="http://192.168.100.40:3128"
export HTTP_PROXY="http://192.168.100.40:3128"
export HTTPS_PROXY="http://192.168.100.40:3128"

echo "[client01] Configuracion de red:"
ip addr show eth0

tail -f /dev/null
