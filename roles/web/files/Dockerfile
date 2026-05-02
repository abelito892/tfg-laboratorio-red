FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y nginx openssl python3 python3-pip curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install fastapi "uvicorn[standard]" mysql-connector-python --break-system-packages

RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx.key \
    -out /etc/ssl/certs/nginx.crt \
    -subj "/C=ES/ST=Madrid/L=Madrid/O=NetCorp/CN=web01.netcorp.local"

RUN mkdir -p /var/www/laboratorio /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80 443

CMD ["/entrypoint.sh"]
