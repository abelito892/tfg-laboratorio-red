FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y openssh-server iproute2 curl rsyslog && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/sshd

# Usuario ubuntu para empleados, root para administracion
RUN echo 'root:laboratorio' | chpasswd
RUN echo 'ubuntu:TFG2026lab' | chpasswd && chsh -s /bin/bash ubuntu

# MOTD corporativo NetCorp
COPY motd /etc/motd
RUN echo "PrintMotd yes" >> /etc/ssh/sshd_config

# SFTP habilitado
RUN echo 'Subsystem sftp /usr/lib/openssh/sftp-server' >> /etc/ssh/sshd_config

# Reenvio de logs SSH a syslog01 via UDP
RUN echo '*.* @172.22.0.10:514' >> /etc/rsyslog.conf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

CMD ["/entrypoint.sh"]
