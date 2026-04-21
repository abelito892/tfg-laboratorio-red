#!/bin/bash
# Wrapper del entrypoint de MySQL
# Arranca rsyslog como daemon y luego cede el control al
# entrypoint original de la imagen mysql:8.0

# Arrancar rsyslog en segundo plano (los logs locales se reenviarán
# al syslog01 si /etc/rsyslog.conf tiene la línea de reenvío)
if command -v rsyslogd >/dev/null 2>&1; then
    rsyslogd
    sleep 1
fi

# Ejecutar el entrypoint original de la imagen mysql:8.0
# con todos los argumentos que reciba (típicamente "mysqld")
exec /usr/local/bin/docker-entrypoint.sh "$@"
