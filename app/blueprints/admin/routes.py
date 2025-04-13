from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Chapter, Subject, User, Quiz, Question
from app.utils.exceptions import ValidationError, handle_exception
from . import admin_bp
from flask_mail import Message
from sqlalchemy import func, or_


@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@handle_exception
def get_admin_stats():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    # Check if admin
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can access site Stats.")
    stats = {
        "totalQuizzes": Quiz.query.count(),
        "totalQuestions": Question.query.count(),
        "totalChapters": Chapter.query.count(),
        "totalSubjects": Subject.query.count(),
        "totalUsers": User.query.count()
    }
    return jsonify(stats)


@admin_bp.route('/mail', methods=['GET'])
@jwt_required()
@handle_exception
def send_mail():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    # Check if admin
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can access site Stats.")
    from app import mail
    msg = Message(
        subject="Test Email",
        recipients=["admin@example.com"],
        body="This is a test email sent via MailHog"
    )
    mail.send(msg)


@admin_bp.route('/search/users')
@jwt_required()
@handle_exception
def search_users():
    q = request.args.get('q', '').lower()
    users = User.query.filter(
        or_(
            User.full_name.ilike(f"%{q}%"),
            User.email.ilike(f"%{q}%")
        )).all()
    return jsonify([u.serialize() for u in users])


@admin_bp.route('/search/subjects')
@jwt_required()
@handle_exception
def search_subjects():
    q = request.args.get('q', '').lower()
    subjects = Subject.query.filter(func.lower(Subject.name).like(f"%{q}%")).all()
    return jsonify([s.serialize() for s in subjects])

@admin_bp.route('/search/quizzes')
@jwt_required()
@handle_exception
def search_quizzes():
    q = request.args.get('q', '').lower()
    quizzes = Quiz.query.join(Subject).filter(
        (func.lower(Quiz.title).like(f"%{q}%")) | (func.lower(Subject.name).like(f"%{q}%"))
    ).all()
    return jsonify([qz.serialize() for qz in quizzes])



@admin_bp.route('/search', methods=['GET'])
@jwt_required()
@handle_exception
def admin_search():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    # Check if admin
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can access site Stats.")
    
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify({"users": [], "subjects": [], "quizzes": []})

    # --- Search Users (match by name or email) ---
    user_results = User.query.filter(
        (User.full_name.ilike(f"%{query}%")) |
        (User.email.ilike(f"%{query}%"))
    ).limit(10).all()

    # --- Search Subjects (match by title/name) ---
    subject_results = Subject.query.filter(
        Subject.name.ilike(f"%{query}%")
    ).limit(10).all()

    # --- Search Quizzes (match by title) ---
    quiz_results = Quiz.query.filter(
        Quiz.title.ilike(f"%{query}%")
    ).limit(10).all()

    return jsonify({
        "users": [user.serialize() for user in user_results],
        "subjects": [subject.serialize() for subject in subject_results],
        "quizzes": [quiz.serialize() for quiz in quiz_results]
    })
