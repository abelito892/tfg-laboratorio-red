#!/bin/bash
# Entrypoint web01 — espera syslog01, arranca rsyslog + nginx

echo "Esperando a syslog01 (172.22.0.10)..."
until bash -c "cat < /dev/null > /dev/tcp/172.22.0.10/514" 2>/dev/null; do
    sleep 2
done
rsyslogd
sleep 1

exec nginx -g "daemon off;"
