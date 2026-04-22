# Laboratorio de Red Virtualizado — TFG ASIR 2026

Laboratorio de red completamente virtualizado sobre un único host Ubuntu 24.04, usando **Docker** como plataforma de contenedores y **Ansible** como herramienta de automatización y despliegue.

## Arquitectura
┌─────────────────────────────────────────────────────────────┐
│                        HOST Ubuntu 24.04                     │
│                                                             │
│  ┌──────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │   WAN    │   │       DMZ       │   │       LAN       │  │
│  │172.20.0.0│   │  172.21.0.0/24  │   │ 192.168.100.0/24│  │
│  │   /24    │   │                 │   │                 │  │
│  │          │   │ proxy01 web01   │   │ ssh01  dns01    │  │
│  └────┬─────┘   └────────┬────────┘   │ dhcp01 squid01  │  │
│       │                  │            │ client01        │  │
│       └──────── fw01 ────┘            └─────────────────┘  │
│                  │                                          │
│  ┌───────────────┴─────────────────────────────────────┐   │
│  │              MGMT 172.22.0.0/24                      │   │
│  │     syslog01   mysql01   dbadmin01   panel01         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

## Contenedores desplegados

| Contenedor | IP | Servicio | Zona |
|---|---|---|---|
| fw01 | 172.20.0.2 / 192.168.100.2 / 172.21.0.2 | Firewall nftables | WAN/LAN/DMZ |
| proxy01 | 172.21.0.10 | Nginx proxy inverso | DMZ |
| web01 | 172.21.0.20 | Nginx + SSL | DMZ |
| ssh01 | 192.168.100.10 | OpenSSH | LAN |
| dns01 | 192.168.100.20 | BIND9 | LAN |
| dhcp01 | 192.168.100.30 | ISC DHCP | LAN |
| squid01 | 192.168.100.40 | Squid proxy | LAN |
| client01 | 192.168.100.50 | Cliente de pruebas | LAN |
| syslog01 | 172.22.0.10 | rsyslog centralizado | MGMT |
| mysql01 | 172.23.0.10 | MySQL 8.0 | DB |
| dbadmin01 | host:8080 | phpMyAdmin | MGMT |
| panel01 | host:5000 | Panel Flask+HTMX | MGMT |

## Requisitos del sistema

- **Sistema operativo:** Ubuntu 24.04 LTS
- **RAM:** mínimo 6 GB (recomendado 8 GB)
- **Disco:** mínimo 10 GB libres
- **CPU:** 2 cores mínimo
- **Conexión a internet** (para descargar imágenes Docker)

## Instalación desde cero

### 1. Clonar el repositorio

```bash
git clone https://github.com/abelito892/tfg-laboratorio-red
cd tfg-laboratorio-red-main
```

### 2. Preparar el entorno

```bash
chmod +x setup.sh
./setup.sh
```

El script instala y configura automáticamente:
- Docker y grupo docker
- Ansible y colección community.docker
- netaddr (Python)
- Sudoers para nft
- IP forwarding del kernel
- Servicio systemd tfg-postdeploy
- Detección automática de interfaz de red

> ⚠️ Si el script añade tu usuario al grupo docker por primera vez, ejecuta `newgrp docker` antes de continuar.

### 3. Desplegar el laboratorio

```bash
ansible-playbook site.yml --ask-become-pass
```

El despliegue completo tarda aproximadamente **3-5 minutos** la primera vez (descarga de imágenes Docker).

### 4. Verificar el despliegue

```bash
./pruebas/healthcheck.sh
```

Resultado esperado: `✓ Todos los tests pasaron: 49/49 (100%)`

### 5. Verificar el firewall

```bash
./pruebas/test_firewall.sh
```

Resultado esperado: `✓ Firewall funcionando correctamente: 12/12 pruebas OK`

## Acceso a los servicios

| Servicio | URL | Descripción |
|---|---|---|
| Panel de control | http://localhost:5000 | Dashboard principal |
| Demo interactiva | http://localhost:5000/demo | Escenarios de demostración |
| phpMyAdmin | http://localhost:8080 | Gestión de base de datos |
| Web01 via proxy | https://172.21.0.10 | Acceso web via proxy inverso |
| Web01 directo | https://172.21.0.20 | Servidor web directo |
| Proxy info | https://172.21.0.10/info | Información del proxy |

> Los certificados SSL son autofirmados — el navegador mostrará advertencia de seguridad. Acepta el riesgo para continuar.

## Credenciales

| Servicio | Usuario | Contraseña |
|---|---|---|
| MySQL root | root | Root_TFG_2026! |
| MySQL rsyslog | rsyslog | Rsyslog_TFG_2026! |
| phpMyAdmin | root | Root_TFG_2026! |
| SSH demo (ubuntu) | ubuntu | TFG2026lab |

## Gestión del laboratorio

### Destruir y redesplegar desde cero

```bash
ansible-playbook teardown.yml
ansible-playbook site.yml --ask-become-pass
```

### Redesplegar un servicio individual

```bash
ansible-playbook site.yml --ask-become-pass --tags <servicio>
```

Servicios disponibles: `ssh`, `dns`, `dhcp`, `web`, `proxy`, `squid`, `syslog`, `mysql`, `firewall`, `postdeploy`

### Ver logs de un servicio

```bash
docker exec syslog01 tail -f /var/log/laboratorio/ssh.log
docker exec syslog01 tail -f /var/log/laboratorio/web.log
# etc.
```

## Estructura del proyecto
tfg-laboratorio-red-main/
├── README.md
├── setup.sh                    # Script de preparación del entorno
├── site.yml                    # Playbook principal de despliegue
├── teardown.yml                # Playbook de destrucción
├── ansible.cfg
├── group_vars/
│   └── all/
│       └── main.yml            # Variables globales
├── inventario/
├── roles/
│   ├── firewall/               # fw01 — nftables
│   ├── ssh/                    # ssh01 — OpenSSH
│   ├── dns/                    # dns01 — BIND9
│   ├── dhcp/                   # dhcp01 — ISC DHCP
│   ├── web/                    # web01 — Nginx+SSL
│   ├── proxy/                  # proxy01 — Nginx proxy inverso
│   ├── squid/                  # squid01 — Squid
│   ├── client/                 # client01 — cliente de pruebas
│   ├── syslog/                 # syslog01 — rsyslog central
│   ├── mysql/                  # mysql01 — MySQL 8.0
│   ├── dbadmin/                # dbadmin01 — phpMyAdmin
│   ├── panel/                  # panel01 — Flask+HTMX
│   ├── redes/                  # Redes Docker
│   └── postdeploy/             # Limpieza reglas Docker
└── pruebas/
├── healthcheck.sh          # 49 tests de verificación
└── test_firewall.sh        # 12 tests de firewall

## Limitaciones conocidas

- **Bypass de fw01:** Docker crea bridges que permiten al host acceder directamente a todas las redes, saltándose fw01. Esto es una limitación arquitectónica de Docker documentada en la memoria del TFG.
- **Certificados SSL autofirmados:** Los certificados son autofirmados para entorno de laboratorio. En producción se usarían certificados válidos.
- **Contraseñas en texto plano:** Las credenciales están en `group_vars/all/main.yml`. En producción se usaría Ansible Vault.

## Autor

Abel — TFG ASIR 2026  
Administración de Sistemas Informáticos en Red
