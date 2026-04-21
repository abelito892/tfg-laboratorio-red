#!/usr/bin/env python3
"""
Panel de Control del Laboratorio - TFG ASIR
Backend Flask con HTMX para control del laboratorio de red virtualizado
"""

import subprocess
import mysql.connector
from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────
MYSQL_CONFIG = {
    'host': '172.23.0.10',
    'user': 'rsyslog',
    'password': 'Rsyslog_TFG_2026!',
    'database': 'Syslog',
    'connection_timeout': 5
}

CONTENEDORES = [
    'fw01', 'ssh01', 'dns01', 'dhcp01',
    'web01', 'proxy01', 'squid01', 'client01',
    'syslog01', 'mysql01', 'dbadmin01', 'panel01'
]

SERVICIOS_LOG = ['ssh', 'dns', 'dhcp', 'web', 'proxy', 'squid', 'mysql']

# ─── UTILIDADES ──────────────────────────────────────────────────────────────
def docker_exec(contenedor, comando):
    """Ejecuta un comando dentro de un contenedor Docker"""
    try:
        result = subprocess.run(
            ['docker', 'exec', contenedor, 'bash', '-c', comando],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "Timeout", 1
    except Exception as e:
        return str(e), 1

def docker_run(comando):
    """Ejecuta un comando docker en el host"""
    try:
        result = subprocess.run(
            comando, capture_output=True, text=True,
            timeout=15, shell=True
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def get_mysql_connection():
    """Obtiene conexión a MySQL"""
    return mysql.connector.connect(**MYSQL_CONFIG)

# ─── RUTAS PRINCIPALES ───────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ─── API: ESTADO CONTENEDORES ────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
    """Devuelve el estado de todos los contenedores"""
    estados = []
    for nombre in CONTENEDORES:
        out, rc = docker_run(
            f"docker ps --filter name=^/{nombre}$ --filter status=running --format '{{{{.Names}}}}'"
        )
        corriendo = nombre in out
        ip_out, _ = docker_run(
            f"docker inspect {nombre} --format '{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}} {{{{end}}}}'"
        )
        ip = ip_out.split()[0] if ip_out else 'N/A'
        estados.append({
            'nombre': nombre,
            'corriendo': corriendo,
            'ip': ip,
            'estado': 'Activo' if corriendo else 'Inactivo'
        })
    return render_template('partials/status.html', estados=estados,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

# ─── API: LOGS ────────────────────────────────────────────────────────────────
@app.route('/api/logs/<servicio>')
def api_logs(servicio):
    """Devuelve los últimos 20 logs de un servicio"""
    if servicio not in SERVICIOS_LOG:
        return render_template('partials/logs.html', logs=[], servicio=servicio,
                               error="Servicio no válido")
    out, rc = docker_exec('syslog01',
                          f'tail -20 /var/log/laboratorio/{servicio}.log')
    logs = []
    if rc == 0 and out:
        for linea in out.split('\n'):
            if linea.strip():
                logs.append(linea)
    return render_template('partials/logs.html', logs=logs, servicio=servicio,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

# ─── API: DHCP LEASES ─────────────────────────────────────────────────────────
@app.route('/api/dhcp/leases')
def api_dhcp_leases():
    """Devuelve los leases DHCP activos"""
    out, rc = docker_exec('dhcp01', 'cat /var/lib/dhcp/dhcpd.leases')
    leases = []
    if rc == 0 and out:
        lease_actual = {}
        for linea in out.split('\n'):
            linea = linea.strip()
            if linea.startswith('lease '):
                lease_actual = {'ip': linea.split()[1]}
            elif 'binding state active' in linea and lease_actual:
                lease_actual['estado'] = 'Activo'
            elif linea.startswith('client-hostname'):
                lease_actual['hostname'] = linea.split('"')[1] if '"' in linea else 'N/A'
            elif linea.startswith('hardware ethernet'):
                lease_actual['mac'] = linea.split()[2].rstrip(';')
            elif linea == '}' and lease_actual.get('estado') == 'Activo':
                if 'hostname' not in lease_actual:
                    lease_actual['hostname'] = 'N/A'
                leases.append(lease_actual)
                lease_actual = {}
    return render_template('partials/dhcp.html', leases=leases,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

# ─── API: MYSQL CONSULTAS ─────────────────────────────────────────────────────
@app.route('/api/mysql/<consulta>')
def api_mysql(consulta):
    """Ejecuta consultas MySQL prefabricadas"""
    consultas = {
        'total_por_host': {
            'titulo': 'Total de logs por host',
            'sql': 'SELECT FromHost, COUNT(*) as Total FROM SystemEvents GROUP BY FromHost ORDER BY Total DESC',
            'columnas': ['Host', 'Total']
        },
        'ultimos_eventos': {
            'titulo': 'Últimos 20 eventos',
            'sql': 'SELECT ReceivedAt, FromHost, SysLogTag, LEFT(Message,80) as Mensaje FROM SystemEvents ORDER BY ID DESC LIMIT 20',
            'columnas': ['Fecha', 'Host', 'Servicio', 'Mensaje']
        },
        'por_severidad': {
            'titulo': 'Logs por severidad',
            'sql': 'SELECT CASE Priority WHEN 0 THEN "Emergency" WHEN 1 THEN "Alert" WHEN 2 THEN "Critical" WHEN 3 THEN "Error" WHEN 4 THEN "Warning" WHEN 5 THEN "Notice" WHEN 6 THEN "Info" WHEN 7 THEN "Debug" ELSE "Desconocido" END as Severidad, COUNT(*) as Total FROM SystemEvents GROUP BY Priority ORDER BY Priority',
            'columnas': ['Severidad', 'Total']
        },
        'ultimas_24h': {
            'titulo': 'Actividad últimas 24 horas',
            'sql': 'SELECT DATE_FORMAT(ReceivedAt, "%H:00") as Hora, COUNT(*) as Total FROM SystemEvents WHERE ReceivedAt >= NOW() - INTERVAL 24 HOUR GROUP BY Hora ORDER BY Hora',
            'columnas': ['Hora', 'Total']
        }
    }

    if consulta not in consultas:
        return render_template('partials/mysql.html', error="Consulta no válida",
                               filas=[], columnas=[], titulo='')

    config = consultas[consulta]
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute(config['sql'])
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('partials/mysql.html',
                               titulo=config['titulo'],
                               columnas=config['columnas'],
                               filas=filas,
                               consulta=consulta,
                               timestamp=datetime.now().strftime('%H:%M:%S'))
    except Exception as e:
        return render_template('partials/mysql.html',
                               error=str(e), filas=[], columnas=[],
                               titulo=config['titulo'])

# ─── API: PRUEBAS CONECTIVIDAD ────────────────────────────────────────────────
@app.route('/api/test/<prueba>', methods=['POST'])
def api_test(prueba):
    """Ejecuta pruebas de conectividad desde client01"""
    pruebas = {
        'ssh': {
            'descripcion': 'Conectividad SSH a ssh01 (192.168.100.10:22)',
            'contenedor': 'client01',
            'comando': 'bash -c "cat < /dev/null > /dev/tcp/192.168.100.10/22 && echo Puerto 22 abierto"'
        },
        'dns': {
            'descripcion': 'Resolución DNS laboratorio.local',
            'contenedor': 'client01',
            'comando': 'nslookup web01.laboratorio.local 192.168.100.20'
        },
        'http': {
            'descripcion': 'Acceso HTTPS a web01 via proxy01',
            'contenedor': 'client01',
            'comando': 'curl -sk -o /dev/null -w %{http_code} --max-time 5 https://172.21.0.10'
        },
        'squid': {
            'descripcion': 'Proxy Squid hacia internet',
            'contenedor': 'client01',
            'comando': 'curl -s -x http://192.168.100.40:3128 -o /dev/null -w %{http_code} --max-time 10 http://example.com'
        },
        'dhcp': {
            'descripcion': 'Servidor DHCP activo',
            'contenedor': 'dhcp01',
            'comando': 'pgrep dhcpd && echo DHCP activo'
        }
    }

    if prueba not in pruebas:
        return render_template('partials/test_resultado.html',
                               ok=False, descripcion='Prueba no válida', output='',
                               timestamp=datetime.now().strftime('%H:%M:%S'))

    config = pruebas[prueba]
    out, rc = docker_exec(config['contenedor'], config['comando'])

    ok = rc == 0
    if prueba in ['http', 'squid'] and out in ['200', '301', '302']:
        ok = True
    elif prueba in ['http', 'squid']:
        ok = False

    return render_template('partials/test_resultado.html',
                           ok=ok,
                           descripcion=config['descripcion'],
                           output=out,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

# ─── API: ANSIBLE ─────────────────────────────────────────────────────────────
@app.route('/api/ansible/<tag>', methods=['POST'])
def api_ansible(tag):
    """Ejecuta ansible-playbook en el host via docker exec al contenedor host"""
    tags_permitidos = ['ssh', 'dns', 'dhcp', 'web', 'proxy', 'squid',
                       'syslog', 'mysql', 'firewall', 'postdeploy']
    if tag not in tags_permitidos:
        return render_template('partials/ansible.html',
                               ok=False, output='Tag no permitido', tag=tag,
                               timestamp=datetime.now().strftime('%H:%M:%S'))
    try:
        # Ejecutamos ansible-playbook en el HOST via el socket Docker
        # usando docker run con la imagen del panel que tiene ansible instalado
        result = subprocess.run(
            ['ansible-playbook', '/ansible/site.yml', f'--tags={tag}'],
            capture_output=True, text=True, timeout=180,
            cwd='/ansible'
        )
        ok = result.returncode == 0
        output = result.stdout + result.stderr
        return render_template('partials/ansible.html',
                               ok=ok, output=output, tag=tag,
                               timestamp=datetime.now().strftime('%H:%M:%S'))
    except subprocess.TimeoutExpired:
        return render_template('partials/ansible.html',
                               ok=False, output='Timeout (180s)', tag=tag,
                               timestamp=datetime.now().strftime('%H:%M:%S'))
    except Exception as e:
        return render_template('partials/ansible.html',
                               ok=False, output=str(e), tag=tag,
                               timestamp=datetime.now().strftime('%H:%M:%S'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
