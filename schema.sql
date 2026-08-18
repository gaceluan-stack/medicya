-- Habilitar extensión UUID si es necesaria
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. ELIMINAR TABLAS Y ENUMS PREVIOS (Para limpieza)
DROP TABLE IF EXISTS facturas CASCADE;
DROP TABLE IF EXISTS eventos_clic_billing CASCADE;
DROP TABLE IF EXISTS proveedores_servicio CASCADE;
DROP TABLE IF EXISTS pacientes CASCADE;
DROP TABLE IF EXISTS usuarios_sistema CASCADE;

DROP TYPE IF EXISTS estado_factura CASCADE;
DROP TYPE IF EXISTS categoria_proveedor CASCADE;
DROP TYPE IF EXISTS canal_atribucion CASCADE;
DROP TYPE IF EXISTS estado_usuario CASCADE;
DROP TYPE IF EXISTS rol_usuario CASCADE;

-- 2. TIPOS ENUM
CREATE TYPE rol_usuario AS ENUM ('ADMIN', 'PROVEEDOR', 'PACIENTE');
CREATE TYPE estado_usuario AS ENUM ('ACTIVO', 'PENDIENTE_PAGO', 'BLOQUEADO');
CREATE TYPE canal_atribucion AS ENUM ('TikTok', 'Instagram', 'Facebook', 'Referido Personal');
CREATE TYPE categoria_proveedor AS ENUM ('Doctores', 'Spas y Estética', 'Clínicas', 'Farmacias', 'Laboratorios');
CREATE TYPE estado_factura AS ENUM ('PAGADA', 'PENDIENTE', 'VENCIDA');

-- 3. TABLA: usuarios_sistema
CREATE TABLE usuarios_sistema (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255), -- NULL para pacientes (registro directo sin contraseña)
    rol rol_usuario NOT NULL,
    estado estado_usuario DEFAULT 'ACTIVO',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. TABLA: pacientes
CREATE TABLE pacientes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID REFERENCES usuarios_sistema(id) ON DELETE CASCADE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    cedula VARCHAR(20) UNIQUE NOT NULL,
    celular_whatsapp VARCHAR(20) NOT NULL,
    origen_informacion canal_atribucion NOT NULL,
    cupon_descuento NUMERIC(10,2) DEFAULT 5.00, -- Cupón de $5 USD de bienvenida
    cupon_usado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. TABLA: proveedores_servicio
CREATE TABLE proveedores_servicio (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID REFERENCES usuarios_sistema(id) ON DELETE CASCADE,
    ruc_cedula VARCHAR(20) UNIQUE NOT NULL,
    nombre_comercial VARCHAR(150) NOT NULL,
    categoria categoria_proveedor NOT NULL,
    especialidad VARCHAR(100),
    latitud DOUBLE PRECISION NOT NULL,
    longitud DOUBLE PRECISION NOT NULL,
    precio_consulta NUMERIC(10,2) NOT NULL,
    imagen_url VARCHAR(255),
    membresia_fija NUMERIC(10,2) DEFAULT 10.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. TABLA: eventos_clic_billing
CREATE TABLE eventos_clic_billing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proveedor_id UUID NOT NULL REFERENCES proveedores_servicio(id) ON DELETE CASCADE,
    paciente_id UUID REFERENCES pacientes(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. TABLA: facturas
CREATE TABLE facturas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proveedor_id UUID NOT NULL REFERENCES proveedores_servicio(id) ON DELETE CASCADE,
    fecha_emision DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_vencimiento DATE NOT NULL,
    monto_fijo NUMERIC(10,2) NOT NULL DEFAULT 10.00,
    monto_clics NUMERIC(10,2) NOT NULL DEFAULT 0.00, -- Calculado en cron: (clics / 1000) * 5.00
    monto_total NUMERIC(10,2) NOT NULL,
    estado estado_factura DEFAULT 'PENDIENTE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimizar la geolocalización y la facturación
CREATE INDEX idx_proveedores_coords ON proveedores_servicio(latitud, longitud);
CREATE INDEX idx_clics_proveedor_fecha ON eventos_clic_billing(proveedor_id, created_at);
