#!/bin/bash
# Entrypoint dhcp01 — espera syslog01, arranca rsyslog + dhcpd

echo "Esperando a syslog01 (172.22.0.10)..."
until bash -c "cat < /dev/null > /dev/tcp/172.22.0.10/514" 2>/dev/null; do
    sleep 2
done
rsyslogd
sleep 1

echo "Esperando dhcpd.conf..."
while [ ! -s /etc/dhcp/dhcpd.conf ]; do
    sleep 1
done

exec /usr/sbin/dhcpd -f -cf /etc/dhcp/dhcpd.conf -pf /var/run/dhcpd.pid
