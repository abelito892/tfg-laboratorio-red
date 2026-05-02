#!/bin/bash
mkdir -p /run/sshd
rsyslogd
exec /usr/sbin/sshd -D
