#!/bin/bash
# Configurar gateway hacia fw01 para que el tráfico a DMZ pase por el firewall
sleep 2
ip route replace default via 192.168.100.2 2>/dev/null || true
# Mantener el contenedor vivo
tail -f /dev/null
