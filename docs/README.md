# Laboratorio de Red Virtualizado — TFG ASIR 2026

Laboratorio de red completamente virtualizado sobre un único host Ubuntu 24.04, usando **Docker** como plataforma de contenedores y **Ansible** como herramienta de automatización y despliegue.

**Autores:** Abel Baños · Daniel Montero · Amina Sefiani  
**Ciclo:** ASIR — Administración de Sistemas Informáticos en Red · 2026

---

## Arquitectura de red

![Topología de red del laboratorio](docs/topologia.svg)

La infraestructura está segmentada en cuatro zonas de red independientes:

| Zona | Subred | Función |
|---|---|---|
| WAN | 172.20.0.0/24 | Simula la red exterior / internet |
| DMZ | 172.21.0.0/24 | Servicios expuestos al exterior |
| LAN | 192.168.100.0/24 | Servicios internos protegidos |
| MGMT | 172.22.0.0/24 | Gestión, logs y monitorización |
| DB | 172.23.0.0/24 | Base de datos dedicada |

El firewall **fw01** actúa como elemento central de enrutamiento entre zonas, aplicando reglas nftables que controlan el tráfico permitido y bloqueado.

---

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

---

## Requisitos del sistema

- **Sistema operativo:** Ubuntu 24.04 LTS
- **RAM:** mínimo 6 GB (recomendado 8 GB)
- **Disco:** mínimo 10 GB libres
- **CPU:** 2 cores mínimo
- **Conexión a internet** para descargar imágenes Docker la primera vez

---

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
- Sudoers para nft sin contraseña
- IP forwarding del kernel
- Servicio systemd tfg-postdeploy (se ejecuta en cada arranque)
- Detección automática de la interfaz de red

> ⚠️ Si el script añade tu usuario al grupo docker por primera vez, ejecuta `newgrp docker` antes de continuar.

### 3. Desplegar el laboratorio

```bash
ansible-playbook site.yml --ask-become-pass
```

El despliegue completo tarda aproximadamente **3–5 minutos** la primera vez (descarga de imágenes Docker). Las siguientes ejecuciones son mucho más rápidas al usar caché.

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

---

## Acceso a los servicios

| Servicio | URL | Descripción |
|---|---|---|
| Panel de control | http://localhost:5000 | Dashboard principal con estado en tiempo real |
| Demo interactiva | http://localhost:5000/demo | 7 escenarios de demostración ejecutables |
| phpMyAdmin | http://localhost:8080 | Gestión visual de la base de datos |
| Web01 via proxy | https://172.21.0.10 | Acceso web a través del proxy inverso |
| Proxy info | https://172.21.0.10/info | Información del proxy inverso |
| Web01 directo | https://172.21.0.20 | Acceso directo al servidor web |

> Los certificados SSL son autofirmados — el navegador mostrará advertencia de seguridad. Es esperado en entorno de laboratorio.

---

## Credenciales

| Servicio | Usuario | Contraseña |
|---|---|---|
| MySQL root | root | Root_TFG_2026! |
| MySQL rsyslog | rsyslog | Rsyslog_TFG_2026! |
| phpMyAdmin | root | Root_TFG_2026! |
| SSH demo | ubuntu | TFG2026lab |

---

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

Servicios disponibles: `ssh`, `dns`, `dhcp`, `web`, `proxy`, `squid`, `syslog`, `mysql`, `firewall`, `postdeploy`, `panel`

### Ver logs en tiempo real

```bash
docker exec syslog01 tail -f /var/log/laboratorio/ssh.log
docker exec syslog01 tail -f /var/log/laboratorio/web.log
docker exec syslog01 tail -f /var/log/laboratorio/proxy.log
```

---

## Estructura del proyecto

```
tfg-laboratorio-red-main/
├── README.md
├── setup.sh                    # Script de preparación del entorno
├── site.yml                    # Playbook principal de despliegue
├── teardown.yml                # Playbook de destrucción completa
├── ansible.cfg
├── group_vars/
│   └── all/
│       └── main.yml            # Variables globales del laboratorio
├── inventario/
├── roles/
│   ├── firewall/               # fw01 — nftables
│   ├── ssh/                    # ssh01 — OpenSSH
│   ├── dns/                    # dns01 — BIND9
│   ├── dhcp/                   # dhcp01 — ISC DHCP
│   ├── web/                    # web01 — Nginx + SSL
│   ├── proxy/                  # proxy01 — Nginx proxy inverso
│   ├── squid/                  # squid01 — Squid
│   ├── client/                 # client01 — cliente de pruebas
│   ├── syslog/                 # syslog01 — rsyslog centralizado
│   ├── mysql/                  # mysql01 — MySQL 8.0
│   ├── dbadmin/                # dbadmin01 — phpMyAdmin
│   ├── panel/                  # panel01 — Panel Flask+HTMX
│   ├── redes/                  # Redes Docker
│   └── postdeploy/             # Limpieza de reglas Docker raw
├── pruebas/
│   ├── healthcheck.sh          # 49 tests de verificación completa
│   └── test_firewall.sh        # 12 tests de reglas de firewall
└── docs/
    └── topologia.svg           # Diagrama de red del laboratorio
```

---

## Limitaciones conocidas y documentadas

- **Bypass de fw01 desde el host:** Docker crea bridges que permiten al host acceder directamente a todas las redes sin pasar por fw01. Es una limitación estructural de Docker en modo bridge sobre un único host. El firewall controla correctamente el tráfico entre contenedores de distintas zonas.
- **Certificados SSL autofirmados:** Para entorno de laboratorio. En producción se usarían certificados emitidos por una CA reconocida.
- **Contraseñas en texto plano:** Las credenciales están en `group_vars/all/main.yml`. En un entorno de producción se usaría Ansible Vault para cifrarlas.

---

## Autores y distribución del trabajo

| Nombre | Rol en el proyecto |
|---|---|
| Abel Baños | Arquitectura de red, infraestructura Docker, firewall nftables, Ansible |
| Daniel Montero | Servicios LAN (SSH, DNS, DHCP, Squid), scripts de prueba y verificación |
| Amina Sefiani | Servicios DMZ (web01, proxy01), logging centralizado, panel Flask+HTMX |

---

*TFG — Administración de Sistemas Informáticos en Red · 2026*
