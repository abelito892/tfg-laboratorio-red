#!/bin/bash
# Entrypoint fw01 — aplica reglas nftables automáticamente al arrancar

echo "Aplicando reglas nftables..."
nft -f /etc/nftables/nftables.conf 2>/dev/null || true

echo "fw01 listo."
tail -f /dev/null
