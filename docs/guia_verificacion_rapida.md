# Guía de verificación rápida
## TFG Laboratorio de Red — ASIR
**Autor:** Abel  
**Fecha:** Abril 2026

---

## Antes de empezar — arrancar el laboratorio

Ansible despliega todo el laboratorio desde cero con un único comando. La primera ejecución tarda más porque construye las imágenes Docker — las siguientes son mucho más rápidas al usar la caché.

```bash
cd ~/tfg-laboratorio-red
ansible-playbook site.yml
```

---

## 1. Redes Docker

Verificamos que las tres redes del laboratorio existen y están activas. Cada red representa una zona de seguridad distinta — WAN (exterior), DMZ (servicios expuestos) y LAN (servicios internos).

```bash
docker network ls --filter driver=bridge
```
**Esperado:** `wan_net`, `dmz_net`, `lan_net` visibles.

---

## 2. Contenedores activos

Comprobamos de un vistazo que todos los contenedores están corriendo. Si alguno aparece en estado `Exited` o `Restarting` hay un problema que investigar con `docker logs <nombre>`.

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```
**Esperado:** `fw01`, `ssh01`, `dns01`, `dhcp01`, `web01`, `proxy01`, `squid01` en estado `Up`.

---

## 3. Firewall — fw01

El firewall es el elemento central de la arquitectura — enruta el tráfico entre zonas y aplica las reglas de seguridad con nftables. Verificamos que las reglas están cargadas y que la LAN puede salir a internet a través del NAT.

```bash
# Ver reglas activas
docker exec fw01 nft list ruleset

# LAN puede salir a internet
docker exec fw01 ping -c 2 8.8.8.8
```
**Esperado:** ruleset con chains `input`, `forward`, `output` y NAT masquerade. Ping responde.

---

## 4. Servidor SSH — ssh01

SSH permite administrar los contenedores de la LAN de forma remota y segura. Verificamos que el servidor escucha en el puerto 22 y acepta conexiones con la contraseña configurada.

```bash
ssh root@192.168.100.10
# Contraseña: laboratorio
```
**Esperado:** acceso correcto al contenedor. `hostname` devuelve el ID del contenedor.

---

## 5. Servidor DNS — dns01

BIND9 resuelve los nombres del dominio `laboratorio.local` y reenvía las consultas externas a Google DNS y Cloudflare. Verificamos los tres tipos de resolución: directa interna, inversa y externa.

```bash
# Resolución interna
dig @192.168.100.20 ssh01.laboratorio.local +short

# Resolución inversa
dig @192.168.100.20 -x 192.168.100.10 +short

# Resolución externa
dig @192.168.100.20 google.com +short
```
**Esperado:** `192.168.100.10`, `ssh01.laboratorio.local.`, IP de Google.

---

## 6. Servidor DHCP — dhcp01

ISC DHCP Server asigna automáticamente IPs del rango `192.168.100.100-200` a los clientes de la LAN. Lanzamos un contenedor Alpine sin IP fija para simular un cliente que se conecta por primera vez.

```bash
docker run --rm --network lan_net alpine udhcpc -i eth0 -t 5 -n
```
**Esperado:** `lease of 192.168.100.1xx obtained from 192.168.100.30`.

---

## 7. Servidor web — web01

Nginx sirve contenido estático con HTTP y HTTPS usando un certificado SSL autofirmado. El puerto 80 redirige automáticamente a HTTPS — requisito de seguridad básico en cualquier servidor web moderno.

```bash
# HTTP redirige a HTTPS
curl -v http://172.21.0.20 2>&1 | grep "< HTTP"

# HTTPS devuelve la página
curl -k https://172.21.0.20 | grep "<title>"
```
**Esperado:** código `301` en HTTP. Título `Laboratorio de Red — TFG ASIR` en HTTPS.
También verificable desde el navegador en `https://172.21.0.20`.

---

## 8. Proxy inverso — proxy01

Nginx actúa como único punto de entrada desde el exterior hacia `web01`. El cliente nunca habla directamente con `web01` — proxy01 recibe la petición, la reenvía internamente y devuelve la respuesta, ocultando completamente el servidor real.

```bash
# Acceder a web01 a través del proxy
curl -k https://172.21.0.10 | grep "<title>"

# HTTP redirige a HTTPS
curl -v http://172.21.0.10 2>&1 | grep "< HTTP"
```
**Esperado:** misma página que web01 pero accediendo por `172.21.0.10`. Código `301` en HTTP.
También verificable desde el navegador en `https://172.21.0.10`.

---

## 9. Proxy de salida — squid01

Squid intercepta y registra todo el tráfico web saliente de los clientes de la LAN. Abrimos dos terminales — en una monitorizamos los logs en tiempo real y en la otra simulamos una petición a través del proxy para ver cómo queda registrada.

```bash
# Terminal 1 — monitorizar logs
docker exec squid01 tail -f /var/log/squid/access.log

# Terminal 2 — hacer una petición a través del proxy
curl -x 192.168.100.40:3128 http://google.com -s -o /dev/null -w "%{http_code}"
```
**Esperado:** código `301` en Terminal 2. En Terminal 1 aparece una línea de log con `TCP_MISS` y la URL solicitada.

---

## 10. Verificación rápida completa

Una sola vista que resume el estado de todo el laboratorio. Útil al inicio de cada sesión de trabajo para confirmar que todo está en pie antes de continuar.

```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
docker network ls --filter driver=bridge
```

---

*Documento generado en Abril 2026*
