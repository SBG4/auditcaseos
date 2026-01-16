-- AuditCaseOS Database Schema
-- PostgreSQL with pgvector extension

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Case Types Enum
CREATE TYPE case_type AS ENUM ('USB', 'EMAIL', 'WEB', 'POLICY');

-- Case Status Enum
CREATE TYPE case_status AS ENUM ('OPEN', 'IN_PROGRESS', 'PENDING_REVIEW', 'CLOSED', 'ARCHIVED');

-- Severity Enum
CREATE TYPE severity_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- User Role Enum
CREATE TYPE user_role AS ENUM ('admin', 'auditor', 'reviewer', 'viewer');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role DEFAULT 'viewer',
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Scopes (departments/areas) table
CREATE TABLE scopes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(10) UNIQUE NOT NULL,  -- FIN, HR, IT, SEC, OPS, CORP
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Case ID sequence tracking (per scope-type combination)
CREATE TABLE case_sequences (
    scope_code VARCHAR(10) NOT NULL,
    case_type case_type NOT NULL,
    last_seq INTEGER DEFAULT 0,
    PRIMARY KEY (scope_code, case_type)
);

-- Cases table (main entity)
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(50) UNIQUE NOT NULL,  -- SCOPE-TYPE-SEQ format (e.g., FIN-USB-0001)

    -- Classification
    scope_code VARCHAR(10) NOT NULL REFERENCES scopes(code),
    case_type case_type NOT NULL,
    status case_status DEFAULT 'OPEN',
    severity severity_level DEFAULT 'MEDIUM',

    -- Core details
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    description TEXT,

    -- Involved parties
    subject_user VARCHAR(255),           -- Primary user being investigated
    subject_computer VARCHAR(255),       -- Primary computer/hostname
    subject_devices TEXT[],              -- Array of device identifiers
    related_users TEXT[],                -- Other involved users

    -- Ownership
    owner_id UUID NOT NULL REFERENCES users(id),
    assigned_to UUID REFERENCES users(id),

    -- Timestamps
    incident_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    tags TEXT[],
    metadata JSONB DEFAULT '{}'
);

-- Evidence table
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,

    -- File info
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,    -- MinIO path
    file_size BIGINT,
    mime_type VARCHAR(100),
    file_hash VARCHAR(128),              -- SHA-256 for integrity

    -- Metadata
    description TEXT,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- For OCR/text extraction (Phase 2)
    extracted_text TEXT,

    metadata JSONB DEFAULT '{}'
);

-- Findings table
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,

    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    severity severity_level DEFAULT 'MEDIUM',

    -- Evidence references
    evidence_ids UUID[],

    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Timeline events
CREATE TABLE timeline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,

    event_time TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,

    -- Source tracking
    source VARCHAR(255),
    evidence_id UUID REFERENCES evidence(id),

    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit log (all actions)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What happened
    action VARCHAR(100) NOT NULL,        -- CREATE, UPDATE, DELETE, VIEW, DOWNLOAD, etc.
    entity_type VARCHAR(50) NOT NULL,    -- case, evidence, finding, etc.
    entity_id UUID,

    -- Who did it
    user_id UUID REFERENCES users(id),
    user_ip VARCHAR(45),

    -- Details
    old_values JSONB,
    new_values JSONB,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings table for RAG (pgvector)
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What this embedding represents
    entity_type VARCHAR(50) NOT NULL,    -- case, evidence, finding, kb
    entity_id UUID NOT NULL,

    -- The embedding
    content TEXT NOT NULL,               -- Original text that was embedded
    embedding vector(768),               -- Embedding vector (nomic-embed-text dimension)

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(entity_type, entity_id)
);

-- Create indexes
CREATE INDEX idx_cases_case_id ON cases(case_id);
CREATE INDEX idx_cases_scope_code ON cases(scope_code);
CREATE INDEX idx_cases_case_type ON cases(case_type);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_owner_id ON cases(owner_id);
CREATE INDEX idx_cases_created_at ON cases(created_at DESC);
CREATE INDEX idx_cases_subject_user ON cases(subject_user);

CREATE INDEX idx_evidence_case_id ON evidence(case_id);
CREATE INDEX idx_findings_case_id ON findings(case_id);
CREATE INDEX idx_timeline_case_id ON timeline_events(case_id);
CREATE INDEX idx_timeline_event_time ON timeline_events(event_time);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);

-- Vector similarity search index
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Insert default scopes
INSERT INTO scopes (code, name, description) VALUES
    ('FIN', 'Finance', 'Financial operations, accounting, and monetary transactions'),
    ('HR', 'Human Resources', 'Employee data, HR processes, and personnel management'),
    ('IT', 'Information Technology', 'IT systems, infrastructure, and technical operations'),
    ('SEC', 'Security', 'Physical and information security, access controls'),
    ('OPS', 'Operations', 'Business operations and process management'),
    ('LEG', 'Legal', 'Legal compliance, contracts, and regulatory matters'),
    ('PRO', 'Procurement', 'Purchasing, vendor management, and supply chain'),
    ('MKT', 'Marketing', 'Marketing activities, campaigns, and communications'),
    ('RND', 'Research & Development', 'R&D activities, innovation, and product development'),
    ('QA', 'Quality Assurance', 'Quality control, testing, and compliance verification'),
    ('ENV', 'Environmental', 'Environmental compliance and sustainability'),
    ('SAF', 'Health & Safety', 'Workplace health and safety compliance'),
    ('EXT', 'External', 'External partnerships, third-party relationships'),
    ('GOV', 'Governance', 'Corporate governance and board-level matters'),
    ('GEN', 'General', 'General audits not fitting other categories');

-- Insert a default admin user (password: admin123)
-- bcrypt hash generated with: passlib.hash.bcrypt.hash("admin123")
INSERT INTO users (username, email, password_hash, full_name, role, department) VALUES
    ('admin', 'admin@example.com', '$2b$12$v5caNNiV5WsfwLdJH3zYHeqQLO7qkKcyNW8vjV5PHxjiV1aFQzjkG', 'System Administrator', 'admin', 'IT');

-- Function to generate next case ID
CREATE OR REPLACE FUNCTION generate_case_id(p_scope_code VARCHAR, p_case_type case_type)
RETURNS VARCHAR AS $$
DECLARE
    v_seq INTEGER;
    v_case_id VARCHAR;
BEGIN
    -- Get and increment sequence
    INSERT INTO case_sequences (scope_code, case_type, last_seq)
    VALUES (p_scope_code, p_case_type, 1)
    ON CONFLICT (scope_code, case_type)
    DO UPDATE SET last_seq = case_sequences.last_seq + 1
    RETURNING last_seq INTO v_seq;

    -- Format: SCOPE-TYPE-XXXX (4 digit padded)
    v_case_id := p_scope_code || '-' || p_case_type || '-' || LPAD(v_seq::TEXT, 4, '0');

    RETURN v_case_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_cases_updated_at
    BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_findings_updated_at
    BEFORE UPDATE ON findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Case Entities table (extracted entities from evidence)
CREATE TABLE case_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    evidence_ids UUID[],                      -- Evidence items this entity was found in

    entity_type VARCHAR(50) NOT NULL,         -- employee_id, ip_address, email, hostname, etc.
    value VARCHAR(1000) NOT NULL,             -- The extracted entity value
    source VARCHAR(255),                      -- Where it was extracted from
    occurrence_count INTEGER DEFAULT 1,       -- How many times found

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique entity per case
    UNIQUE(case_id, entity_type, value)
);

-- Indexes for case_entities
CREATE INDEX idx_case_entities_case_id ON case_entities(case_id);
CREATE INDEX idx_case_entities_type ON case_entities(entity_type);
CREATE INDEX idx_case_entities_value ON case_entities(value);
CREATE INDEX idx_case_entities_case_type ON case_entities(case_id, entity_type);

-- Trigger for case_entities updated_at
CREATE TRIGGER trigger_case_entities_updated_at
    BEFORE UPDATE ON case_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- WORKFLOW AUTOMATION TABLES (Feature 3.12)
-- ============================================

-- Workflow Trigger Types Enum
CREATE TYPE workflow_trigger_type AS ENUM (
    'STATUS_CHANGE',      -- When case status transitions
    'TIME_BASED',         -- After X days in a status
    'EVENT',              -- When event occurs (evidence added, finding created, etc.)
    'CONDITION'           -- When conditions match (e.g., severity=CRITICAL AND status=OPEN)
);

-- Workflow Action Types Enum
CREATE TYPE workflow_action_type AS ENUM (
    'CHANGE_STATUS',      -- Update case status
    'ASSIGN_USER',        -- Assign case to a user
    'ADD_TAG',            -- Add a tag to the case
    'SEND_NOTIFICATION',  -- Send in-app notification
    'CREATE_TIMELINE'     -- Add timeline event
);

-- Notification Priority Enum
CREATE TYPE notification_priority AS ENUM ('LOW', 'NORMAL', 'HIGH', 'URGENT');

-- Workflow Rules table
CREATE TABLE workflow_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Trigger configuration
    trigger_type workflow_trigger_type NOT NULL,
    trigger_config JSONB NOT NULL DEFAULT '{}',
    -- Examples:
    -- STATUS_CHANGE: {"from_status": "OPEN", "to_status": "IN_PROGRESS"}
    -- TIME_BASED: {"status": "OPEN", "days": 7}
    -- EVENT: {"event_type": "evidence_added"} or {"event_type": "finding_created"}
    -- CONDITION: {"conditions": [{"field": "severity", "operator": "eq", "value": "CRITICAL"}]}

    -- Rule state
    is_enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100,  -- Lower number = higher priority

    -- Scope limiting (optional - null means all cases)
    scope_codes TEXT[],            -- Limit to specific scopes
    case_types TEXT[],             -- Limit to specific case types

    -- Audit
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflow Actions table (linked to rules)
CREATE TABLE workflow_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID NOT NULL REFERENCES workflow_rules(id) ON DELETE CASCADE,

    -- Action configuration
    action_type workflow_action_type NOT NULL,
    action_config JSONB NOT NULL DEFAULT '{}',
    -- Examples:
    -- CHANGE_STATUS: {"new_status": "IN_PROGRESS"}
    -- ASSIGN_USER: {"user_id": "uuid-here"} or {"assign_to_owner": true}
    -- ADD_TAG: {"tag": "escalated"}
    -- SEND_NOTIFICATION: {"title": "...", "message": "...", "recipient_type": "owner|assignee|role", "recipient_value": "admin"}
    -- CREATE_TIMELINE: {"event_type": "workflow", "description_template": "Case auto-escalated after {days} days"}

    -- Execution order within rule
    sequence INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Notifications table
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Recipient
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Content
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    priority notification_priority DEFAULT 'NORMAL',

    -- Related entity
    entity_type VARCHAR(50),       -- 'case', 'evidence', 'finding', etc.
    entity_id UUID,
    link_url VARCHAR(500),         -- URL to navigate to when clicked

    -- State
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,

    -- Source (for tracking what generated this notification)
    source VARCHAR(100),           -- 'workflow', 'system', 'user'
    source_rule_id UUID REFERENCES workflow_rules(id) ON DELETE SET NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflow Execution History table
CREATE TABLE workflow_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What was executed
    rule_id UUID REFERENCES workflow_rules(id) ON DELETE SET NULL,
    rule_name VARCHAR(255) NOT NULL,  -- Preserve name even if rule deleted

    -- What triggered it
    trigger_type workflow_trigger_type NOT NULL,
    trigger_data JSONB,

    -- Target
    case_id UUID REFERENCES cases(id) ON DELETE SET NULL,
    case_id_str VARCHAR(50),         -- Preserve case_id string even if case deleted

    -- Execution details
    actions_executed JSONB,           -- Array of executed actions with results
    -- Example: [{"action_type": "CHANGE_STATUS", "success": true, "details": {...}}, ...]

    -- Result
    success BOOLEAN NOT NULL,
    error_message TEXT,

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Who/what triggered it
    triggered_by VARCHAR(100)        -- 'scheduler', 'event:case_update', 'manual'
);

-- Indexes for workflow tables
CREATE INDEX idx_workflow_rules_enabled ON workflow_rules(is_enabled) WHERE is_enabled = true;
CREATE INDEX idx_workflow_rules_trigger ON workflow_rules(trigger_type);
CREATE INDEX idx_workflow_actions_rule ON workflow_actions(rule_id);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
CREATE INDEX idx_workflow_history_rule ON workflow_history(rule_id);
CREATE INDEX idx_workflow_history_case ON workflow_history(case_id);
CREATE INDEX idx_workflow_history_created ON workflow_history(created_at DESC);

-- Trigger for workflow_rules updated_at
CREATE TRIGGER trigger_workflow_rules_updated_at
    BEFORE UPDATE ON workflow_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
