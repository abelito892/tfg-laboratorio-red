#!/bin/bash
# Entrypoint syslog01 — rsyslogd como proceso hijo en bucle
# Si pkill lo mata para recargar config, el bucle lo relanza automáticamente

while true; do
    rsyslogd -n
    echo "rsyslogd terminó, relanzando en 2s..."
    sleep 2
done
