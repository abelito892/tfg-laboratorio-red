#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Script de verificación del laboratorio TFG ASIR
# Versión completa — incluye todas las verificaciones
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
docker exec client01 udhcpc -i eth0 -q 2>/dev/null || true
sleep 5
echo -e "${AZUL}Iniciando verificaciones...${RESET}"

# ─── 1. CONTENEDORES ACTIVOS ─────────────────────────────────────────────────
seccion "1. Contenedores activos"
for c in fw01 ssh01 dns01 dhcp01 web01 proxy01 squid01 client01 syslog01 mysql01 dbadmin01 panel01; do
    test_check "$c corriendo" "docker ps --filter name=$c --filter status=running --format '{{.Names}}' | grep -q $c"
done

# ─── 2. REDES DOCKER ─────────────────────────────────────────────────────────
seccion "2. Redes Docker del laboratorio"
for r in wan_net dmz_net lan_net mgmt_net db_net; do
    test_check "$r existe" "docker network inspect $r"
done

# ─── 3. FIREWALL ─────────────────────────────────────────────────────────────
seccion "3. Firewall nftables"
test_check "fw01 tiene reglas nftables cargadas" \
    "docker exec fw01 nft list ruleset | grep -q 'chain forward'"
test_check "fw01 tiene NAT activo" \
    "docker exec fw01 nft list ruleset | grep -q 'masquerade'"
test_check "fw01 política forward es DROP" \
    "docker exec fw01 nft list ruleset | grep -q 'policy drop'"

# ─── 4. SERVICIOS PRINCIPALES ────────────────────────────────────────────────
seccion "4. Servicios principales"
test_check "SSH corriendo en ssh01" "docker exec ssh01 pgrep sshd"
test_check "DNS (BIND9) corriendo en dns01" "docker exec dns01 pgrep named"
test_check "DHCP corriendo en dhcp01" "docker exec dhcp01 pgrep dhcpd"
test_check "Nginx corriendo en web01" "docker exec web01 pgrep nginx"
test_check "Nginx corriendo en proxy01" "docker exec proxy01 pgrep nginx"
test_check "Squid corriendo en squid01" "docker exec squid01 pgrep squid"
test_check "rsyslog corriendo en syslog01" "docker exec syslog01 pgrep rsyslogd"
test_check "MySQL corriendo en mysql01" "docker exec mysql01 pgrep mysqld"

# ─── 5. CONECTIVIDAD DE RED ──────────────────────────────────────────────────
seccion "5. Conectividad de red"
test_check "DNS resuelve web01.laboratorio.local" \
    "docker exec client01 nslookup web01.laboratorio.local 192.168.100.20 | grep -q '172.21.0.20'"
test_check "DNS resuelve ssh01.laboratorio.local" \
    "docker exec client01 nslookup ssh01.laboratorio.local 192.168.100.20 | grep -q '192.168.100.10'"
test_check "DNS resuelve nombres externos (google.com)" \
    "docker exec client01 nslookup google.com 192.168.100.20 | grep -q 'Address'"
test_check "web01 responde HTTPS desde host" \
    "curl -sk -o /dev/null -w '%{http_code}' --max-time 5 https://172.21.0.20 | grep -q 200"
test_check "proxy01 responde HTTPS (código 200)" \
    "docker exec client01 curl -sk -o /dev/null -w '%{http_code}' --max-time 5 https://172.21.0.10 | grep -q 200"
test_check "proxy01 /info responde (página propia del proxy)" \
    "curl -skL -o /dev/null -w '%{http_code}' --max-time 5 https://172.21.0.10/info | grep -q 200"
test_check "squid01 proxy funciona hacia internet" \
    "docker exec client01 curl -s --max-time 10 -x http://192.168.100.40:3128 -o /dev/null -w '%{http_code}' http://example.com | grep -q 200"
test_check "LAN puede salir a internet via NAT" \
    "docker exec client01 curl -s --max-time 10 -o /dev/null -w '%{http_code}' http://1.1.1.1 | grep -qE '200|301|302'"

# ─── 6. SSH Y SCP ────────────────────────────────────────────────────────────
seccion "6. SSH y SCP"
test_check "SSH acepta conexiones en ssh01 puerto 22" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/192.168.100.10/22\"'"
test_check "SSH login con usuario ubuntu" \
    "docker exec client01 bash -c \"sshpass -p 'TFG2026lab' ssh ubuntu@192.168.100.10 'echo OK' 2>/dev/null\" | grep -q OK"
test_check "SCP transfiere fichero a ssh01" \
    "docker exec client01 bash -c \"echo test > /tmp/hc_test.txt && sshpass -p 'TFG2026lab' scp /tmp/hc_test.txt ubuntu@192.168.100.10:/tmp/ 2>/dev/null\" && docker exec ssh01 test -f /tmp/hc_test.txt"
test_check "SFTP habilitado en ssh01 (para SCP)" \
    "docker exec ssh01 grep -q 'sftp' /etc/ssh/sshd_config"

# ─── 7. DHCP ─────────────────────────────────────────────────────────────────
seccion "7. DHCP"
test_check "DHCP asigna IP a client01" \
    "docker exec client01 udhcpc -i eth0 -q 2>&1 | grep -q 'obtained'"
test_check "Lease DHCP registrado en dhcpd.leases" \
    "docker exec dhcp01 grep -q 'binding state active' /var/lib/dhcp/dhcpd.leases"

# ─── 8. LOGS CENTRALIZADOS ───────────────────────────────────────────────────
seccion "8. Sistema de logs centralizados"
for f in ssh dns dhcp web proxy squid; do
    test_check "Fichero $f.log existe en syslog01" \
        "docker exec syslog01 test -s /var/log/laboratorio/$f.log"
done

# ─── 9. MYSQL ────────────────────────────────────────────────────────────────
seccion "9. Base de datos MySQL"
test_check "BBDD Syslog existe" \
    "docker exec mysql01 bash -c 'mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" -e \"SHOW DATABASES;\" 2>/dev/null | grep -q Syslog'"
test_check "Tabla SystemEvents existe" \
    "docker exec mysql01 bash -c 'mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" Syslog -e \"SHOW TABLES;\" 2>/dev/null | grep -q SystemEvents'"
test_check "Usuario rsyslog puede conectar" \
    "docker exec mysql01 mysql -u rsyslog -pRsyslog_TFG_2026! -e 'SELECT 1;' 2>/dev/null"
test_check "phpMyAdmin responde HTTP (código 200)" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:8080 | grep -q 200"

TOTAL_LOGS=$(docker exec mysql01 bash -c \
    'mysql -u root -p"$MYSQL_ROOT_PASSWORD" Syslog -N -e "SELECT COUNT(*) FROM SystemEvents;" 2>/dev/null' \
    | tr -d ' ')
if [[ "$TOTAL_LOGS" =~ ^[0-9]+$ ]] && [[ "$TOTAL_LOGS" -gt 0 ]]; then
    echo -e "  ${VERDE}✓${RESET} Hay $TOTAL_LOGS registros en SystemEvents"
    ((OK++))
else
    echo -e "  ${ROJO}✗${RESET} La tabla SystemEvents está vacía"
    ((FALLOS++))
fi

# ─── 10. PANEL FLASK ─────────────────────────────────────────────────────────
seccion "10. Panel de control Flask"
test_check "panel01 responde HTTP (código 200)" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:5000 | grep -q 200"
test_check "Página demo responde (código 200)" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:5000/demo | grep -q 200"
test_check "API status devuelve datos" \
    "curl -s --max-time 5 http://localhost:5000/api/status | grep -q 'fw01'"
test_check "API logs SSH devuelve datos" \
    "curl -s --max-time 5 http://localhost:5000/api/logs/ssh | grep -q 'log'"
test_check "API MySQL devuelve datos" \
    "curl -s --max-time 5 http://localhost:5000/api/mysql/total_por_host | grep -q 'Host'"
test_check "API DHCP devuelve leases" \
    "curl -s --max-time 5 http://localhost:5000/api/dhcp/leases | grep -q '192.168'"
test_check "API firewall devuelve resultados" \
    "curl -s --max-time 30 http://localhost:5000/api/firewall | grep -q 'reglas'"

# ─── 11. SEGMENTACIÓN DE RED ─────────────────────────────────────────────────
seccion "11. Segmentación de red (firewall)"
test_check "DMZ no puede acceder a LAN (bloqueado)" \
    "! docker exec proxy01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/192.168.100.10/22\"' 2>/dev/null"
test_check "LAN no puede acceder a web01 directo (bloqueado)" \
    "! docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/172.21.0.20/443\"' 2>/dev/null"
test_check "LAN puede acceder a proxy01 (permitido)" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/172.21.0.10/443\"' 2>/dev/null"

# ─── 12. END-TO-END ──────────────────────────────────────────────────────────
seccion "12. Prueba end-to-end: log completo ssh01 → syslog01 → MySQL"
MARCA="healthcheck_$(date +%s)"
docker exec ssh01 logger -t healthcheck "$MARCA desde ssh01" 2>/dev/null
sleep 3
test_check "Log aparece en fichero ssh.log" \
    "docker exec syslog01 grep -q '$MARCA' /var/log/laboratorio/ssh.log"
test_check "Log aparece en MySQL SystemEvents" \
    "docker exec mysql01 bash -c 'mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" Syslog -N -e \"SELECT Message FROM SystemEvents WHERE Message LIKE \\\"%$MARCA%\\\";\" 2>/dev/null' | grep -q '$MARCA'"

# ─── RESUMEN ─────────────────────────────────────────────────────────────────
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
