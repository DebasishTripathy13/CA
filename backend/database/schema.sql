-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    is_approver BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decision responses table
CREATE TABLE decision_responses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    responses JSONB NOT NULL,
    recommendation VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Certificate requests table
CREATE TABLE certificate_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    decision_response_id INTEGER REFERENCES decision_responses(id),
    common_name VARCHAR(255) NOT NULL,
    san_entries JSONB,
    csr_content TEXT,
    csr_uploaded BOOLEAN DEFAULT FALSE,
    ca_type VARCHAR(50),
    force_public_reason TEXT,
    status VARCHAR(50) DEFAULT 'PENDING',
    s3_cert_path VARCHAR(500),
    s3_key_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Approvals table
CREATE TABLE approvals (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES certificate_requests(id) ON DELETE CASCADE,
    approver_id INTEGER REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'PENDING',
    comments TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    request_id INTEGER REFERENCES certificate_requests(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Certificate revocations table
CREATE TABLE certificate_revocations (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES certificate_requests(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    reason VARCHAR(255),
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    crl_updated BOOLEAN DEFAULT FALSE,
    ocsp_updated BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX idx_cert_requests_user_id ON certificate_requests(user_id);
CREATE INDEX idx_cert_requests_status ON certificate_requests(status);
CREATE INDEX idx_approvals_request_id ON approvals(request_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);