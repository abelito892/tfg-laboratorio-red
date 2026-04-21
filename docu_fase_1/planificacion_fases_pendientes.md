# Planificación — Fases Pendientes y Variantes
## TFG Laboratorio de Red — ASIR

**Autor:** Abel  
**Fecha:** Marzo 2026  
**Estado del proyecto:** Fases 0–3 completadas ✅

---

## Índice

1. [Resumen del estado actual](#estado-actual)
2. [Fase 4 — Servicios LAN](#fase-4)
3. [Fase 5 — Optimización Ansible](#fase-5)
4. [Fase 6 — Pruebas y hardening](#fase-6)
5. [Fase 7 — Memoria del TFG](#fase-7)
6. [Variante: Red de monitorización centralizada](#variante)

---

## 1. Resumen del estado actual {#estado-actual}

### Completado ✅

| Fase | Descripción | Resultado |
|------|-------------|-----------|
| Fase 0 | Diseño de arquitectura, tabla de direccionamiento, política de seguridad | Documentado |
| Fase 1 | Host Ubuntu 24.04, Docker 29.3, Ansible 2.16, estructura del proyecto | Operativo |
| Fase 2 | Redes Docker WAN/DMZ/LAN creadas con Ansible | `wan_net`, `dmz_net`, `lan_net` activas |
| Fase 3 | Contenedor `fw01` con reglas nftables, NAT, stateful firewall | Operativo en `172.20.0.2` / `192.168.100.2` |

### Pendiente ⏳

- Fase 4: Servicios SSH, DNS, DHCP en la LAN
- Fase 5: Optimización y pulido de Ansible
- Fase 6: Pruebas automatizadas y hardening
- Fase 7: Redacción de la memoria del TFG

---

## 2. Fase 4 — Servicios LAN {#fase-4}

### Objetivo

Desplegar los tres servicios de red core en la zona LAN, cada uno en su propio contenedor con IP fija.

### Servicios a desplegar

| Contenedor | IP | Servicio | Puerto |
|------------|-----|---------|--------|
| `ssh01` | 192.168.100.10 | OpenSSH Server | 22/TCP |
| `dns01` | 192.168.100.20 | BIND9 | 53/UDP y TCP |
| `dhcp01` | 192.168.100.30 | ISC DHCP Server | 67/UDP |

---

### Bloque 4.1 — Servidor SSH (`ssh01`)

**Qué hay que hacer:**

- Crear `roles/ssh/files/Dockerfile` con OpenSSH instalado y configurado
- Crear `roles/ssh/tasks/main.yml` con las tareas Ansible de despliegue
- Crear `roles/ssh/templates/sshd_config.j2` plantilla de configuración SSH
- Desplegar el contenedor en la LAN con IP fija `192.168.100.10`
- Verificar que se puede conectar por SSH desde el host

**Configuración prevista de SSH:**
- Usuario root con contraseña (laboratorio)
- Autenticación por clave pública como alternativa
- Puerto 22 estándar
- Acceso restringido a la red LAN (el firewall ya bloquea acceso directo desde WAN)

**Verificación:**
```bash
ssh root@192.168.100.10
```

---

### Bloque 4.2 — Servidor DNS (`dns01`)

**Qué hay que hacer:**

- Crear `roles/dns/files/Dockerfile` con BIND9 instalado
- Crear `roles/dns/tasks/main.yml` con las tareas Ansible
- Crear `roles/dns/templates/named.conf.j2` configuración principal de BIND9
- Crear `roles/dns/files/db.laboratorio.local` zona DNS del laboratorio
- Desplegar el contenedor en la LAN con IP fija `192.168.100.20`
- Registrar los nombres de todos los contenedores en la zona DNS

**Zona DNS prevista (`laboratorio.local`):**
```
fw01.laboratorio.local    → 192.168.100.2
ssh01.laboratorio.local   → 192.168.100.10
dns01.laboratorio.local   → 192.168.100.20
dhcp01.laboratorio.local  → 192.168.100.30
```

**Verificación:**
```bash
dig @192.168.100.20 ssh01.laboratorio.local
```

---

### Bloque 4.3 — Servidor DHCP (`dhcp01`)

**Qué hay que hacer:**

- Crear `roles/dhcp/files/Dockerfile` con ISC DHCP Server instalado
- Crear `roles/dhcp/tasks/main.yml` con las tareas Ansible
- Crear `roles/dhcp/templates/dhcpd.conf.j2` configuración del servidor DHCP
- Desplegar el contenedor en la LAN con IP fija `192.168.100.30`
- Configurar el rango de asignación dinámica y el DNS como opción

**Configuración DHCP prevista:**
```
Subred:        192.168.100.0/24
Rango:         192.168.100.100 – 192.168.100.200
Gateway:       192.168.100.1
DNS:           192.168.100.20
Dominio:       laboratorio.local
Lease time:    86400 segundos (24h)
```

**Verificación:**
- Arrancar un contenedor cliente sin IP fija y verificar que recibe una del rango DHCP

---

### Bloque 4.4 — Actualizar `site.yml`

Añadir el Play 3 con los servicios LAN:

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

## 3. Fase 5 — Optimización Ansible {#fase-5}

### Objetivo

Pulir la automatización para que sea robusta, legible y profesional. Esta fase no añade funcionalidad nueva, sino que mejora la calidad del código existente.

### Tareas previstas

**5.1 — Manejo de errores y condiciones**
- Añadir `failed_when` y `ignore_errors` donde sea apropiado
- Añadir validaciones previas (`pre_tasks`) que comprueben el estado del sistema antes de ejecutar

**5.2 — Variables y organización**
- Revisar que todas las IPs y nombres están en `group_vars` y no hardcodeados en los roles
- Añadir variables con valores por defecto en `roles/*/defaults/main.yml`

**5.3 — Handlers**
- Añadir `handlers` para reiniciar servicios solo cuando su configuración cambia
- Ejemplo: si `sshd_config` cambia → reiniciar SSH; si `named.conf` cambia → reiniciar BIND9

**5.4 — Tags**
- Añadir tags a las tareas para poder ejecutar partes del playbook de forma selectiva
- Ejemplo: `ansible-playbook site.yml --tags firewall` solo ejecuta el rol del firewall

**5.5 — Playbook de destrucción**
- Crear `teardown.yml` que elimine todos los contenedores y redes del laboratorio
- Útil para limpiar el entorno y empezar desde cero en pruebas

```yaml
# teardown.yml — elimina todo el laboratorio
- name: "Destruir laboratorio"
  hosts: localhost
  connection: local
  tasks:
    - name: "Eliminar contenedores"
      community.docker.docker_container:
        name: "{{ item }}"
        state: absent
      loop: [fw01, ssh01, dns01, dhcp01]

    - name: "Eliminar redes"
      community.docker.docker_network:
        name: "{{ item }}"
        state: absent
      loop: [wan_net, dmz_net, lan_net]
```

---

## 4. Fase 6 — Pruebas y hardening {#fase-6}

### Objetivo

Verificar que todo el laboratorio funciona correctamente mediante pruebas sistemáticas, y aplicar medidas de seguridad adicionales (hardening).

### Bloque 6.1 — Batería de pruebas de conectividad

**Pruebas de red:**
```bash
# Ping entre zonas
ping -c 3 172.20.0.2        # Host → Firewall WAN
ping -c 3 192.168.100.2     # Host → Firewall LAN
ping -c 3 192.168.100.10    # Host → SSH
ping -c 3 192.168.100.20    # Host → DNS
ping -c 3 192.168.100.30    # Host → DHCP

# Verificar que LAN puede salir a internet a través del firewall
docker exec ssh01 ping -c 3 8.8.8.8
docker exec dns01 curl -s https://example.com
```

**Pruebas de servicios:**
```bash
# SSH
ssh root@192.168.100.10 "hostname && ip addr show"

# DNS
dig @192.168.100.20 ssh01.laboratorio.local
dig @192.168.100.20 google.com              # Resolución externa

# DHCP
# Arrancar contenedor cliente y verificar IP asignada automáticamente
```

**Pruebas del firewall:**
```bash
# Verificar que WAN NO puede acceder directamente a la LAN
# (debe ser bloqueado)
docker run --rm --network wan_net alpine ping -c 3 192.168.100.10

# Verificar que las reglas nftables están activas
docker exec fw01 nft list ruleset

# Ver contadores de paquetes por regla
docker exec fw01 nft list ruleset -a
```

### Bloque 6.2 — Script de pruebas automáticas

Crear `pruebas/test_laboratorio.sh` que ejecute todas las pruebas y genere un informe:

```bash
#!/bin/bash
# Script de validación automática del laboratorio TFG

PASS=0
FAIL=0

check() {
    local descripcion="$1"
    local comando="$2"
    if eval "$comando" &>/dev/null; then
        echo "✅ PASS: $descripcion"
        ((PASS++))
    else
        echo "❌ FAIL: $descripcion"
        ((FAIL++))
    fi
}

echo "=== Pruebas del laboratorio TFG ==="

check "Contenedor fw01 activo"   "docker ps | grep fw01"
check "Contenedor ssh01 activo"  "docker ps | grep ssh01"
check "Contenedor dns01 activo"  "docker ps | grep dns01"
check "Contenedor dhcp01 activo" "docker ps | grep dhcp01"
check "Red wan_net existe"       "docker network inspect wan_net"
check "Red dmz_net existe"       "docker network inspect dmz_net"
check "Red lan_net existe"       "docker network inspect lan_net"
check "Firewall WAN responde"    "ping -c 1 -W 2 172.20.0.2"
check "Firewall LAN responde"    "ping -c 1 -W 2 192.168.100.2"
check "SSH01 responde"           "ping -c 1 -W 2 192.168.100.10"
check "DNS01 responde"           "ping -c 1 -W 2 192.168.100.20"
check "Reglas nftables activas"  "docker exec fw01 nft list ruleset | grep masquerade"
check "LAN sale a internet"      "docker exec ssh01 ping -c 1 -W 3 8.8.8.8"
check "DNS resuelve interno"     "dig @192.168.100.20 ssh01.laboratorio.local +short"

echo ""
echo "=== Resultado: $PASS pasados, $FAIL fallados ==="
```

### Bloque 6.3 — Hardening de seguridad

**SSH:**
- Deshabilitar autenticación por contraseña en producción (solo claves públicas)
- Cambiar puerto por defecto (22 → otro puerto)
- Limitar usuarios que pueden conectarse

**Firewall (nftables):**
- Añadir límite de tasa (rate limiting) para prevenir fuerza bruta
- Añadir logging de conexiones rechazadas para auditoría
- Revisar que no hay reglas más permisivas de lo necesario

**Docker:**
- Revisar que los contenedores no corren como root innecesariamente
- Verificar que los volúmenes montados son de solo lectura donde sea posible

---

## 5. Fase 7 — Memoria del TFG {#fase-7}

### Estructura recomendada del documento

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
   5.3 Seguridad perimetral y firewalls
   5.4 Servicios de red (DNS, DHCP, SSH)
6. Diseño de la solución
   6.1 Arquitectura del laboratorio
   6.2 Diagrama de red
   6.3 Tabla de direccionamiento
   6.4 Política de seguridad
7. Implementación
   7.1 Preparación del entorno
   7.2 Creación de redes Docker
   7.3 Despliegue del firewall
   7.4 Despliegue de servicios LAN
   7.5 Automatización con Ansible
8. Pruebas y validación
   8.1 Pruebas de conectividad
   8.2 Pruebas de servicios
   8.3 Pruebas de seguridad
9. Conclusiones
   9.1 Objetivos alcanzados
   9.2 Dificultades encontradas
   9.3 Posibles ampliaciones
10. Bibliografía
Anexos
   A. Código fuente completo
   B. Manual de despliegue
   C. Capturas de pantalla
```

### Claves para obtener la máxima nota

- **Incluir contexto profesional**: mencionar equivalentes en AWS, Azure, Kubernetes
- **Documentar las incidencias**: los errores encontrados y cómo se resolvieron demuestran profundidad técnica
- **Justificar las decisiones**: no solo explicar el cómo, sino el por qué de cada elección tecnológica
- **Incluir el diagrama de red** generado durante la Fase 0
- **Capturas de pantalla** de cada fase funcionando
- **Código fuente** completo en los anexos o enlace al repositorio Git

---

## 6. Variante: Red de monitorización centralizada {#variante}

### Descripción de la variante

Esta variante fue propuesta como referencia de un proyecto alternativo. Consiste en añadir una **cuarta red Docker dedicada a observabilidad**, separada de la LAN de servicios.

### Arquitectura de la variante (4 redes)

```
Internet
    │
    ▼
┌─────────────────────────────────┐
│  ZONA WAN — 172.20.0.0/24       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  ZONA DMZ — fw01                │
│  Firewall/Router                │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌─────────────┐  ┌─────────────────────┐
│  ZONA LAN   │  │  ZONA MGMT          │
│  Servicios  │  │  monitor_net        │
│  ssh01      │  │  172.22.0.0/24      │
│  dns01      │  │                     │
│  dhcp01     │  │  logserver01        │
└─────────────┘  │  (Graylog / Loki)   │
                 │                     │
                 │  metrics01          │
                 │  (Prometheus+Graf.) │
                 └─────────────────────┘
```

### Componentes adicionales de la variante

**Red adicional:**
- `monitor_net`: 172.22.0.0/24 — red aislada para tráfico de gestión

**Contenedores adicionales:**

| Contenedor | Servicio | Función |
|------------|---------|---------|
| `logserver01` | Graylog o Loki + Promtail | Centralizar logs de todos los contenedores y del firewall |
| `metrics01` | Prometheus + Grafana | Monitorizar CPU, RAM, red y disco de cada contenedor |

**Integración con los servicios existentes:**
- Cada contenedor de la LAN tendría una segunda interfaz en `monitor_net`
- El firewall enviaría sus logs de nftables al servidor de logs centralizado
- Grafana mostraría dashboards en tiempo real del estado del laboratorio

**Logs que se centralizarían:**
- Logs del firewall nftables (conexiones permitidas y bloqueadas)
- Logs de acceso SSH (quién se conectó, desde dónde, cuándo)
- Logs de queries DNS (qué nombres se resuelven)
- Logs de asignaciones DHCP (qué IP se asignó a qué MAC)
- Métricas de recursos de cada contenedor (CPU, RAM, red, disco)

### Comparativa con el proyecto base

| Aspecto | Proyecto base (3 redes) | Variante (4 redes) |
|---------|------------------------|--------------------|
| Complejidad | Media-alta | Alta |
| Redes Docker | 3 | 4 |
| Contenedores | 4 | 6-7 |
| Observabilidad | Ninguna | Completa |
| Auditoría de accesos | No | Sí |
| Monitorización recursos | No | Sí (Grafana) |
| Logs centralizados | No | Sí (Graylog/Loki) |
| Tiempo estimado adicional | — | +2 semanas |
| Valor académico añadido | — | Alto |

### Decisión actual

**En espera.** De momento el proyecto base cubre el alcance del TFG. Esta variante queda documentada como **posible ampliación** que puede:

- Implementarse en la Fase 6 si hay tiempo disponible
- Mencionarse en la sección "Posibles ampliaciones" de la memoria del TFG (suma puntos sin necesidad de implementarla)
- Servir como referencia para un proyecto futuro o ampliación del TFG

---

*Documento generado en Marzo 2026 — pendiente de actualización conforme avancen las fases*
