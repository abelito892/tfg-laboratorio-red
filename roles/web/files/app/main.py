from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
import os

app = FastAPI(title="NetCorp API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "172.23.0.10"),
        user=os.getenv("MYSQL_USER", "netcorp"),
        password=os.getenv("MYSQL_PASSWORD", "NetCorp_TFG_2026!"),
        database="NetCorp",
        connection_timeout=5
    )

def get_client_ip(request: Request) -> str:
    # nginx sets X-Real-IP to the remote addr before proxying to uvicorn
    return (
        request.headers.get("X-Real-IP") or
        (request.headers.get("X-Forwarded-For", "").split(",")[0].strip()) or
        (request.client.host if request.client else "0.0.0.0")
    )

def log_access(ip: str, servicio: str, accion: str):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO accesos (ip_origen, servicio, accion) VALUES (%s, %s, %s)",
            (ip, servicio, accion)
        )
        db.commit()
        db.close()
    except Exception:
        pass

@app.get("/api/health")
async def health(request: Request):
    ip = get_client_ip(request)
    log_access(ip, "intranet", "GET /api/health")
    return {"status": "ok", "service": "NetCorp API", "version": "1.0.0"}

@app.get("/api/empleados")
async def get_empleados(request: Request):
    ip = get_client_ip(request)
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT e.id, e.nombre, e.apellidos, e.email, e.puesto, "
        "d.nombre as departamento FROM empleados e "
        "JOIN departamentos d ON e.departamento_id = d.id "
        "WHERE e.activo = 1 ORDER BY d.nombre, e.apellidos"
    )
    rows = cur.fetchall()
    db.close()
    log_access(ip, "intranet", "GET /api/empleados")
    return {"empleados": rows, "total": len(rows)}

@app.get("/api/departamentos")
async def get_departamentos(request: Request):
    ip = get_client_ip(request)
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, nombre, descripcion FROM departamentos ORDER BY nombre")
    rows = cur.fetchall()
    db.close()
    log_access(ip, "intranet", "GET /api/departamentos")
    return {"departamentos": rows}

@app.get("/api/accesos")
async def get_accesos():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT id, ip_origen, servicio, accion, "
        "CAST(timestamp AS CHAR) as timestamp, resultado "
        "FROM accesos ORDER BY timestamp DESC LIMIT 50"
    )
    rows = cur.fetchall()
    db.close()
    return {"accesos": rows}

@app.get("/api/stats")
async def get_stats():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) as n FROM empleados WHERE activo=1")
    emp = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) as n FROM accesos")
    acc = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) as n FROM departamentos")
    dep = cur.fetchone()["n"]
    db.close()
    return {"empleados": emp, "accesos": acc, "departamentos": dep}
