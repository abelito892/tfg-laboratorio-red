CREATE DATABASE IF NOT EXISTS NetCorp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE NetCorp;

CREATE USER IF NOT EXISTS 'netcorp'@'%' IDENTIFIED BY 'NetCorp_TFG_2026!';
GRANT SELECT, INSERT, UPDATE, DELETE ON NetCorp.* TO 'netcorp'@'%';
FLUSH PRIVILEGES;

CREATE TABLE departamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT
);

CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellidos VARCHAR(150) NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    usuario VARCHAR(50) UNIQUE NOT NULL,
    departamento_id INT,
    puesto VARCHAR(150),
    fecha_alta DATE DEFAULT (CURRENT_DATE),
    activo TINYINT(1) DEFAULT 1,
    FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
);

CREATE TABLE accesos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT,
    ip_origen VARCHAR(45) NOT NULL,
    servicio VARCHAR(100) NOT NULL DEFAULT 'intranet',
    accion VARCHAR(100) DEFAULT 'GET /',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    resultado VARCHAR(20) DEFAULT 'OK',
    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
);

INSERT INTO departamentos (nombre, descripcion) VALUES
    ('IT', 'Infraestructura y sistemas informaticos'),
    ('Comercial', 'Ventas y atencion al cliente'),
    ('RRHH', 'Recursos humanos y nominas'),
    ('Administracion', 'Gestion administrativa y contabilidad');

INSERT INTO empleados (nombre,apellidos,email,usuario,departamento_id,puesto) VALUES
('Abel','Banos Garcia','abel.banos@netcorp.local','abanos',1,'Administrador de Sistemas'),
('Daniel','Montero Lopez','daniel.montero@netcorp.local','dmontero',2,'Responsable Comercial'),
('Amina','Sefiani Benali','amina.sefiani@netcorp.local','asefiani',3,'Tecnico RRHH'),
('Laura','Gomez Ruiz','laura.gomez@netcorp.local','lgomez',1,'Desarrolladora Backend'),
('Carlos','Fernandez Pena','carlos.fernandez@netcorp.local','cfernandez',2,'Agente Comercial'),
('Sofia','Martinez Alba','sofia.martinez@netcorp.local','smartinez',4,'Contable'),
('Miguel','Torres Vidal','miguel.torres@netcorp.local','mtorres',1,'Tecnico de Redes'),
('Elena','Sanchez Mora','elena.sanchez@netcorp.local','esanchez',3,'Directora RRHH'),
('Pablo','Jimenez Castro','pablo.jimenez@netcorp.local','pjimenez',2,'Director Comercial'),
('Maria','Lopez Herrera','maria.lopez@netcorp.local','mlopez',4,'Directora Administracion'),
('Jorge','Ruiz Navarro','jorge.ruiz@netcorp.local','jruiz',1,'DevOps Engineer'),
('Ana','Perez Delgado','ana.perez@netcorp.local','aperez',3,'Tecnico Seleccion'),
('Luis','Garcia Blanco','luis.garcia@netcorp.local','lgarcia',2,'Agente Comercial'),
('Carmen','Moreno Iglesias','carmen.moreno@netcorp.local','cmoreno',4,'Auxiliar Administrativo'),
('David','Alvarez Santos','david.alvarez@netcorp.local','dalvarez',1,'Tecnico Helpdesk');

INSERT INTO accesos (empleado_id, ip_origen, servicio, accion, resultado) VALUES
(1, '192.168.100.50', 'intranet', 'GET /api/empleados',    'OK'),
(2, '192.168.100.51', 'intranet', 'GET /api/empleados',    'OK'),
(5, '192.168.100.52', 'intranet', 'GET /api/empleados',    'OK'),
(3, '192.168.100.53', 'intranet', 'GET /api/health',       'OK'),
(7, '192.168.100.50', 'ssh',      'LOGIN ubuntu',           'OK'),
(1, '192.168.100.50', 'intranet', 'GET /api/stats',        'OK'),
(9, '192.168.100.54', 'intranet', 'GET /api/empleados',    'OK'),
(4, '192.168.100.51', 'intranet', 'GET /api/departamentos','OK'),
(6, '192.168.100.55', 'intranet', 'GET /api/empleados',    'OK'),
(11,'192.168.100.50', 'ssh',      'LOGIN ubuntu',           'OK'),
(2, '192.168.100.51', 'intranet', 'GET /api/health',       'OK'),
(8, '192.168.100.56', 'intranet', 'GET /api/empleados',    'OK'),
(1, '192.168.100.50', 'intranet', 'GET /api/empleados',    'OK'),
(13,'192.168.100.57', 'intranet', 'GET /api/stats',        'OK'),
(10,'192.168.100.54', 'intranet', 'GET /api/departamentos','OK');
