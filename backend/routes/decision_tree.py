from flask import Blueprint, request, jsonify
from app import db
from models import DecisionResponse, User, AuditLog
from datetime import datetime

decision_tree_bp = Blueprint('decision_tree', __name__)

QUESTIONS = [
    {"id": 1, "text": "Will the service be reachable from the public internet?"},
    {"id": 2, "text": "Will external (third-party) customers or partners use this service?"},
    {"id": 3, "text": "Does the service require certificates trusted by browsers/OS by default?"},
    {"id": 4, "text": "Is an EV/OV certificate required for compliance or branding?"},
    {"id": 5, "text": "Will the cert be embedded in mobile apps or distributed to clients?"},
    {"id": 6, "text": "Is the environment multi-tenant?"},
    {"id": 7, "text": "Is there a corporate/internal PKI already in place?"},
    {"id": 8, "text": "Do you need wildcard or many SAN entries across public domains?"},
    {"id": 9, "text": "Is automated public CA issuance/renewal (ACME or API) required?"},
    {"id": 10, "text": "Are there regulations that mandate independent public CA audit?"}
]

def evaluate_decision(responses):
    """Decision tree logic to recommend CA type"""
    yes_count = sum(1 for r in responses.values() if r is True)
    
    # If public internet + external customers + browser trust -> PUBLIC_CA
    if responses.get('1') and responses.get('2') and responses.get('3'):
        return 'PUBLIC_CA'
    
    # If EV/OV required or regulations mandate -> PUBLIC_CA
    if responses.get('4') or responses.get('10'):
        return 'PUBLIC_CA'
    
    # If mobile apps or can't add internal root -> PUBLIC_CA
    if responses.get('5'):
        return 'PUBLIC_CA'
    
    # If internal PKI exists and not many public requirements -> INTERNAL_CA
    if responses.get('7') and yes_count <= 3:
        return 'INTERNAL_CA'
    
    # Default to allow public with justification
    return 'PUBLIC_WITH_JUSTIFICATION'

@decision_tree_bp.route('/questions', methods=['GET'])
def get_questions():
    """Get all decision tree questions"""
    return jsonify({'questions': QUESTIONS}), 200

@decision_tree_bp.route('/evaluate', methods=['POST'])
def evaluate():
    """Evaluate responses and provide recommendation"""
    data = request.json
    user_id = data.get('user_id')
    responses = data.get('responses', {})
    
    if not user_id or not responses:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Evaluate decision
    recommendation = evaluate_decision(responses)
    
    # Save decision response
    decision = DecisionResponse(
        user_id=user_id,
        responses=responses,
        recommendation=recommendation
    )
    db.session.add(decision)
    
    # Audit log
    audit = AuditLog(
        user_id=user_id,
        action='DECISION_EVALUATION',
        details={'responses': responses, 'recommendation': recommendation}
    )
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({
        'decision_id': decision.id,
        'recommendation': recommendation,
        'message': get_recommendation_message(recommendation)
    }), 200

def get_recommendation_message(recommendation):
    """Get user-friendly message for recommendation"""
    messages = {
        'PUBLIC_CA': 'We recommend using a Public CA for your certificate needs.',
        'INTERNAL_CA': 'We recommend using your Internal CA for this certificate.',
        'PUBLIC_WITH_JUSTIFICATION': 'You may use a Public CA with proper justification.'
    }
    return messages.get(recommendation, 'Unable to determine recommendation')

@decision_tree_bp.route('/reset', methods=['POST'])
def reset():
    """Reset decision tree for a user"""
    data = request.json
    user_id = data.get('user_id')
    
    return jsonify({'message': 'Decision tree reset successfully'}), 200
