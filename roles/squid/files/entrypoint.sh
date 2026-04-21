#!/bin/bash
# Entrypoint squid01 — arranca rsyslog + squid

rsyslogd
sleep 1

rm -f /run/squid.pid
exec squid -NYCd 1
