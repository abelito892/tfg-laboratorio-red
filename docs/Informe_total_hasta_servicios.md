# Informe total hasta servicios
## TFG Laboratorio de Red — ASIR
**Autor:** Abel  
**Fecha:** Abril 2026  
**Estado:** Fases 0–4.7 completadas ✅

---

## Índice

1. [Visión general del proyecto](#vision)
2. [Fase 0 — Diseño de arquitectura](#fase0)
3. [Fase 1 — Preparación del entorno](#fase1)
4. [Fase 2 — Redes Docker](#fase2)
5. [Fase 3 — Firewall fw01](#fase3)
6. [Fase 4 — Servicios LAN y DMZ](#fase4)
7. [Estado actual del laboratorio](#estado)
8. [Limitaciones conocidas](#limitaciones)

---

## 1. Visión general del proyecto {#vision}

El proyecto consiste en diseñar y desplegar un laboratorio de red completo sobre un único host Ubuntu 24.04 utilizando Docker como plataforma de contenedores y Ansible como herramienta de automatización. El objetivo es simular una infraestructura de red empresarial real con zonas segmentadas, servicios de red core, proxies y un firewall perimetral.

Todo el laboratorio se despliega desde cero con un único comando:

```bash
ansible-playbook site.yml
```

---

## 2. Fase 0 — Diseño de arquitectura {#fase0}

Se definió la topología de tres zonas de red siguiendo el modelo estándar de segmentación perimetral:

| Zona | Red | Gateway | Función |
|---|---|---|---|
| WAN | 172.20.0.0/24 | 172.20.0.1 | Simula internet / red externa |
| DMZ | 172.21.0.0/24 | 172.21.0.1 | Servicios expuestos al exterior |
| LAN | 192.168.100.0/24 | 192.168.100.1 | Servicios internos protegidos |

El firewall `fw01` actúa como elemento central de enrutamiento entre zonas, controlando qué tráfico puede pasar de una zona a otra mediante reglas nftables.

---

## 3. Fase 1 — Preparación del entorno {#fase1}

Se verificó el entorno del host y se creó la estructura completa del proyecto Ansible siguiendo las oficiales Ansible Best Practices:

**Entorno verificado:**
- Ubuntu 24.04.4, kernel 6.14
- Docker 29.3
- Ansible 2.16.3
- Python 3.12.3
- Usuario `abel` en grupo docker

**Estructura del proyecto creada en** `~/tfg-laboratorio-red`:
```
tfg-laboratorio-red/
├── ansible.cfg
├── site.yml
├── inventario/
│   └── hosts.yml
├── group_vars/
│   ├── all/main.yml
│   └── firewall/main.yml
├── roles/
│   ├── redes/
│   ├── firewall/
│   ├── ssh/
│   ├── dns/
│   ├── dhcp/
│   ├── web/
│   ├── proxy/
│   └── squid/
└── docs/
```

---

## 4. Fase 2 — Redes Docker {#fase2}

Se desplegaron las tres redes Docker mediante el módulo `community.docker.docker_network` con subredes y gateways fijos:

```bash
docker network ls
# wan_net   172.20.0.0/24
# dmz_net   172.21.0.0/24
# lan_net   192.168.100.0/24
```

**Aprendizaje clave:** Docker reserva automáticamente la primera IP de cada red como gateway (`.1`), por lo que los contenedores deben empezar en `.2`.

---

## 5. Fase 3 — Firewall fw01 {#fase3}

Se desplegó el contenedor `fw01` basado en Ubuntu 24.04 con nftables como motor de firewall.

**Interfaces:**
- `eth0` → `wan_net` — `172.20.0.2`
- `eth1` → `lan_net` — `192.168.100.2`

**Reglas nftables implementadas:**

| Regla | Descripción |
|---|---|
| `iif "lo" accept` | Tráfico loopback siempre permitido |
| `ct state established,related accept` | Conexiones establecidas permitidas (stateful) |
| `icmp type echo-request accept` | Ping permitido para diagnóstico |
| `iif "eth1" tcp dport 22 accept` | SSH desde LAN al firewall permitido |
| `iif "eth1" oif "eth0" accept` | LAN puede salir a WAN |
| `oif "eth0" masquerade` | NAT para que la LAN salga con la IP del firewall |
| `policy drop` | Todo lo demás bloqueado por defecto |

**Incidencias resueltas:**
- Go template syntax (`{{.Names}}`) dentro de YAML conflictúa con Jinja2 — se usaron comandos `docker ps --filter` en su lugar.
- La colección `community.docker.docker_network_info` devuelve estructuras de datos inesperadas — las verificaciones se hacen con comandos directos.

---

## 6. Fase 4 — Servicios LAN y DMZ {#fase4}

### Bloque 4.1 — Servidor SSH (ssh01)

Contenedor Ubuntu 24.04 con OpenSSH Server desplegado en la LAN.

- **IP:** 192.168.100.10
- **Puerto:** 22/tcp
- **Configuración:** PermitRootLogin yes, autenticación por contraseña y clave pública
- **Verificación:** `ssh root@192.168.100.10` — acceso correcto

**Incidencia resuelta:** `service ssh restart` devolvía rc=137 porque sshd es el proceso principal del contenedor. Solución: `kill -HUP <PID>` para recargar sin matar el proceso.

### Bloque 4.2 — Servidor DNS (dns01)

Contenedor con BIND9 como servidor DNS autoritativo para la zona `laboratorio.local`.

- **IP:** 192.168.100.20
- **Puertos:** 53/tcp y 53/udp
- **Zona interna:** `laboratorio.local`
- **Forwarders:** 8.8.8.8 y 1.1.1.1 para resolución externa
- **Zona inversa:** `100.168.192.in-addr.arpa`

**Verificaciones:**
```bash
dig @192.168.100.20 ssh01.laboratorio.local +short  # → 192.168.100.10 ✅
dig @192.168.100.20 -x 192.168.100.10 +short        # → ssh01.laboratorio.local ✅
dig @192.168.100.20 google.com +short               # → 216.58.205.46 ✅
```

### Bloque 4.3 — Servidor DHCP (dhcp01)

Contenedor con ISC DHCP Server para asignación dinámica de IPs en la LAN.

- **IP:** 192.168.100.30
- **Puerto:** 67/udp
- **Rango:** 192.168.100.100 — 192.168.100.200
- **Gateway asignado:** 192.168.100.2 (fw01)
- **DNS asignado:** 192.168.100.20 (dns01)
- **Dominio asignado:** laboratorio.local
- **Lease time:** 86400 segundos (24h)

**Verificación:** cliente Alpine obtuvo `192.168.100.100` desde `192.168.100.30` ✅

### Bloque 4.4 — Actualización site.yml

Se activó el Play 3 con los servicios LAN siguiendo el patrón `hosts: localhost / connection: local`.

### Bloque 4.5 — Servidor web (web01)

Contenedor con Nginx sirviendo contenido estático con HTTP y HTTPS en la DMZ.

- **IP:** 172.21.0.20
- **Puertos:** 80/tcp (redirige a HTTPS) y 443/tcp
- **Certificado:** SSL autofirmado generado durante el build con openssl
- **CN:** web01.laboratorio.local
- **Contenido:** página HTML con la tabla de infraestructura del laboratorio
- **Verificación:** acceso correcto desde navegador del host ✅

### Bloque 4.6 — Proxy inverso (proxy01)

Contenedor con Nginx en modo reverse proxy en la DMZ, único punto de entrada desde WAN hacia web01.

- **IP:** 172.21.0.10
- **Puertos:** 80/tcp (redirige a HTTPS) y 443/tcp
- **Función:** recibe peticiones externas y las reenvía internamente a web01
- **Certificado:** SSL autofirmado propio con CN=proxy01.laboratorio.local
- **Cabeceras:** X-Real-IP, X-Forwarded-For, X-Forwarded-Proto
- **Verificación:** acceso a web01 a través de proxy01 correcto ✅

**web01 queda completamente oculto al exterior** — el cliente solo conoce proxy01.

### Bloque 4.7 — Proxy de salida (squid01)

Contenedor con Squid como proxy de salida para clientes de la LAN.

- **IP:** 192.168.100.40
- **Puerto:** 3128/tcp
- **ACL:** solo permite peticiones desde 192.168.100.0/24
- **Logging:** todas las peticiones registradas en `/var/log/squid/access.log`
- **Caché:** deshabilitada en disco (laboratorio)
- **forwarded_for off:** no revela la IP del cliente al servidor destino

**Verificación desde el host:**
```
192.168.100.1 - "GET http://google.com/ HTTP/1.1" 301 TCP_MISS:HIER_DIRECT ✅
```

**Incidencias resueltas:**
- `squid -z` fallaba porque Squid ya estaba corriendo — se eliminó la inicialización de caché en tiempo de ejecución y se movió al build.
- Bucle de reinicios por fallo en `store_swapout.cc` — se deshabilitó la caché en disco con `cache deny all`.
- Formato de log `squid` requería módulo daemon — se cambió a `stdio:/var/log/squid/access.log`.

---

## 7. Estado actual del laboratorio {#estado}

### Contenedores activos

| Contenedor | Imagen | IP | Puertos | Zona |
|---|---|---|---|---|
| `fw01` | tfg/firewall | 172.20.0.2 / 192.168.100.2 | — | WAN/LAN |
| `web01` | tfg/web | 172.21.0.20 | 80, 443 | DMZ |
| `proxy01` | tfg/proxy | 172.21.0.10 | 80, 443 | DMZ |
| `ssh01` | tfg/ssh | 192.168.100.10 | 22 | LAN |
| `dns01` | tfg/dns | 192.168.100.20 | 53 | LAN |
| `dhcp01` | tfg/dhcp | 192.168.100.30 | 67 | LAN |
| `squid01` | tfg/squid | 192.168.100.40 | 3128 | LAN |

### Rendimiento del playbook

```
PLAY RECAP
localhost: ok=69  changed=23  unreachable=0  failed=0
Playbook run: ~1 minuto 37 segundos
```

### Registros DNS activos

| Nombre | IP |
|---|---|
| fw01.laboratorio.local | 192.168.100.2 |
| ssh01.laboratorio.local | 192.168.100.10 |
| dns01.laboratorio.local | 192.168.100.20 |
| dhcp01.laboratorio.local | 192.168.100.30 |
| web01.laboratorio.local | 172.21.0.20 |
| proxy01.laboratorio.local | 172.21.0.10 |
| squid01.laboratorio.local | 192.168.100.40 |
| syslog01.laboratorio.local | 172.22.0.10 |

---

## 8. Limitaciones conocidas {#limitaciones}

El host tiene acceso directo a todas las redes Docker a través de los bridges automáticos que Docker crea como gateways (`172.20.0.1`, `172.21.0.1`, `192.168.100.1`). Esto significa que el tráfico originado desde el propio host hacia cualquier contenedor no pasa por `fw01`.

Esta es una limitación estructural de Docker en modo bridge sobre un único host. En producción real se resolvería añadiendo reglas `iptables DOCKER-USER` en el host o usando hardware dedicado para el firewall.

El firewall `fw01` sí controla correctamente el tráfico entre contenedores de distintas redes — que es el escenario que evalúa el TFG.

---

*Documento generado en Abril 2026*
