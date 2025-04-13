from flask import request, jsonify, send_file, after_this_request
from datetime import datetime, timezone
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from app.extensions import db, cache   
from app.models import Chapter, Subject, User, Quiz, Question, Option, QuizAttempt
from app.utils.exceptions import ValidationError, handle_exception
from . import user_bp
from fpdf import FPDF
import base64
import io
import os
import tempfile


@user_bp.route('/scores')
@jwt_required()
def filter_scores():
    current_user_id = get_jwt_identity()
    date_filter = request.args.get('date')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)

    query = QuizAttempt.query.filter_by(user_id=current_user_id)

    if date_filter:
        query = query.filter(func.date(QuizAttempt.timestamp) == date_filter)
    if min_score is not None:
        query = query.filter(QuizAttempt.score >= min_score)
    if max_score is not None:
        query = query.filter(QuizAttempt.score <= max_score)

    results = query.all()
    return jsonify([r.serialize() for r in results])


@user_bp.route('/search', methods=['GET'])
@jwt_required()
@handle_exception
def user_search():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    # Check if valid user
    if not user :
        raise ValidationError("User not found.")
    
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify({"subjects": [], "quizzes": [], "attempts": []})

    # --- Search Subjects (match by title/name) ---
    subject_results = Subject.query.filter(
        Subject.name.ilike(f"%{query}%")
    ).limit(20).all()

    # --- Search Quizzes (match by title) ---
    quiz_results = Quiz.query.filter(
        Quiz.start_time.ilike(f"%{query}%") | Quiz.end_time.ilike(f"%{query}%") | Quiz.title.ilike(f"%{query}%") | Quiz.created_at.ilike(f"%{query}%") | Quiz.updated_at.ilike(f"%{query}%")
    ).limit(20).all()

    # --- Search Attempts (match by user name) ---
    my_attempts = QuizAttempt.query.filter(
        QuizAttempt.user_id == int(current_user_id)
    ).filter(
        QuizAttempt.attempt_date.ilike(f"%{query}%") | QuizAttempt.score.ilike(f"%{query}%")
    ).limit(20).all()
    
    return jsonify({
        "attempts": [attempt.serialize() for attempt in my_attempts],
        "subjects": [subject.serialize() for subject in subject_results],
        "quizzes": [quiz.serialize() for quiz in quiz_results]
    })


@user_bp.route('/generate-pdf', methods=['POST'])
@jwt_required()
def generate_pdf():
    # Get current user
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json
    subject_chart = data.get("subject_chart")
    monthly_chart = data.get("monthly_chart")
    quiz_attempts = data.get("quiz_attempts", [])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Your Quiz Report", ln=True, align="C")
    pdf.ln(10)

    # Add Subject Chart
    if subject_chart:
        pdf.cell(200, 10, "Subject Score Chart", ln=True)
        img_data = base64.b64decode(subject_chart.split(",")[1])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
            temp_img.write(img_data)
            temp_img_path = temp_img.name
        pdf.image(temp_img_path, x=30, w=150)
        os.unlink(temp_img_path)  # Clean up the temporary file
        pdf.ln(10)

    # Add Monthly Attempts Chart
    if monthly_chart:
        pdf.cell(200, 10, "Monthly Attempts Chart", ln=True)
        img_data = base64.b64decode(monthly_chart.split(",")[1])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
            temp_img.write(img_data)
            temp_img_path = temp_img.name
        pdf.image(temp_img_path, x=40, w=125)
        os.unlink(temp_img_path)  # Clean up the temporary file
        pdf.ln(10)

    # Add Quiz Attempts Table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Quiz Attempts", ln=True)
    pdf.set_font("Arial", "", 10)
    for attempt in quiz_attempts:
        pdf.cell(200, 10, f"{attempt['quiz_title']}: {attempt['score']} / {attempt['total_marks']}", ln=True)

    pdf_path = os.path.join(os.path.dirname(__file__), '..', "monthly_report.pdf")
    pdf_path = os.path.abspath(pdf_path)
    pdf.output(pdf_path)

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception as e:
            print(f"Error deleting file {pdf_path}: {e}")
        return response

    return send_file(pdf_path, as_attachment=True, mimetype="application/pdf")