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
    'user': 'netcorp',
    'password': 'NetCorp_TFG_2026!',
    'database': 'NetCorp',
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
            'titulo': 'Accesos por IP origen',
            'sql': 'SELECT ip_origen, COUNT(*) as Total FROM accesos GROUP BY ip_origen ORDER BY Total DESC',
            'columnas': ['IP Origen', 'Total']
        },
        'ultimos_eventos': {
            'titulo': 'Ultimos 20 accesos',
            'sql': 'SELECT CAST(timestamp AS CHAR), ip_origen, servicio, accion FROM accesos ORDER BY id DESC LIMIT 20',
            'columnas': ['Fecha', 'IP Origen', 'Servicio', 'Accion']
        },
        'por_severidad': {
            'titulo': 'Empleados por departamento',
            'sql': 'SELECT d.nombre, COUNT(*) as Total FROM empleados e JOIN departamentos d ON e.departamento_id=d.id GROUP BY d.nombre ORDER BY Total DESC',
            'columnas': ['Departamento', 'Total']
        },
        'ultimas_24h': {
            'titulo': 'Accesos ultimas 24 horas',
            'sql': 'SELECT DATE_FORMAT(timestamp, "%H:00") as Hora, COUNT(*) as Total FROM accesos WHERE timestamp >= NOW() - INTERVAL 24 HOUR GROUP BY Hora ORDER BY Hora',
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
        ('proxy01', '192.168.100.10', 22, 'DMZ → LAN ssh01 desde proxy01 (🚫 bloqueado)'),
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
    """Escenario 3: Flujo completo NetCorp — cliente accede a la intranet corporativa"""
    import time
    pasos = []
    ok_total = True

    # Paso 1: Solicitar IP via DHCP
    out, rc = docker_exec('client01', 'udhcpc -i eth0 -q 2>&1 | tail -3')
    ip_out, _ = docker_exec('client01', "ip addr show eth0 | grep 'inet ' | awk '{print $2}'")
    ok = bool(ip_out)
    pasos.append({'descripcion': f'IP obtenida via DHCP desde dhcp01', 'ok': ok, 'output': f'IP asignada: {ip_out}'})
    if not ok:
        ok_total = False

    # Paso 2: Resolver intranet.netcorp.local via DNS
    out, rc = docker_exec('client01', 'nslookup intranet.netcorp.local 192.168.100.20 | grep Address | tail -1')
    ok = rc == 0 and '172.21.0.10' in out
    pasos.append({'descripcion': 'DNS resuelve intranet.netcorp.local → 172.21.0.10 (proxy01)', 'ok': ok, 'output': out})
    if not ok:
        ok_total = False

    # Paso 3: Acceder a la intranet via Squid (client01 → squid01:3128 → proxy01:443 → web01)
    out, rc = docker_exec('client01',
        'curl -sk --max-time 15 --proxy http://192.168.100.40:3128 https://intranet.netcorp.local/api/health')
    ok = rc == 0 and 'ok' in out.lower()
    pasos.append({'descripcion': 'client01 → squid01:3128 → proxy01:443 → web01 (/api/health)', 'ok': ok, 'output': out})
    if not ok:
        ok_total = False

    # Paso 4: Consultar empleados via squid (registra acceso en MySQL)
    out, rc = docker_exec('client01',
        'curl -sk --max-time 15 --proxy http://192.168.100.40:3128 https://intranet.netcorp.local/api/empleados')
    ok = rc == 0 and 'empleados' in out.lower()
    pasos.append({'descripcion': 'API /api/empleados devuelve directorio NetCorp (via squid)', 'ok': ok, 'output': out[:200] if out else 'Sin respuesta'})
    if not ok:
        ok_total = False

    # Paso 5: Verificar acceso registrado en MySQL
    time.sleep(2)
    out, rc = docker_exec('mysql01', 'mysql -unetcorp -pNetCorp_TFG_2026! NetCorp -e "SELECT ip_origen, servicio, accion, timestamp FROM accesos ORDER BY id DESC LIMIT 1;" 2>/dev/null')
    ok = rc == 0 and bool(out)
    pasos.append({'descripcion': 'Acceso registrado en BD NetCorp (MySQL)', 'ok': ok, 'output': out})

    # Paso 6: Ver log en syslog01
    time.sleep(1)
    log_out, _ = docker_exec('syslog01', 'grep -v rsyslogd /var/log/laboratorio/all.log | grep -E "squid01|proxy01" | tail -3')
    pasos.append({'descripcion': 'Trafico registrado en syslog01 (all.log)', 'ok': bool(log_out), 'output': log_out})

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Flujo completo NetCorp: DHCP → DNS → Squid → Proxy → Web → MySQL',
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
    log_out, _ = docker_exec('syslog01', 'grep -v rsyslogd /var/log/laboratorio/all.log | grep proxy01 | tail -3')
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

        # Total de empleados
        cursor.execute('SELECT COUNT(*) FROM empleados WHERE activo=1')
        total = cursor.fetchone()[0]
        pasos.append({'descripcion': 'Total empleados activos en NetCorp', 'ok': True,
                      'output': f'{total} empleados'})

        # Ultimos 5 accesos
        cursor.execute(
            'SELECT CAST(timestamp AS CHAR), ip_origen, servicio, accion '
            'FROM accesos ORDER BY id DESC LIMIT 5'
        )
        rows = cursor.fetchall()
        output = '\n'.join([f'{r[0]} | {r[1]} | {r[2]} | {r[3]}' for r in rows])
        pasos.append({'descripcion': 'Ultimos 5 accesos registrados', 'ok': bool(rows),
                      'output': output})

        # Empleados por departamento
        cursor.execute(
            'SELECT d.nombre, COUNT(*) as n FROM empleados e '
            'JOIN departamentos d ON e.departamento_id=d.id GROUP BY d.nombre ORDER BY n DESC'
        )
        deps = cursor.fetchall()
        output = '\n'.join([f'{d[0]}: {d[1]} empleados' for d in deps])
        pasos.append({'descripcion': 'Empleados por departamento', 'ok': bool(deps), 'output': output})

        cursor.close()
        conn.close()

    except Exception as e:
        ok_total = False
        pasos.append({'descripcion': 'Conexion a MySQL NetCorp', 'ok': False, 'output': str(e)})

    return render_template('partials/demo_resultado.html',
                           ok=ok_total,
                           titulo='Base de datos NetCorp en tiempo real',
                           pasos=pasos,
                           log_generado=False,
                           timestamp=datetime.now().strftime('%H:%M:%S'))


# ─── NETCORP HTML PARA HTMX ───────────────────────────────────────────────────
@app.route('/api/netcorp/stats')
def netcorp_stats_html():
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) as n FROM empleados WHERE activo=1")
        emp = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as n FROM accesos")
        acc = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as n FROM departamentos")
        dep = cur.fetchone()["n"]
        cur.close(); conn.close()
        html = f"""
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;padding:1rem 0">
            <div style="text-align:center;background:var(--bg-secondary);padding:1rem;border-radius:8px">
                <div style="font-size:2rem;font-weight:bold;color:var(--accent)">{emp}</div>
                <div style="color:var(--text-secondary)">Empleados activos</div>
            </div>
            <div style="text-align:center;background:var(--bg-secondary);padding:1rem;border-radius:8px">
                <div style="font-size:2rem;font-weight:bold;color:var(--accent)">{dep}</div>
                <div style="color:var(--text-secondary)">Departamentos</div>
            </div>
            <div style="text-align:center;background:var(--bg-secondary);padding:1rem;border-radius:8px">
                <div style="font-size:2rem;font-weight:bold;color:var(--accent)">{acc}</div>
                <div style="color:var(--text-secondary)">Accesos registrados</div>
            </div>
        </div>"""
        return html
    except Exception as ex:
        return f'<p style="color:red">Error: {ex}</p>'

@app.route("/api/netcorp/empleados")
def netcorp_empleados_html():
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT e.id, e.nombre, e.apellidos, e.email, e.puesto, "
            "d.nombre as departamento, e.activo "
            "FROM empleados e JOIN departamentos d ON e.departamento_id=d.id "
            "ORDER BY d.nombre, e.apellidos"
        )
        empleados = cur.fetchall()
        cur.close(); conn.close()
        rows = []
        for e in empleados:
            estado_color = "#4caf50" if e["activo"] else "#f44336"
            estado_txt = "Activo" if e["activo"] else "Inactivo"
            opacity = "1" if e["activo"] else "0.5"
            eid = e["id"]
            if e["activo"]:
                btn_accion = (
                    f'<button hx-post="/api/netcorp/empleados/{eid}/baja" ' +
                    f'hx-target="#netcorp-content" hx-swap="innerHTML" ' +
                    f'hx-confirm="Dar de baja a {e["nombre"]}?" ' +
                    'style="background:#f44336;color:white;border:none;padding:0.2rem 0.4rem;border-radius:3px;cursor:pointer">🚫 Baja</button>'
                )
            else:
                btn_accion = (
                    f'<button hx-post="/api/netcorp/empleados/{eid}/activar" ' +
                    f'hx-target="#netcorp-content" hx-swap="innerHTML" ' +
                    'style="background:#4caf50;color:white;border:none;padding:0.2rem 0.4rem;border-radius:3px;cursor:pointer">✅ Activar</button>'
                )
            btn_editar = (
                f'<button hx-get="/api/netcorp/empleados/{eid}" ' +
                f'hx-target="#form-empleado" hx-swap="innerHTML" ' +
                'style="background:#2196f3;color:white;border:none;padding:0.2rem 0.4rem;border-radius:3px;cursor:pointer;margin-right:0.25rem">✏️ Editar</button>'
            )
            rows.append(
                f'<tr style="opacity:{opacity}">' +
                f'<td style="padding:0.4rem">{e["id"]}</td>' +
                f'<td style="padding:0.4rem">{e["nombre"]} {e["apellidos"]}</td>' +
                f'<td style="padding:0.4rem">{e["email"]}</td>' +
                f'<td style="padding:0.4rem">{e["departamento"]}</td>' +
                f'<td style="padding:0.4rem">{e["puesto"]}</td>' +
                f'<td style="padding:0.4rem"><span style="color:{estado_color}">{estado_txt}</span></td>' +
                f'<td style="padding:0.4rem;white-space:nowrap">{btn_editar}{btn_accion}</td>' +
                '</tr>'
            )
        rows_html = "".join(rows)
        return (
            f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:0.85rem">' +
            '<thead><tr style="background:var(--bg-secondary)">' +
            '<th style="padding:0.4rem;text-align:left">ID</th>' +
            '<th style="padding:0.4rem;text-align:left">Nombre</th>' +
            '<th style="padding:0.4rem;text-align:left">Email</th>' +
            '<th style="padding:0.4rem;text-align:left">Departamento</th>' +
            '<th style="padding:0.4rem;text-align:left">Puesto</th>' +
            '<th style="padding:0.4rem;text-align:left">Estado</th>' +
            '<th style="padding:0.4rem;text-align:left">Acciones</th>' +
            f'</tr></thead><tbody>{rows_html}</tbody></table></div>' +
            f'<p style="color:var(--text-secondary);margin-top:0.5rem;font-size:0.8rem">' +
            f'{len(empleados)} empleados — actualizado {datetime.now().strftime("%H:%M:%S")}</p>'
        )
    except Exception as ex:
        return f'<p style="color:red">Error: {ex}</p>'


@app.route("/api/netcorp/accesos")
def netcorp_accesos_html():
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, ip_origen, servicio, accion, "
            "CAST(timestamp AS CHAR) as timestamp, resultado "
            "FROM accesos ORDER BY timestamp DESC LIMIT 50"
        )
        accesos = cur.fetchall()
        cur.close(); conn.close()
        rows = "".join([
            f"<tr><td>{a['id']}</td><td>{a['ip_origen']}</td>"
            f"<td>{a['servicio']}</td><td>{a['accion']}</td>"
            f"<td>{a['timestamp']}</td>"
            f"<td><span style=\"color:{'green' if a['resultado']=='OK' else 'red'}\">"
            f"{a['resultado']}</span></td></tr>"
            for a in accesos
        ])
        return f"""<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse">
            <thead><tr style="background:var(--bg-secondary)">
                <th style="padding:0.5rem;text-align:left">ID</th>
                <th style="padding:0.5rem;text-align:left">IP Origen</th>
                <th style="padding:0.5rem;text-align:left">Servicio</th>
                <th style="padding:0.5rem;text-align:left">Accion</th>
                <th style="padding:0.5rem;text-align:left">Timestamp</th>
                <th style="padding:0.5rem;text-align:left">Resultado</th>
            </tr></thead><tbody>{rows}</tbody></table></div>
            <p style="color:var(--text-secondary);margin-top:0.5rem;font-size:0.8rem">
            {len(accesos)} accesos — actualizado {datetime.now().strftime("%H:%M:%S")}</p>"""
    except Exception as ex:
        return f'<p style="color:red">Error: {ex}</p>'

@app.route("/api/netcorp/empleados/nuevo", methods=["POST"])
def netcorp_empleado_nuevo_html():
    from flask import request as req
    data = req.form
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO empleados(nombre,apellidos,email,usuario,departamento_id,puesto) "
            "VALUES(%s,%s,%s,%s,%s,%s)",
            (data["nombre"], data["apellidos"], data["email"],
             data["usuario"], data["departamento_id"], data["puesto"])
        )
        conn.commit()
        cur.close(); conn.close()
        # Devolver lista actualizada
        return netcorp_empleados_html()
    except Exception as ex:
        return f'<p style="color:red">Error al dar de alta: {ex}</p>'


# ─── TERMINAL INTERACTIVA ────────────────────────────────────────────────────
import re as _re

def _sanitizar_comando(cmd):
    """Ajusta comandos que bloquearían la terminal indefinidamente."""
    cmd = cmd.strip()
    # ping sin -c: añadir -c 4
    if _re.match(r'^ping(\s+)', cmd) and '-c' not in cmd:
        cmd = _re.sub(r'^ping(\s+)', r'ping -c 4 \1', cmd, count=1).replace('-c 4  ', '-c 4 ')
    # tail sin -n ni --lines: limitar a 20 líneas
    if _re.match(r'^tail(\s+)', cmd) and '-n' not in cmd and '--lines' not in cmd and '-f' not in cmd and '-F' not in cmd:
        cmd = _re.sub(r'^tail(\s+)', r'tail -n 20 \1', cmd, count=1)
    return cmd

@app.route('/api/terminal', methods=['POST'])
def api_terminal():
    from flask import request as req
    contenedor = req.form.get('contenedor', 'client01')
    comando_original = req.form.get('comando', 'echo hola').strip()

    contenedores_permitidos = [
        'fw01', 'ssh01', 'dns01', 'dhcp01', 'web01', 'proxy01',
        'squid01', 'client01', 'syslog01', 'mysql01', 'panel01'
    ]
    if contenedor not in contenedores_permitidos:
        return '<pre style="color:red">Contenedor no permitido</pre>'
    if not comando_original:
        return ''

    comando = _sanitizar_comando(comando_original)
    aviso = ''
    if comando != comando_original:
        aviso = f'<div style="color:#f0ad4e;font-family:monospace;font-size:0.8rem;margin-bottom:0.25rem">⚠ Ajustado: {comando}</div>'

    out, rc = docker_exec(contenedor, comando)
    color = 'var(--text-primary)' if rc == 0 else '#ff6b6b'
    timestamp = datetime.now().strftime('%H:%M:%S')

    import html as _html
    out_escaped = _html.escape(out) if out else '<span style="color:#666">(sin output)</span>'

    return f"""
    <div style="margin-bottom:0.25rem">
        <span style="color:var(--accent);font-family:monospace">{timestamp} [{contenedor}]$</span>
        <span style="color:#aaa;font-family:monospace"> {_html.escape(comando_original)}</span>
    </div>
    {aviso}<pre style="color:{color};background:transparent;margin:0 0 0.25rem 0;white-space:pre-wrap;font-family:monospace;font-size:0.85rem">{out_escaped}</pre>
    <hr style="border-color:var(--border);margin:0.5rem 0">
    """


# ─── NETCORP CRUD EMPLEADOS ───────────────────────────────────────────────────
@app.route("/api/netcorp/empleados/<int:emp_id>/baja", methods=["POST"])
def netcorp_empleado_baja(emp_id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("UPDATE empleados SET activo=0 WHERE id=%s", (emp_id,))
        conn.commit()
        cur.close(); conn.close()
        return netcorp_empleados_html()
    except Exception as ex:
        return f'<p style="color:red">Error: {ex}</p>'

@app.route("/api/netcorp/empleados/<int:emp_id>/activar", methods=["POST"])
def netcorp_empleado_activar(emp_id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("UPDATE empleados SET activo=1 WHERE id=%s", (emp_id,))
        conn.commit()
        cur.close(); conn.close()
        return netcorp_empleados_html()
    except Exception as ex:
        return f'<p style="color:red">Error: {ex}</p>'

@app.route("/api/netcorp/empleados/<int:emp_id>", methods=["GET"])
def netcorp_empleado_get(emp_id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM empleados WHERE id=%s", (emp_id,))
        emp = cur.fetchone()
        cur.close(); conn.close()
        if not emp:
            return '<p style="color:red">Empleado no encontrado</p>'
        deps = [
            (1,"IT"),(2,"Comercial"),(3,"RRHH"),(4,"Administracion")
        ]
        opts = "".join([
            f'<option value="{d[0]}" {"selected" if d[0]==emp["departamento_id"] else ""}>{d[1]}</option>'
            for d in deps
        ])
        return f"""
        <div style="background:var(--bg-secondary);padding:1rem;border-radius:8px;margin-bottom:1rem">
            <h3 style="margin-bottom:1rem">Editar empleado #{emp_id}</h3>
            <form hx-post="/api/netcorp/empleados/{emp_id}/editar"
                  hx-target="#netcorp-content"
                  hx-swap="innerHTML"
                  style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem">
                <input type="text" name="nombre" value="{emp["nombre"]}" placeholder="Nombre" required
                       style="padding:0.5rem;border:1px solid var(--border);border-radius:4px;background:var(--bg-primary);color:var(--text-primary)">
                <input type="text" name="apellidos" value="{emp["apellidos"]}" placeholder="Apellidos" required
                       style="padding:0.5rem;border:1px solid var(--border);border-radius:4px;background:var(--bg-primary);color:var(--text-primary)">
                <input type="email" name="email" value="{emp["email"]}" placeholder="Email" required
                       style="padding:0.5rem;border:1px solid var(--border);border-radius:4px;background:var(--bg-primary);color:var(--text-primary)">
                <input type="text" name="usuario" value="{emp["usuario"]}" placeholder="Usuario" required
                       style="padding:0.5rem;border:1px solid var(--border);border-radius:4px;background:var(--bg-primary);color:var(--text-primary)">
                <input type="text" name="puesto" value="{emp["puesto"] or ""}" placeholder="Puesto"
                       style="padding:0.5rem;border:1px solid var(--border);border-radius:4px;background:var(--bg-primary);color:var(--text-primary)">
                <select name="departamento_id"
                        style="padding:0.5rem;border:1px solid var(--border);border-radius:4px;background:var(--bg-primary);color:var(--text-primary)">
                    {opts}
                </select>
                <button type="submit" class="btn btn-primary" style="grid-column:span 2">💾 Guardar cambios</button>
            </form>
        </div>
        """
    except Exception as ex:
        return f'<p style="color:red">Error: {ex}</p>'

@app.route("/api/netcorp/empleados/<int:emp_id>/editar", methods=["POST"])
def netcorp_empleado_editar(emp_id):
    from flask import request as req
    data = req.form
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE empleados SET nombre=%s, apellidos=%s, email=%s, usuario=%s, puesto=%s, departamento_id=%s WHERE id=%s",
            (data["nombre"], data["apellidos"], data["email"],
             data["usuario"], data["puesto"], data["departamento_id"], emp_id)
        )
        conn.commit()
        cur.close(); conn.close()
        return netcorp_empleados_html()
    except Exception as ex:
        return f'<p style="color:red">Error al editar: {ex}</p>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
