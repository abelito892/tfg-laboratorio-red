#!/bin/bash
echo "[web01] Arrancando FastAPI..."
cd /app && uvicorn main:app --host 127.0.0.1 --port 8000 --log-level warning &

echo "[web01] Esperando a que FastAPI arranque..."
sleep 3

echo "[web01] Iniciando reenvio de logs a syslog01..."
tail -F -n0 /var/log/nginx/web01_access.log | while IFS= read -r line; do
  logger -n 172.22.0.10 -P 514 --udp "web01: $line"
done &
disown

echo "[web01] Arrancando Nginx..."
exec nginx -g "daemon off;"
