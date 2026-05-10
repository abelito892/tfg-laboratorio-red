#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# setup.sh — Preparación del entorno para el laboratorio TFG ASIR
# Uso: chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e

VERDE='\033[0;32m'
ROJO='\033[0;31m'
AZUL='\033[0;34m'
AMARILLO='\033[1;33m'
RESET='\033[0m'
ERRORES=0

function info()   { echo -e "${AZUL}[INFO]${RESET} $1"; }
function ok()     { echo -e "${VERDE}[OK]${RESET} $1"; }
function warn()   { echo -e "${AMARILLO}[WARN]${RESET} $1"; }
function error()  { echo -e "${ROJO}[ERROR]${RESET} $1"; ERRORES=$((ERRORES+1)); }
function fatal()  { echo -e "${ROJO}[FATAL]${RESET} $1"; exit 1; }
function titulo() {
    echo ""
    echo -e "${AZUL}═══════════════════════════════════════════${RESET}"
    echo -e "${AZUL}  $1${RESET}"
    echo -e "${AZUL}═══════════════════════════════════════════${RESET}"
}

# ─── VERIFICAR QUE NO SOMOS ROOT ─────────────────────────────────────────────
if [ "$EUID" -eq 0 ]; then
    fatal "No ejecutes este script como root. Usa tu usuario normal con sudo."
fi

echo -e "${AZUL}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   Laboratorio de Red TFG ASIR                         ║"
echo "║   Script de preparación del entorno                   ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# ─── 1. SISTEMA OPERATIVO ────────────────────────────────────────────────────
titulo "1. Verificando sistema operativo"
if grep -q "Ubuntu 24" /etc/os-release 2>/dev/null; then
    ok "Ubuntu 24.04 detectado"
else
    warn "Este script está optimizado para Ubuntu 24.04"
    warn "Continuando bajo tu responsabilidad..."
fi

# ─── 2. ESPACIO EN DISCO ─────────────────────────────────────────────────────
titulo "2. Verificando espacio en disco"
ESPACIO=$(df / --output=avail | tail -1)
ESPACIO_GB=$(echo "scale=1; $ESPACIO/1024/1024" | bc)
if [ "$ESPACIO" -lt 10485760 ]; then
    warn "Espacio libre: ${ESPACIO_GB}GB — se recomiendan al menos 10GB"
else
    ok "Espacio libre: ${ESPACIO_GB}GB"
fi

# ─── 3. MÓDULOS DE KERNEL ────────────────────────────────────────────────────
titulo "3. Verificando módulos de kernel"
for modulo in br_netfilter ip_tables iptable_filter; do
    if lsmod | grep -q "^$modulo" || modprobe $modulo 2>/dev/null; then
        ok "Módulo $modulo disponible"
    else
        warn "Módulo $modulo no disponible — puede afectar al firewall"
    fi
done

# ─── 4. PUERTOS LIBRES ───────────────────────────────────────────────────────
titulo "4. Verificando puertos necesarios"
for puerto in 5000 8080; do
    if ss -tlnp | grep -q ":$puerto "; then
        warn "Puerto $puerto ocupado — el laboratorio ya está corriendo"
    else
        ok "Puerto $puerto libre"
    fi
done

# ─── 5. INSTALAR DEPENDENCIAS BASE ───────────────────────────────────────────
titulo "5. Actualizando repositorios e instalando dependencias"
sudo apt-get update -qq
sudo apt-get install -y curl wget git bc nftables 2>/dev/null || true
ok "Dependencias base instaladas"

# ─── 6. INSTALAR DOCKER ──────────────────────────────────────────────────────
titulo "6. Instalando Docker"
if command -v docker &>/dev/null; then
    ok "Docker ya instalado: $(docker --version)"
else
    info "Instalando Docker..."
    sudo apt-get install -y docker.io
    sudo systemctl enable docker
    sudo systemctl start docker
    ok "Docker instalado: $(docker --version)"
fi

# Verificar que Docker funciona
if ! docker info &>/dev/null; then
    sudo systemctl start docker
    sleep 3
fi
if docker info &>/dev/null; then
    ok "Docker daemon funcionando"
else
    fatal "Docker no arranca. Revisa: sudo systemctl status docker"
fi

# ─── 7. GRUPO DOCKER ─────────────────────────────────────────────────────────
titulo "7. Configurando grupo docker"
if groups "$USER" | grep -q docker; then
    ok "Usuario $USER ya está en el grupo docker"
else
    sudo usermod -aG docker "$USER"
    ok "Usuario $USER añadido al grupo docker"
    warn "Ejecuta: newgrp docker (o cierra sesión y vuelve a entrar)"
fi

# ─── 8. INSTALAR ANSIBLE ─────────────────────────────────────────────────────
titulo "8. Instalando Ansible"
if command -v ansible &>/dev/null; then
    ok "Ansible ya instalado: $(ansible --version | head -1)"
else
    info "Instalando Ansible..."
    sudo apt-get install -y ansible
    ok "Ansible instalado"
fi

# ─── 9. COLECCIÓN COMMUNITY.DOCKER ───────────────────────────────────────────
titulo "9. Instalando colección community.docker"
if ansible-galaxy collection list 2>/dev/null | grep -q "community.docker"; then
    ok "community.docker ya instalada"
else
    info "Instalando community.docker..."
    ansible-galaxy collection install community.docker
    ok "community.docker instalada"
fi

# ─── 10. NETADDR ─────────────────────────────────────────────────────────────
titulo "10. Instalando netaddr (Python)"
if python3 -c "import netaddr" 2>/dev/null; then
    ok "netaddr ya instalado"
else
    pip3 install netaddr --break-system-packages 2>/dev/null || \
    sudo apt-get install -y python3-netaddr
    ok "netaddr instalado"
fi

# ─── 11. SUDOERS PARA NFT ────────────────────────────────────────────────────
titulo "11. Configurando sudoers para nft"
SUDOERS_FILE="/etc/sudoers.d/tfg-ansible-nft"
if [ -f "$SUDOERS_FILE" ]; then
    ok "Sudoers para nft ya configurado"
else
    echo "$USER ALL=(ALL) NOPASSWD: /usr/sbin/nft" | sudo tee "$SUDOERS_FILE" > /dev/null
    sudo chmod 440 "$SUDOERS_FILE"
    ok "Sudoers configurado para nft"
fi

# ─── 12. SYSCTL IP FORWARDING ────────────────────────────────────────────────
titulo "12. Habilitando IP forwarding"
if sysctl net.ipv4.ip_forward | grep -q "= 1"; then
    ok "IP forwarding ya habilitado"
else
    sudo sysctl -w net.ipv4.ip_forward=1
    echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf > /dev/null
    ok "IP forwarding habilitado"
fi

# ─── 13. DETECTAR INTERFAZ DE RED ────────────────────────────────────────────
titulo "13. Detectando interfaz de red"
INTERFAZ=$(ip route | grep default | awk '{print $5}' | head -1)
if [ -z "$INTERFAZ" ]; then
    warn "No se pudo detectar la interfaz automáticamente"
    warn "Edita group_vars/all/main.yml y actualiza host_interfaz_red manualmente"
else
    ok "Interfaz detectada: $INTERFAZ"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    VARS_FILE="$SCRIPT_DIR/group_vars/all/main.yml"
    if [ -f "$VARS_FILE" ]; then
        sed -i "s/host_interfaz_red:.*/host_interfaz_red: \"$INTERFAZ\"/" "$VARS_FILE"
        ok "group_vars/all/main.yml actualizado: host_interfaz_red = $INTERFAZ"
    fi
fi

# ─── 14. SERVICIO SYSTEMD POSTDEPLOY ─────────────────────────────────────────
titulo "14. Configurando servicio systemd tfg-postdeploy"

sudo tee /usr/local/bin/tfg-postdeploy.sh > /dev/null << 'POSTDEPLOY'
#!/bin/bash
# Elimina reglas raw de Docker que bloquean tráfico entre bridges LAN y DMZ
sleep 10
LAN_ID=$(docker network inspect lan_net --format '{{.Id}}' 2>/dev/null | cut -c1-12)
DMZ_ID=$(docker network inspect dmz_net --format '{{.Id}}' 2>/dev/null | cut -c1-12)
if [ -z "$LAN_ID" ] || [ -z "$DMZ_ID" ]; then
    sleep 15
    LAN_ID=$(docker network inspect lan_net --format '{{.Id}}' 2>/dev/null | cut -c1-12)
    DMZ_ID=$(docker network inspect dmz_net --format '{{.Id}}' 2>/dev/null | cut -c1-12)
fi
for handle in $(nft -a list chain ip raw PREROUTING 2>/dev/null | \
    grep "br-${DMZ_ID}.*drop" | awk '{print $NF}'); do
    nft delete rule ip raw PREROUTING handle $handle 2>/dev/null
done
for handle in $(nft -a list chain ip raw PREROUTING 2>/dev/null | \
    grep "br-${LAN_ID}.*drop" | awk '{print $NF}'); do
    nft delete rule ip raw PREROUTING handle $handle 2>/dev/null
done
echo "TFG postdeploy completado"
POSTDEPLOY

sudo chmod +x /usr/local/bin/tfg-postdeploy.sh

sudo tee /etc/systemd/system/tfg-postdeploy.service > /dev/null << 'SERVICE'
[Unit]
Description=TFG Laboratorio - Postdeploy Docker rules
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/tfg-postdeploy.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable tfg-postdeploy.service
ok "Servicio tfg-postdeploy instalado y habilitado"

# ─── RESUMEN FINAL ────────────────────────────────────────────────────────────
echo ""
echo -e "${AZUL}"
echo "╔═══════════════════════════════════════════════════════╗"
if [ "$ERRORES" -eq 0 ]; then
echo "║   ✅ Entorno preparado correctamente                   ║"
else
echo "║   ⚠️  Entorno preparado con $ERRORES advertencia(s)          ║"
fi
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo -e "${VERDE}Pasos siguientes:${RESET}"
echo ""
echo "  1. Si acabas de ser añadido al grupo docker:"
echo -e "     ${AMARILLO}newgrp docker${RESET}"
echo ""
echo "  2. Desplegar el laboratorio:"
echo -e "     ${AMARILLO}ansible-playbook site.yml --ask-become-pass${RESET}"
echo ""
echo "  3. Verificar que todo funciona:"
echo -e "     ${AMARILLO}./pruebas/healthcheck.sh${RESET}"
echo ""
echo "  4. Pruebas de firewall:"
echo -e "     ${AMARILLO}./pruebas/test_firewall.sh${RESET}"
echo ""
echo -e "  5. Panel de control:  ${AMARILLO}http://localhost:5000${RESET}"
echo -e "  6. Demo interactiva:  ${AMARILLO}http://localhost:5000/demo${RESET}"
echo -e "  7. phpMyAdmin:        ${AMARILLO}http://localhost:8080${RESET}"
echo ""
echo -e "${AZUL}Credenciales MySQL:${RESET}"
echo "  Root:    Root_TFG_2026!"
echo "  rsyslog: Rsyslog_TFG_2026!"
echo ""
echo -e "${AZUL}Usuario SSH (demo):${RESET}"
echo "  Usuario: ubuntu / Password: TFG2026lab"
echo ""
