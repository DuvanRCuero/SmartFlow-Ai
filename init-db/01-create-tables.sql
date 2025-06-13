-- init-db/01-create-tables.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Tabla de usuarios
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de tareas (compatible con Android + AI features)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,

    -- Campos Android
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Campos AI adicionales
    est_minutes INTEGER,
    energy_req VARCHAR(20) CHECK (energy_req IN ('low', 'medium', 'high')),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de pasos de plan (plan_steps) con jerarquía
CREATE TABLE plan_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES plan_steps(id) ON DELETE CASCADE,

    step_order INTEGER NOT NULL,
    text TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),

    -- Campos para tracking
    est_minutes INTEGER,
    actual_minutes INTEGER,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(task_id, step_order)
);

-- Tabla de logs de productividad
CREATE TABLE productivity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,

    ts TIMESTAMPTZ DEFAULT NOW(),
    focus_score FLOAT CHECK (focus_score >= 0 AND focus_score <= 1),
    energy_level FLOAT CHECK (energy_level >= 0 AND energy_level <= 1),

    session_duration INTEGER,  -- minutos
    interruptions INTEGER DEFAULT 0,
    mood VARCHAR(20) CHECK (mood IN ('great', 'good', 'ok', 'bad', 'terrible')),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convertir productivity_logs en hypertable para TimescaleDB
SELECT create_hypertable('productivity_logs', 'ts');

-- Tabla de logs de actividad (TimescaleDB hypertable)
CREATE TABLE activity_logs (
    id UUID DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Convertir activity_logs en hypertable para TimescaleDB
SELECT create_hypertable('activity_logs', 'timestamp');

-- Tabla de sugerencias generadas por IA
CREATE TABLE suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,

    message TEXT NOT NULL,
    suggestion_type VARCHAR(50) DEFAULT 'general',

    -- Metadatos de IA
    reason JSONB,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),

    -- Estado
    is_applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_priority ON tasks(priority);

CREATE INDEX idx_plan_steps_task_id ON plan_steps(task_id);
CREATE INDEX idx_plan_steps_parent_id ON plan_steps(parent_id);
CREATE INDEX idx_plan_steps_status ON plan_steps(status);

CREATE INDEX idx_productivity_logs_user_id ON productivity_logs(user_id);
CREATE INDEX idx_productivity_logs_task_id ON productivity_logs(task_id);
CREATE INDEX idx_productivity_logs_ts ON productivity_logs(ts);

CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_task_id ON activity_logs(task_id);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);

CREATE INDEX idx_suggestions_user_id ON suggestions(user_id);
CREATE INDEX idx_suggestions_task_id ON suggestions(task_id);
CREATE INDEX idx_suggestions_type ON suggestions(suggestion_type);
CREATE INDEX idx_suggestions_applied ON suggestions(is_applied);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$ language 'plpgsql';

-- Triggers para actualizar updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_plan_steps_updated_at BEFORE UPDATE ON plan_steps FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();