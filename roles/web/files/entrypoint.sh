#!/bin/bash
# Entrypoint web01 — arranca rsyslog + nginx

rsyslogd
sleep 1

exec nginx -g "daemon off;"
