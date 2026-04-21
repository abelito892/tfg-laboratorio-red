#!/bin/bash
# Entrypoint dns01 — arranca rsyslog + named

rsyslogd
sleep 1

exec /usr/sbin/named -g -u bind
