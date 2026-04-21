FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y nginx openssl iputils-ping && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/proxy.key \
    -out /etc/ssl/certs/proxy.crt \
    -subj "/C=ES/ST=Madrid/L=Madrid/O=TFG-ASIR/CN=proxy01.laboratorio.local"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
EXPOSE 443

CMD ["/entrypoint.sh"]
