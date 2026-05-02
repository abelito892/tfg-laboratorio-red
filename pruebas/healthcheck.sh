#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Healthcheck del Laboratorio NetCorp — TFG ASIR
# IES Francisco de Quevedo | Abel Baños García | 2026
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

# ─── CALENTAMIENTO ────────────────────────────────────────────────────────────
echo -e "${AZUL}Generando actividad en todos los servicios...${RESET}"
docker exec client01 udhcpc -i eth0 -q 2>/dev/null || true
# SSH — login real para que sshd escriba en syslog
docker exec client01 bash -c \
    "sshpass -p 'TFG2026lab' ssh -o StrictHostKeyChecking=no ubuntu@192.168.100.10 'uptime' 2>/dev/null" || true
# Web + Squid — peticion HTTPS via squid para poblar web.log y squid.log
docker exec client01 curl -sk --proxy http://192.168.100.40:3128 \
    https://intranet.netcorp.local/api/health -o /dev/null 2>/dev/null || true
docker exec client01 curl -s --proxy http://192.168.100.40:3128 \
    http://example.com -o /dev/null 2>/dev/null || true
# DNS
docker exec client01 nslookup intranet.netcorp.local 192.168.100.20 > /dev/null 2>&1 || true
sleep 8
echo -e "${AZUL}Iniciando verificaciones...${RESET}"

# ─── 1. CONTENEDORES ACTIVOS ──────────────────────────────────────────────────
seccion "1. Contenedores activos"
for c in fw01 ssh01 dns01 dhcp01 web01 proxy01 squid01 client01 syslog01 mysql01 dbadmin01 panel01; do
    test_check "$c corriendo" \
        "docker ps --filter name=^/${c}$ --filter status=running --format '{{.Names}}' | grep -q ${c}"
done

# ─── 2. REDES DOCKER ──────────────────────────────────────────────────────────
seccion "2. Redes Docker"
for r in wan_net dmz_net lan_net mgmt_net db_net; do
    test_check "$r existe" "docker network inspect $r"
done

# ─── 3. FIREWALL ──────────────────────────────────────────────────────────────
seccion "3. Firewall nftables (fw01)"
test_check "Reglas nftables cargadas"  "docker exec fw01 nft list ruleset | grep -q 'chain forward'"
test_check "NAT masquerade activo"     "docker exec fw01 nft list ruleset | grep -q 'masquerade'"
test_check "Politica forward DROP"     "docker exec fw01 nft list ruleset | grep -q 'policy drop'"

# ─── 4. SERVICIOS PRINCIPALES ─────────────────────────────────────────────────
seccion "4. Servicios principales"
test_check "OpenSSH corriendo en ssh01"   "docker exec ssh01 pgrep sshd"
test_check "BIND9 corriendo en dns01"     "docker exec dns01 pgrep named"
test_check "DHCP corriendo en dhcp01"     "docker exec dhcp01 pgrep dhcpd"
test_check "Nginx corriendo en web01"     "docker exec web01 pgrep nginx"
test_check "FastAPI corriendo en web01"   "docker exec web01 pgrep -f uvicorn"
test_check "Nginx corriendo en proxy01"   "docker exec proxy01 pgrep nginx"
test_check "Squid corriendo en squid01"   "docker exec squid01 pgrep squid"
test_check "rsyslog corriendo en syslog01" "docker exec syslog01 pgrep rsyslogd"
test_check "MySQL corriendo en mysql01"   "docker exec mysql01 pgrep mysqld"

# ─── 5. CONECTIVIDAD DE RED ───────────────────────────────────────────────────
seccion "5. Conectividad de red"
test_check "DNS resuelve web01.laboratorio.local" \
    "docker exec client01 nslookup web01.laboratorio.local 192.168.100.20 | grep -q '172.21.0.20'"
test_check "DNS resuelve ssh01.laboratorio.local" \
    "docker exec client01 nslookup ssh01.laboratorio.local 192.168.100.20 | grep -q '192.168.100.10'"
test_check "DNS resuelve intranet.netcorp.local" \
    "docker exec client01 nslookup intranet.netcorp.local 192.168.100.20 | grep -q '172.21.0.10'"
test_check "DNS resuelve nombres externos (1.1.1.1)" \
    "docker exec client01 nslookup google.com 192.168.100.20 | grep -q 'Address'"
test_check "proxy01 responde HTTPS (cliente LAN)" \
    "docker exec client01 curl -sk -o /dev/null -w '%{http_code}' --max-time 8 https://172.21.0.10 | grep -q 200"
test_check "proxy01 /info responde (pagina propia)" \
    "curl -skL -o /dev/null -w '%{http_code}' --max-time 8 https://172.21.0.10/info/ | grep -q 200"
test_check "squid01 proxy HTTP hacia internet" \
    "docker exec client01 curl -s --max-time 12 -x http://192.168.100.40:3128 -o /dev/null -w '%{http_code}' http://example.com | grep -q 200"
test_check "intranet.netcorp.local accesible via squid (HTTPS CONNECT)" \
    "docker exec client01 curl -sk --max-time 12 --proxy http://192.168.100.40:3128 -o /dev/null -w '%{http_code}' https://intranet.netcorp.local/api/health | grep -q 200"

# ─── 6. SSH Y SCP ─────────────────────────────────────────────────────────────
seccion "6. SSH y SCP"
test_check "Puerto 22 abierto en ssh01" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/192.168.100.10/22\"'"
test_check "Login SSH con usuario ubuntu" \
    "docker exec client01 bash -c \"sshpass -p 'TFG2026lab' ssh -o StrictHostKeyChecking=no ubuntu@192.168.100.10 'echo OK' 2>/dev/null\" | grep -q OK"
test_check "SCP transfiere fichero a ssh01" \
    "docker exec client01 bash -c \"echo prueba > /tmp/hc_\$\$.txt && sshpass -p 'TFG2026lab' scp -o StrictHostKeyChecking=no /tmp/hc_\$\$.txt ubuntu@192.168.100.10:/tmp/ 2>/dev/null\""
test_check "SFTP habilitado en sshd_config" \
    "docker exec ssh01 grep -q -i 'sftp\|Subsystem' /etc/ssh/sshd_config"

# ─── 7. DHCP ──────────────────────────────────────────────────────────────────
seccion "7. DHCP"
test_check "DHCP asigna IP a client01" \
    "docker exec client01 udhcpc -i eth0 -q 2>&1 | grep -q 'obtained'"
test_check "Lease activo en dhcpd.leases" \
    "docker exec dhcp01 grep -q 'binding state active' /var/lib/dhcp/dhcpd.leases"

# ─── 8. LOGS CENTRALIZADOS ────────────────────────────────────────────────────
seccion "8. Logs centralizados (syslog01)"
for f in ssh dns dhcp web proxy squid; do
    test_check "Fichero /var/log/laboratorio/${f}.log existe y tiene contenido" \
        "docker exec syslog01 test -s /var/log/laboratorio/${f}.log"
done
test_check "all.log existe y tiene contenido" \
    "docker exec syslog01 test -s /var/log/laboratorio/all.log"

# ─── 9. BASE DE DATOS NETCORP ─────────────────────────────────────────────────
seccion "9. Base de datos MySQL (NetCorp)"
test_check "BD NetCorp existe" \
    "docker exec mysql01 mysql -uroot -pRoot_TFG_2026! -e 'SHOW DATABASES;' 2>/dev/null | grep -q NetCorp"
test_check "Tabla empleados tiene datos" \
    "docker exec mysql01 mysql -uroot -pRoot_TFG_2026! NetCorp -N -e 'SELECT COUNT(*) FROM empleados;' 2>/dev/null | grep -qE '^[1-9]'"
test_check "Tabla departamentos tiene datos" \
    "docker exec mysql01 mysql -uroot -pRoot_TFG_2026! NetCorp -N -e 'SELECT COUNT(*) FROM departamentos;' 2>/dev/null | grep -qE '^[1-9]'"
test_check "Tabla accesos existe" \
    "docker exec mysql01 mysql -uroot -pRoot_TFG_2026! NetCorp -e 'SELECT 1 FROM accesos LIMIT 1;' 2>/dev/null"
test_check "Usuario netcorp puede consultar empleados" \
    "docker exec mysql01 mysql -unetcorp -pNetCorp_TFG_2026! NetCorp -e 'SELECT COUNT(*) FROM empleados;' 2>/dev/null"
test_check "FastAPI /api/health devuelve 200" \
    "docker exec web01 curl -sk -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/health | grep -q 200"
test_check "phpMyAdmin responde (codigo 200)" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:8080 | grep -q 200"

# ─── 10. PANEL DE CONTROL ─────────────────────────────────────────────────────
seccion "10. Panel de control Flask (panel01)"
test_check "Panel responde en localhost:5000" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:5000 | grep -q 200"
test_check "Pagina /demo responde" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:5000/demo | grep -q 200"
test_check "API /api/status devuelve contenedores" \
    "curl -s --max-time 8 http://localhost:5000/api/status | grep -q 'fw01'"
test_check "API /api/logs/ssh devuelve contenido" \
    "curl -s --max-time 8 http://localhost:5000/api/logs/ssh | grep -q 'log'"
test_check "API /api/dhcp/leases devuelve datos" \
    "curl -s --max-time 8 http://localhost:5000/api/dhcp/leases | grep -qE '192\.168|lease'"
test_check "API /api/netcorp/empleados devuelve tabla" \
    "curl -s --max-time 8 http://localhost:5000/api/netcorp/empleados | grep -q 'NetCorp\|netcorp'"
test_check "API /api/firewall devuelve resultados" \
    "curl -s --max-time 35 http://localhost:5000/api/firewall | grep -qiE 'firewall|Permitido|Bloqueado'"

# ─── 11. SEGMENTACIÓN DE RED ──────────────────────────────────────────────────
seccion "11. Segmentacion de red (politica de firewall)"
test_check "DMZ → LAN bloqueado (proxy01 no alcanza ssh01:22)" \
    "! docker exec proxy01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/192.168.100.10/22\"' 2>/dev/null"
test_check "LAN → web01 directo BLOQUEADO (solo via proxy01)" \
    "! docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/172.21.0.20/443\"' 2>/dev/null"
test_check "LAN → proxy01 HTTPS PERMITIDO" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/172.21.0.10/443\"' 2>/dev/null"
test_check "LAN → ssh01:22 PERMITIDO" \
    "docker exec client01 bash -c 'timeout 3 bash -c \"cat < /dev/null > /dev/tcp/192.168.100.10/22\"' 2>/dev/null"

# ─── 12. END-TO-END ───────────────────────────────────────────────────────────
seccion "12. Prueba end-to-end: client01 → squid01 → proxy01 → web01 → MySQL"
docker exec client01 curl -sk --max-time 12 \
    --proxy http://192.168.100.40:3128 \
    https://intranet.netcorp.local/api/empleados > /dev/null 2>&1 || true
sleep 3

test_check "intranet.netcorp.local accesible via squid" \
    "docker exec client01 curl -sk -o /dev/null -w '%{http_code}' --max-time 12 \
     --proxy http://192.168.100.40:3128 https://intranet.netcorp.local/api/health | grep -q 200"

ACCESOS=$(docker exec mysql01 mysql -uroot -pRoot_TFG_2026! NetCorp -N \
    -e "SELECT COUNT(*) FROM accesos WHERE servicio='intranet';" 2>/dev/null | tr -d ' \r\n')
if [[ "$ACCESOS" =~ ^[0-9]+$ ]] && [[ "$ACCESOS" -gt 0 ]]; then
    echo -e "  ${VERDE}✓${RESET} MySQL registra accesos a la intranet ($ACCESOS total)"
    ((OK++))
else
    echo -e "  ${ROJO}✗${RESET} No se encontraron accesos registrados en MySQL"
    ((FALLOS++))
fi

test_check "Trafico visible en syslog01 all.log" \
    "docker exec syslog01 test -s /var/log/laboratorio/all.log"

# ─── RESUMEN ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${AZUL}═══════════════════════════════════════════════════════════${RESET}"
TOTAL=$((OK + FALLOS))
PORCENTAJE=$((OK * 100 / TOTAL))
if [[ $FALLOS -eq 0 ]]; then
    echo -e "${VERDE}  ✓ Todos los tests pasaron: $OK/$TOTAL (100%)${RESET}"
    echo -e "${VERDE}  Laboratorio NetCorp funcionando correctamente.${RESET}"
elif [[ $PORCENTAJE -ge 90 ]]; then
    echo -e "${AMARILLO}  Resultado: $OK/$TOTAL tests OK ($PORCENTAJE%) — $FALLOS fallos menores${RESET}"
else
    echo -e "${ROJO}  Resultado: $OK/$TOTAL tests OK ($PORCENTAJE%) — $FALLOS fallos${RESET}"
fi
echo -e "${AZUL}═══════════════════════════════════════════════════════════${RESET}"
echo ""
