from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Subject, User
from app.utils.exceptions import handle_exception, ValidationError
from datetime import datetime
from . import subject_bp

### Used for debugging ### --------------------
@subject_bp.route('/protected', methods=['POST'])
@jwt_required()
@handle_exception
def protected():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    role = user.role
    data = request.json
    name = data.get('code')
    return jsonify({
        "user_id" : current_user_id,
        "user" : user.serialize(),
        "role" : role,
        "sub_name" : name
        }), 201
##------------------------------------------        
        
@subject_bp.route('/create', methods=['POST'])
@jwt_required()
@handle_exception
def create_subject():
    # Check if the current user is an admin
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can create subjects.")
    
    # Parse data from the request
    data = request.json
    name = data.get('name')
    code = data.get('code')
    description = data.get('description', '')
    
    # Validate input
    if not name or not code:
        raise ValidationError("Both 'name' and 'code' fields are required.")
    
    # Check for duplicates
    if Subject.query.filter((Subject.name == name) | (Subject.code == code)).first():
        raise ValidationError("Subject with the same name or code already exists.")
    
    # Create the new subject
    subject = Subject(name=name, code=code, description=description)
    db.session.add(subject)
    db.session.commit()

    return jsonify({
        "message": "Subject created successfully!",
        "subject": {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "description": subject.description,
            "created_at": subject.created_at.isoformat()
        }
    }), 201


@subject_bp.route('/edit/<int:id>', methods=['PUT'])
@jwt_required()
@handle_exception
def update_subject(id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can update subjects.")

    subject = Subject.query.get(id)
    if not subject:
        raise ValidationError("Subject not found.")

    data = request.json
    name = data.get('name')
    code = data.get('code')
    description = data.get('description', '')

    if name:
        subject.name = name
    if code:
        subject.code = code
    if description:
        subject.description = description

    db.session.commit()
    
    return jsonify({
        "message": "Subject updated successfully!",
        "subject": {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "description": subject.description,
            "created_at": subject.created_at.isoformat()
        }
    }), 200


# Delete a subject
@subject_bp.route('/delete/<int:id>', methods=['DELETE'])
@jwt_required()
@handle_exception
def delete_subject(id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can delete subjects.")

    subject = Subject.query.get(id)
    if not subject:
        raise ValidationError("Subject not found.")

    db.session.delete(subject)
    db.session.commit()
    return jsonify({"message": "Subject deleted successfully."}), 200
    


@subject_bp.route('/', methods=['GET'])
@jwt_required()
@handle_exception
def list_subjects():
    subjects = Subject.query.order_by(Subject.created_at).all()
    result = [
        {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "description": subject.description,
            "created_at": subject.created_at.isoformat(),
            "chapters_count": len(subject.chapters)
        }
        for subject in subjects
    ]
    return jsonify(result), 200

