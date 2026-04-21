# Informe Técnico — Fase 4: Servicios LAN
## TFG Laboratorio de Red — ASIR
**Autor:** Abel  
**Fecha:** Abril 2026  
**Estado:** Completada ✅

---

## Índice

1. [Resumen ejecutivo](#resumen)
2. [Bloque 4.1 — Servidor SSH](#ssh)
3. [Bloque 4.2 — Servidor DNS](#dns)
4. [Bloque 4.3 — Servidor DHCP](#dhcp)
5. [Bloque 4.4 — Actualización site.yml](#siteyml)
6. [Verificaciones realizadas](#verificaciones)
7. [Incidencias y resoluciones](#incidencias)
8. [Estado final del laboratorio](#estado)

---

## 1. Resumen ejecutivo {#resumen}

La Fase 4 ha completado el despliegue de los tres servicios core de red en la zona LAN del laboratorio. Cada servicio corre en su propio contenedor Docker con IP fija, desplegado y configurado íntegramente mediante Ansible siguiendo el patrón establecido en fases anteriores.

El playbook maestro `site.yml` ejecuta ahora 40 tareas en 21 segundos desplegando el laboratorio completo desde cero, con 0 errores en todas las ejecuciones de verificación.

---

## 2. Bloque 4.1 — Servidor SSH (`ssh01`) {#ssh}

### Objetivo
Desplegar un servidor OpenSSH en la LAN accesible desde el host para administración de los contenedores.

### Ficheros creados

| Fichero | Descripción |
|---|---|
| `roles/ssh/files/Dockerfile` | Imagen Ubuntu 24.04 con OpenSSH instalado |
| `roles/ssh/templates/sshd_config.j2` | Plantilla de configuración SSH |
| `roles/ssh/tasks/main.yml` | Tareas Ansible de despliegue |

### Configuración aplicada

- Puerto 22 estándar, protocolo SSH-2
- Autenticación por contraseña habilitada (laboratorio)
- Autenticación por clave pública habilitada (preparado para hardening Fase 6)
- `PermitRootLogin yes` — necesario para el laboratorio, protegido por el firewall

### Detalles técnicos relevantes

El proceso `sshd` es el CMD principal del contenedor. Esto provocó un error en la primera ejecución al intentar reiniciarlo con `service ssh restart` (rc=137, SIGKILL). La solución fue separar la recarga en dos tareas: primero obtener el PID con `pgrep sshd` y luego ejecutar `kill -HUP` sobre ese PID, recargando la configuración sin matar el proceso principal.

### Verificación

```bash
ssh root@192.168.100.10
# Contraseña: laboratorio
# Resultado: acceso correcto al contenedor ssh01
```

---

## 3. Bloque 4.2 — Servidor DNS (`dns01`) {#dns}

### Objetivo
Desplegar BIND9 como servidor DNS autoritativo para la zona `laboratorio.local` con reenvío de consultas externas.

### Ficheros creados

| Fichero | Descripción |
|---|---|
| `roles/dns/files/Dockerfile` | Imagen Ubuntu 24.04 con BIND9 y bind9utils |
| `roles/dns/files/db.laboratorio.local` | Zona DNS directa del laboratorio |
| `roles/dns/files/db.192.168.100` | Zona DNS inversa |
| `roles/dns/templates/named.conf.j2` | Plantilla de configuración BIND9 |
| `roles/dns/tasks/main.yml` | Tareas Ansible de despliegue |

### Configuración aplicada

- Zona autoritativa: `laboratorio.local`
- Forwarders: `8.8.8.8` y `1.1.1.1` para resolución externa
- `allow-query`: restringido a `192.168.100.0/24` y localhost
- `allow-transfer: none` — transferencias de zona deshabilitadas por seguridad
- Resolución inversa habilitada (`100.168.192.in-addr.arpa`)

### Registros DNS configurados

| Nombre | IP |
|---|---|
| `fw01.laboratorio.local` | 192.168.100.2 |
| `ssh01.laboratorio.local` | 192.168.100.10 |
| `dns01.laboratorio.local` | 192.168.100.20 |
| `dhcp01.laboratorio.local` | 192.168.100.30 |

### Verificaciones realizadas

```bash
# Resolución directa
dig @192.168.100.20 ssh01.laboratorio.local +short
# Resultado: 192.168.100.10 ✅

# Resolución inversa
dig @192.168.100.20 -x 192.168.100.10 +short
# Resultado: ssh01.laboratorio.local. ✅

# Resolución externa
dig @192.168.100.20 google.com +short
# Resultado: 216.58.205.46 ✅
```

---

## 4. Bloque 4.3 — Servidor DHCP (`dhcp01`) {#dhcp}

### Objetivo
Desplegar ISC DHCP Server para asignación dinámica de IPs a clientes de la LAN.

### Ficheros creados

| Fichero | Descripción |
|---|---|
| `roles/dhcp/files/Dockerfile` | Imagen Ubuntu 24.04 con ISC DHCP Server |
| `roles/dhcp/templates/dhcpd.conf.j2` | Plantilla de configuración DHCP |
| `roles/dhcp/tasks/main.yml` | Tareas Ansible de despliegue |

### Configuración aplicada

| Parámetro | Valor |
|---|---|
| Subred | 192.168.100.0/24 |
| Rango dinámico | 192.168.100.100 — 192.168.100.200 |
| Gateway | 192.168.100.2 (fw01) |
| DNS | 192.168.100.20 (dns01) |
| Dominio | laboratorio.local |
| Lease time | 86400 segundos (24h) |

### Verificación

```bash
docker run --rm --network lan_net alpine udhcpc -i eth0 -t 5 -n
# Resultado: lease of 192.168.100.100 obtained from 192.168.100.30 ✅
```

El cliente recibió correctamente la primera IP del rango desde `dhcp01` con un tiempo de concesión de 86400 segundos.

---

## 5. Bloque 4.4 — Actualización de site.yml {#siteyml}

Se activó el Play 3 en `site.yml`, añadiendo los tres roles de servicios LAN con el patrón `hosts: localhost / connection: local` consistente con los plays anteriores.

```yaml
- name: "Despliegue de servicios LAN"
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - ssh
    - dns
    - dhcp
```

---

## 6. Verificaciones realizadas {#verificaciones}

### Resultado final del playbook

```
PLAY RECAP
localhost: ok=40  changed=13  unreachable=0  failed=0  skipped=0
Playbook run took 0 days, 0 hours, 0 minutes, 21 seconds
```

### Contenedores activos tras la Fase 4

| Contenedor | Imagen | IP | Puerto | Estado |
|---|---|---|---|---|
| `fw01` | tfg/firewall:latest | 172.20.0.2 / 192.168.100.2 | — | Up |
| `ssh01` | tfg/ssh:latest | 192.168.100.10 | 22/tcp | Up |
| `dns01` | tfg/dns:latest | 192.168.100.20 | 53/tcp, 53/udp | Up |
| `dhcp01` | tfg/dhcp:latest | 192.168.100.30 | 67/udp | Up |

---

## 7. Incidencias y resoluciones {#incidencias}

### Incidencia 1 — Error rc=137 al reiniciar SSH

**Descripción:** La tarea `service ssh restart` dentro del contenedor devolvía `rc=137` (SIGKILL). El proceso sshd es el CMD principal del contenedor y Docker lo reiniciaba al detectar su muerte, interrumpiendo el comando.

**Resolución:** Separar la recarga en dos tareas independientes:
1. `pgrep sshd` para obtener el PID del proceso
2. `kill -HUP <PID>` para recargar la configuración sin matar el proceso

### Incidencia 2 — Ejecución desde directorio incorrecto

**Descripción:** En la primera ejecución el Play 3 no apareció en la salida porque el playbook se ejecutó desde `~/tfg-laboratorio-red` en lugar de `/media/abel/ABEL_2/tfg-laboratorio-red`.

**Resolución:** Verificar siempre el directorio de trabajo antes de ejecutar con `pwd`. El proyecto reside en el disco externo `/media/abel/ABEL_2/tfg-laboratorio-red`.

---

## 8. Estado final del laboratorio {#estado}

### Limitación conocida y documentada

El host tiene acceso directo a todas las redes Docker (`wan_net`, `dmz_net`, `lan_net`) a través de los bridges que Docker crea automáticamente. Esto significa que el tráfico desde el propio host hacia cualquier contenedor no pasa por `fw01`.

Esta es una limitación estructural de Docker en modo bridge sobre un único host. En un entorno de producción real se resolvería con hardware dedicado o mediante reglas `iptables DOCKER-USER` en el host. Se documenta como limitación conocida en la memoria del TFG.

**El firewall `fw01` sí controla:**
- Tráfico entre contenedores de distintas redes
- Tráfico WAN → LAN entre zonas
- NAT/Masquerade para salida a internet desde la LAN

**El firewall `fw01` no controla:**
- Tráfico originado desde el propio host hacia cualquier red

---

*Documento generado en Abril 2026 — Fase 4 completada*
