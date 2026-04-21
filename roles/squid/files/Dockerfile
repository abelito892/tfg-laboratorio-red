FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y squid rsyslog && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/log/squid && \
    mkdir -p /var/spool/squid && \
    chown -R proxy:proxy /var/log/squid && \
    chown -R proxy:proxy /var/spool/squid

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 3128

CMD ["/entrypoint.sh"]
