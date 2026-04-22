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
    try:
        result = subprocess.run(
            comando, capture_output=True, text=True,
            timeout=15, shell=True
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def get_mysql_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

def test_conexion(contenedor, ip, puerto, debe_conectar=True):
    """Prueba conexión TCP con timeout de 3s"""
    cmd = f"timeout 3 bash -c 'cat < /dev/null > /dev/tcp/{ip}/{puerto}' 2>&1; echo rc=$?"
    out, _ = docker_exec(contenedor, cmd)
    conecta = 'rc=0' in out
    if debe_conectar:
        return conecta, '✅ Permitido' if conecta else '❌ Bloqueado (error)'
    else:
        return not conecta, '✅ Bloqueado' if not conecta else '❌ Permitido (error)'

# ─── RUTAS PRINCIPALES ───────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ─── API: ESTADO CONTENEDORES ────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
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

# ─── API: FIREWALL ────────────────────────────────────────────────────────────
@app.route('/api/firewall')
def api_firewall():
    """Ejecuta todas las pruebas de firewall y devuelve resultados"""
    resultados = []

    # Pruebas de tráfico PERMITIDO
    pruebas_permitidas = [
        ('client01', '172.21.0.10', 80,  'LAN → proxy01 HTTP (✅ debe funcionar)'),
        ('client01', '172.21.0.10', 443, 'LAN → proxy01 HTTPS (✅ debe funcionar)'),
        ('client01', '192.168.100.10', 22, 'LAN → SSH ssh01 (✅ debe funcionar)'),
        ('client01', '192.168.100.20', 53, 'LAN → DNS dns01 (✅ debe funcionar)'),
        ('proxy01',  '172.21.0.20', 443, 'DMZ proxy01 → web01 (✅ debe funcionar)'),
    ]

    for contenedor, ip, puerto, desc in pruebas_permitidas:
        ok, estado = test_conexion(contenedor, ip, puerto, debe_conectar=True)
        resultados.append({
            'descripcion': desc,
            'ok': ok,
            'estado': estado,
            'tipo': 'permitido'
        })

    # Pruebas de tráfico BLOQUEADO
    pruebas_bloqueadas = [
        ('proxy01', '192.168.100.10', 22, 'DMZ → LAN ssh01 (🚫 debe estar bloqueado)'),
        ('web01',   '192.168.100.10', 22, 'DMZ → LAN ssh01 desde web01 (🚫 bloqueado)'),
        ('proxy01', '192.168.100.20', 53, 'DMZ → LAN dns01 (🚫 debe estar bloqueado)'),
        ('client01','172.21.0.20', 443,   'LAN → web01 directo HTTPS (🚫 bloqueado)'),
        ('client01','172.21.0.20', 80,    'LAN → web01 directo HTTP (🚫 bloqueado)'),
    ]

    for contenedor, ip, puerto, desc in pruebas_bloqueadas:
        ok, estado = test_conexion(contenedor, ip, puerto, debe_conectar=False)
        resultados.append({
            'descripcion': desc,
            'ok': ok,
            'estado': estado,
            'tipo': 'bloqueado'
        })

    # Ruleset activo de fw01
    ruleset, _ = docker_exec('fw01', 'nft list ruleset')

    total = len(resultados)
    correctos = sum(1 for r in resultados if r['ok'])

    return render_template('partials/firewall.html',
                           resultados=resultados,
                           ruleset=ruleset,
                           total=total,
                           correctos=correctos,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

# ─── API: ANSIBLE ─────────────────────────────────────────────────────────────
@app.route('/api/ansible/<tag>', methods=['POST'])
def api_ansible(tag):
    tags_permitidos = ['ssh', 'dns', 'dhcp', 'web', 'proxy', 'squid',
                       'syslog', 'mysql', 'firewall', 'postdeploy']
    if tag not in tags_permitidos:
        return render_template('partials/ansible.html',
                               ok=False, output='Tag no permitido', tag=tag,
                               timestamp=datetime.now().strftime('%H:%M:%S'))
    try:
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


# ─── API: DEMO ────────────────────────────────────────────────────────────────
SSH_PASS = 'TFG2026lab'
SSH_USER = 'ubuntu'
SSH_HOST = '192.168.100.10'

@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/api/demo/ssh', methods=['POST'])
def demo_ssh():
    """Escenario 1: Sesión SSH real desde client01 a ssh01"""
    pasos = []
    ok_total = True

    # Paso 1: Verificar conectividad
    out, rc = docker_exec('client01',
        f'timeout 3 bash -c "cat < /dev/null > /dev/tcp/{SSH_HOST}/22" && echo OK')
    pasos.append({'descripcion': f'Conectividad TCP a {SSH_HOST}:22', 'ok': rc==0, 'output': ''})
    if rc != 0:
        ok_total = False

    # Paso 2: Ejecutar comandos via SSH
    cmd = f"sshpass -p '{SSH_PASS}' ssh -o StrictHostKeyChecking=no {SSH_USER}@{SSH_HOST} 'echo === USUARIO: $(whoami) === && echo === HOSTNAME: $(hostname) === && echo === FECHA: $(date) === && echo === UPTIME: $(uptime -p) ==='"
    out, rc = docker_exec('client01', cmd)
    pasos.append({'descripcion': 'Sesión SSH ejecutada correctamente', 'ok': rc==0, 'output': out})
    if rc != 0:
        ok_total = False

    # Paso 3: Verificar log
    import time; time.sleep(2)
    log_out, _ = docker_exec('syslog01', 'tail -3 /var/log/laboratorio/ssh.log')
    pasos.append({'descripcion': 'Acceso registrado en ssh.log', 'ok': bool(log_out), 'output': log_out})

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Sesión SSH desde client01 a ssh01',
                           pasos=pasos,
                           log_generado=True,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

@app.route('/api/demo/scp', methods=['POST'])
def demo_scp():
    """Escenario 2: Transferencia de fichero via SCP"""
    pasos = []
    ok_total = True

    # Paso 1: Crear fichero en client01
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    fichero = f'/tmp/tfg_demo_{marca}.txt'
    contenido = f'Fichero de demo TFG ASIR - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    out, rc = docker_exec('client01', f'echo "{contenido}" > {fichero} && echo OK')
    pasos.append({'descripcion': f'Fichero creado en client01: {fichero}', 'ok': rc==0, 'output': contenido})
    if rc != 0:
        ok_total = False

    # Paso 2: Transferir via SCP
    cmd = f"sshpass -p '{SSH_PASS}' scp -o StrictHostKeyChecking=no {fichero} {SSH_USER}@{SSH_HOST}:/tmp/"
    out, rc = docker_exec('client01', cmd)
    pasos.append({'descripcion': f'SCP a {SSH_HOST}:/tmp/', 'ok': rc==0, 'output': out or 'Transferencia completada'})
    if rc != 0:
        ok_total = False

    # Paso 3: Verificar que llegó
    nombre_fichero = fichero.split('/')[-1]
    out, rc = docker_exec('ssh01', f'cat /tmp/{nombre_fichero}')
    pasos.append({'descripcion': 'Fichero verificado en ssh01', 'ok': rc==0, 'output': out})
    if rc != 0:
        ok_total = False

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Transferencia SCP de client01 a ssh01',
                           pasos=pasos,
                           log_generado=True,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

@app.route('/api/demo/navegacion', methods=['POST'])
def demo_navegacion():
    """Escenario 3: Navegación web via Squid"""
    pasos = []
    ok_total = True

    # Paso 1: Verificar Squid
    out, rc = docker_exec('client01',
        'timeout 3 bash -c "cat < /dev/null > /dev/tcp/192.168.100.40/3128" && echo OK')
    pasos.append({'descripcion': 'Conectividad a squid01 (192.168.100.40:3128)', 'ok': rc==0, 'output': ''})

    # Paso 2: Navegar via Squid
    out, rc = docker_exec('client01',
        'curl -s -x http://192.168.100.40:3128 --max-time 10 http://example.com | head -20')
    ok = rc == 0 and 'html' in out.lower()
    pasos.append({'descripcion': 'Descarga de http://example.com via squid01', 'ok': ok, 'output': out[:300] if out else 'Sin respuesta'})
    if not ok:
        ok_total = False

    # Paso 3: Ver log de squid
    import time; time.sleep(2)
    log_out, _ = docker_exec('syslog01', 'grep -v rsyslogd /var/log/laboratorio/squid.log | tail -3')
    pasos.append({'descripcion': 'Acceso registrado en squid.log', 'ok': bool(log_out), 'output': log_out})

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Navegación web via proxy Squid',
                           pasos=pasos,
                           log_generado=True,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

@app.route('/api/demo/dns', methods=['POST'])
def demo_dns():
    """Escenario 4: Resolución DNS interna"""
    pasos = []
    ok_total = True

    nombres = [
        ('ssh01.laboratorio.local',   '192.168.100.10'),
        ('dns01.laboratorio.local',   '192.168.100.20'),
        ('dhcp01.laboratorio.local',  '192.168.100.30'),
        ('web01.laboratorio.local',   '172.21.0.20'),
        ('proxy01.laboratorio.local', '172.21.0.10'),
        ('squid01.laboratorio.local', '192.168.100.40'),
    ]

    for nombre, ip_esperada in nombres:
        out, rc = docker_exec('client01',
            f'nslookup {nombre} 192.168.100.20 | grep -A1 "Name:" | grep Address | awk \'{{print $2}}\'')
        ip_resuelta = out.strip()
        ok = ip_resuelta == ip_esperada
        if not ok:
            ok_total = False
        pasos.append({
            'descripcion': f'{nombre}',
            'ok': ok,
            'output': f'Esperada: {ip_esperada} → Resuelta: {ip_resuelta if ip_resuelta else "sin respuesta"}'
        })

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Resolución DNS interna del laboratorio',
                           pasos=pasos,
                           log_generado=False,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

@app.route('/api/demo/dhcp', methods=['POST'])
def demo_dhcp():
    """Escenario 5: Asignación DHCP"""
    pasos = []
    ok_total = True

    # Paso 1: Verificar DHCP activo
    out, rc = docker_exec('dhcp01', 'pgrep dhcpd && echo DHCP activo')
    pasos.append({'descripcion': 'Servidor DHCP activo en dhcp01', 'ok': rc==0, 'output': out})

    # Paso 2: Solicitar IP via udhcpc
    out, rc = docker_exec('client01', 'udhcpc -i eth0 -q 2>&1')
    ok = rc == 0 and 'obtained' in out.lower()
    pasos.append({'descripcion': 'Solicitud DHCP desde client01', 'ok': ok, 'output': out})
    if not ok:
        ok_total = False

    # Paso 3: Ver IP asignada
    out, rc = docker_exec('client01', 'ip addr show eth0 | grep "inet " | awk \'{print $2}\'')
    pasos.append({'descripcion': 'IP asignada a client01', 'ok': bool(out), 'output': out})

    # Paso 4: Ver lease en dhcp01
    import time; time.sleep(2)
    out, rc = docker_exec('dhcp01',
        'grep -A6 "binding state active" /var/lib/dhcp/dhcpd.leases | tail -6')
    pasos.append({'descripcion': 'Lease registrado en dhcpd.leases', 'ok': bool(out), 'output': out})

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Asignación de IP dinámica via DHCP',
                           pasos=pasos,
                           log_generado=True,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

@app.route('/api/demo/proxy', methods=['POST'])
def demo_proxy():
    """Escenario 6: Acceso web via proxy inverso"""
    pasos = []
    ok_total = True

    # Paso 1: Conectividad a proxy01
    out, rc = docker_exec('client01',
        'timeout 3 bash -c "cat < /dev/null > /dev/tcp/172.21.0.10/443" && echo OK')
    pasos.append({'descripcion': 'Conectividad HTTPS a proxy01 (172.21.0.10:443)', 'ok': rc==0, 'output': ''})

    # Paso 2: Petición HTTPS via proxy inverso
    out, rc = docker_exec('client01',
        'curl -sk --max-time 10 https://172.21.0.10 | grep -o "<title>.*</title>" | head -1')
    ok = rc == 0 and bool(out)
    pasos.append({'descripcion': 'Petición HTTPS a proxy01 → web01', 'ok': ok,
                  'output': f'Título recibido: {out}' if out else 'Sin título en respuesta'})
    if not ok:
        ok_total = False

    # Paso 3: Código HTTP
    out, rc = docker_exec('client01',
        'curl -sk -o /dev/null -w "%{http_code}" --max-time 10 https://172.21.0.10')
    pasos.append({'descripcion': f'Código HTTP recibido', 'ok': out in ['200','301','302'],
                  'output': f'HTTP {out}'})

    # Paso 4: Ver log proxy
    import time; time.sleep(2)
    log_out, _ = docker_exec('syslog01', 'grep -v rsyslogd /var/log/laboratorio/proxy.log | tail -3')
    pasos.append({'descripcion': 'Acceso registrado en proxy.log', 'ok': bool(log_out), 'output': log_out})

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Acceso web via proxy inverso (proxy01 → web01)',
                           pasos=pasos,
                           log_generado=True,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

@app.route('/api/demo/mysql_demo')
def demo_mysql():
    """Escenario 7: Logs en MySQL en tiempo real"""
    pasos = []
    ok_total = True

    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()

        # Total de registros
        cursor.execute('SELECT COUNT(*) FROM SystemEvents')
        total = cursor.fetchone()[0]
        pasos.append({'descripcion': 'Total de eventos en SystemEvents', 'ok': True,
                      'output': f'{total} registros'})

        # Últimos 5 eventos
        cursor.execute('''
            SELECT ReceivedAt, FromHost, SysLogTag, LEFT(Message, 60)
            FROM SystemEvents ORDER BY ID DESC LIMIT 5
        ''')
        rows = cursor.fetchall()
        output = '\n'.join([f'{r[0]} | {r[1]} | {r[2]} | {r[3]}' for r in rows])
        pasos.append({'descripcion': 'Últimos 5 eventos registrados', 'ok': bool(rows),
                      'output': output})

        # Hosts que han enviado logs
        cursor.execute('SELECT FromHost, COUNT(*) as n FROM SystemEvents GROUP BY FromHost ORDER BY n DESC')
        hosts = cursor.fetchall()
        output = '\n'.join([f'{h[0]}: {h[1]} eventos' for h in hosts])
        pasos.append({'descripcion': 'Eventos por host origen', 'ok': bool(hosts), 'output': output})

        cursor.close()
        conn.close()

    except Exception as e:
        ok_total = False
        pasos.append({'descripcion': 'Conexión a MySQL', 'ok': False, 'output': str(e)})

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Consulta MySQL — SystemEvents en tiempo real',
                           pasos=pasos,
                           log_generado=False,
                           timestamp=datetime.now().strftime('%H:%M:%S'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
