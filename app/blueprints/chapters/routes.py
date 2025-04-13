from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Chapter, Subject, User
from app.extensions import db
from app.utils.exceptions import ValidationError, handle_exception
from . import chapter_bp


@chapter_bp.route('/create', methods=['POST'])
@jwt_required()
@handle_exception
def create_chapter():
    # Get the current user
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can create chapters.")

    # Parse data from the request
    data = request.json
    name = data.get('name')
    code = data.get('code')
    description = data.get('description', '')
    subject_id = data.get('subject_id')

    # Validate input
    if not name or not name.strip() or not code or not code.strip():
        raise ValidationError("Both 'name' and 'code' fields are required.")

    if not subject_id or not isinstance(subject_id, int):
        raise ValidationError("A valid 'subject_id' is required.")

    # Check if the subject exists
    subject = Subject.query.get(subject_id)
    if not subject:
        raise ValidationError("Subject with the given ID does not exist.")

    # Check for duplicates
    if Chapter.query.filter((Chapter.name == name) | (Chapter.code == code)).first():
        raise ValidationError("Chapter with the same name or code already exists.")

    # Create the new chapter
    chapter = Chapter(name=name, code=code, description=description, subject_id=subject_id)
    db.session.add(chapter)
    db.session.commit()

    return jsonify({
        "message": "Chapter created successfully!",
        "chapter": {
            "id": chapter.id,
            "name": chapter.name,
            "code": chapter.code,
            "description": chapter.description,
            "subject_id": chapter.subject_id,
            "created_at": chapter.created_at.isoformat()
        }
    }), 201

@chapter_bp.route('/<int:chapter_id>', methods=['GET'])
@jwt_required()
@handle_exception
def get_chapter(chapter_id):
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        raise ValidationError("Chapter with the given ID does not exist.")

    return jsonify({
        "chapter": {
            "id": chapter.id,
            "name": chapter.name,
            "code": chapter.code,
            "description": chapter.description,
            "subject_id": chapter.subject_id,
            "created_at": chapter.created_at.isoformat()
        }
    }), 200

@chapter_bp.route('/<int:chapter_id>', methods=['PUT'])
@jwt_required()
@handle_exception
def update_chapter(chapter_id):
    # Get the current user
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can update chapters.")

    # Parse data from the request
    data = request.json
    name = data.get('name')
    code = data.get('code')
    description = data.get('description')

    # Validate input
    if not name or not name.strip() or not code or not code.strip():
        raise ValidationError("Both 'name' and 'code' fields are required.")

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        raise ValidationError("Chapter with the given ID does not exist.")

    # Check for duplicates
    existing_chapter = Chapter.query.filter((Chapter.name == name) | (Chapter.code == code)).first()
    if existing_chapter and existing_chapter.id != chapter_id:
        raise ValidationError("Chapter with the same name or code already exists.")

    # Update the chapter
    chapter.name = name
    chapter.code = code
    chapter.description = description

    db.session.commit()

    return jsonify({
        "message": "Chapter updated successfully!",
        "chapter": {
            "id": chapter.id,
            "name": chapter.name,
            "code": chapter.code,
            "description": chapter.description,
            "subject_id": chapter.subject_id,
            "created_at": chapter.created_at.isoformat()
        }
    }), 200


@chapter_bp.route('/<int:chapter_id>', methods=['DELETE'])
@jwt_required()
@handle_exception
def delete_chapter(chapter_id):
    # Get the current user
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can delete chapters.")

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        raise ValidationError(f"Chapter with ID {chapter_id} does not exist.")

    db.session.delete(chapter)
    db.session.commit()

    return jsonify({"message": "Chapter deleted successfully!"}), 200

@chapter_bp.route('/', methods=['GET'])
@jwt_required()
@handle_exception
def list_chapters():
    subject_id = request.args.get('subject_id', type=int)
    
    if subject_id:
        chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    else:
        chapters = Chapter.query.all()
    return jsonify({
        "chapters": [
            {
                "id": chapter.id,
                "name": chapter.name,
                "code": chapter.code,
                "description": chapter.description,
                "subject_id": chapter.subject_id,
                "created_at": chapter.created_at.isoformat()
            }
            for chapter in chapters
        ]
    }), 200

