-- ============================================================
-- Schema de base de datos para rsyslog - TFG ASIR
-- Este script se ejecuta automáticamente la primera vez
-- que el contenedor mysql01 arranca (vía docker-entrypoint-initdb.d)
-- ============================================================

-- Crear base de datos Syslog (nombre estándar para rsyslog)
CREATE DATABASE IF NOT EXISTS Syslog
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE Syslog;

-- ────────────────────────────────────────────────────────────
-- Tabla SystemEvents: schema estándar de rsyslog-mysql
-- Define los eventos recibidos de los clientes syslog
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS SystemEvents (
    ID INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    CustomerID BIGINT,
    ReceivedAt DATETIME NULL,
    DeviceReportedTime DATETIME NULL,
    Facility SMALLINT NULL,
    Priority SMALLINT NULL,
    FromHost VARCHAR(60) NULL,
    Message TEXT,
    NTSeverity INT NULL,
    Importance INT NULL,
    EventSource VARCHAR(60),
    EventUser VARCHAR(60) NULL,
    EventCategory INT NULL,
    EventID INT NULL,
    EventBinaryData TEXT NULL,
    MaxAvailable INT NULL,
    CurrUsage INT NULL,
    MinUsage INT NULL,
    MaxUsage INT NULL,
    InfoUnitID INT NULL,
    SysLogTag VARCHAR(60),
    EventLogType VARCHAR(60),
    GenericFileName VARCHAR(60),
    SystemID INT NULL,
    INDEX idx_receivedat (ReceivedAt),
    INDEX idx_fromhost (FromHost),
    INDEX idx_priority (Priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ────────────────────────────────────────────────────────────
-- Tabla SystemEventsProperties: propiedades adicionales
-- Schema estándar de rsyslog, necesaria aunque rara vez se use
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS SystemEventsProperties (
    ID INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    SystemEventID INT NULL,
    ParamName VARCHAR(255) NULL,
    ParamValue TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ────────────────────────────────────────────────────────────
-- Usuario rsyslog: permisos mínimos sobre la base de datos Syslog
-- SOLO puede INSERTAR y SELECT, no puede modificar estructura
-- ────────────────────────────────────────────────────────────
CREATE USER IF NOT EXISTS 'rsyslog'@'%' IDENTIFIED BY 'Rsyslog_TFG_2026!';
GRANT SELECT, INSERT ON Syslog.* TO 'rsyslog'@'%';

FLUSH PRIVILEGES;
