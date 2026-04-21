# Imagen base para el contenedor MySQL del laboratorio TFG ASIR
# Partimos de la imagen oficial de MySQL 8.0

FROM mysql:8.0

# Instalamos rsyslog dentro del contenedor MySQL para que sus logs
# locales (errores, conexiones, queries lentas) puedan reenviarse
# al servidor centralizado syslog01
RUN microdnf install -y rsyslog procps-ng || \
    (apt-get update && apt-get install -y rsyslog procps && \
     apt-get clean && rm -rf /var/lib/apt/lists/*)

# Copiamos el script de inicio personalizado
COPY entrypoint-wrapper.sh /entrypoint-wrapper.sh
RUN chmod +x /entrypoint-wrapper.sh

# El puerto 3306 lo expone la imagen base, lo dejamos explícito
EXPOSE 3306

# Sobrescribimos el entrypoint para arrancar rsyslog antes que MySQL
ENTRYPOINT ["/entrypoint-wrapper.sh"]
CMD ["mysqld"]
