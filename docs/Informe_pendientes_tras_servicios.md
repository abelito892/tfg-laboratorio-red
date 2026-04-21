# Informe pendientes tras servicios
## TFG Laboratorio de Red — ASIR
**Autor:** Abel  
**Fecha:** Abril 2026  
**Estado:** En progreso — Bloques 4.8 y siguientes pendientes

---

## Índice

1. [Resumen de lo pendiente](#resumen)
2. [Bloque 4.8 — Actualización nftables](#bloque48)
3. [Bloque 4.9 — Cliente de pruebas](#bloque49)
4. [Fase 5 — Optimización Ansible](#fase5)
5. [Fase 6 — Logs, pruebas y hardening](#fase6)
6. [Fase 7 — Memoria del TFG](#fase7)
7. [Variante opcional — Monitorización](#variante)

---

## 1. Resumen de lo pendiente {#resumen}

| Tarea | Descripción | Prioridad |
|---|---|---|
| **Bloque 4.8** | Actualizar reglas nftables para DMZ | Alta |
| **Bloque 4.9** | Contenedor cliente de pruebas | Alta |
| **Fase 5** | Optimización Ansible | Media |
| **Fase 6** | Logs, pruebas y hardening | Alta |
| **Fase 7** | Memoria del TFG | Alta |
| **Variante** | Monitorización avanzada | Opcional |

---

## 2. Bloque 4.8 — Actualización nftables {#bloque48}

### Problema actual

`fw01` solo tiene dos interfaces — `eth0` (WAN) y `eth1` (LAN). La DMZ existe como red Docker pero `fw01` no está conectado a ella, por lo que no puede enrutar ni filtrar el tráfico hacia `proxy01` y `web01`.

### Qué hay que hacer

**Paso 1 — Conectar fw01 a dmz_net**

Actualizar `roles/firewall/tasks/main.yml` para añadir una tercera interfaz en `dmz_net`:

```yaml
networks:
  - name: "{{ redes.wan.nombre }}"
    ipv4_address: "{{ contenedores.firewall.ip_wan }}"
  - name: "{{ redes.lan.nombre }}"
    ipv4_address: "{{ contenedores.firewall.ip_lan }}"
  - name: "{{ redes.dmz.nombre }}"
    ipv4_address: "{{ contenedores.firewall.ip_dmz }}"
```

Y añadir en `group_vars/all/main.yml`:
```yaml
firewall:
  ip_dmz: "172.21.0.2"
```

**Paso 2 — Actualizar reglas nftables**

Añadir las siguientes reglas en `roles/firewall/files/nftables.conf`:

```
# WAN → DMZ: solo proxy01 en puertos 80 y 443
iif "eth0" oif "eth2" ip daddr 172.21.0.10 tcp dport { 80, 443 } accept

# DMZ → DMZ: proxy01 puede alcanzar web01
iif "eth2" oif "eth2" ip saddr 172.21.0.10 ip daddr 172.21.0.20 accept

# Bloquear acceso directo WAN → web01
iif "eth0" oif "eth2" ip daddr 172.21.0.20 drop

# DMZ → LAN bloqueado (DMZ no puede acceder a servicios internos)
iif "eth2" oif "eth1" drop
```

### Resultado esperado

- WAN puede acceder a `proxy01` en puertos 80 y 443 ✅
- WAN no puede acceder directamente a `web01` ✅
- `proxy01` puede reenviar peticiones a `web01` ✅
- DMZ no puede acceder a la LAN ✅

---

## 3. Bloque 4.9 — Cliente de pruebas (client01) {#bloque49}

### Objetivo

Desplegar un contenedor en la LAN sin IP fija que demuestre de forma integrada el funcionamiento de todos los servicios del laboratorio.

### Ficheros a crear

```
roles/client/
├── files/
│   └── Dockerfile
└── tasks/
    └── main.yml
```

### Qué demostrará client01

| Prueba | Servicio | Comando |
|---|---|---|
| Obtiene IP automáticamente | dhcp01 | `udhcpc -i eth0` |
| Resuelve nombres internos | dns01 | `nslookup ssh01.laboratorio.local` |
| Resuelve nombres externos | dns01 → forwarder | `nslookup google.com` |
| Navega por internet | squid01 → fw01 | `curl -x squid01:3128 http://example.com` |
| Accede al servidor web | proxy01 → web01 | `curl -k https://proxy01.laboratorio.local` |
| Conecta por SSH | ssh01 | `ssh root@ssh01.laboratorio.local` |

---

## 4. Fase 5 — Optimización Ansible {#fase5}

Esta fase no añade servicios nuevos. Mejora la calidad y robustez del código Ansible existente.

### 5.1 — Handlers

Actualmente todos los roles recargan su configuración en cada ejecución aunque nada haya cambiado. Los handlers permiten ejecutar tareas de recarga solo cuando algo realmente cambia.

```yaml
# Tarea que modifica configuración
- name: "Copiar sshd_config"
  notify: "Recargar SSH"   # Solo dispara el handler si changed=true

# handlers/main.yml
- name: "Recargar SSH"
  command: docker exec ssh01 kill -HUP <pid>
```

Se añadirán handlers a los roles `ssh`, `dns`, `dhcp`, `web`, `proxy` y `squid`.

### 5.2 — Tags

Permiten ejecutar partes del playbook de forma selectiva:

```bash
ansible-playbook site.yml --tags ssh         # Solo SSH
ansible-playbook site.yml --tags dns,dhcp    # Solo DNS y DHCP
ansible-playbook site.yml --tags dmz         # Solo servicios DMZ
ansible-playbook site.yml --skip-tags squid  # Todo excepto Squid
```

### 5.3 — Variables y defaults

Revisión de que todas las IPs, puertos y nombres están en `group_vars` sin hardcodear dentro de los roles. Añadir `roles/*/defaults/main.yml` con valores por defecto.

### 5.4 — Teardown

Crear `teardown.yml` para destruir todo el laboratorio de una sola ejecución:

```bash
ansible-playbook teardown.yml
# Elimina: fw01, ssh01, dns01, dhcp01, web01, proxy01, squid01, syslog01
# Elimina: wan_net, dmz_net, lan_net, mgmt_net
```

Muy útil para demostrar la reproducibilidad del laboratorio desde cero en la demo con el tutor.

### 5.5 — Manejo de errores

Añadir `pre_tasks` al playbook maestro que verifiquen el entorno antes de ejecutar:
- Docker está corriendo
- La colección `community.docker` está instalada
- Espacio en disco suficiente

---

## 5. Fase 6 — Logs, pruebas y hardening {#fase6}

### 6.1 — Red de gestión (mgmt_net)

Nueva red Docker `172.22.0.0/24` dedicada exclusivamente al tráfico de logs y gestión, separada del tráfico de producción. Todos los contenedores tendrán una segunda interfaz en esta red.

### 6.2 — Servidor de logs (syslog01)

Contenedor con rsyslog centralizado en `mgmt_net` (`172.22.0.10`) que recibe logs de todos los servicios:

```
/var/log/laboratorio/
├── firewall.log    ← reglas nftables aceptadas y rechazadas
├── ssh.log         ← conexiones y autenticaciones
├── dns.log         ← queries DNS
├── dhcp.log        ← asignaciones de IP
├── web.log         ← accesos HTTP/HTTPS
├── proxy.log       ← tráfico proxy inverso
└── squid.log       ← navegación de clientes LAN
```

### 6.3 — Configuración de envío de logs

Cada contenedor configurado para enviar logs a `syslog01` vía UDP/514 (protocolo syslog estándar).

### 6.4 — Script de pruebas automáticas

Crear `pruebas/test_laboratorio.sh` con batería completa de pruebas:

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
✅ PASS: Web accesible vía proxy01 HTTP
✅ PASS: Web accesible vía proxy01 HTTPS
✅ PASS: Squid acepta conexiones en 3128
✅ PASS: Reglas nftables activas
✅ PASS: LAN sale a internet
✅ PASS: WAN no accede directamente a LAN
✅ PASS: Logs llegando a syslog01
=== Resultado: 19 pasados, 0 fallados ===
```

### 6.5 — Pruebas de conectividad entre zonas

```bash
# LAN → Internet a través del firewall
docker exec ssh01 ping -c 1 8.8.8.8

# LAN → DMZ
docker exec ssh01 curl -k https://172.21.0.10

# WAN NO puede acceder a LAN (debe fallar)
docker run --rm --network wan_net alpine ping -c 2 192.168.100.10

# WAN SÍ puede acceder a proxy01
docker run --rm --network wan_net alpine wget -qO- http://172.21.0.10
```

### 6.6 — Pruebas del firewall

```bash
# WAN NO puede acceder directamente a web01 (debe fallar)
docker run --rm --network wan_net alpine wget -qO- http://172.21.0.20

# Ver contadores de paquetes por regla
docker exec fw01 nft list ruleset -a
```

### 6.7 — Pruebas de los proxies

```bash
# Proxy inverso — HTTP redirige a HTTPS
curl -I http://172.21.0.10

# Proxy de salida — tráfico LAN a través de Squid
curl -x 192.168.100.40:3128 http://example.com -s -o /dev/null -w "%{http_code}"

# Ver logs de Squid
docker exec squid01 tail -20 /var/log/squid/access.log
```

### 6.8 — Revisión de logs centralizados

```bash
docker exec syslog01 ls -la /var/log/laboratorio/
docker exec syslog01 tail -20 /var/log/laboratorio/firewall.log
docker exec syslog01 tail -20 /var/log/laboratorio/ssh.log
```

### 6.9 — Hardening

**SSH:**
- Generar par de claves RSA en el host
- Copiar clave pública a `ssh01`
- Deshabilitar `PasswordAuthentication` — solo claves públicas
- Reducir `MaxAuthTries` a 3

**Firewall (nftables):**
- Rate limiting para prevenir fuerza bruta SSH:
  ```
  tcp dport 22 ct state new limit rate 5/minute accept
  ```
- Logging de conexiones rechazadas:
  ```
  log prefix "nftables DROP: " drop
  ```

**Docker:**
- Revisar contenedores que corren con más privilegios de los necesarios
- Verificar volúmenes montados como solo lectura donde sea posible

---

## 6. Fase 7 — Memoria del TFG {#fase7}

### Estructura del documento

```
1. Portada
2. Índice
3. Resumen / Abstract
4. Introducción
5. Marco teórico
   - Virtualización y contenedores (Docker)
   - Automatización con Ansible
   - Seguridad perimetral (nftables)
   - Servicios de red (DNS, DHCP, SSH)
   - Proxies (inverso y de salida)
   - Centralización de logs (rsyslog)
6. Diseño de la solución
   - Arquitectura del laboratorio (4 redes)
   - Diagrama de red completo
   - Tabla de direccionamiento
   - Política de seguridad entre zonas
7. Implementación
   - Preparación del entorno
   - Redes Docker
   - Firewall y nftables
   - Servicios LAN
   - Servicios DMZ
   - Proxies
   - Red de gestión y logs
   - Optimización Ansible
8. Pruebas y validación
9. Conclusiones
   - Objetivos alcanzados
   - Dificultades y resoluciones
   - Limitaciones conocidas
   - Posibles ampliaciones
10. Bibliografía
Anexos
   A. Código fuente completo
   B. Manual de despliegue
   C. Capturas de pantalla
```

### Claves para la máxima nota

- **Documentar incidencias** — los errores encontrados y sus resoluciones demuestran profundidad técnica real.
- **Justificar decisiones** — explicar el por qué de cada elección tecnológica, no solo el cómo.
- **Contexto profesional** — mencionar equivalentes en AWS, Azure y Kubernetes.
- **Limitaciones conocidas** — documentar el acceso directo del host a las redes Docker y la solución con `iptables DOCKER-USER`.
- **Posibles ampliaciones** — describir la variante de monitorización avanzada.

---

## 7. Variante opcional — Monitorización avanzada {#variante}

**Estado:** En espera. Decisión al finalizar la Fase 6.

**Ventaja:** la red `mgmt_net` ya estará creada desde la Fase 6. Añadir monitorización avanzada solo requiere dos contenedores adicionales.

| Contenedor | IP | Servicio |
|---|---|---|
| `metrics01` | 172.22.0.20 | Prometheus + Grafana |
| `logserver01` | 172.22.0.30 | Graylog o Loki + Promtail |

Implementar esta variante elevaría el proyecto a nivel de infraestructura empresarial completa con observabilidad centralizada. Se recomienda mencionarla en la memoria como ampliación propuesta independientemente de si se implementa.

---

*Documento generado en Abril 2026 — pendiente de actualización conforme avancen las fases*
