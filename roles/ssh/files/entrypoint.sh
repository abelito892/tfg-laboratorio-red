#!/bin/bash
# Entrypoint ssh01 — arranca rsyslog + sshd

# Arrancar rsyslog como daemon en segundo plano
rsyslogd

# Pequeña espera para que rsyslog esté listo antes de sshd
sleep 1

# Arrancar sshd en primer plano (PID 1)
exec /usr/sbin/sshd -D
