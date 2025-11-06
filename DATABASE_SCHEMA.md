# Database Schema Design - AWS Certificate Decision Assistant

## Database: PostgreSQL 15+ (AWS RDS)

## Overview

This document defines the database schema for the AWS Certificate Decision Assistant. The schema is designed for PostgreSQL but can be adapted for MySQL with minor modifications.

## Design Principles

- Normalization (3NF) for data integrity
- Audit trail for all critical operations
- Soft deletes (deleted_at) for data retention
- UUID primary keys for distributed systems
- Timestamps (created_at, updated_at) on all tables
- Foreign key constraints for referential integrity
- Indexes on frequently queried columns

## Schema Diagram

```
┌─────────────┐
│   users     │◄────┐
└─────────────┘     │
       ▲            │
       │            │
       │            │
┌─────────────┐     │          ┌──────────────────┐
│  requests   │─────┼─────────►│  certificates    │
└─────────────┘     │          └──────────────────┘
       │            │                    │
       │            │                    │
       ▼            │                    ▼
┌─────────────┐     │          ┌──────────────────┐
│  approvals  │     │          │  revocations     │
└─────────────┘     │          └──────────────────┘
                    │
                    │
┌─────────────┐     │
│ audit_logs  │◄────┘
└─────────────┘
       
┌──────────────────┐
│ recommendation_  │
│    answers       │
└──────────────────┘

┌──────────────────┐
│   notifications  │
└──────────────────┘

┌──────────────────┐
│ system_config    │
└──────────────────┘
```

## Table Definitions

### 1. users

Stores user information from SSO integration.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(200),
    department VARCHAR(100),
    organization VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    -- Roles: 'user', 'approver', 'admin', 'auditor'
    is_active BOOLEAN NOT NULL DEFAULT true,
    sso_provider VARCHAR(50),
    -- 'azure_ad', 'okta', 'adfs', etc.
    sso_user_id VARCHAR(255),
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_role CHECK (role IN ('user', 'approver', 'admin', 'auditor'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_sso_user_id ON users(sso_user_id);
CREATE INDEX idx_users_deleted_at ON users(deleted_at);
```

**Sample Data:**
```sql
INSERT INTO users (email, first_name, last_name, display_name, department, role) VALUES
('john.doe@example.com', 'John', 'Doe', 'John Doe', 'IT', 'user'),
('jane.smith@example.com', 'Jane', 'Smith', 'Jane Smith', 'Security', 'approver'),
('admin@example.com', 'Admin', 'User', 'System Admin', 'IT', 'admin');
```

---

### 2. certificate_requests

Main table for certificate requests.

```sql
CREATE TABLE certificate_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_number VARCHAR(20) UNIQUE NOT NULL,
    -- Format: REQ-YYYYMMDD-XXXXX
    user_id UUID NOT NULL REFERENCES users(id),
    approver_id UUID REFERENCES users(id),
    
    -- Certificate Details
    common_name VARCHAR(255) NOT NULL,
    organization VARCHAR(255),
    organizational_unit VARCHAR(255),
    locality VARCHAR(100),
    state_province VARCHAR(100),
    country CHAR(2),
    email_address VARCHAR(255),
    subject_alternative_names TEXT[],
    -- Array of SANs
    
    -- Request Details
    certificate_type VARCHAR(50) NOT NULL,
    -- 'web_server', 'email', 'code_signing', 'vpn', 'database', 'user_auth', 'other'
    key_algorithm VARCHAR(20) NOT NULL,
    -- 'RSA_2048', 'RSA_4096', 'ECC_P256', 'ECC_P384'
    validity_period_days INTEGER NOT NULL,
    -- 90, 365, 730
    
    -- CSR
    csr_type VARCHAR(20) NOT NULL,
    -- 'generated', 'uploaded'
    csr_content TEXT NOT NULL,
    -- PEM-encoded CSR
    
    -- Business Context
    business_justification TEXT NOT NULL,
    department VARCHAR(100),
    cost_center VARCHAR(50),
    project_code VARCHAR(50),
    additional_notes TEXT,
    
    -- Workflow
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    -- 'draft', 'pending_approval', 'approved', 'in_progress', 'issued', 'rejected', 'failed', 'cancelled', 'revoked'
    submitted_at TIMESTAMP WITH TIME ZONE,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE,
    issued_at TIMESTAMP WITH TIME ZONE,
    
    -- ADCS Integration
    adcs_request_id VARCHAR(100),
    adcs_status VARCHAR(50),
    adcs_error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Recommendation Override
    recommended_ca_type VARCHAR(20),
    -- 'public', 'internal'
    override_requested BOOLEAN DEFAULT false,
    override_reason TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_status CHECK (status IN ('draft', 'pending_approval', 'approved', 'in_progress', 'issued', 'rejected', 'failed', 'cancelled', 'revoked')),
    CONSTRAINT valid_cert_type CHECK (certificate_type IN ('web_server', 'email', 'code_signing', 'vpn', 'database', 'user_auth', 'other')),
    CONSTRAINT valid_key_algo CHECK (key_algorithm IN ('RSA_2048', 'RSA_4096', 'ECC_P256', 'ECC_P384')),
    CONSTRAINT valid_csr_type CHECK (csr_type IN ('generated', 'uploaded'))
);

CREATE INDEX idx_requests_user_id ON certificate_requests(user_id);
CREATE INDEX idx_requests_approver_id ON certificate_requests(approver_id);
CREATE INDEX idx_requests_status ON certificate_requests(status);
CREATE INDEX idx_requests_request_number ON certificate_requests(request_number);
CREATE INDEX idx_requests_common_name ON certificate_requests(common_name);
CREATE INDEX idx_requests_submitted_at ON certificate_requests(submitted_at);
CREATE INDEX idx_requests_deleted_at ON certificate_requests(deleted_at);
```

---

### 3. recommendation_answers

Stores user responses to the recommendation questionnaire.

```sql
CREATE TABLE recommendation_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES certificate_requests(id) ON DELETE CASCADE,
    
    -- Questionnaire Answers (JSON for flexibility)
    service_type VARCHAR(50),
    -- 'web_server', 'database', 'api', 'email', 'code_signing', 'vpn', 'other'
    publicly_accessible VARCHAR(20),
    -- 'yes', 'no', 'hybrid'
    expected_lifespan VARCHAR(20),
    -- 'under_90', '90_to_365', '1_to_2_years', 'over_2_years'
    browser_trust_required VARCHAR(20),
    -- 'yes', 'no', 'partial'
    environment_type VARCHAR(20),
    -- 'production', 'development', 'testing', 'sandbox'
    certificate_count VARCHAR(20),
    -- 'single', 'multiple', 'bulk'
    domain_type VARCHAR(20),
    -- 'single', 'wildcard', 'san'
    criticality_level VARCHAR(20),
    -- 'critical', 'high', 'medium', 'low'
    compliance_requirements TEXT[],
    -- Array: ['PCI_DSS', 'HIPAA', 'SOC2', 'ISO27001', 'none']
    renewal_preference VARCHAR(20),
    -- 'automatic', 'manual', 'notification'
    
    -- Recommendation Result
    recommended_ca_type VARCHAR(20) NOT NULL,
    -- 'public', 'internal'
    recommendation_reason TEXT,
    recommendation_confidence DECIMAL(3,2),
    -- 0.00 to 1.00
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recommendation_request_id ON recommendation_answers(request_id);
CREATE INDEX idx_recommendation_ca_type ON recommendation_answers(recommended_ca_type);
```

---

### 4. approvals

Tracks approval workflow for certificate requests.

```sql
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES certificate_requests(id) ON DELETE CASCADE,
    approver_id UUID NOT NULL REFERENCES users(id),
    
    status VARCHAR(20) NOT NULL,
    -- 'pending', 'approved', 'rejected', 'delegated'
    decision VARCHAR(20),
    -- 'approve', 'reject'
    comments TEXT,
    decided_at TIMESTAMP WITH TIME ZONE,
    
    -- Delegation
    delegated_to_id UUID REFERENCES users(id),
    delegation_reason TEXT,
    
    -- Notifications
    notified_at TIMESTAMP WITH TIME ZONE,
    reminder_count INTEGER DEFAULT 0,
    last_reminder_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_approval_status CHECK (status IN ('pending', 'approved', 'rejected', 'delegated')),
    CONSTRAINT valid_decision CHECK (decision IN ('approve', 'reject'))
);

CREATE INDEX idx_approvals_request_id ON approvals(request_id);
CREATE INDEX idx_approvals_approver_id ON approvals(approver_id);
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_decided_at ON approvals(decided_at);
```

---

### 5. certificates

Stores issued certificates.

```sql
CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES certificate_requests(id),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Certificate Identification
    serial_number VARCHAR(100) UNIQUE NOT NULL,
    thumbprint_sha1 VARCHAR(40),
    thumbprint_sha256 VARCHAR(64),
    
    -- Certificate Details
    common_name VARCHAR(255) NOT NULL,
    subject_dn TEXT NOT NULL,
    issuer_dn TEXT NOT NULL,
    subject_alternative_names TEXT[],
    
    -- Validity
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_to TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Key Information
    key_algorithm VARCHAR(20) NOT NULL,
    key_size INTEGER NOT NULL,
    signature_algorithm VARCHAR(50),
    
    -- Storage
    s3_bucket VARCHAR(100) NOT NULL,
    s3_key_certificate VARCHAR(255) NOT NULL,
    s3_key_chain VARCHAR(255),
    s3_key_private_key VARCHAR(255),
    -- Only if generated by system
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    -- 'active', 'revoked', 'expired', 'suspended'
    
    -- Download Tracking
    download_count INTEGER DEFAULT 0,
    first_downloaded_at TIMESTAMP WITH TIME ZONE,
    last_downloaded_at TIMESTAMP WITH TIME ZONE,
    
    -- Expiry Monitoring
    expiry_notification_sent BOOLEAN DEFAULT false,
    expiry_notifications JSONB DEFAULT '[]'::jsonb,
    -- Track notification history: [{"sent_at": "2024-01-01", "days_before": 90}]
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_cert_status CHECK (status IN ('active', 'revoked', 'expired', 'suspended'))
);

CREATE INDEX idx_certificates_request_id ON certificates(request_id);
CREATE INDEX idx_certificates_user_id ON certificates(user_id);
CREATE INDEX idx_certificates_serial_number ON certificates(serial_number);
CREATE INDEX idx_certificates_common_name ON certificates(common_name);
CREATE INDEX idx_certificates_status ON certificates(status);
CREATE INDEX idx_certificates_valid_to ON certificates(valid_to);
CREATE INDEX idx_certificates_deleted_at ON certificates(deleted_at);

-- Index for expiry monitoring
CREATE INDEX idx_certificates_active_expiring ON certificates(valid_to) 
WHERE status = 'active' AND deleted_at IS NULL;
```

---

### 6. certificate_revocations

Tracks certificate revocation requests and status.

```sql
CREATE TABLE certificate_revocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_id UUID NOT NULL REFERENCES certificates(id),
    request_id UUID REFERENCES certificate_requests(id),
    user_id UUID NOT NULL REFERENCES users(id),
    -- User who requested revocation
    
    -- Revocation Details
    reason_code VARCHAR(50) NOT NULL,
    -- 'unspecified', 'key_compromise', 'ca_compromise', 'affiliation_changed', 
    -- 'superseded', 'cessation_of_operation', 'certificate_hold', 'remove_from_crl'
    reason_text TEXT,
    revoked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- ADCS Integration
    adcs_revocation_id VARCHAR(100),
    adcs_status VARCHAR(50),
    adcs_error_message TEXT,
    crl_updated_at TIMESTAMP WITH TIME ZONE,
    ocsp_updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Approval (if required)
    approver_id UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    approval_required BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_reason_code CHECK (reason_code IN (
        'unspecified', 'key_compromise', 'ca_compromise', 'affiliation_changed',
        'superseded', 'cessation_of_operation', 'certificate_hold', 'remove_from_crl'
    ))
);

CREATE INDEX idx_revocations_certificate_id ON certificate_revocations(certificate_id);
CREATE INDEX idx_revocations_user_id ON certificate_revocations(user_id);
CREATE INDEX idx_revocations_revoked_at ON certificate_revocations(revoked_at);
```

---

### 7. audit_logs

Comprehensive audit trail for all system actions.

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event Details
    event_type VARCHAR(100) NOT NULL,
    -- 'user_login', 'user_logout', 'request_created', 'request_approved', 
    -- 'certificate_issued', 'certificate_downloaded', 'certificate_revoked', etc.
    event_category VARCHAR(50) NOT NULL,
    -- 'authentication', 'authorization', 'certificate', 'request', 'approval', 'system'
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    -- 'debug', 'info', 'warning', 'error', 'critical'
    
    -- Actor
    user_id UUID REFERENCES users(id),
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(100),
    
    -- Resource
    resource_type VARCHAR(50),
    -- 'request', 'certificate', 'user', 'config'
    resource_id UUID,
    resource_identifier VARCHAR(255),
    -- Human-readable ID (e.g., request_number, serial_number)
    
    -- Action
    action VARCHAR(100) NOT NULL,
    -- 'create', 'read', 'update', 'delete', 'approve', 'reject', 'download', 'revoke'
    result VARCHAR(20) NOT NULL,
    -- 'success', 'failure', 'partial'
    error_message TEXT,
    
    -- Additional Data
    metadata JSONB,
    -- Store additional context as JSON
    
    -- Timestamp
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_severity CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    CONSTRAINT valid_result CHECK (result IN ('success', 'failure', 'partial'))
);

CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_event_category ON audit_logs(event_category);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_resource_id ON audit_logs(resource_id);
CREATE INDEX idx_audit_logs_result ON audit_logs(result);

-- Partial index for failed events
CREATE INDEX idx_audit_logs_failures ON audit_logs(timestamp DESC) 
WHERE result = 'failure';

-- GIN index for JSONB metadata queries
CREATE INDEX idx_audit_logs_metadata ON audit_logs USING GIN (metadata);
```

---

### 8. notifications

Queue and history of notifications sent to users.

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Recipient
    user_id UUID NOT NULL REFERENCES users(id),
    recipient_email VARCHAR(255) NOT NULL,
    
    -- Notification Details
    notification_type VARCHAR(50) NOT NULL,
    -- 'request_submitted', 'request_approved', 'request_rejected', 
    -- 'certificate_issued', 'certificate_expiring', 'certificate_revoked'
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    
    -- Channel
    channel VARCHAR(20) NOT NULL DEFAULT 'email',
    -- 'email', 'slack', 'teams', 'sms'
    
    -- Related Resource
    resource_type VARCHAR(50),
    resource_id UUID,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 'pending', 'sent', 'failed', 'bounced'
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- External IDs (from SES, Slack, etc.)
    external_message_id VARCHAR(255),
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_notification_status CHECK (status IN ('pending', 'sent', 'failed', 'bounced')),
    CONSTRAINT valid_channel CHECK (channel IN ('email', 'slack', 'teams', 'sms'))
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_sent_at ON notifications(sent_at);
CREATE INDEX idx_notifications_notification_type ON notifications(notification_type);

-- Index for pending notifications to be processed
CREATE INDEX idx_notifications_pending ON notifications(created_at) 
WHERE status = 'pending';
```

---

### 9. system_config

System-wide configuration settings.

```sql
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    value_type VARCHAR(20) NOT NULL DEFAULT 'string',
    -- 'string', 'integer', 'boolean', 'json'
    description TEXT,
    is_sensitive BOOLEAN DEFAULT false,
    -- If true, value is encrypted
    
    -- Audit
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_value_type CHECK (value_type IN ('string', 'integer', 'boolean', 'json'))
);

CREATE INDEX idx_system_config_key ON system_config(config_key);

-- Sample configuration
INSERT INTO system_config (config_key, config_value, value_type, description) VALUES
('adcs.server.endpoint', 'https://adcs.internal.example.com', 'string', 'ADCS server endpoint'),
('adcs.polling.interval_seconds', '30', 'integer', 'ADCS polling interval in seconds'),
('certificate.default_validity_days', '365', 'integer', 'Default certificate validity period'),
('notification.email.from', 'cert-assistant@example.com', 'string', 'Email sender address'),
('expiry.notification.days', '[90,60,30,14,7]', 'json', 'Days before expiry to send notifications'),
('approval.escalation.hours', '48', 'integer', 'Hours before escalating approval'),
('session.timeout.minutes', '480', 'integer', 'Session timeout in minutes (8 hours)');
```

---

### 10. private_keys (Optional, if system generates keys)

Stores encrypted private keys for certificates generated by the system.

```sql
CREATE TABLE private_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_id UUID NOT NULL REFERENCES certificates(id) ON DELETE CASCADE,
    request_id UUID NOT NULL REFERENCES certificate_requests(id),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Encrypted Key
    encrypted_key TEXT NOT NULL,
    -- Private key encrypted with user password or KMS
    encryption_algorithm VARCHAR(50) NOT NULL,
    -- 'AES-256-GCM', 'AWS-KMS'
    encryption_key_id VARCHAR(255),
    -- KMS key ID or reference
    
    -- Access Control
    download_allowed BOOLEAN DEFAULT true,
    downloaded BOOLEAN DEFAULT false,
    download_count INTEGER DEFAULT 0,
    first_downloaded_at TIMESTAMP WITH TIME ZONE,
    last_downloaded_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_private_keys_certificate_id ON private_keys(certificate_id);
CREATE INDEX idx_private_keys_user_id ON private_keys(user_id);
```

---

## Views

### Active Certificates View

```sql
CREATE VIEW v_active_certificates AS
SELECT 
    c.id,
    c.serial_number,
    c.common_name,
    c.valid_from,
    c.valid_to,
    c.status,
    u.email as owner_email,
    u.display_name as owner_name,
    cr.request_number,
    EXTRACT(DAY FROM (c.valid_to - NOW())) as days_until_expiry,
    CASE 
        WHEN c.valid_to < NOW() THEN 'expired'
        WHEN c.valid_to < NOW() + INTERVAL '30 days' THEN 'expiring_soon'
        WHEN c.valid_to < NOW() + INTERVAL '60 days' THEN 'expiring'
        ELSE 'valid'
    END as expiry_status
FROM certificates c
JOIN users u ON c.user_id = u.id
JOIN certificate_requests cr ON c.request_id = cr.id
WHERE c.status = 'active' 
  AND c.deleted_at IS NULL
ORDER BY c.valid_to ASC;
```

### Pending Approvals View

```sql
CREATE VIEW v_pending_approvals AS
SELECT 
    a.id as approval_id,
    cr.id as request_id,
    cr.request_number,
    cr.common_name,
    cr.certificate_type,
    u.email as requester_email,
    u.display_name as requester_name,
    ap.email as approver_email,
    ap.display_name as approver_name,
    cr.submitted_at,
    a.created_at as approval_created_at,
    EXTRACT(HOUR FROM (NOW() - a.created_at)) as pending_hours
FROM approvals a
JOIN certificate_requests cr ON a.request_id = cr.id
JOIN users u ON cr.user_id = u.id
JOIN users ap ON a.approver_id = ap.id
WHERE a.status = 'pending'
  AND cr.deleted_at IS NULL
ORDER BY a.created_at ASC;
```

### Certificate Request Summary View

```sql
CREATE VIEW v_request_summary AS
SELECT 
    DATE(cr.created_at) as request_date,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN cr.status = 'pending_approval' THEN 1 END) as pending,
    COUNT(CASE WHEN cr.status = 'approved' THEN 1 END) as approved,
    COUNT(CASE WHEN cr.status = 'rejected' THEN 1 END) as rejected,
    COUNT(CASE WHEN cr.status = 'issued' THEN 1 END) as issued,
    COUNT(CASE WHEN cr.status = 'failed' THEN 1 END) as failed
FROM certificate_requests cr
WHERE cr.deleted_at IS NULL
GROUP BY DATE(cr.created_at)
ORDER BY request_date DESC;
```

---

## Functions and Triggers

### Auto-update updated_at Timestamp

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_certificate_requests_updated_at BEFORE UPDATE ON certificate_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_approvals_updated_at BEFORE UPDATE ON approvals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_certificates_updated_at BEFORE UPDATE ON certificates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Audit Log Trigger

```sql
CREATE OR REPLACE FUNCTION log_certificate_download()
RETURNS TRIGGER AS $$
BEGIN
    -- Update download tracking
    NEW.download_count = NEW.download_count + 1;
    NEW.last_downloaded_at = NOW();
    
    IF NEW.first_downloaded_at IS NULL THEN
        NEW.first_downloaded_at = NOW();
    END IF;
    
    -- Create audit log entry
    INSERT INTO audit_logs (
        event_type, event_category, severity, user_id, resource_type, 
        resource_id, resource_identifier, action, result
    ) VALUES (
        'certificate_downloaded', 'certificate', 'info', NEW.user_id,
        'certificate', NEW.id, NEW.serial_number, 'download', 'success'
    );
    
    RETURN NEW;
END;
$$ language 'plpgsql';
```

---

## Data Retention and Archival

### Retention Policies

1. **Active Data (RDS):**
   - Certificates: Retain for 7 years after expiry
   - Requests: Retain for 7 years
   - Audit logs: 1 year in RDS, then archive to S3

2. **Archived Data (S3):**
   - Audit logs: 10 years in S3 Glacier
   - Certificate copies: 7 years

3. **Deletion:**
   - User data: Soft delete, retain for 1 year
   - Private keys: Delete immediately on revocation (if policy allows)

### Archive Job (Pseudocode)

```sql
-- Archive old audit logs to S3 (run monthly)
-- This would be executed by a scheduled Lambda function
SELECT * FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '1 year'
ORDER BY timestamp ASC;

-- After successful export to S3:
DELETE FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '1 year';
```

---

## Backup and Recovery

### RDS Backup Strategy

- **Automated Backups:** Daily, 7-day retention
- **Manual Snapshots:** Weekly, 30-day retention
- **Point-in-Time Recovery:** Enabled, 5-minute granularity
- **Cross-Region Replication:** Optional, for DR

### Restore Procedure

1. Identify the snapshot or point-in-time
2. Restore to new RDS instance
3. Update application configuration
4. Validate data integrity
5. Switch traffic to restored instance

---

## Performance Optimization

### Partitioning

For large datasets, consider partitioning:

```sql
-- Partition audit_logs by month
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE audit_logs_2024_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... and so on
```

### Query Optimization

- Use prepared statements
- Leverage connection pooling
- Implement read replicas for read-heavy queries
- Use materialized views for complex aggregations
- Monitor slow queries with pg_stat_statements

---

## Security Considerations

1. **Encryption at Rest:** Enable RDS encryption with KMS
2. **Encryption in Transit:** Enforce SSL/TLS connections
3. **Access Control:** 
   - Least privilege IAM roles
   - Database user roles with minimal permissions
   - No public access to RDS instance
4. **Secrets Management:** Store DB credentials in AWS Secrets Manager
5. **Audit:** Enable RDS audit logging
6. **Rotation:** Rotate database passwords every 90 days

---

## Migration Scripts

### Initial Setup

```sql
-- Run all CREATE TABLE statements in order
-- Run CREATE INDEX statements
-- Run CREATE VIEW statements
-- Run CREATE TRIGGER statements
-- Insert initial system_config data
-- Create admin user
```

### Rollback

```sql
-- Drop all triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
-- ... (drop all triggers)

-- Drop all views
DROP VIEW IF EXISTS v_active_certificates;
DROP VIEW IF EXISTS v_pending_approvals;
DROP VIEW IF EXISTS v_request_summary;

-- Drop all tables (in reverse order of dependencies)
DROP TABLE IF EXISTS private_keys;
DROP TABLE IF EXISTS system_config;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS certificate_revocations;
DROP TABLE IF EXISTS certificates;
DROP TABLE IF EXISTS approvals;
DROP TABLE IF EXISTS recommendation_answers;
DROP TABLE IF EXISTS certificate_requests;
DROP TABLE IF EXISTS users;
```

---

## Summary

This database schema provides:
- **10 core tables** for data management
- **3 views** for common queries
- **Audit logging** for all critical operations
- **Soft deletes** for data retention
- **Indexes** for query performance
- **Constraints** for data integrity
- **Triggers** for automation
- **Scalability** through partitioning

The schema is designed to support all functional requirements while maintaining data integrity, security, and performance at scale.
