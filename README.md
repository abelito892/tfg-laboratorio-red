# NetCorp — Laboratorio de Red Virtualizado
## TFG ASIR — IES Francisco de Quevedo

Laboratorio de red corporativo simulado con Docker y Ansible.
Simula la infraestructura de red de una empresa (NetCorp S.L.) con
firewall, DNS, DHCP, proxy, servidor web, base de datos y logs centralizados.

---

## Requisitos

### Linux (Ubuntu 24.04)
- Docker 20.10+
- Ansible 2.16+ con coleccion community.docker
- Python 3.10+

Instalacion automatica:
    chmod +x setup.sh && ./setup.sh

### Windows (Docker Desktop)
- Docker Desktop 4.x con WSL2 habilitado
- Git for Windows

No necesitas instalar Ansible — se ejecuta dentro de un contenedor.

---

## Despliegue

### Linux
    ansible-playbook site.yml

### Windows (y tambien Linux)
    docker compose run --rm deploy

### Teardown
    # Linux
    ansible-playbook teardown.yml

    # Windows
    docker compose run --rm teardown

### Shell interactivo (debug)
    docker compose run --rm shell

---

## Accesos

| Servicio         | URL                    | Credenciales            |
|------------------|------------------------|-------------------------|
| Panel de control | http://localhost:5000  | —                       |
| phpMyAdmin       | http://localhost:8080  | root / Root_TFG_2026!   |
| SSH corporativo  | ssh -p 2222 ubuntu@localhost | TFG2026lab        |

---

## Arquitectura

    WAN (172.20.0.0/24)
      └── fw01 (firewall nftables)
            ├── DMZ (172.21.0.0/24)
            │     ├── proxy01 (Nginx proxy inverso)
            │     └── web01   (Nginx + FastAPI + MySQL)
            └── LAN (192.168.100.0/24)
                  ├── ssh01   (OpenSSH)
                  ├── dns01   (BIND9)
                  ├── dhcp01  (ISC DHCP)
                  ├── squid01 (Squid proxy salida)
                  └── client01 (cliente DHCP)

    MGMT (172.22.0.0/24) — red de gestion
      └── syslog01 (rsyslog centralizado)

    DB (172.23.0.0/24) — red de base de datos
      ├── mysql01  (MySQL 8.0 — BD NetCorp)
      └── panel01  (Flask + HTMX — panel de control)

---

## Credenciales

| Servicio     | Usuario | Contrasena        |
|--------------|---------|-------------------|
| MySQL root   | root    | Root_TFG_2026!    |
| MySQL app    | netcorp | NetCorp_TFG_2026! |
| SSH ubuntu   | ubuntu  | TFG2026lab        |
| SSH root     | root    | laboratorio       |

---

## Comandos de demo

Ver logs en tiempo real:
    docker exec syslog01 tail -f /var/log/laboratorio/all.log

Empleado accede a la intranet:
    docker exec client01 curl -sk https://intranet.netcorp.local/api/empleados

Empleado navega a internet via Squid:
    docker exec client01 curl -s http://example.com

Empleado conecta por SSH al servidor corporativo:
    docker exec client01 bash -c "sshpass -p 'TFG2026lab' ssh -o StrictHostKeyChecking=no ubuntu@192.168.100.10 'whoami && date'"

Ver accesos registrados en MySQL:
    docker exec mysql01 bash -c 'mysql -unetcorp -pNetCorp_TFG_2026! NetCorp -e "SELECT ip_origen, servicio, timestamp FROM accesos ORDER BY id DESC LIMIT 5;"'
