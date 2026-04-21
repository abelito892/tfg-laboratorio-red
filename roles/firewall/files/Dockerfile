FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nftables \
    iproute2 \
    iputils-ping \
    dnsutils \
    curl \
    net-tools \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

RUN echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
RUN mkdir -p /etc/nftables

# Incluir las reglas nftables en la imagen
# Ansible las sobreescribirá si cambian, pero así siempre hay una versión base
COPY nftables.conf /etc/nftables/nftables.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
