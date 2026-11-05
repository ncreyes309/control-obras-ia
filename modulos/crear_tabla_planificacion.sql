-- Ejecutar UNA vez en la consola de Cloud SQL.
-- Planificación diaria: qué empleados van a qué obra en cada fecha.
-- Un empleado puede aparecer en varias obras el mismo día (una fila por obra).

CREATE TABLE IF NOT EXISTS planificacion_diaria (
    id           SERIAL PRIMARY KEY,
    fecha        DATE    NOT NULL,
    obra_id      INTEGER NOT NULL REFERENCES obras(id),
    empleado_id  INTEGER NOT NULL REFERENCES empleados(id),
    UNIQUE (fecha, obra_id, empleado_id)
);

CREATE INDEX IF NOT EXISTS ix_planificacion_fecha ON planificacion_diaria (fecha);

-- La tabla empleado_obra (desde/hasta) ya no se usa. Si no tiene datos que quieras conservar:
-- DROP TABLE IF EXISTS empleado_obra;
