#!/bin/bash
# Entrypoint dhcp01 — arranca rsyslog + dhcpd

rsyslogd
sleep 1

# Esperar a que Ansible copie dhcpd.conf antes de arrancar
echo "Esperando dhcpd.conf..."
while [ ! -s /etc/dhcp/dhcpd.conf ]; do
    sleep 1
done

exec /usr/sbin/dhcpd -f -cf /etc/dhcp/dhcpd.conf -pf /var/run/dhcpd.pid
