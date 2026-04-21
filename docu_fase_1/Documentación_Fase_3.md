# Documentación Técnica — TFG Laboratorio de Red
## Ciclo Superior ASIR — Administración de Sistemas Informáticos en Red

**Autor:** Abel  
**Proyecto:** Laboratorio de red empresarial con Docker y Ansible sobre Ubuntu 24.04  
**Estado:** Fases 0–3 completadas  

---

## Índice

1. [Fase 0 — Diseño y arquitectura](#fase-0)
2. [Fase 1 — Preparación del entorno](#fase-1)
3. [Fase 2 — Creación de redes Docker](#fase-2)
4. [Fase 3 — Despliegue del firewall](#fase-3)
5. [Estructura completa del proyecto](#estructura)
6. [Referencia de comandos utilizados](#comandos)

---

## Fase 0 — Diseño y arquitectura {#fase-0}

### Objetivo

Diseñar la arquitectura de red del laboratorio antes de escribir ningún código. En un entorno profesional, esta fase equivale a la etapa de diseño de infraestructura que precede a cualquier despliegue.

### Arquitectura de tres zonas

El laboratorio simula un entorno empresarial real con tres zonas de seguridad diferenciadas:

```
Internet
    │
    ▼
┌─────────────────────────────────┐
│  ZONA WAN — 172.20.0.0/24       │
│  Red bridge Docker (wan_net)    │
│  Simula la salida a internet    │
└──────────────┬──────────────────┘
               │ eth0: 172.20.0.2
               ▼
┌─────────────────────────────────┐
│  ZONA DMZ — 172.21.0.0/24       │
│  Contenedor: fw01               │
│  Firewall/Router con nftables   │
└──────────────┬──────────────────┘
               │ eth1: 192.168.100.2
               ▼
┌─────────────────────────────────────────────────────┐
│  ZONA LAN — 192.168.100.0/24                        │
│                                                     │
│  ssh01: 192.168.100.10  (OpenSSH Server)            │
│  dns01: 192.168.100.20  (BIND9 / dnsmasq)           │
│  dhcp01: 192.168.100.30 (ISC DHCP Server)           │
│  web01:  192.168.100.40 (Nginx) — opcional          │
│  mon01:  192.168.100.50 (Prometheus+Grafana) — opc  │
└─────────────────────────────────────────────────────┘
```

### Por qué Docker y no máquinas virtuales

Los contenedores Docker utilizan **namespaces de red del kernel Linux**, que son redes reales, no simuladas. Cada contenedor tiene su propio stack de red aislado. Esto permite:

- Menor consumo de RAM y CPU que las VMs (los contenedores comparten el kernel del host)
- Despliegue reproducible y automatizable con Ansible
- Redes virtuales con comportamiento idéntico a redes físicas

En un entorno profesional real, esta misma arquitectura se implementaría con:
- **WAN**: Línea dedicada de ISP con router de borde (Cisco ASR, Juniper MX)
- **DMZ**: VLAN dedicada con firewall físico (Fortinet FortiGate, Palo Alto) o virtual (pfSense, OPNsense)
- **LAN**: VLANs por departamento con switches gestionados (Cisco Catalyst)
- **En AWS**: VPC con subredes públicas (DMZ) y privadas (LAN), Internet Gateway y Security Groups

### Tabla de direccionamiento

| Dispositivo | Interfaz | Red | IP | Función |
|-------------|----------|-----|----|---------|
| Host Ubuntu | wlp0s20f3 | física | DHCP ISP | Acceso a internet |
| Host Ubuntu | docker0 | bridge | 172.17.0.1 | Bridge por defecto de Docker |
| fw01 | eth0 | wan_net | 172.20.0.2 | Cara exterior del firewall |
| fw01 | eth1 | lan_net | 192.168.100.2 | Cara interior / gateway LAN |
| ssh01 | eth0 | lan_net | 192.168.100.10 | Servidor SSH |
| dns01 | eth0 | lan_net | 192.168.100.20 | Servidor DNS |
| dhcp01 | eth0 | lan_net | 192.168.100.30 | Servidor DHCP |

### Política de seguridad del firewall

| Origen | Destino | Política | Motivo |
|--------|---------|----------|--------|
| WAN | LAN | DROP (bloquear) | Nadie de fuera accede a la red interna sin permiso explícito |
| LAN | WAN | ACCEPT + NAT | Los servicios internos pueden actualizar paquetes y acceder a internet |
| LAN | LAN | ACCEPT | Tráfico interno libre entre servicios |
| WAN | Firewall | DROP excepto SSH | Solo administración remota permitida |

### Requisitos del host verificados

| Recurso | Valor detectado | Requisito mínimo | Estado |
|---------|----------------|-----------------|--------|
| SO | Ubuntu 24.04.4 LTS | Ubuntu 24.04 | ✅ |
| Kernel | 6.14.0-37-generic | 6.x | ✅ |
| RAM | 7.5 GB (4.5 GB libres) | 4 GB | ✅ |
| Disco | 24 GB libres | 20 GB | ✅ |
| CPU | 4 cores | 2 cores | ✅ |
| ip_forward | 1 (habilitado) | 1 | ✅ |
| Interfaz red | wlp0s20f3 (WiFi) | cualquiera | ✅ |

---

## Fase 1 — Preparación del entorno {#fase-1}

### Objetivo

Instalar y configurar todas las herramientas necesarias, y crear la estructura de directorios del proyecto siguiendo el estándar oficial de Ansible.

### Software instalado y verificado

| Herramienta | Versión | Función |
|-------------|---------|---------|
| Docker Engine | 29.3.0 | Motor de contenedores |
| Docker Compose | v5.1.0 | Orquestación local (para pruebas manuales) |
| Ansible | 2.16.3 | Automatización del despliegue completo |
| Python | 3.12.3 | Dependencia de Ansible |
| Git | (preinstalado) | Control de versiones del proyecto |

### Extensiones de VS Code instaladas

```bash
code --install-extension ms-azuretools.vscode-docker   # Panel visual de Docker
code --install-extension redhat.ansible                # Syntax highlighting Ansible
code --install-extension redhat.vscode-yaml            # Validación YAML
code --install-extension eamodio.gitlens               # Gestión Git visual
code --install-extension mikestead.dotenv              # Ficheros .env
```

### Estructura del proyecto

```
~/tfg-laboratorio-red/
│
├── ansible.cfg                    # Configuración global de Ansible
├── site.yml                       # Playbook maestro (punto de entrada)
├── .gitignore                     # Ficheros excluidos del repositorio Git
│
├── inventario/
│   └── hosts.yml                  # Inventario de hosts gestionados por Ansible
│
├── group_vars/
│   ├── all/
│   │   └── main.yml               # Variables globales (IPs, nombres, subredes)
│   └── firewall/
│       └── main.yml               # Variables específicas del firewall
│
├── roles/
│   ├── redes/
│   │   └── tasks/
│   │       └── main.yml           # Tareas: crear redes Docker WAN/DMZ/LAN
│   ├── firewall/
│   │   ├── tasks/
│   │   │   └── main.yml           # Tareas: desplegar fw01 y aplicar nftables
│   │   └── files/
│   │       ├── Dockerfile         # Imagen personalizada del firewall
│   │       └── nftables.conf      # Reglas del firewall
│   ├── ssh/
│   │   ├── tasks/                 # (Fase 4)
│   │   └── templates/             # (Fase 4)
│   ├── dns/
│   │   ├── tasks/                 # (Fase 4)
│   │   ├── templates/             # (Fase 4)
│   │   └── files/                 # (Fase 4)
│   └── dhcp/
│       ├── tasks/                 # (Fase 4)
│       └── templates/             # (Fase 4)
│
├── pruebas/                       # Scripts de validación (Fase 6)
└── docs/                          # Capturas y diagramas para la memoria
```

Esta estructura sigue el **Ansible Best Practices** oficial. En proyectos open source y empresas reales, esta es la organización estándar.

### Descripción detallada de cada fichero

#### `ansible.cfg`

Fichero de configuración global de Ansible para este proyecto. Sin este fichero, Ansible usa valores por defecto del sistema que pueden no ser adecuados.

```ini
[defaults]
inventory = inventario/hosts.yml      # Dónde está el inventario
host_key_checking = False             # No verificar clave SSH (solo en laboratorio)
stdout_callback = yaml                # Salida más legible
remote_tmp = /tmp/.ansible/tmp        # Ficheros temporales en hosts gestionados
callbacks_enabled = timer, profile_tasks  # Mostrar tiempos de ejecución

[ssh_connection]
pipelining = True                     # Reutilizar sesiones SSH (más rápido)
```

> **Nota de seguridad**: `host_key_checking = False` es aceptable en un laboratorio controlado, pero en producción siempre debe ser `True` para prevenir ataques MITM (Man In The Middle).

#### `inventario/hosts.yml`

Define qué "máquinas" gestiona Ansible y cómo conectarse a ellas. Es el equivalente a una lista de servidores en un CPD real.

```yaml
all:
  children:
    host_docker:          # El propio host Ubuntu
      hosts:
        localhost:
          ansible_connection: local   # Sin SSH, ejecuta comandos localmente
    firewall:             # Contenedor fw01
      hosts:
        fw01:
          ansible_connection: docker  # Ansible se conecta via "docker exec"
    servicios_lan:        # Contenedores de servicios
      hosts:
        ssh01:
          ansible_connection: docker
        dns01:
          ansible_connection: docker
        dhcp01:
          ansible_connection: docker
```

La clave `ansible_connection: docker` le dice a Ansible que en lugar de conectarse por SSH, use `docker exec` para ejecutar comandos dentro del contenedor. Esto es más eficiente y no requiere que el contenedor tenga SSH configurado.

#### `group_vars/all/main.yml`

Variables globales accesibles por todos los roles. Centralizar las IPs y nombres aquí significa que si necesitas cambiar una IP, solo lo haces en un sitio y afecta a todo el proyecto automáticamente.

```yaml
redes:
  wan:
    nombre: wan_net
    subnet: "172.20.0.0/24"
    gateway: "172.20.0.1"
  dmz:
    nombre: dmz_net
    subnet: "172.21.0.0/24"
    gateway: "172.21.0.1"
  lan:
    nombre: lan_net
    subnet: "192.168.100.0/24"
    gateway: "192.168.100.1"

contenedores:
  firewall:
    nombre: fw01
    ip_wan: "172.20.0.2"
    ip_lan: "192.168.100.2"
  ssh:
    nombre: ssh01
    ip: "192.168.100.10"
  dns:
    nombre: dns01
    ip: "192.168.100.20"
  dhcp:
    nombre: dhcp01
    ip: "192.168.100.30"

host_interfaz_red: "wlp0s20f3"
imagen_base: "ubuntu:24.04"
```

#### `group_vars/firewall/main.yml`

Variables específicas del grupo `firewall`. Permite configurar el firewall de forma diferente al resto de contenedores.

#### `.gitignore`

Excluye del repositorio Git los ficheros innecesarios o sensibles:
- `*.retry`: ficheros de reintento de Ansible
- `vault_pass.txt`: contraseñas de Ansible Vault (nunca deben subirse a Git)
- `*.log`: logs de ejecución

---

## Fase 2 — Creación de redes Docker {#fase-2}

### Objetivo

Crear las tres redes Docker (WAN, DMZ, LAN) de forma automatizada con Ansible, usando el módulo `community.docker`.

### Concepto clave: Idempotencia

Una tarea de Ansible es **idempotente** cuando puede ejecutarse múltiples veces y el resultado siempre es el mismo. Si la red ya existe, Ansible no la borra y la recrea, sino que detecta que ya está en el estado deseado y no hace nada. Esto es fundamental para la automatización: puedes ejecutar el playbook N veces sin miedo a romper nada.

```
Primera ejecución:  changed=3  (crea las 3 redes)
Segunda ejecución:  ok=3       (detecta que ya existen, no hace nada)
```

### Instalación de la colección Docker

```bash
ansible-galaxy collection install community.docker
```

Las **colecciones** son paquetes de módulos adicionales para Ansible, equivalentes a librerías en programación. `community.docker` proporciona los módulos `docker_network`, `docker_container`, `docker_image`, etc.

### `roles/redes/tasks/main.yml`

```yaml
---
- name: "Crear red WAN ({{ redes.wan.nombre }})"
  community.docker.docker_network:
    name: "{{ redes.wan.nombre }}"
    driver: bridge
    ipam_config:
      - subnet: "{{ redes.wan.subnet }}"
        gateway: "{{ redes.wan.gateway }}"
    state: present    # "present" = crear si no existe, no hacer nada si ya existe

- name: "Crear red DMZ ({{ redes.dmz.nombre }})"
  community.docker.docker_network:
    name: "{{ redes.dmz.nombre }}"
    driver: bridge
    ipam_config:
      - subnet: "{{ redes.dmz.subnet }}"
        gateway: "{{ redes.dmz.gateway }}"
    state: present

- name: "Crear red LAN ({{ redes.lan.nombre }})"
  community.docker.docker_network:
    name: "{{ redes.lan.nombre }}"
    driver: bridge
    ipam_config:
      - subnet: "{{ redes.lan.subnet }}"
        gateway: "{{ redes.lan.gateway }}"
    state: present

- name: "Listar redes Docker existentes"
  ansible.builtin.command: docker network ls --filter driver=bridge
  register: lista_redes
  changed_when: false   # Este comando nunca modifica nada

- name: "Mostrar redes del laboratorio"
  ansible.builtin.debug:
    msg: "{{ lista_redes.stdout_lines }}"
```

**Por qué `docker_network` y no `docker network create` en bash:**
El módulo es idempotente. El comando bash falla si la red ya existe. En automatización, los errores evitables son inaceptables.

### `site.yml` (versión Fase 2)

El **playbook maestro** es el punto de entrada de toda la automatización. Se va ampliando fase a fase:

```yaml
---
- name: "Despliegue de redes Docker del laboratorio"
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - redes
```

### Resultado verificado

```
NETWORK ID     NAME      DRIVER    SCOPE
23c180820bee   bridge    bridge    local   ← red por defecto de Docker
b0c99d208996   dmz_net   bridge    local   ← creada por Ansible ✅
53aebb6b2dbc   lan_net   bridge    local   ← creada por Ansible ✅
c0491654ba62   wan_net   bridge    local   ← creada por Ansible ✅
```

### ¿Por qué bridge y no otros drivers?

Docker soporta varios drivers de red:
- **bridge** (usado aquí): red aislada en el host, perfecta para laboratorio en un solo host
- **overlay**: para clusters multi-host (Docker Swarm, Kubernetes)
- **host**: el contenedor comparte directamente la interfaz del host (sin aislamiento)
- **macvlan**: asigna MAC propia al contenedor, para integrarse con redes físicas

Para un laboratorio en un único host, `bridge` es siempre la elección correcta.

---

## Fase 3 — Despliegue del firewall {#fase-3}

### Objetivo

Desplegar el contenedor `fw01` como router/firewall con reglas `nftables` que controlen el tráfico entre las tres zonas.

### ¿Por qué un contenedor puede ser un firewall?

Un contenedor Docker es un proceso Linux con su propio **namespace de red**. Al conectarlo a múltiples redes Docker tiene múltiples interfaces de red (igual que un router físico). Con `ip_forward` habilitado puede reenviar paquetes entre interfaces, y con `nftables` controlamos exactamente qué tráfico se permite.

Esto replica el comportamiento de un firewall empresarial (Fortinet, Palo Alto, Cisco ASA) usando únicamente herramientas nativas del kernel Linux.

### `roles/firewall/files/Dockerfile`

Imagen Docker personalizada basada en Ubuntu 24.04 con las herramientas de red necesarias:

```dockerfile
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nftables \       # Firewall moderno del kernel Linux (sucesor de iptables)
    iproute2 \       # Comandos ip, ss para diagnóstico de red
    iputils-ping \   # Comando ping para pruebas de conectividad
    dnsutils \       # Comando dig para pruebas DNS
    curl \           # Pruebas HTTP
    net-tools \      # Comandos clásicos: netstat, ifconfig
    openssh-server \ # Para conexiones SSH de administración
    && rm -rf /var/lib/apt/lists/*

RUN echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
RUN mkdir -p /etc/nftables

CMD ["tail", "-f", "/dev/null"]
```

**¿Por qué `CMD ["tail", "-f", "/dev/null"]`?**  
Los contenedores Docker se detienen cuando su proceso principal termina. Como el firewall no tiene un servicio en primer plano (nftables se carga en el kernel, no corre como proceso), usamos `tail -f /dev/null` para mantener el contenedor vivo indefinidamente. En producción se usaría un supervisor de procesos como `s6-overlay` o `supervisord`.

**¿Por qué `--rm -rf /var/lib/apt/lists/*`?**  
Elimina la caché de APT después de instalar los paquetes. Reduce el tamaño de la imagen final considerablemente (los índices de APT pueden ocupar varios cientos de MB).

### `roles/firewall/files/nftables.conf`

Fichero de reglas del firewall. Define la política de seguridad completa del laboratorio:

```
#!/usr/sbin/nft -f

flush ruleset    # Borra todas las reglas anteriores antes de aplicar las nuevas
                 # Garantiza que el estado siempre sea exactamente el definido aquí

table inet filter {      # "inet" aplica tanto a IPv4 como IPv6

    chain input {        # Tráfico destinado AL PROPIO FIREWALL
        type filter hook input priority 0; policy drop;  # Política por defecto: DROP

        iif "lo" accept                        # Loopback siempre permitido
        ct state established,related accept    # Conexiones ya establecidas (stateful)
        icmp type echo-request accept          # Ping permitido (diagnóstico)
        iif "eth1" tcp dport 22 accept         # SSH solo desde la LAN
        reject with icmp admin-prohibited      # Todo lo demás: rechazar con ICMP
    }

    chain forward {      # Tráfico que ATRAVIESA el firewall (entre redes)
        type filter hook forward priority 0; policy drop;

        ct state established,related accept    # Conexiones establecidas: siempre permitir
        iif "eth1" oif "eth0" accept           # LAN → WAN: permitido (con NAT)
        # WAN → LAN: bloqueado por la política DROP del chain
    }

    chain output {       # Tráfico generado POR el firewall
        type filter hook output priority 0; policy accept;  # Todo permitido
    }
}

table inet nat {

    chain prerouting {   # DNAT: redirigir puertos entrantes
        type nat hook prerouting priority -100;
        # Aquí se añadirán reglas de port-forwarding en fases posteriores
    }

    chain postrouting {  # SNAT/Masquerade: modificar IPs salientes
        type nat hook postrouting priority 100;
        oif "eth0" masquerade    # NAT: los paquetes de LAN que salen por WAN
                                  # usan la IP del firewall como origen
    }
}
```

**Diferencia entre `drop` y `reject`:**
- `drop`: descarta el paquete silenciosamente. El origen no sabe si el paquete llegó.
- `reject`: envía un ICMP de "admin-prohibited" al origen. El origen sabe inmediatamente que fue bloqueado y no espera timeout.

En el `chain input` usamos `reject` para que las conexiones no autorizadas fallen rápido. En el `chain forward` la política `drop` es más adecuada (no revelar información sobre la red interna).

**¿Qué es `ct state established,related`?**  
`ct` = connection tracking. Esta regla implementa el firewall **stateful**: si una conexión fue iniciada desde dentro y aceptada, los paquetes de respuesta se permiten automáticamente sin necesidad de reglas explícitas de retorno. Sin esto, necesitaríamos reglas simétricas para cada conexión.

**¿Qué es `masquerade`?**  
Es NAT dinámico. Cuando un paquete de la LAN (192.168.100.x) sale por eth0 (WAN), el firewall reemplaza la IP origen con su propia IP WAN (172.20.0.2). Cuando llega la respuesta, el firewall sabe a quién reenviarla gracias al connection tracking. Esto permite que múltiples dispositivos internos compartan una única IP pública.

### `roles/firewall/tasks/main.yml`

```yaml
---
- name: "Construir imagen Docker del firewall"
  community.docker.docker_image:
    name: "tfg/firewall"
    tag: "latest"
    build:
      path: "{{ role_path }}/files"    # Directorio con el Dockerfile
      dockerfile: "Dockerfile"
    source: build
    force_source: false    # No reconstruir si la imagen ya existe (idempotencia)

- name: "Desplegar contenedor fw01"
  community.docker.docker_container:
    name: "{{ contenedores.firewall.nombre }}"
    image: "tfg/firewall:latest"
    state: started
    restart_policy: unless-stopped    # Reiniciar automáticamente si el host reinicia
    capabilities:
      - NET_ADMIN      # Permite modificar interfaces de red y reglas de firewall
      - SYS_MODULE     # Permite cargar módulos del kernel (necesario para nftables)
    volumes:
      - /lib/modules:/lib/modules:ro  # Acceso de solo lectura a módulos del kernel
    networks:
      - name: "{{ redes.wan.nombre }}"
        ipv4_address: "{{ contenedores.firewall.ip_wan }}"    # IP fija en WAN
      - name: "{{ redes.lan.nombre }}"
        ipv4_address: "{{ contenedores.firewall.ip_lan }}"    # IP fija en LAN

- name: "Copiar reglas nftables al contenedor"
  ansible.builtin.command: >
    docker cp {{ role_path }}/files/nftables.conf
    {{ contenedores.firewall.nombre }}:/etc/nftables/nftables.conf

- name: "Aplicar reglas nftables"
  ansible.builtin.command: >
    docker exec {{ contenedores.firewall.nombre }}
    nft -f /etc/nftables/nftables.conf

- name: "Verificar ruleset activo"
  ansible.builtin.command: >
    docker exec {{ contenedores.firewall.nombre }} nft list ruleset
  register: ruleset
  changed_when: false

- name: "Mostrar ruleset"
  ansible.builtin.debug:
    msg: "{{ ruleset.stdout_lines }}"
```

**¿Por qué `NET_ADMIN` y `SYS_MODULE`?**  
Por defecto, los contenedores Docker tienen capacidades limitadas por seguridad. `NET_ADMIN` es necesario para que nftables pueda instalar reglas en el kernel. Sin esta capacidad, el comando `nft` falla con "Permission denied". `SYS_MODULE` permite cargar los módulos de kernel que nftables necesita (nf_tables, etc.).

**¿Por qué montar `/lib/modules`?**  
nftables necesita acceder a los módulos del kernel del host para cargar las extensiones de filtrado (conntrack, nat, etc.). Al montar el directorio como volumen de solo lectura (`:ro`), el contenedor puede leerlos pero no modificarlos.

**Incidencia resuelta — IP del firewall en la LAN:**  
La IP `192.168.100.1` está reservada por Docker como gateway de la red `lan_net` y no puede asignarse a un contenedor. Se usó `192.168.100.2` en su lugar, que es la primera IP disponible para hosts en esa subred.

### Resultado verificado

```bash
$ docker exec fw01 ip addr show

eth0: 172.20.0.2/24   ← cara WAN ✅
eth1: 192.168.100.2/24 ← cara LAN ✅

$ ping -c 3 172.20.0.2    → 0% packet loss ✅
$ ping -c 3 192.168.100.1 → 0% packet loss ✅
```

El firewall responde en ambas interfaces y las reglas nftables están activas.

---

## Estructura completa del proyecto {#estructura}

### Estado actual de ficheros

```
~/tfg-laboratorio-red/
├── ansible.cfg
├── site.yml
├── .gitignore
├── inventario/
│   └── hosts.yml
├── group_vars/
│   ├── all/
│   │   └── main.yml
│   └── firewall/
│       └── main.yml
└── roles/
    ├── redes/
    │   └── tasks/
    │       └── main.yml
    └── firewall/
        ├── tasks/
        │   └── main.yml
        └── files/
            ├── Dockerfile
            └── nftables.conf
```

### `site.yml` — estado actual

```yaml
---
- name: "Despliegue de redes Docker del laboratorio"
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - redes

- name: "Despliegue del firewall"
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - firewall

# Pendiente Fase 4:
# - name: "Despliegue de servicios LAN"
#   hosts: servicios_lan
#   roles:
#     - ssh
#     - dns
#     - dhcp
```

---

## Referencia de comandos utilizados {#comandos}

### Diagnóstico del sistema

```bash
# Ver versión y detalles del SO
cat /etc/os-release

# Ver memoria RAM disponible
free -h

# Ver espacio en disco
df -h /

# Ver número de cores de CPU
nproc

# Ver versión del kernel
uname -r

# Ver si el reenvío de paquetes IP está habilitado (debe ser 1)
cat /proc/sys/net/ipv4/ip_forward

# Ver interfaces de red del sistema
ip link show

# Ver el usuario actual
whoami

# Ver grupos del usuario (verificar que 'docker' está incluido)
groups $USER
```

### Docker

```bash
# Ver versión de Docker
docker --version

# Ver versión de Docker Compose
docker compose version

# Ver estado del servicio Docker
sudo systemctl status docker --no-pager

# Listar contenedores en ejecución
docker ps

# Listar todas las redes Docker
docker network ls

# Ver detalles de una red específica
docker network inspect lan_net

# Ver el gateway de una red
docker network inspect lan_net | grep Gateway

# Ejecutar un comando dentro de un contenedor
docker exec fw01 ip addr show

# Ver las interfaces de red de un contenedor
docker exec fw01 ip addr show

# Ver las reglas nftables de un contenedor
docker exec fw01 nft list ruleset

# Eliminar un contenedor forzosamente (usado al corregir la IP del firewall)
docker rm -f fw01

# Copiar un fichero del host a un contenedor
docker cp /ruta/local contenedor:/ruta/destino
```

### Ansible

```bash
# Ver versión de Ansible
ansible --version

# Instalar una colección de módulos adicionales
ansible-galaxy collection install community.docker

# Ver colecciones instaladas
ansible-galaxy collection list | grep docker

# Ejecutar el playbook en modo simulación (sin hacer cambios reales)
ansible-playbook site.yml --check

# Ejecutar el playbook
ansible-playbook site.yml

# Ejecutar el playbook con salida detallada (para depurar errores)
ansible-playbook site.yml -v       # verbose
ansible-playbook site.yml -vvv     # muy verbose (muestra cada tarea al detalle)
```

### Git

```bash
# Ver el estado del repositorio
git status

# Añadir todos los cambios al área de staging
git add .

# Crear un commit
git commit -m "mensaje descriptivo"

# Ver el historial de commits
git log --oneline

# Ver qué hay en el proyecto (ficheros y directorios)
find . -not -path './.git/*' -type f | sort
```

### VS Code

```bash
# Instalar una extensión desde la terminal
code --install-extension nombre.extension

# Abrir el proyecto en VS Code desde la terminal
code .
```

---

## Historial de incidencias y soluciones

### Incidencia 1: Error en tarea de verificación de redes (Fase 2)

**Error:** `'None' has no attribute 'Name'`  
**Causa:** El módulo `community.docker.docker_network_info` devuelve la estructura de datos en un formato diferente al esperado según la versión instalada.  
**Solución:** Reemplazar la verificación con `docker network ls --filter driver=bridge`, un comando más simple y robusto.

### Incidencia 2: Conflicto de sintaxis con templates Go en YAML (Fase 3)

**Error:** `mapping values are not allowed in this context` al usar `{{.Names}}` en comandos Docker dentro de YAML.  
**Causa:** Ansible interpreta cualquier `{{` como inicio de una variable Jinja2, aunque esté dentro de un string que debería pasarse literalmente a Docker.  
**Solución:** Evitar completamente el uso de templates de Go (`{{.Field}}`) en ficheros YAML de Ansible. Usar `docker ps --filter name=fw01` sin formato personalizado.

### Incidencia 3: IP del firewall en conflicto con el gateway de Docker (Fase 3)

**Error:** `Address already in use` al intentar asignar `192.168.100.1` al contenedor fw01.  
**Causa:** Docker reserva automáticamente la primera IP de cada subred como gateway de la red virtual. En `192.168.100.0/24`, la IP `192.168.100.1` es el gateway de `lan_net` y no puede asignarse a ningún contenedor.  
**Solución:** Usar `192.168.100.2` como IP del firewall en la LAN, actualizando la variable `contenedores.firewall.ip_lan` en `group_vars/all/main.yml`.

---

*Documentación generada durante el desarrollo del TFG — Fases 0 a 3 completadas*  
*Próximas fases: 4 (servicios LAN), 5 (optimización Ansible), 6 (pruebas), 7 (memoria)*
