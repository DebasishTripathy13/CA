from datetime import datetime
from app import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255))
    is_approver = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DecisionResponse(db.Model):
    __tablename__ = 'decision_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    responses = db.Column(db.JSON, nullable=False)
    recommendation = db.Column(db.String(50))  # PUBLIC_CA, INTERNAL_CA, PUBLIC_WITH_JUSTIFICATION
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CertificateRequest(db.Model):
    __tablename__ = 'certificate_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    decision_response_id = db.Column(db.Integer, db.ForeignKey('decision_responses.id'))
    
    common_name = db.Column(db.String(255), nullable=False)
    san_entries = db.Column(db.JSON)
    csr_content = db.Column(db.Text)
    csr_uploaded = db.Column(db.Boolean, default=False)
    
    ca_type = db.Column(db.String(50))  # PUBLIC or INTERNAL
    force_public_reason = db.Column(db.Text)
    
    status = db.Column(db.String(50), default='PENDING')  # PENDING, APPROVED, REJECTED, ISSUED, ERROR
    s3_cert_path = db.Column(db.String(500))
    s3_key_path = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

class Approval(db.Model):
    __tablename__ = 'approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('certificate_requests.id'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    status = db.Column(db.String(50))  # PENDING, APPROVED, REJECTED
    comments = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    request_id = db.Column(db.Integer, db.ForeignKey('certificate_requests.id'))
    
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CertificateRevocation(db.Model):
    __tablename__ = 'certificate_revocations'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('certificate_requests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    reason = db.Column(db.String(255))
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    crl_updated = db.Column(db.Boolean, default=False)
    ocsp_updated = db.Column(db.Boolean, default=False)
