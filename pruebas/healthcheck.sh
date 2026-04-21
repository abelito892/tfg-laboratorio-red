#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Script de verificación del laboratorio TFG ASIR
# ═══════════════════════════════════════════════════════════════════════════

VERDE='\033[0;32m'
ROJO='\033[0;31m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
RESET='\033[0m'
OK=0
FALLOS=0

function test_check() {
    local descripcion="$1"
    local comando="$2"
    if eval "$comando" &>/dev/null; then
        echo -e "  ${VERDE}✓${RESET} $descripcion"
        ((OK++))
    else
        echo -e "  ${ROJO}✗${RESET} $descripcion"
        ((FALLOS++))
    fi
}

function seccion() {
    echo ""
    echo -e "${AZUL}═══ $1 ═══${RESET}"
}

# ─── CALENTAMIENTO ───────────────────────────────────────────────────────────
echo -e "${AZUL}Generando actividad inicial en el laboratorio...${RESET}"
for c in ssh01 dns01 dhcp01 web01 proxy01 squid01; do
    docker exec $c logger -t healthcheck "arranque del laboratorio" 2>/dev/null
done
# Forzar lease DHCP en client01
docker exec client01 udhcpc -i eth0 -q 2>/dev/null || true
sleep 5
echo -e "${AZUL}Iniciando verificaciones...${RESET}"

seccion "1. Contenedores activos"
for c in fw01 ssh01 dns01 dhcp01 web01 proxy01 squid01 client01 syslog01 mysql01 dbadmin01 panel01; do
    test_check "$c corriendo" "docker ps --filter name=$c --filter status=running --format '{{.Names}}' | grep -q $c"
done

seccion "2. Redes Docker del laboratorio"
for r in wan_net dmz_net lan_net mgmt_net db_net; do
    test_check "$r existe" "docker network inspect $r"
done

seccion "3. Firewall nftables"
test_check "fw01 tiene reglas nftables cargadas" "docker exec fw01 nft list ruleset | grep -q 'chain forward'"
test_check "fw01 tiene NAT activo" "docker exec fw01 nft list ruleset | grep -q 'masquerade'"

seccion "4. Servicios principales"
test_check "SSH corriendo en ssh01" "docker exec ssh01 pgrep sshd"
test_check "DNS (BIND9) corriendo en dns01" "docker exec dns01 pgrep named"
test_check "DHCP corriendo en dhcp01" "docker exec dhcp01 pgrep dhcpd"
test_check "Nginx corriendo en web01" "docker exec web01 pgrep nginx"
test_check "Nginx corriendo en proxy01" "docker exec proxy01 pgrep nginx"
test_check "Squid corriendo en squid01" "docker exec squid01 pgrep squid"
test_check "rsyslog corriendo en syslog01" "docker exec syslog01 pgrep rsyslogd"
test_check "MySQL corriendo en mysql01" "docker exec mysql01 pgrep mysqld"

seccion "5. Pruebas funcionales de servicios"
test_check "DNS resuelve web01.laboratorio.local" \
    "docker exec client01 nslookup web01.laboratorio.local 192.168.100.20 | grep -q '172.21.0.20'"
test_check "web01 responde HTTPS desde host" \
    "curl -sk -o /dev/null -w '%{http_code}' --max-time 5 https://172.21.0.20 | grep -q 200"
test_check "proxy01 responde HTTPS (código 200)" \
    "docker exec client01 curl -sk -o /dev/null -w '%{http_code}' --max-time 5 https://172.21.0.10 | grep -q 200"
test_check "squid01 proxy funciona" \
    "docker exec client01 curl -s --max-time 10 -x http://192.168.100.40:3128 -o /dev/null -w '%{http_code}' http://example.com | grep -q 200"

seccion "6. Sistema de logs centralizados"
for f in ssh dns dhcp web proxy squid; do
    test_check "Fichero $f.log existe en syslog01" "docker exec syslog01 test -s /var/log/laboratorio/$f.log"
done

seccion "7. Base de datos MySQL"
test_check "BBDD Syslog existe" \
    "docker exec mysql01 bash -c 'mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" -e \"SHOW DATABASES;\" 2>/dev/null | grep -q Syslog'"
test_check "Tabla SystemEvents existe" \
    "docker exec mysql01 bash -c 'mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" Syslog -e \"SHOW TABLES;\" 2>/dev/null | grep -q SystemEvents'"
test_check "Usuario rsyslog puede conectar" \
    "docker exec mysql01 mysql -u rsyslog -pRsyslog_TFG_2026! -e 'SELECT 1;' 2>/dev/null"
test_check "phpMyAdmin responde HTTP (código 200)" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:8080 | grep -q 200"

TOTAL_LOGS=$(docker exec mysql01 bash -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" Syslog -N -e "SELECT COUNT(*) FROM SystemEvents;" 2>/dev/null' | tr -d ' ')
if [[ "$TOTAL_LOGS" -gt 0 ]]; then
    echo -e "  ${VERDE}✓${RESET} Hay $TOTAL_LOGS registros en SystemEvents"
    ((OK++))
else
    echo -e "  ${ROJO}✗${RESET} La tabla SystemEvents está vacía"
    ((FALLOS++))
fi

seccion "8. Panel de control Flask"
test_check "panel01 responde HTTP (código 200)" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:5000 | grep -q 200"
test_check "API status devuelve datos" \
    "curl -s --max-time 5 http://localhost:5000/api/status | grep -q 'fw01'"
test_check "API logs SSH devuelve datos" \
    "curl -s --max-time 5 http://localhost:5000/api/logs/ssh | grep -q 'log'"
test_check "API MySQL devuelve datos" \
    "curl -s --max-time 5 http://localhost:5000/api/mysql/total_por_host | grep -q 'Host'"
test_check "API DHCP devuelve leases" \
    "curl -s --max-time 5 http://localhost:5000/api/dhcp/leases | grep -q '192.168'"

seccion "9. Prueba end-to-end: enviar log y verificar persistencia"
MARCA="healthcheck_$(date +%s)"
docker exec ssh01 logger -t healthcheck "$MARCA desde ssh01" 2>/dev/null
sleep 3
test_check "Log aparece en fichero ssh.log" \
    "docker exec syslog01 grep -q '$MARCA' /var/log/laboratorio/ssh.log"
test_check "Log aparece en MySQL SystemEvents" \
    "docker exec mysql01 bash -c 'mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" Syslog -N -e \"SELECT Message FROM SystemEvents WHERE Message LIKE \\\"%$MARCA%\\\";\" 2>/dev/null' | grep -q '$MARCA'"

echo ""
echo -e "${AZUL}═══════════════════════════════════════════════════════════${RESET}"
TOTAL=$((OK + FALLOS))
PORCENTAJE=$((OK * 100 / TOTAL))
if [[ $FALLOS -eq 0 ]]; then
    echo -e "${VERDE}✓ Todos los tests pasaron: $OK/$TOTAL (100%)${RESET}"
    echo -e "${VERDE}  Laboratorio funcionando correctamente${RESET}"
else
    echo -e "${AMARILLO}Resultado: $OK/$TOTAL tests OK ($PORCENTAJE%)${RESET}"
    echo -e "${ROJO}  $FALLOS fallos detectados${RESET}"
fi
echo -e "${AZUL}═══════════════════════════════════════════════════════════${RESET}"
