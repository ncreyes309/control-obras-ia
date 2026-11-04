-- Ejecutar UNA vez en la consola de Cloud SQL (editor de consultas).
-- Crea: categorias (maestra con valor hora), empleados y empleado_obra (asignaciones a obras).

CREATE TABLE IF NOT EXISTS categorias (
    id          SERIAL PRIMARY KEY,
    empresa_id  INTEGER NOT NULL REFERENCES empresas(id),
    nombre      VARCHAR(100) NOT NULL,
    valor_hora  NUMERIC(12,2) NOT NULL DEFAULT 0,
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (empresa_id, nombre)
);

CREATE TABLE IF NOT EXISTS empleados (
    id             SERIAL PRIMARY KEY,
    empresa_id     INTEGER NOT NULL REFERENCES empresas(id),
    dni            VARCHAR(15) NOT NULL,
    cuil           VARCHAR(15),
    apellido       VARCHAR(100) NOT NULL,
    nombre         VARCHAR(100) NOT NULL,
    categoria_id   INTEGER REFERENCES categorias(id),
    telefono       VARCHAR(40),
    fecha_ingreso  DATE,
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (empresa_id, dni)
);

-- Un empleado puede estar en varias obras a la vez (una fila por obra).
-- fecha_hasta NULL = asignación vigente.
CREATE TABLE IF NOT EXISTS empleado_obra (
    id           SERIAL PRIMARY KEY,
    empleado_id  INTEGER NOT NULL REFERENCES empleados(id),
    obra_id      INTEGER NOT NULL REFERENCES obras(id),
    fecha_desde  DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_hasta  DATE,
    CHECK (fecha_hasta IS NULL OR fecha_hasta >= fecha_desde)
);

-- Evita asignar dos veces al mismo empleado a la misma obra mientras la asignación siga vigente.
CREATE UNIQUE INDEX IF NOT EXISTS uq_empleado_obra_vigente
    ON empleado_obra (empleado_id, obra_id) WHERE fecha_hasta IS NULL;

-- Categorías iniciales (cargá el valor hora desde la app, módulo Empleados > Categorías).
INSERT INTO categorias (empresa_id, nombre, valor_hora) VALUES
    (100, 'Oficial Especializado', 0),
    (100, 'Oficial', 0),
    (100, 'Medio Oficial', 0),
    (100, 'Ayudante', 0),
    (100, 'Capataz', 0)
ON CONFLICT (empresa_id, nombre) DO NOTHING;
