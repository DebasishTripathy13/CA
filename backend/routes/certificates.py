from flask import Blueprint, request, jsonify
from app import db
from models import CertificateRequest, Approval, AuditLog, User
from services.s3_service import S3Service
from services.adcs_service import ADCSService
from datetime import datetime

certificates_bp = Blueprint('certificates', __name__)
s3_service = S3Service()
adcs_service = ADCSService()

@certificates_bp.route('/request', methods=['POST'])
def create_request():
    """Create a new certificate request"""
    data = request.json
    
    cert_request = CertificateRequest(
        user_id=data.get('user_id'),
        decision_response_id=data.get('decision_id'),
        common_name=data.get('common_name'),
        san_entries=data.get('san_entries', []),
        csr_content=data.get('csr_content'),
        csr_uploaded=data.get('csr_uploaded', False),
        ca_type=data.get('ca_type'),
        force_public_reason=data.get('force_public_reason'),
        status='PENDING'
    )
    
    db.session.add(cert_request)
    
    # Create approval record
    approval = Approval(
        request_id=cert_request.id,
        status='PENDING'
    )
    db.session.add(approval)
    
    # Audit log
    audit = AuditLog(
        user_id=data.get('user_id'),
        request_id=cert_request.id,
        action='REQUEST_CREATED',
        details=data
    )
    db.session.add(audit)
    
db.session.commit()
    
    # TODO: Send notification to approver
    
    return jsonify({
        'request_id': cert_request.id,
        'status': 'PENDING',
        'message': 'Certificate request submitted successfully'
    }), 201

@certificates_bp.route('/approve/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    """Approve a certificate request"""
    data = request.json
    approver_id = data.get('approver_id')
    
    cert_request = CertificateRequest.query.get_or_404(request_id)
    approval = Approval.query.filter_by(request_id=request_id).first()
    
    approval.approver_id = approver_id
    approval.status = 'APPROVED'
    approval.approved_at = datetime.utcnow()
    approval.comments = data.get('comments')
    
    cert_request.status = 'APPROVED'
    
    # Audit log
    audit = AuditLog(
        user_id=approver_id,
        request_id=request_id,
        action='REQUEST_APPROVED',
        details={'comments': data.get('comments')}
    )
    db.session.add(audit)
    db.session.commit()
    
    # Submit to ADCS
    if cert_request.ca_type == 'INTERNAL':
        adcs_service.submit_request(cert_request)
    
    return jsonify({'message': 'Request approved successfully'}), 200

@certificates_bp.route('/reject/<int:request_id>', methods=['POST'])
def reject_request(request_id):
    """Reject a certificate request"""
    data = request.json
    approver_id = data.get('approver_id')
    
    cert_request = CertificateRequest.query.get_or_404(request_id)
    approval = Approval.query.filter_by(request_id=request_id).first()
    
    approval.approver_id = approver_id
    approval.status = 'REJECTED'
    approval.comments = data.get('comments', 'Request rejected')
    
    cert_request.status = 'REJECTED'
    
    # Audit log
    audit = AuditLog(
        user_id=approver_id,
        request_id=request_id,
        action='REQUEST_REJECTED',
        details={'comments': data.get('comments')}
    )
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({'message': 'Request rejected'}), 200

@certificates_bp.route('/download/<int:request_id>', methods=['GET'])
def download_certificate(request_id):
    """Download issued certificate"""
    cert_request = CertificateRequest.query.get_or_404(request_id)
    
    if cert_request.status != 'ISSUED':
        return jsonify({'error': 'Certificate not issued yet'}), 400
    
    cert_url = s3_service.generate_presigned_url(cert_request.s3_cert_path)
    
    return jsonify({'download_url': cert_url}), 200

@certificates_bp.route('/revoke/<int:request_id>', methods=['POST'])
def revoke_certificate(request_id):
    """Revoke a certificate"""
    data = request.json
    
    cert_request = CertificateRequest.query.get_or_404(request_id)
    
    # Submit revocation to ADCS
    success = adcs_service.revoke_certificate(cert_request, data.get('reason'))
    
    if success:
        cert_request.status = 'REVOKED'
        db.session.commit()
        return jsonify({'message': 'Certificate revoked successfully'}), 200
    
    return jsonify({'error': 'Revocation failed'}), 500

@certificates_bp.route('/list', methods=['GET'])
def list_requests():
    """List certificate requests for a user"""
    user_id = request.args.get('user_id')
    
    requests = CertificateRequest.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'requests': [{
            'id': r.id,
            'common_name': r.common_name,
            'status': r.status,
            'created_at': r.created_at.isoformat(),
            'expires_at': r.expires_at.isoformat() if r.expires_at else None
        } for r in requests]
    }), 200
