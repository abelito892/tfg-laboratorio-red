#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Script de verificación de reglas de firewall - TFG ASIR
# ═══════════════════════════════════════════════════════════════════════════

VERDE='\033[0;32m'
ROJO='\033[0;31m'
AZUL='\033[0;34m'
AMARILLO='\033[1;33m'
RESET='\033[0m'
OK=0
FALLOS=0

function test_permitido() {
    local descripcion="$1"
    local comando="$2"
    if eval "$comando" &>/dev/null; then
        echo -e "  ${VERDE}✓ PERMITIDO${RESET} $descripcion"
        ((OK++))
    else
        echo -e "  ${ROJO}✗ FALLO${RESET} $descripcion (debería estar permitido)"
        ((FALLOS++))
    fi
}

function test_bloqueado() {
    local descripcion="$1"
    local contenedor="$2"
    local ip="$3"
    local puerto="$4"
    # Usamos timeout 3s — si no conecta en 3s, está bloqueado (DROP)
    resultado=$(docker exec $contenedor bash -c \
        "timeout 3 bash -c 'cat < /dev/null > /dev/tcp/$ip/$puerto' 2>&1; echo rc=\$?")
    if echo "$resultado" | grep -q "rc=0"; then
        echo -e "  ${ROJO}✗ FALLO${RESET} $descripcion (debería estar bloqueado)"
        ((FALLOS++))
    else
        echo -e "  ${VERDE}✓ BLOQUEADO${RESET} $descripcion"
        ((OK++))
    fi
}

function seccion() {
    echo ""
    echo -e "${AZUL}═══ $1 ═══${RESET}"
}

echo -e "${AZUL}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║     Verificación de Firewall - TFG ASIR               ║"
echo "║     fw01 con nftables                                  ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${RESET}"

seccion "0. Estado del firewall"
echo -e "  Reglas activas en fw01:"
docker exec fw01 nft list ruleset 2>/dev/null | \
    grep -E "policy|masquerade|dport|saddr.*daddr" | sed 's/^/    /'

# ─── TRÁFICO PERMITIDO ────────────────────────────────────────────────────────
seccion "1. Tráfico PERMITIDO (debe funcionar)"

test_permitido "LAN → proxy01 HTTP (puerto 80)" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/172.21.0.10/80\"'"

test_permitido "LAN → proxy01 HTTPS (puerto 443)" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/172.21.0.10/443\"'"

test_permitido "LAN → SSH en ssh01 (puerto 22)" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/192.168.100.10/22\"'"

test_permitido "LAN → DNS en dns01 (puerto 53)" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/192.168.100.20/53\"'"

test_permitido "proxy01 DMZ → web01 DMZ (tráfico interno DMZ)" \
    "docker exec proxy01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/172.21.0.20/443\"'"

test_permitido "LAN → internet via Squid (NAT)" \
    "docker exec client01 curl -s -x http://192.168.100.40:3128 -o /dev/null -w '%{http_code}' --max-time 10 http://example.com | grep -q 200"

# ─── TRÁFICO BLOQUEADO ────────────────────────────────────────────────────────
seccion "2. Tráfico BLOQUEADO (debe fallar)"

test_bloqueado "DMZ → LAN: proxy01 no puede acceder a ssh01 (22)" \
    proxy01 192.168.100.10 22

test_bloqueado "DMZ → LAN: web01 no puede acceder a ssh01 (22)" \
    web01 192.168.100.10 22

test_bloqueado "DMZ → LAN: proxy01 no puede acceder a dns01 (53)" \
    proxy01 192.168.100.20 53

test_bloqueado "LAN → web01 directo sin proxy (443 bloqueado)" \
    client01 172.21.0.20 443

test_bloqueado "LAN → web01 directo sin proxy (80 bloqueado)" \
    client01 172.21.0.20 80

# ─── NAT ─────────────────────────────────────────────────────────────────────
seccion "3. NAT y enmascaramiento"

test_permitido "LAN → internet directo via fw01 (NAT masquerade)" \
    "docker exec client01 curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://1.1.1.1 | grep -qE '200|301|302'"

# ─── RESUMEN ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${AZUL}═══════════════════════════════════════════════════════════${RESET}"
TOTAL=$((OK + FALLOS))
PORCENTAJE=$((OK * 100 / TOTAL))
if [[ $FALLOS -eq 0 ]]; then
    echo -e "${VERDE}✓ Firewall funcionando correctamente: $OK/$TOTAL pruebas OK${RESET}"
    echo -e "${VERDE}  Las reglas de segmentación de red están aplicadas${RESET}"
else
    echo -e "${AMARILLO}Resultado: $OK/$TOTAL pruebas OK ($PORCENTAJE%)${RESET}"
    echo -e "${ROJO}  $FALLOS reglas de firewall no funcionan como se esperaba${RESET}"
fi
echo -e "${AZUL}═══════════════════════════════════════════════════════════${RESET}"
