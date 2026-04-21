# Imagen base para el contenedor firewall del laboratorio TFG ASIR
FROM ubuntu:24.04

# Evita preguntas interactivas durante la instalación de paquetes
ENV DEBIAN_FRONTEND=noninteractive

# Instalamos las herramientas necesarias:
# - nftables: firewall moderno del kernel Linux (sucesor de iptables)
# - iproute2: comandos ip, ss (diagnóstico de red)
# - iputils-ping: comando ping para pruebas de conectividad
# - dnsutils: comando dig para pruebas DNS
# - curl: pruebas HTTP
# - net-tools: comandos clásicos como netstat, ifconfig
# - openssh-server: para que Ansible pueda conectarse via SSH si es necesario
RUN apt-get update && apt-get install -y \
    nftables \
    iproute2 \
    iputils-ping \
    dnsutils \
    curl \
    net-tools \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Habilitamos ip_forward dentro del contenedor
# Esto es lo que permite que el contenedor actúe como router
RUN echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

# Creamos el directorio para las reglas nftables
RUN mkdir -p /etc/nftables

# El contenedor se mantiene vivo con tail -f
# En producción usaríamos un proceso supervisor como s6 o supervisord
CMD ["tail", "-f", "/dev/null"]
