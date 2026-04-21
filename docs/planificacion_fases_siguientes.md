# Planificación Detallada — Fases Siguientes
## TFG Laboratorio de Red — ASIR
**Autor:** Abel  
**Fecha:** Abril 2026  
**Estado:** Planificación activa

---

## Índice

1. [Tabla de direccionamiento actualizada](#direccionamiento)
2. [Bloques pendientes Fase 4](#fase4-pendiente)
3. [Fase 5 — Optimización Ansible](#fase5)
4. [Fase 6 — Logs, pruebas y hardening](#fase6)
5. [Fase 7 — Memoria del TFG](#fase7)
6. [Variante opcional — Monitorización avanzada](#variante)

---

## 1. Tabla de direccionamiento actualizada {#direccionamiento}

| Contenedor | Red | IP | Servicio | Estado |
|---|---|---|---|---|
| `fw01` | WAN + LAN | 172.20.0.2 / 192.168.100.2 | Firewall/Router nftables | ✅ Desplegado |
| `ssh01` | LAN | 192.168.100.10 | OpenSSH Server | ✅ Desplegado |
| `dns01` | LAN | 192.168.100.20 | BIND9 | ✅ Desplegado |
| `dhcp01` | LAN | 192.168.100.30 | ISC DHCP Server | ✅ Desplegado |
| `proxy01` | DMZ | 172.21.0.10 | Proxy inverso Nginx | ⏳ Pendiente |
| `web01` | DMZ | 172.21.0.20 | Servidor web Nginx + SSL | ⏳ Pendiente |
| `squid01` | LAN | 192.168.100.40 | Proxy de salida Squid | ⏳ Pendiente |
| `client01` | LAN | DHCP dinámico | Cliente de pruebas | ⏳ Pendiente |
| `syslog01` | mgmt_net | 172.22.0.10 | Logs centralizados rsyslog | ⏳ Pendiente |

### Redes Docker

| Red | Subred | Gateway | Estado |
|---|---|---|---|
| `wan_net` | 172.20.0.0/24 | 172.20.0.1 | ✅ Activa |
| `dmz_net` | 172.21.0.0/24 | 172.21.0.1 | ✅ Activa |
| `lan_net` | 192.168.100.0/24 | 192.168.100.1 | ✅ Activa |
| `mgmt_net` | 172.22.0.0/24 | 172.22.0.1 | ⏳ Pendiente |

---

## 2. Bloques pendientes Fase 4 {#fase4-pendiente}

Antes de pasar a la Fase 5 se completarán cinco bloques adicionales que amplían la arquitectura con servicios DMZ y un cliente de pruebas.

### Preparación previa a los bloques

Antes de empezar el bloque 4.5 hay que actualizar dos ficheros existentes:

**`group_vars/all/main.yml`** — añadir los nuevos contenedores (`proxy01`, `web01`, `squid01`, `client01`) y la nueva red `mgmt_net`.

**`roles/dns/files/db.laboratorio.local`** — añadir registros A para los nuevos servicios:
```
proxy01.laboratorio.local   → 172.21.0.10
web01.laboratorio.local     → 172.21.0.20
squid01.laboratorio.local   → 192.168.100.40
syslog01.laboratorio.local  → 172.22.0.10
```

---

### Bloque 4.5 — Servidor web (`web01`) en DMZ

**Objetivo:** Desplegar Nginx sirviendo contenido estático con HTTP y HTTPS en la DMZ.

**Ficheros a crear:**
```
roles/web/
├── files/
│   ├── Dockerfile
│   └── index.html
├── tasks/
│   └── main.yml
└── templates/
    └── nginx.conf.j2
```

**Detalles técnicos:**

El certificado SSL autofirmado se genera durante el build de la imagen usando `openssl`:
```dockerfile
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx.key \
    -out /etc/ssl/certs/nginx.crt \
    -subj "/C=ES/ST=Madrid/L=Madrid/O=TFG-ASIR/CN=web01.laboratorio.local"
```

Nginx se configura con dos bloques `server`: uno en el puerto 80 que redirige automáticamente a HTTPS, y otro en el puerto 443 con el certificado autofirmado.

**IP fija:** `172.21.0.20` en `dmz_net`

**Puertos expuestos:** 80/tcp y 443/tcp

**Verificación:**
```bash
curl -k https://172.21.0.20
```

---

### Bloque 4.6 — Proxy inverso (`proxy01`) en DMZ

**Objetivo:** Desplegar Nginx en modo reverse proxy como único punto de entrada desde WAN hacia `web01`. `web01` queda completamente oculto al exterior.

**Ficheros a crear:**
```
roles/proxy/
├── files/
│   └── Dockerfile
├── tasks/
│   └── main.yml
└── templates/
    └── nginx-proxy.conf.j2
```

**Detalles técnicos:**

`proxy01` recibe las peticiones en los puertos 80 y 443 y las reenvía internamente a `web01` en `172.21.0.20`. La configuración de Nginx incluye cabeceras de proxy estándar:
```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

`proxy01` también necesita estar conectado a `dmz_net` para poder alcanzar a `web01`.

**IP fija:** `172.21.0.10` en `dmz_net`

**Puertos expuestos:** 80/tcp y 443/tcp (los únicos accesibles desde WAN)

**Verificación:**
```bash
curl -k https://172.21.0.10
# La respuesta viene de web01 a través del proxy
```

---

### Bloque 4.7 — Proxy de salida (`squid01`) en LAN

**Objetivo:** Desplegar Squid como proxy de salida para los clientes de la LAN. El tráfico web saliente pasa por Squid antes de llegar al firewall, permitiendo filtrado de URLs y logging de navegación.

**Ficheros a crear:**
```
roles/squid/
├── files/
│   └── Dockerfile
├── tasks/
│   └── main.yml
└── templates/
    └── squid.conf.j2
```

**Detalles técnicos:**

Squid escucha en el puerto 3128 (estándar). La configuración incluye:
- ACL para permitir acceso desde la red LAN (`192.168.100.0/24`)
- Logging de todas las peticiones en `/var/log/squid/access.log`
- Cache básico de contenido web

Los clientes de la LAN configuran `192.168.100.40:3128` como proxy HTTP/HTTPS.

**IP fija:** `192.168.100.40` en `lan_net`

**Puerto:** 3128/tcp

**Verificación:**
```bash
docker exec ssh01 curl -x 192.168.100.40:3128 http://example.com
```

---

### Bloque 4.8 — Actualización de reglas nftables en `fw01`

**Objetivo:** Actualizar las reglas del firewall para reflejar la nueva arquitectura con DMZ activa y proxies.

**Reglas a añadir:**

```
# WAN → DMZ: solo proxy01 en puertos 80 y 443
iif "eth0" oif "eth2" ip daddr 172.21.0.10 tcp dport { 80, 443 } accept

# DMZ → DMZ: proxy01 puede alcanzar web01
iif "eth2" oif "eth2" ip saddr 172.21.0.10 ip daddr 172.21.0.20 accept

# LAN → Internet vía squid01
iif "eth1" oif "eth0" ip saddr 192.168.100.40 accept

# Bloquear acceso directo WAN → web01 (solo a través de proxy01)
iif "eth0" oif "eth2" ip daddr 172.21.0.20 drop
```

`fw01` necesitará una tercera interfaz conectada a `dmz_net` para poder enrutar tráfico hacia la DMZ.

---

### Bloque 4.9 — Cliente de pruebas (`client01`) en LAN

**Objetivo:** Desplegar un contenedor cliente en la LAN sin IP fija que demuestre el funcionamiento integrado de todos los servicios.

**Ficheros a crear:**
```
roles/client/
├── files/
│   └── Dockerfile
└── tasks/
    └── main.yml
```

**Qué demostrará `client01`:**

| Prueba | Servicio utilizado | Comando |
|---|---|---|
| Obtiene IP automáticamente | dhcp01 | `udhcpc -i eth0` |
| Resuelve nombres internos | dns01 | `nslookup ssh01.laboratorio.local` |
| Resuelve nombres externos | dns01 → forwarder | `nslookup google.com` |
| Navega por internet | squid01 → fw01 | `curl -x squid01:3128 http://example.com` |
| Accede al servidor web | proxy01 → web01 | `curl -k https://proxy01.laboratorio.local` |
| Conecta por SSH | ssh01 | `ssh root@ssh01.laboratorio.local` |

---

## 3. Fase 5 — Optimización Ansible {#fase5}

**Objetivo:** Mejorar la calidad, robustez y profesionalidad del código Ansible existente sin añadir funcionalidad nueva.

### 5.1 — Handlers

Los handlers permiten ejecutar tareas de recarga solo cuando algo realmente cambia, en lugar de hacerlo siempre. Actualmente todos los roles recargan su configuración en cada ejecución del playbook.

**Cómo funcionan:**
```yaml
# En la tarea que modifica la configuración:
- name: "Copiar sshd_config al contenedor"
  ansible.builtin.command: >
    docker cp ...
  changed_when: true
  notify: "Recargar SSH"   # Solo se ejecuta si esta tarea reporta changed

# En handlers/main.yml del rol:
- name: "Recargar SSH"
  ansible.builtin.command: >
    docker exec ssh01 kill -HUP <pid>
```

Se añadirán handlers a los roles `ssh`, `dns` y `dhcp`.

### 5.2 — Tags

Los tags permiten ejecutar partes del playbook de forma selectiva, muy útil durante el desarrollo y las pruebas.

**Ejemplos de uso:**
```bash
ansible-playbook site.yml --tags ssh        # Solo despliega SSH
ansible-playbook site.yml --tags dns,dhcp   # Solo DNS y DHCP
ansible-playbook site.yml --tags servicios  # Todos los servicios LAN
ansible-playbook site.yml --skip-tags web   # Todo excepto el servidor web
```

### 5.3 — Variables y defaults

Se revisará que todas las IPs, puertos y nombres están en `group_vars` y nunca hardcodeados dentro de los roles. Se añadirán ficheros `roles/*/defaults/main.yml` con valores por defecto para variables opcionales como puertos, tiempos de lease, etc.

### 5.4 — Teardown

Se creará `teardown.yml` para eliminar todos los contenedores y redes del laboratorio de una sola ejecución:

```bash
ansible-playbook teardown.yml
```

Útil para limpiar el entorno y demostrar la reproducibilidad del laboratorio desde cero durante la demo con el tutor.

### 5.5 — Manejo de errores

Se añadirán `pre_tasks` al playbook maestro que verifiquen el estado del sistema antes de ejecutar:
- Docker está corriendo
- La colección `community.docker` está instalada
- El espacio en disco es suficiente

---

## 4. Fase 6 — Logs, pruebas y hardening {#fase6}

### 6.1 — Red de gestión (`mgmt_net`)

Se creará una cuarta red Docker `172.22.0.0/24` dedicada exclusivamente al tráfico de logs y gestión. Esta red estará aislada del tráfico de producción.

Todos los contenedores existentes recibirán una segunda interfaz en `mgmt_net` para enviar sus logs a `syslog01` sin mezclar ese tráfico con el de producción.

**Valor académico:** La separación del tráfico de gestión del tráfico de producción es una práctica estándar en redes empresariales. Demuestra conocimiento avanzado de segmentación de red.

### 6.2 — Servidor de logs (`syslog01`)

Se desplegará un contenedor con rsyslog centralizado en `mgmt_net`:

**Ficheros a crear:**
```
roles/syslog/
├── files/
│   └── Dockerfile
├── tasks/
│   └── main.yml
└── templates/
    └── rsyslog.conf.j2
```

**Estructura de logs:**
```
/var/log/laboratorio/
    ├── firewall.log    ← reglas nftables (aceptadas y rechazadas)
    ├── ssh.log         ← conexiones y autenticaciones
    ├── dns.log         ← queries DNS realizadas
    ├── dhcp.log        ← asignaciones de IP
    ├── web.log         ← accesos HTTP/HTTPS
    ├── proxy.log       ← tráfico a través del proxy inverso
    └── squid.log       ← navegación de clientes LAN
```

**IP fija:** `172.22.0.10` en `mgmt_net`

**Puerto:** 514/udp (syslog estándar)

### 6.3 — Configuración de envío de logs

Cada contenedor se configurará para enviar sus logs a `syslog01` via UDP/514 usando el protocolo syslog estándar. En la práctica esto implica:

- Configurar rsyslog o el demonio de logs de cada servicio para reenviar a `172.22.0.10:514`
- Añadir una tarea Ansible en cada rol que copie la configuración de envío de logs

### 6.4 — Script de pruebas automáticas

Se creará `pruebas/test_laboratorio.sh` con una batería completa de pruebas que genera un informe pass/fail:

```bash
./pruebas/test_laboratorio.sh
=== Pruebas del laboratorio TFG ===
✅ PASS: Contenedor fw01 activo
✅ PASS: Contenedor ssh01 activo
✅ PASS: Contenedor dns01 activo
✅ PASS: Contenedor dhcp01 activo
✅ PASS: Contenedor proxy01 activo
✅ PASS: Contenedor web01 activo
✅ PASS: Contenedor squid01 activo
✅ PASS: Contenedor syslog01 activo
✅ PASS: DNS resuelve ssh01.laboratorio.local
✅ PASS: DNS resuelve nombres externos
✅ PASS: DHCP asigna IP en rango correcto
✅ PASS: SSH accesible en 192.168.100.10
✅ PASS: Web accesible vía proxy01 (HTTP)
✅ PASS: Web accesible vía proxy01 (HTTPS)
✅ PASS: Squid acepta conexiones en 3128
✅ PASS: Reglas nftables activas (masquerade)
✅ PASS: LAN sale a internet
✅ PASS: WAN no accede directamente a LAN
✅ PASS: Logs llegando a syslog01

=== Resultado: 19 pasados, 0 fallados ===
```

### 6.5 — Pruebas de conectividad

Verificación sistemática de la comunicación entre todas las zonas según la política de seguridad:

```bash
# Host → todas las zonas (acceso directo por bridges Docker)
ping -c 1 172.20.0.2     # fw01 WAN
ping -c 1 172.21.0.10    # proxy01 DMZ
ping -c 1 192.168.100.10 # ssh01 LAN

# Contenedor LAN → Internet (a través del firewall)
docker exec ssh01 ping -c 1 8.8.8.8

# Contenedor LAN → DMZ
docker exec ssh01 curl -k https://172.21.0.10
```

### 6.6 — Pruebas del firewall

Verificar que las reglas nftables funcionan correctamente:

```bash
# WAN NO puede acceder directamente a LAN (debe fallar)
docker run --rm --network wan_net alpine ping -c 2 192.168.100.10

# WAN SÍ puede acceder a proxy01 (debe funcionar)
docker run --rm --network wan_net alpine wget -qO- http://172.21.0.10

# WAN NO puede acceder directamente a web01 (debe fallar)
docker run --rm --network wan_net alpine wget -qO- http://172.21.0.20

# Ver contadores de paquetes por regla
docker exec fw01 nft list ruleset -a
```

### 6.7 — Pruebas de los proxies

```bash
# Proxy inverso — acceso a web01 a través de proxy01
curl -k https://172.21.0.10
curl -I http://172.21.0.10  # Debe redirigir a HTTPS

# Proxy de salida — tráfico LAN a través de Squid
docker exec ssh01 curl -x 192.168.100.40:3128 http://example.com

# Verificar logs de Squid
docker exec squid01 tail -f /var/log/squid/access.log
```

### 6.8 — Revisión de logs centralizados

Tras ejecutar todas las pruebas, verificar que `syslog01` ha recibido logs de todos los servicios:

```bash
docker exec syslog01 ls -la /var/log/laboratorio/
docker exec syslog01 tail -20 /var/log/laboratorio/firewall.log
docker exec syslog01 tail -20 /var/log/laboratorio/ssh.log
docker exec syslog01 tail -20 /var/log/laboratorio/dns.log
```

### 6.9 — Hardening

**SSH (`ssh01`):**
- Generar par de claves RSA en el host y copiar la clave pública al contenedor
- Deshabilitar `PasswordAuthentication` — solo claves públicas
- Reducir `MaxAuthTries` a 3

**Firewall (`fw01`) — nftables:**
- Añadir rate limiting para prevenir fuerza bruta en SSH:
  ```
  tcp dport 22 ct state new limit rate 5/minute accept
  ```
- Añadir logging de conexiones rechazadas para auditoría:
  ```
  log prefix "nftables DROP: " drop
  ```

**Docker:**
- Revisar que los contenedores no corren con más privilegios de los necesarios
- Verificar que los volúmenes montados son de solo lectura donde sea posible

---

## 5. Fase 7 — Memoria del TFG {#fase7}

### Estructura del documento

```
1. Portada
2. Índice
3. Resumen / Abstract
4. Introducción
   4.1 Motivación del proyecto
   4.2 Objetivos
   4.3 Alcance
5. Marco teórico
   5.1 Virtualización y contenedores (Docker)
   5.2 Automatización con Ansible
   5.3 Seguridad perimetral y firewalls (nftables)
   5.4 Servicios de red (DNS, DHCP, SSH)
   5.5 Proxies (inverso y de salida)
   5.6 Centralización de logs (rsyslog)
6. Diseño de la solución
   6.1 Arquitectura del laboratorio (4 redes)
   6.2 Diagrama de red completo
   6.3 Tabla de direccionamiento
   6.4 Política de seguridad entre zonas
7. Implementación
   7.1 Preparación del entorno
   7.2 Creación de redes Docker
   7.3 Despliegue del firewall y reglas nftables
   7.4 Despliegue de servicios LAN (SSH, DNS, DHCP)
   7.5 Despliegue de servicios DMZ (web01, proxy01)
   7.6 Proxy de salida Squid
   7.7 Red de gestión y logs centralizados
   7.8 Optimización Ansible (handlers, tags, teardown)
8. Pruebas y validación
   8.1 Pruebas de conectividad entre zonas
   8.2 Pruebas de servicios
   8.3 Pruebas de seguridad del firewall
   8.4 Resultados del script de pruebas automáticas
9. Conclusiones
   9.1 Objetivos alcanzados
   9.2 Dificultades encontradas y resoluciones
   9.3 Limitaciones conocidas
   9.4 Posibles ampliaciones
10. Bibliografía
Anexos
   A. Código fuente completo
   B. Manual de despliegue
   C. Capturas de pantalla
```

### Secciones clave para la máxima nota

**Limitaciones conocidas (sección 9.3):** Documentar que el host tiene acceso directo a todas las redes Docker a través de los bridges automáticos, explicar por qué ocurre y cómo se resolvería en producción con `iptables DOCKER-USER`. Esta honestidad técnica demuestra madurez y suma puntos.

**Posibles ampliaciones (sección 9.4):** Describir la variante de monitorización avanzada (Prometheus + Grafana + Graylog) sobre la red `mgmt_net` ya existente. La red de gestión ya estará creada, por lo que la implementación sería directa.

**Contexto profesional:** Mencionar equivalentes en entornos reales y cloud: Docker Swarm / Kubernetes para orquestación, AWS VPC con Security Groups para la segmentación de red, Terraform para la infraestructura como código equivalente a Ansible.

**Incidencias documentadas:** Los errores encontrados y sus resoluciones (rc=137 en SSH, directorio de trabajo incorrecto, etc.) demuestran profundidad técnica real.

---

## 6. Variante opcional — Monitorización avanzada {#variante}

**Estado:** En espera. Decisión al finalizar la Fase 6 según tiempo disponible.

**Ventaja clave:** La red `mgmt_net` ya estará creada y operativa desde la Fase 6. Añadir la monitorización avanzada solo requiere desplegar dos contenedores adicionales sobre esa red.

### Componentes adicionales

| Contenedor | IP | Servicio | Función |
|---|---|---|---|
| `metrics01` | 172.22.0.20 | Prometheus + Grafana | Dashboards de CPU, RAM, red y disco |
| `logserver01` | 172.22.0.30 | Graylog o Loki + Promtail | Búsqueda avanzada en logs centralizados |

### Qué monitorizaría

- Métricas de recursos de cada contenedor en tiempo real (Grafana)
- Logs del firewall nftables con búsqueda (Graylog/Loki)
- Logs de acceso SSH — quién se conectó, cuándo y desde dónde
- Queries DNS — qué nombres se resuelven y con qué frecuencia
- Asignaciones DHCP — historial de IPs asignadas
- Tráfico a través de los proxies

### Valor académico

Implementar esta variante elevaría el proyecto a un nivel de infraestructura empresarial completo con observabilidad centralizada. Se recomienda mencionar en la memoria independientemente de si se implementa, ya que demuestra visión de conjunto del proyecto.

---

*Documento generado en Abril 2026 — pendiente de actualización conforme avancen las fases*
