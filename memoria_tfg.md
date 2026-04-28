# Memoria del Trabajo de Fin de Grado
## Laboratorio de Red Virtualizado con Docker y Ansible

**Título:** Diseño e implementación de un laboratorio de red virtualizado con Docker y Ansible sobre Ubuntu 24.04

**Autores:**
- Abel Baños
- Daniel Montero
- Amina Sefiani

**Ciclo formativo:** Administración de Sistemas Informáticos en Red (ASIR)  
**Curso:** 2025–2026  
**Fecha de entrega:** Abril 2026

---

## Índice

1. [Introducción](#1-introducción)
2. [Objetivos del proyecto](#2-objetivos-del-proyecto)
3. [Marco teórico](#3-marco-teórico)
4. [Diseño de la solución](#4-diseño-de-la-solución)
5. [Distribución del trabajo](#5-distribución-del-trabajo)
6. [Implementación — Abel Baños](#6-implementación--abel-baños)
7. [Implementación — Daniel Montero](#7-implementación--daniel-montero)
8. [Implementación — Amina Sefiani](#8-implementación--amina-sefiani)
9. [Pruebas y verificación](#9-pruebas-y-verificación)
10. [Resultados obtenidos](#10-resultados-obtenidos)
11. [Incidencias y resoluciones](#11-incidencias-y-resoluciones)
12. [Conclusiones](#12-conclusiones)
13. [Trabajo futuro y ampliaciones](#13-trabajo-futuro-y-ampliaciones)
14. [Bibliografía](#14-bibliografía)
15. [Anexos](#15-anexos)

---

## 1. Introducción

El presente Trabajo de Fin de Grado tiene como objeto el diseño, implementación y verificación de un laboratorio de red virtualizado completo sobre un único host físico con Ubuntu 24.04. El laboratorio simula la infraestructura de red de una organización mediana, incluyendo zonas de seguridad diferenciadas, servicios de red core, proxies, firewall perimetral y sistema de monitorización centralizada.

La motivación principal del proyecto nace de la necesidad de disponer de entornos de red realistas para formación y experimentación sin requerir hardware dedicado. Los laboratorios físicos tienen un coste económico elevado, requieren espacio físico y son difíciles de reproducir. Un laboratorio virtualizado en Docker resuelve estos tres problemas: se despliega en cualquier ordenador moderno, ocupa únicamente espacio en disco y puede recrearse desde cero en minutos con un único comando.

La herramienta de automatización elegida es Ansible, que permite describir el estado deseado de la infraestructura como código y reproducir el despliegue de forma idempotente. La combinación Docker + Ansible es ampliamente utilizada en entornos profesionales DevOps, lo que convierte este proyecto en una práctica directamente aplicable al mundo laboral.

El resultado final es un laboratorio completamente funcional con doce contenedores Docker desplegados en cinco redes segmentadas, un firewall nftables, servicios de red (SSH, DNS, DHCP, proxies), logging centralizado con persistencia en MySQL y un panel de control web accesible desde el navegador.

---

## 2. Objetivos del proyecto

### Objetivo principal

Diseñar e implementar un laboratorio de red virtualizado reproducible, completamente automatizado y documentado, que simule la infraestructura de red de una organización real con segmentación por zonas de seguridad.

### Objetivos específicos

- Implementar una arquitectura de red segmentada en zonas WAN, DMZ y LAN usando Docker como plataforma de virtualización.
- Automatizar el despliegue completo de la infraestructura mediante Ansible, de forma que un único comando recree el laboratorio desde cero.
- Desplegar y configurar los servicios de red fundamentales: firewall nftables, SSH, DNS (BIND9), DHCP, proxy inverso (Nginx) y proxy de salida (Squid).
- Implementar un sistema de logging centralizado con rsyslog y persistencia en MySQL.
- Desarrollar un panel de control web con Flask y HTMX para monitorización y demostración en tiempo real.
- Documentar las decisiones técnicas, incidencias y limitaciones del proyecto de forma rigurosa.
- Crear una batería de pruebas automatizadas que verifiquen el correcto funcionamiento del laboratorio.

---

## 3. Marco teórico

### 3.1 Virtualización y contenedores

La virtualización es la tecnología que permite ejecutar múltiples entornos aislados sobre un único hardware físico. Existen dos aproximaciones principales: la virtualización completa mediante hipervisores (VMware, VirtualBox, KVM) y la virtualización a nivel de sistema operativo mediante contenedores.

Los contenedores comparten el kernel del sistema operativo anfitrión y solo virtualizan el espacio de usuario, lo que los hace significativamente más ligeros y rápidos que las máquinas virtuales tradicionales. Un contenedor Docker arranca en milisegundos frente a los minutos que requiere una VM, y consume una fracción de la memoria RAM.

**Docker** es la plataforma de contenedores más extendida en la industria. Utiliza tres conceptos fundamentales: las imágenes (plantillas inmutables que definen el contenido del contenedor), los contenedores (instancias en ejecución de una imagen) y los registros (repositorios donde se almacenan y distribuyen las imágenes). En este proyecto todas las imágenes se construyen localmente mediante Dockerfiles, garantizando el control total sobre el software instalado.

Las redes Docker de tipo bridge permiten crear redes privadas virtuales donde los contenedores se comunican entre sí con IPs fijas. Esta característica es fundamental para simular la segmentación de red en zonas WAN, DMZ y LAN.

### 3.2 Automatización con Ansible

Ansible es una herramienta de automatización de infraestructura que sigue el paradigma de Infrastructure as Code (IaC). A diferencia de herramientas como Puppet o Chef, Ansible no requiere agente en los nodos gestionados — opera mediante SSH o, en este caso, ejecutando comandos directamente en el host local.

La unidad básica de Ansible es el playbook, un fichero YAML que describe tareas a ejecutar en un orden determinado. Los roles organizan las tareas, variables, plantillas y ficheros estáticos de forma modular, permitiendo reutilizar configuraciones entre proyectos.

Una característica clave de Ansible es la idempotencia: ejecutar el mismo playbook varias veces produce el mismo resultado, sin efectos secundarios acumulativos. Esto es esencial para la reproducibilidad del laboratorio.

En este proyecto se usa la colección `community.docker` que proporciona módulos específicos para gestionar contenedores, imágenes y redes Docker desde Ansible.

### 3.3 Seguridad perimetral con nftables

nftables es el sucesor de iptables en el kernel Linux desde la versión 3.13. Unifica en un único subsistema las funcionalidades de filtrado de paquetes, NAT y clasificación de tráfico que antes requerían herramientas separadas (iptables, ip6tables, arptables, ebtables).

La arquitectura de nftables se basa en tablas que contienen cadenas, y cadenas que contienen reglas. Las cadenas de tipo `filter` inspeccionan el tráfico; las de tipo `nat` realizan traducción de direcciones. La política por defecto de una cadena (`accept` o `drop`) determina qué ocurre con los paquetes que no coinciden con ninguna regla.

En este proyecto fw01 implementa un modelo de firewall con política drop por defecto, permitiendo explícitamente solo el tráfico necesario. El NAT masquerade permite a los contenedores de la LAN salir a internet usando la IP del firewall.

### 3.4 Servicios de red

**OpenSSH** proporciona acceso remoto seguro cifrado mediante criptografía de clave pública. El protocolo SSH-2 autentica al servidor mediante su clave de host y al cliente mediante contraseña o clave pública.

**BIND9** (Berkeley Internet Name Domain) es el servidor DNS más usado en internet. Actúa como servidor autoritativo para la zona interna `laboratorio.local` y como resolver con forwarding hacia servidores públicos para resolución externa.

**ISC DHCP Server** asigna automáticamente configuración de red (IP, máscara, gateway, DNS) a los clientes de la LAN mediante el protocolo DHCP. El servidor mantiene un fichero de leases con las asignaciones activas.

**Nginx** como proxy inverso recibe peticiones del exterior y las reenvía internamente al servidor real, ocultando completamente la topología interna. Gestiona los certificados SSL, añade cabeceras de proxy estándar (X-Forwarded-For, X-Real-IP) y puede balancear carga entre múltiples backends.

**Squid** como proxy de salida intercepta y registra el tráfico HTTP/HTTPS de los clientes de la LAN. Permite aplicar políticas de acceso, filtrar contenidos y generar registros de auditoría.

### 3.5 Logging centralizado

rsyslog es el daemon de logging estándar en la mayoría de distribuciones Linux. El protocolo syslog (RFC 5424) define un formato estándar para los mensajes de log que incluye prioridad, timestamp, hostname y el mensaje. rsyslog puede recibir logs de múltiples fuentes vía UDP/514 y enrutarlos a ficheros, bases de datos u otros destinos.

En este proyecto syslog01 actúa como colector central: todos los contenedores envían sus logs a 172.22.0.10:514 y rsyslog los clasifica en ficheros separados por servicio. El módulo ommysql permite además insertar cada evento en una base de datos MySQL para consultas SQL posteriores.

### 3.6 Flask y HTMX para el panel de control

Flask es un microframework web Python que permite crear aplicaciones web con pocas líneas de código. Su filosofía minimalista lo hace ideal para APIs y paneles de administración internos.

HTMX es una librería JavaScript que extiende HTML con atributos para realizar peticiones AJAX y actualizar fragmentos de la página sin recargarla completamente. La combinación Flask + HTMX permite crear interfaces dinámicas con muy poco JavaScript, manteniendo la lógica en el servidor.

---

## 4. Diseño de la solución

### 4.1 Topología de red

La infraestructura se divide en cinco zonas de red con subredes Docker independientes:

| Zona | Subred | Gateway Docker | Función |
|---|---|---|---|
| WAN | 172.20.0.0/24 | 172.20.0.1 | Simula internet / red exterior |
| DMZ | 172.21.0.0/24 | 172.21.0.1 | Servicios expuestos |
| LAN | 192.168.100.0/24 | 192.168.100.1 | Red interna protegida |
| MGMT | 172.22.0.0/24 | 172.22.0.1 | Gestión y logs |
| DB | 172.23.0.0/24 | 172.23.0.1 | Base de datos |

El firewall fw01 está conectado simultáneamente a WAN, LAN y DMZ con una IP fija en cada red, actuando como router entre ellas.

### 4.2 Política de seguridad

Las reglas nftables en fw01 implementan la siguiente política:

| Origen | Destino | Puerto | Acción |
|---|---|---|---|
| LAN | proxy01 (DMZ) | 80, 443 | Permitido |
| LAN | Cualquier | Cualquiera | Permitido (NAT) |
| DMZ | LAN | Cualquiera | Bloqueado |
| WAN | web01 (DMZ) | Cualquiera | Bloqueado |
| proxy01 (DMZ) | web01 (DMZ) | 443 | Permitido |
| Cualquiera | fw01 | 22 (desde LAN) | Permitido |

Esta política garantiza que web01 nunca es accesible directamente desde exterior — todo el tráfico debe pasar por proxy01. La DMZ no puede acceder a la LAN, limitando el impacto de un posible compromiso de los servicios expuestos.

### 4.3 Diagrama de contenedores

Cada servicio corre en su propio contenedor con imagen personalizada construida desde Dockerfile. Todas las imágenes se basan en Ubuntu 24.04 para consistencia, excepto mysql01 que usa la imagen oficial `mysql:8.0`.

### 4.4 Patrón de despliegue Ansible

Todos los roles siguen el mismo patrón de despliegue:

1. Construir la imagen Docker desde el Dockerfile del rol
2. Desplegar el contenedor con IP fija en su red principal
3. Conectar el contenedor a mgmt_net con IP fija para logging
4. Copiar ficheros de configuración al contenedor mediante `docker cp`
5. Aplicar la configuración mediante `docker exec`
6. Verificar que el servicio está funcionando correctamente

Este patrón evita usar SSH para entrar en los contenedores desde Ansible, que requeriría configurar credenciales adicionales. En su lugar, Ansible opera desde localhost usando el socket Docker.

---

## 5. Distribución del trabajo

El proyecto se desarrolló de forma colaborativa durante aproximadamente tres meses. La distribución de tareas fue la siguiente:

### Abel Baños — Arquitectura e infraestructura

Abel se encargó de las bases del proyecto: el diseño de la arquitectura de red, la configuración del entorno Ansible con la estructura de roles, el despliegue del firewall fw01 con nftables y la resolución de los problemas estructurales de Docker (reglas raw, IPs en conflicto, robustez post-reinicio).

Tareas específicas:
- Diseño de la topología de red y elección de subredes
- Configuración del entorno Ansible (ansible.cfg, inventario, group_vars, estructura de roles)
- Rol `redes`: creación de las cinco redes Docker con IPs y gateways fijos
- Rol `firewall`: Dockerfile de fw01, reglas nftables, entrypoint para carga automática de reglas, restart_policy always
- Rol `postdeploy`: eliminación de reglas raw de Docker que bloquean tráfico entre bridges
- Servicio systemd `tfg-postdeploy` para ejecutar postdeploy automáticamente en cada arranque del sistema
- `setup.sh`: script de preparación del entorno con 14 verificaciones automáticas
- `teardown.yml`: playbook de destrucción completa del laboratorio
- `site.yml`: playbook maestro con pre_tasks de verificación del entorno

### Daniel Montero — Servicios LAN y pruebas

Daniel implementó los cuatro servicios de la zona LAN y desarrolló la batería de pruebas automatizadas del laboratorio.

Tareas específicas:
- Rol `ssh`: contenedor ssh01 con OpenSSH, configuración sshd, usuario ubuntu para demos, subsistema SFTP para SCP
- Rol `dns`: contenedor dns01 con BIND9, zona `laboratorio.local`, resolución inversa, forwarders
- Rol `dhcp`: contenedor dhcp01 con ISC DHCP Server, rango 192.168.100.100-200, lease de 24h
- Rol `squid`: contenedor squid01 con Squid proxy de salida, ACLs, logging de accesos
- Rol `client`: contenedor client01 con herramientas de diagnóstico, IP fija, gateway hacia fw01
- `pruebas/healthcheck.sh`: 49 tests automáticos de verificación completa
- `pruebas/test_firewall.sh`: 12 tests de reglas de firewall (permitidos y bloqueados)
- Entrypoints de todos los servicios LAN con espera a syslog01 antes de arrancar rsyslog

### Amina Sefiani — Servicios DMZ, logging y panel web

Amina implementó los servicios de la zona DMZ, el sistema de logging centralizado con persistencia en base de datos y el panel de control web.

Tareas específicas:
- Rol `web`: contenedor web01 con Nginx, certificado SSL autofirmado, página web personalizada
- Rol `proxy`: contenedor proxy01 con Nginx proxy inverso, SSL, rutas estáticas, página `/info` propia
- Rol `syslog`: contenedor syslog01 con rsyslog centralizado, separación de logs por servicio en `/var/log/laboratorio/`
- Rol `mysql`: contenedor mysql01 con MySQL 8.0, schema SystemEvents, usuario rsyslog
- Rol `dbadmin`: contenedor dbadmin01 con phpMyAdmin accesible en puerto 8080
- Rol `panel`: contenedor panel01 con Flask+HTMX, panel de control completo con 8 secciones
- Página demo interactiva con 7 escenarios de demostración reales ejecutables desde el navegador
- Integración rsyslog → MySQL mediante módulo ommysql con cola de persistencia
- `README.md`: documentación completa del proyecto

---

## 6. Implementación — Abel Baños

### 6.1 Diseño y preparación del entorno

El proyecto comenzó con el diseño de la topología de red. La decisión de usar cinco zonas separadas (WAN, DMZ, LAN, MGMT, DB) sigue el modelo estándar de segmentación perimetral que se usa en organizaciones reales: los servicios expuestos al exterior van en la DMZ, los internos en la LAN, y la gestión tiene su propia red segregada para no mezclar tráfico operacional con tráfico de administración.

La elección de los rangos de IP evita colisiones con redes domésticas habituales (192.168.1.0/24) y sigue el estándar RFC 1918 para direccionamiento privado. La subred LAN usa el prefijo 192.168.100.0/24 para distinguirse visualmente del espacio 172.x.x.x usado en las demás zonas.

La estructura del proyecto Ansible sigue las Ansible Best Practices oficiales con un directorio de roles independiente para cada servicio, variables globales en `group_vars/all/main.yml` y playbooks separados para despliegue y destrucción.

### 6.2 Redes Docker

La creación de redes con el módulo `community.docker.docker_network` requirió especificar explícitamente el driver bridge y el IPAM (IP Address Management) para asignar subnets y gateways fijos. Se descubrió que Docker reserva automáticamente la primera IP de cada subred (.1) como gateway del bridge, por lo que todos los contenedores deben usar IPs a partir de .2.

La red MGMT (172.22.0.0/24) se añadió en una fase posterior cuando se implementó el logging centralizado. Todos los contenedores de servicios recibieron una segunda interfaz en esta red con IP fija, permitiendo comunicación de gestión independiente del tráfico de producción.

### 6.3 Firewall fw01

El diseño del firewall fue la parte más compleja del proyecto. nftables en un contenedor Docker requiere la capability `NET_ADMIN` y acceso a los módulos de kernel del host, que se montan como volumen de solo lectura.

El fichero `nftables.conf` usa IPs explícitas en lugar de nombres de interfaz para mayor portabilidad. Las reglas implementan:

- Chain input con política drop: solo acepta loopback, conexiones establecidas, ICMP y SSH desde LAN
- Chain forward con política drop: permite LAN→WAN, LAN→proxy01:80/443, proxy01→web01:443, bloquea DMZ→LAN
- Chain nat postrouting: masquerade para la subred LAN completa

El problema más persistente fue la pérdida de reglas tras reinicios. La solución definitiva fue incluir el fichero nftables.conf dentro de la imagen Docker y aplicarlo en el entrypoint al arrancar el contenedor, sin depender de Ansible para la recarga.

### 6.4 Problema de las reglas raw de Docker

Docker añade automáticamente reglas en la cadena `raw PREROUTING` de iptables/nftables para aislar los bridges entre sí. Estas reglas bloquean el tráfico entre contenedores de diferentes redes (como LAN y DMZ), impidiendo que fw01 enrute correctamente.

La solución fue crear el rol `postdeploy` que elimina estas reglas tras cada despliegue, y el servicio systemd `tfg-postdeploy` que las elimina también en cada arranque del sistema. El script identifica los bridges de lan_net y dmz_net por su ID y elimina las reglas que los referencian.

### 6.5 setup.sh

El script de preparación del entorno realiza 14 verificaciones y configuraciones automáticas en el siguiente orden:

1. Verificación de Ubuntu 24.04
2. Comprobación de espacio en disco (avisa si hay menos de 10 GB)
3. Carga de módulos de kernel necesarios (br_netfilter, ip_tables)
4. Verificación de puertos libres (5000 y 8080)
5. Instalación de dependencias base (curl, wget, git, bc, nftables)
6. Instalación de Docker y arranque del daemon
7. Adición del usuario al grupo docker
8. Instalación de Ansible
9. Instalación de la colección community.docker
10. Instalación de netaddr (Python)
11. Configuración de sudoers para nft sin contraseña
12. Habilitación de IP forwarding en el kernel
13. Detección automática de la interfaz de red y actualización de group_vars
14. Instalación del servicio systemd tfg-postdeploy

---

## 7. Implementación — Daniel Montero

### 7.1 Servidor SSH (ssh01)

El servidor SSH se basa en OpenSSH instalado sobre Ubuntu 24.04. La configuración habilita autenticación por contraseña (necesaria para el laboratorio), limita el acceso a SSH-2 y habilita el subsistema SFTP que permite transferencias SCP.

Un problema encontrado durante el desarrollo fue que al intentar reiniciar el servicio SSH con `service ssh restart` dentro del contenedor, el proceso moría con rc=137 (SIGKILL). Esto ocurre porque sshd es el proceso principal del contenedor (PID 1), y Docker lo interpreta como una señal de parada del contenedor completo. La solución fue usar `kill -HUP $(pgrep sshd)` para recargar la configuración sin matar el proceso.

Para las demos del panel web, se configuró el usuario ubuntu con contraseña TFG2026lab. El subsistema SFTP se habilitó añadiendo `Subsystem sftp /usr/lib/openssh/sftp-server` al sshd_config dentro de la imagen.

### 7.2 Servidor DNS (dns01)

BIND9 actúa como servidor autoritativo para la zona `laboratorio.local`. El fichero de zona define registros A para todos los contenedores del laboratorio:

- fw01, ssh01, dns01, dhcp01: zona LAN
- web01, proxy01: zona DMZ
- syslog01: zona MGMT

La zona inversa `100.168.192.in-addr.arpa` permite resolución inversa de IPs a nombres. Los forwarders 8.8.8.8 y 1.1.1.1 resuelven nombres externos.

La configuración `allow-query` restringe las consultas DNS a la subred LAN (192.168.100.0/24) y localhost, evitando que el servidor DNS sea accesible desde el exterior.

### 7.3 Servidor DHCP (dhcp01)

ISC DHCP Server asigna IPs del rango 192.168.100.100-200 con un lease time de 86400 segundos (24 horas). Cada lease incluye:

- Dirección IP asignada
- Máscara de subred 255.255.255.0
- Gateway 192.168.100.2 (fw01)
- DNS primario 192.168.100.20 (dns01)
- Nombre de dominio laboratorio.local

El servidor escucha en la interfaz eth0 del contenedor. El fichero de leases `/var/lib/dhcp/dhcpd.leases` registra todas las asignaciones y es leído por el panel de control para mostrar los clientes conectados.

### 7.4 Proxy Squid (squid01)

Squid actúa como proxy de salida HTTP/HTTPS para los clientes de la LAN. La configuración define una ACL que solo permite peticiones desde 192.168.100.0/24, rechazando cualquier otro origen.

Durante el desarrollo se encontraron varios problemas con Squid en contenedor:

- El comando `squid -z` (inicialización de caché) fallaba si Squid ya estaba corriendo. Se movió la inicialización al Dockerfile.
- La caché en disco causaba bucles de reinicios por errores en `store_swapout.cc`. Se deshabilitó con `cache deny all`.
- El formato de log `squid` requería el módulo daemon no disponible en contenedor. Se cambió a `stdio:/var/log/squid/access.log`.

### 7.5 Cliente de pruebas (client01)

client01 es un contenedor Ubuntu 24.04 con herramientas de diagnóstico instaladas: curl, wget, iputils-ping, dnsutils, openssh-client, sshpass, net-tools, iproute2 y udhcpc. Tiene IP fija 192.168.100.50 para evitar conflictos con fw01 y capability NET_ADMIN para modificar rutas.

El entrypoint configura automáticamente el gateway hacia fw01 (192.168.100.2) al arrancar, asegurando que el tráfico hacia la DMZ pasa siempre por el firewall.

### 7.6 Script healthcheck.sh

El script de verificación ejecuta 49 tests organizados en 9 secciones:

1. Contenedores activos (12 tests)
2. Redes Docker (5 tests)
3. Firewall nftables (2 tests)
4. Servicios principales corriendo (8 tests)
5. Pruebas funcionales de servicios (4 tests)
6. Ficheros de log centralizados (6 tests)
7. Base de datos MySQL (5 tests)
8. Panel de control Flask (5 tests)
9. Prueba end-to-end completa (2 tests)

Antes de las verificaciones, el script genera actividad en el laboratorio (envía logs a syslog01, solicita IP DHCP desde client01) para garantizar que los tests de datos no fallen por falta de actividad reciente.

### 7.7 Script test_firewall.sh

El script de pruebas de firewall verifica 12 reglas de segmentación de red:

- 6 pruebas de tráfico permitido (LAN→proxy01 HTTP/HTTPS, LAN→SSH, LAN→DNS, DMZ interna, LAN→internet via Squid)
- 5 pruebas de tráfico bloqueado (DMZ→LAN:22, DMZ→LAN desde web01, DMZ→LAN:53, LAN→web01 directo HTTPS, LAN→web01 directo HTTP)
- 1 prueba de NAT masquerade (LAN→internet directo)

Para las pruebas de bloqueo se usa `timeout 3 bash -c "cat < /dev/null > /dev/tcp/IP/PUERTO"`, que falla en 3 segundos si el tráfico está bloqueado con DROP (sin respuesta), en lugar de esperar el timeout completo de TCP.

---

## 8. Implementación — Amina Sefiani

### 8.1 Servidor web (web01)

web01 ejecuta Nginx sobre Ubuntu 24.04 sirviendo contenido estático con HTTPS. El certificado SSL autofirmado se genera durante el build de la imagen Docker con openssl, con CN=web01.laboratorio.local y validez de 365 días.

La configuración Nginx redirige automáticamente HTTP a HTTPS (código 301) y sirve el contenido estático desde `/var/www/html`. La página HTML muestra información del servidor con un diseño moderno (fondo oscuro, tarjetas de información, indicadores de estado).

El bloque server incluye las directivas SSL estándar: `ssl_protocols TLSv1.2 TLSv1.3` y `ssl_ciphers HIGH:!aNULL:!MD5` que siguen las recomendaciones actuales de seguridad.

### 8.2 Proxy inverso (proxy01)

proxy01 es el único punto de entrada desde el exterior hacia web01. Nginx actúa como proxy inverso con su propio certificado SSL, terminando la conexión TLS del cliente y estableciendo una nueva conexión TLS hacia web01.

La configuración añade las cabeceras estándar de proxy: `X-Real-IP` con la IP real del cliente, `X-Forwarded-For` con la cadena de proxies y `X-Forwarded-Proto` indicando el protocolo original. Estas cabeceras son importantes para que los logs de web01 registren la IP real del cliente en lugar de la IP de proxy01.

Un problema encontrado fue que proxy01 perdía las rutas estáticas hacia LAN y WAN tras reinicios del sistema. Se resolvió añadiendo las rutas directamente en el entrypoint del contenedor, junto con una espera activa hasta que fw01 responde a ping (señal de que las rutas están disponibles).

La ruta `/info` sirve una página HTML propia del proxy con diseño diferenciado (tema azul/morado) que explica la función del proxy y muestra el flujo de tráfico: Cliente LAN → proxy01 → web01.

### 8.3 Logging centralizado (syslog01)

syslog01 centraliza los logs de todos los contenedores del laboratorio. Escucha en el puerto 514/UDP de la red MGMT y clasifica los mensajes entrantes en ficheros separados según el hostname de origen.

La configuración rsyslog utiliza templates dinámicos para crear el fichero correcto según el servicio que envía el log:

- /var/log/laboratorio/ssh.log ← logs de ssh01
- /var/log/laboratorio/dns.log ← logs de dns01
- /var/log/laboratorio/dhcp.log ← logs de dhcp01
- /var/log/laboratorio/web.log ← logs de web01
- /var/log/laboratorio/proxy.log ← logs de proxy01
- /var/log/laboratorio/squid.log ← logs de squid01
- /var/log/laboratorio/mysql.log ← logs de mysql01

Un problema relevante fue que rsyslog crea los ficheros de log como root pero necesita escribir como usuario syslog (uid 101). Se resolvió creando el directorio `/var/log/laboratorio/` con `chown syslog:syslog` en el Dockerfile.

En los contenedores clientes se encontró que rsyslog arrancaba antes de que la red MGMT estuviera disponible, por lo que los logs no se enviaban a syslog01. La solución fue añadir un bucle de espera en el entrypoint de cada contenedor: `until bash -c "cat < /dev/null > /dev/tcp/172.22.0.10/514"` antes de arrancar rsyslogd.

### 8.4 Base de datos MySQL (mysql01)

mysql01 usa la imagen oficial `mysql:8.0` con variables de entorno para la configuración inicial (contraseña root, base de datos, usuario). El schema de la tabla SystemEvents sigue el estándar de rsyslog-mysql:

```sql
CREATE TABLE SystemEvents (
    ID int unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
    CustomerID bigint,
    ReceivedAt datetime NULL,
    DeviceReportedTime datetime NULL,
    Facility smallint NULL,
    Priority smallint NULL,
    FromHost varchar(60) NULL,
    Message text,
    NTSeverity int NULL,
    Importance int NULL,
    EventSource varchar(60),
    EventUser varchar(60) NULL,
    EventCategory int NULL,
    EventID int NULL,
    EventBinaryData text NULL,
    MaxAvailable int NULL,
    CurrUsage int NULL,
    MinUsage int NULL,
    AvgUsage int NULL,
    SysLogTag varchar(60)
);
```

La conexión rsyslog→MySQL usa el módulo `ommysql` con una cola de mensajes que persiste los logs localmente si MySQL no está disponible, reenviándolos cuando se recupera la conexión.

mysql01 está conectado tanto a db_net (172.23.0.0/24) para el tráfico de base de datos como a mgmt_net para recibir sus propios logs.

### 8.5 phpMyAdmin (dbadmin01)

dbadmin01 usa la imagen oficial `phpmyadmin/phpmyadmin` con variables de entorno que apuntan a mysql01. Expone el puerto 8080 del host para acceso desde el navegador. Permite gestionar la base de datos visualmente: ejecutar consultas SQL, explorar la tabla SystemEvents y exportar datos.

### 8.6 Panel de control Flask (panel01)

El panel de control es una aplicación web Flask con HTMX que permite monitorizar y gestionar el laboratorio desde el navegador. Está dividido en 8 secciones principales:

**Estado del laboratorio:** muestra el estado (activo/inactivo) de los 12 contenedores con su IP, actualizándose automáticamente cada 30 segundos mediante HTMX polling.

**Pruebas de conectividad:** 5 botones que ejecutan pruebas desde client01: conectividad SSH, resolución DNS, acceso HTTPS via proxy, proxy Squid hacia internet y estado del servidor DHCP. Cada prueba muestra el resultado y el output del comando.

**Verificación de firewall:** 10 pruebas de reglas de firewall ejecutadas en tiempo real, mostrando qué tráfico está permitido y bloqueado según la política configurada.

**Logs centralizados:** selector de servicio con actualización dinámica del panel de logs. Muestra las últimas 20 líneas del log correspondiente con coloreado por severidad (error=rojo, warn=amarillo, info=blanco).

**Leases DHCP:** tabla de asignaciones DHCP activas con IP, MAC y hostname del cliente.

**MySQL:** 4 consultas prefabricadas (logs por host, últimos 20 eventos, por severidad, actividad últimas 24h) ejecutadas contra la tabla SystemEvents.

**Topología de red:** diagrama SVG interactivo de la arquitectura del laboratorio con las zonas y conexiones.

**Control Ansible:** 10 botones para redesplegar servicios individuales sin interrumpir el resto del laboratorio.

### 8.7 Página demo interactiva

La página `/demo` implementa 7 escenarios de demostración reales que se ejecutan contra los contenedores del laboratorio:

1. **Sesión SSH:** client01 se conecta a ssh01, ejecuta whoami/hostname/date/uptime y muestra el log de acceso en ssh.log.
2. **Transferencia SCP:** client01 crea un fichero y lo transfiere a ssh01 via SCP, verificando que llegó correctamente.
3. **Navegación via Squid:** client01 descarga http://example.com via squid01, mostrando el HTML recibido y el log de acceso.
4. **Resolución DNS:** client01 resuelve los 6 nombres del laboratorio contra dns01, verificando que cada IP coincide con la esperada.
5. **Asignación DHCP:** client01 solicita IP via udhcpc, mostrando la IP asignada y el lease registrado.
6. **Acceso web via proxy:** client01 accede a https://172.21.0.10, que proxy01 reenvía a web01, mostrando el título HTML y el código HTTP.
7. **Logs MySQL en tiempo real:** consulta los últimos eventos registrados en SystemEvents durante la sesión de demo.

---

## 9. Pruebas y verificación

### 9.1 Metodología de pruebas

Las pruebas del laboratorio se organizan en tres niveles:

**Pruebas unitarias:** verifican que cada servicio individual está corriendo y responde correctamente (ssh01 acepta conexiones en el puerto 22, dns01 resuelve nombres, etc.)

**Pruebas de integración:** verifican que los servicios interactúan correctamente entre sí (client01 puede acceder a proxy01 que reenvía a web01, los logs de ssh01 aparecen en syslog01 y en MySQL).

**Pruebas end-to-end:** simulan un flujo completo de usuario (enviar un mensaje de log desde ssh01 y verificar que aparece tanto en el fichero de log como en la base de datos MySQL).

### 9.2 Resultados del healthcheck

El script `pruebas/healthcheck.sh` ejecuta 49 tests automáticos. Resultado tras despliegue limpio desde cero:

```
✓ Todos los tests pasaron: 49/49 (100%)
  Laboratorio funcionando correctamente
```

Tiempo de ejecución del healthcheck: aproximadamente 45 segundos (incluye el calentamiento inicial que genera actividad en el laboratorio).

### 9.3 Resultados del test de firewall

El script `pruebas/test_firewall.sh` verifica 12 reglas de segmentación:

```
✓ Firewall funcionando correctamente: 12/12 pruebas OK
  Las reglas de segmentación de red están aplicadas
```

Detalle de los resultados:

| Prueba | Resultado |
|---|---|
| LAN → proxy01 HTTP (puerto 80) | ✅ Permitido |
| LAN → proxy01 HTTPS (puerto 443) | ✅ Permitido |
| LAN → SSH en ssh01 (puerto 22) | ✅ Permitido |
| LAN → DNS en dns01 (puerto 53) | ✅ Permitido |
| proxy01 DMZ → web01 DMZ | ✅ Permitido |
| LAN → internet via Squid (NAT) | ✅ Permitido |
| DMZ → LAN: proxy01 no accede a ssh01 | ✅ Bloqueado |
| DMZ → LAN: web01 no accede a ssh01 | ✅ Bloqueado |
| DMZ → LAN: proxy01 no accede a dns01 | ✅ Bloqueado |
| LAN → web01 directo HTTPS (bloqueado) | ✅ Bloqueado |
| LAN → web01 directo HTTP (bloqueado) | ✅ Bloqueado |
| LAN → internet directo via fw01 (NAT) | ✅ Permitido |

### 9.4 Prueba de robustez post-reinicio

Se realizó una prueba de reinicio completo del host para verificar que el laboratorio arranca automáticamente sin intervención manual:

1. `sudo reboot` — reinicio completo del sistema
2. Esperar 2 minutos para que Docker arranque todos los contenedores
3. `./pruebas/healthcheck.sh` — resultado: 49/49 (100%)

Esta prueba confirma que todos los mecanismos de robustez funcionan correctamente:
- fw01 arranca con restart_policy always y aplica las reglas nftables desde la imagen
- Los 6 contenedores de servicios esperan a syslog01 antes de arrancar rsyslog
- proxy01 espera a fw01 y configura las rutas estáticas automáticamente
- client01 configura el gateway hacia fw01 desde el entrypoint
- El servicio systemd tfg-postdeploy elimina las reglas raw de Docker

---

## 10. Resultados obtenidos

### Métricas del laboratorio

| Métrica | Valor |
|---|---|
| Contenedores desplegados | 12 |
| Redes Docker | 5 |
| Tests automáticos | 49 + 12 = 61 |
| Tasa de éxito en tests | 100% |
| Tiempo de despliegue desde cero | ~4 minutos |
| Registros en MySQL (tras uso normal) | >700 eventos |
| Roles Ansible | 14 |
| Tareas Ansible en site.yml | ~141 |
| Tiempo de ejecución site.yml | ~1 minuto 30 segundos |

### Infraestructura de código

| Componente | Líneas de código |
|---|---|
| site.yml | 161 |
| teardown.yml | 121 |
| group_vars/all/main.yml | 102 |
| setup.sh | 212 |
| pruebas/healthcheck.sh | ~150 |
| pruebas/test_firewall.sh | ~120 |
| app.py (panel Flask) | ~576 |
| Templates HTML | ~800 |

---

## 11. Incidencias y resoluciones

### Incidencia 1 — sshd PID 1 en contenedor (rc=137)

**Descripción:** La tarea Ansible `service ssh restart` dentro del contenedor devolvía rc=137 (SIGKILL). sshd es el proceso CMD principal del contenedor y Docker lo reiniciaba al detectar su parada.

**Resolución:** Separar la recarga en dos tareas: primero `pgrep sshd` para obtener el PID, luego `kill -HUP <PID>` para recargar sin matar el proceso. Este patrón se documentó como buena práctica y se aplicó también a otros servicios.

### Incidencia 2 — Go template syntax en YAML

**Descripción:** La sintaxis `{{.Names}}` de los templates Go dentro de strings YAML conflictuaba con el parser de Jinja2 de Ansible, causando errores de parsing.

**Resolución:** Reemplazar los strings `--format "{{.Names}}"` por `--filter name=<nombre>` que no usa templates y produce el mismo resultado.

### Incidencia 3 — Reglas raw de Docker bloquean tráfico entre bridges

**Descripción:** Docker añade automáticamente reglas en nftables `raw PREROUTING` que aíslan los bridges entre sí. Esto impedía que los contenedores de LAN accedieran a los de DMZ incluso con las reglas de fw01 correctamente configuradas.

**Resolución:** Rol postdeploy que identifica los IDs de los bridges lan_net y dmz_net y elimina las reglas raw que los referencian. Servicio systemd para ejecutarlo automáticamente en cada arranque.

### Incidencia 4 — rsyslog arranca antes de syslog01

**Descripción:** En reinicios del sistema, rsyslog en los contenedores clientes arrancaba antes de que syslog01 estuviera disponible en la red MGMT, por lo que los logs no se enviaban.

**Resolución:** Añadir en el entrypoint de cada contenedor un bucle de espera TCP: `until bash -c "cat < /dev/null > /dev/tcp/172.22.0.10/514"` antes de arrancar rsyslogd. El bucle verifica que el puerto 514 de syslog01 está aceptando conexiones.

### Incidencia 5 — client01 robaba la IP de fw01

**Descripción:** Tras reinicios, Docker asignaba la IP 192.168.100.2 (reservada para fw01) a client01, impidiendo que fw01 arrancara.

**Resolución:** Asignar IP fija 192.168.100.50 a client01 en el módulo `docker_container` de Ansible, fuera del rango DHCP (.100-.200) y alejada de las IPs de infraestructura.

### Incidencia 6 — Squid bucle de reinicios

**Descripción:** Squid entraba en bucle de reinicios por errores en `store_swapout.cc` relacionados con la caché en disco.

**Resolución:** Deshabilitar la caché en disco con `cache deny all` en squid.conf. La caché en memoria sigue funcionando para el laboratorio.

### Incidencia 7 — proxy01 perdía rutas estáticas

**Descripción:** Tras reinicios, proxy01 no tenía las rutas estáticas hacia LAN (192.168.100.0/24) y WAN (172.20.0.0/24), impidiendo que el proxy inverso funcionara.

**Resolución:** Añadir las rutas en el entrypoint del contenedor, con una espera previa a que fw01 responda a ping como señal de disponibilidad.

### Incidencia 8 — Código de la página demo aparecía después de if __name__

**Descripción:** Los endpoints de la página demo se añadieron después del bloque `if __name__ == '__main__': app.run(...)` en app.py. Flask arrancaba el servidor antes de registrar las rutas de demo, devolviendo 404.

**Resolución:** Mover el bloque `if __name__` al final del fichero, después de todos los endpoints. Las rutas se registran en el momento de importar el módulo, antes de que Flask arranque el servidor.

---

## 12. Conclusiones

### 12.1 Objetivos alcanzados

Todos los objetivos del proyecto se han cumplido satisfactoriamente:

- Se ha diseñado e implementado una arquitectura de red segmentada en cinco zonas con firewall perimetral funcional.
- El despliegue está completamente automatizado con Ansible — un único comando `ansible-playbook site.yml` recrea el laboratorio desde cero.
- Están operativos todos los servicios planificados: firewall nftables, SSH, DNS, DHCP, proxy inverso, proxy de salida, logging centralizado, MySQL y panel web.
- La batería de pruebas automatizadas verifica 61 aspectos del laboratorio y obtiene un 100% de éxito.
- El laboratorio es reproducible en cualquier sistema Ubuntu 24.04 mediante el script setup.sh.

### 12.2 Aprendizajes técnicos

El desarrollo del proyecto ha generado aprendizajes significativos en varias áreas:

En Docker se profundizó en la gestión de redes bridge, el comportamiento de las reglas raw y la problemática de los procesos PID 1 en contenedores. Se aprendió que los contenedores no son máquinas virtuales y tienen particularidades propias que requieren aproximaciones específicas.

En Ansible se consolidó el uso de roles, handlers, tags y módulos de la colección community.docker. Se comprendió la importancia de la idempotencia y cómo diseñar tareas que puedan ejecutarse múltiples veces sin efectos secundarios.

En nftables se implementó un firewall con estado (stateful) con NAT y políticas drop por defecto, siguiendo las mejores prácticas actuales de seguridad perimetral.

### 12.3 Limitaciones conocidas

**Bypass de fw01 desde el host:** Docker crea bridges que permiten al host acceder directamente a todos los contenedores sin pasar por fw01. Esta es una limitación estructural de Docker en modo bridge sobre un único host. En un entorno de producción real se utilizaría hardware dedicado para el firewall o se añadirían reglas `iptables DOCKER-USER` en el host para forzar todo el tráfico a pasar por fw01.

**Certificados SSL autofirmados:** Los certificados son autofirmados para entorno de laboratorio. En producción se usarían certificados emitidos por una autoridad de certificación reconocida (Let's Encrypt, por ejemplo).

**Credenciales en texto plano:** Las contraseñas están en `group_vars/all/main.yml` sin cifrar. En producción se usaría Ansible Vault para cifrar los secretos.

**Único host:** Al correr todo en un único host físico, no hay redundancia ni alta disponibilidad. Una caída del host tumba todo el laboratorio. En producción se distribuiría la carga entre varios nodos.

---

## 13. Trabajo futuro y ampliaciones

### Ampliación 1 — Monitorización avanzada

Añadir una red `monitor_net` (172.24.0.0/24) con dos contenedores:

- **prometheus01:** servidor Prometheus para recolección de métricas de todos los contenedores
- **grafana01:** panel Grafana con dashboards preconstruidos para visualización de métricas

Esta ampliación elevaría el laboratorio a nivel de infraestructura empresarial completa con observabilidad centralizada, similar a lo que se usa en entornos cloud.

### Ampliación 2 — Ansible Vault

Cifrar todas las credenciales del proyecto con Ansible Vault:

```bash
ansible-vault encrypt_string 'Root_TFG_2026!' --name 'mysql_root_password'
```

Las contraseñas cifradas pueden incluirse en el repositorio de forma segura. Al ejecutar el playbook, Ansible solicita la contraseña del vault para descifrarlas.

### Ampliación 3 — Alta disponibilidad DNS

Añadir un segundo servidor DNS (dns02) como réplica de dns01, con transferencia de zona automática. Los clientes DHCP recibirían dos servidores DNS, garantizando la resolución de nombres si uno falla.

### Ampliación 4 — Hardening SSH con claves públicas

Generar un par de claves RSA en el host, copiar la clave pública a ssh01 y deshabilitar la autenticación por contraseña. Añadir rate limiting en nftables para prevenir ataques de fuerza bruta:

```
tcp dport 22 ct state new limit rate 3/minute accept
```

### Ampliación 5 — OVA para Windows

Crear una máquina virtual VirtualBox con Ubuntu 24.04 y el laboratorio preinstalado, exportarla como fichero OVA. Esto permitiría a usuarios de Windows desplegar el laboratorio con doble clic, sin necesidad de instalar ninguna dependencia.

---

## 14. Bibliografía

- Docker Documentation. Docker Inc. https://docs.docker.com
- Ansible Documentation. Red Hat Inc. https://docs.ansible.com
- nftables Wiki. Netfilter Project. https://wiki.nftables.org
- BIND9 Administrator Reference Manual. ISC. https://bind9.readthedocs.io
- ISC DHCP Server Documentation. ISC. https://www.isc.org/dhcp/
- Nginx Documentation. Nginx Inc. https://nginx.org/en/docs/
- Squid Configuration Reference. Squid Project. http://www.squid-cache.org/Doc/config/
- rsyslog Documentation. Rainer Gerhards. https://www.rsyslog.com/doc/
- MySQL 8.0 Reference Manual. Oracle. https://dev.mysql.com/doc/refman/8.0/en/
- Flask Documentation. Pallets Projects. https://flask.palletsprojects.com
- HTMX Documentation. https://htmx.org/docs/
- RFC 1918 — Address Allocation for Private Internets. IETF. https://tools.ietf.org/html/rfc1918
- RFC 5424 — The Syslog Protocol. IETF. https://tools.ietf.org/html/rfc5424
- Ubuntu 24.04 LTS Server Guide. Canonical. https://ubuntu.com/server/docs

---

## 15. Anexos

### Anexo A — Tabla de direccionamiento completa

| Contenedor | Red principal | IP principal | Red MGMT | IP MGMT | Red DB | IP DB |
|---|---|---|---|---|---|---|
| fw01 | wan_net | 172.20.0.2 | — | — | — | — |
| fw01 | lan_net | 192.168.100.2 | — | — | — | — |
| fw01 | dmz_net | 172.21.0.2 | — | — | — | — |
| proxy01 | dmz_net | 172.21.0.10 | mgmt_net | 172.22.0.15 | — | — |
| web01 | dmz_net | 172.21.0.20 | mgmt_net | 172.22.0.14 | — | — |
| ssh01 | lan_net | 192.168.100.10 | mgmt_net | 172.22.0.11 | — | — |
| dns01 | lan_net | 192.168.100.20 | mgmt_net | 172.22.0.12 | — | — |
| dhcp01 | lan_net | 192.168.100.30 | mgmt_net | 172.22.0.13 | — | — |
| squid01 | lan_net | 192.168.100.40 | mgmt_net | 172.22.0.16 | — | — |
| client01 | lan_net | 192.168.100.50 | — | — | — | — |
| syslog01 | mgmt_net | 172.22.0.10 | — | — | db_net | 172.23.0.20 |
| mysql01 | db_net | 172.23.0.10 | mgmt_net | 172.22.0.17 | — | — |
| dbadmin01 | mgmt_net | DHCP | — | — | — | — |
| panel01 | mgmt_net | DHCP | — | — | db_net | DHCP |

### Anexo B — Variables globales (group_vars/all/main.yml)

Las variables globales del laboratorio están centralizadas en un único fichero YAML. Incluyen definiciones de todas las redes, IPs de todos los contenedores y credenciales de la base de datos. Cualquier cambio en la arquitectura se realiza en este fichero y se propaga automáticamente a todos los roles en la siguiente ejecución del playbook.

### Anexo C — Comandos de diagnóstico útiles

```bash
# Ver estado de todos los contenedores
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Ver reglas nftables del firewall
docker exec fw01 nft list ruleset

# Monitorizar logs en tiempo real
docker exec syslog01 tail -f /var/log/laboratorio/ssh.log

# Consultar eventos MySQL
docker exec mysql01 bash -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" Syslog -e "SELECT ReceivedAt, FromHost, Message FROM SystemEvents ORDER BY ID DESC LIMIT 10;"'

# Ver leases DHCP activos
docker exec dhcp01 cat /var/lib/dhcp/dhcpd.leases

# Probar resolución DNS
docker exec client01 nslookup web01.laboratorio.local 192.168.100.20

# Probar acceso web via proxy
docker exec client01 curl -sk -o /dev/null -w "%{http_code}" https://172.21.0.10
```

### Anexo D — Credenciales del laboratorio

| Servicio | Acceso | Usuario | Contraseña |
|---|---|---|---|
| MySQL | mysql01:3306 | root | Root_TFG_2026! |
| MySQL | mysql01:3306 | rsyslog | Rsyslog_TFG_2026! |
| phpMyAdmin | http://localhost:8080 | root | Root_TFG_2026! |
| SSH demo | 192.168.100.10:22 | ubuntu | TFG2026lab |
| Panel web | http://localhost:5000 | — | — |

---

*Trabajo de Fin de Grado — ASIR 2025–2026*  
*Abel Baños · Daniel Montero · Amina Sefiani*
