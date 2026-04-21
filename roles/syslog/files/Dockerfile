FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# rsyslog + módulo mysql (ommysql) + cliente mysql para diagnóstico
RUN apt-get update && \
    apt-get install -y rsyslog rsyslog-mysql mysql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Crear directorio para logs del laboratorio
RUN mkdir -p /var/log/laboratorio && \
    chown -R syslog:syslog /var/log/laboratorio

# Crear directorio para la cola persistente de rsyslog
# (si MySQL está caído, los mensajes se guardan aquí hasta que vuelva)
RUN mkdir -p /var/spool/rsyslog && \
    chown -R syslog:syslog /var/spool/rsyslog

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 514/udp
EXPOSE 514/tcp

CMD ["/entrypoint.sh"]
