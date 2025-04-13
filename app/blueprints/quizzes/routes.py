from flask import request, jsonify, send_file
from datetime import datetime, timezone
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from app.extensions import db, cache   
from app.models import Chapter, Subject, User, Quiz, Question, Option, QuizAttempt
from app.utils.exceptions import ValidationError, handle_exception
from . import quiz_bp
import io
import csv
from app.tasks.csv_export import export_all_users_quiz_csv


@quiz_bp.route('/create_quiz', methods=['POST'])
@jwt_required()
@handle_exception
def create_quiz():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    # Check if admin
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can create quizzes.")

    # Parse data
    data = request.json
    title = data.get('title')
    description = data.get('description', '')
    subject_id = data.get('subject_id')
    chapter_ids = data.get('chapter_ids', [])  # List of chapter IDs
    time_limit = data.get('time_limit', None)
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    # Validate
    if not title or not subject_id or not start_time_str or not end_time_str:
        raise ValidationError("Fields 'title', 'subject_id', 'start_time', and 'end_time' are required.")
        
    # Convert start_time and end_time to datetime
    try:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise ValidationError("Invalid date format. Use 'YYYY-MM-DD HH:MM:SS'.")

    # Ensure start_time is before end_time
    if start_time >= end_time:
        raise ValidationError("Start time must be before end time.")


    # Validate Subject
    subject = Subject.query.get(subject_id)
    if not subject:
        raise ValidationError(f"Subject with ID {subject_id} does not exist.")

    # Validate Chapters
    chapters = Chapter.query.filter(Chapter.id.in_(chapter_ids)).all()
    if not chapters or len(chapters) != len(chapter_ids):
        raise ValidationError("Some or all chapters do not exist.")

    # Create Quiz
    quiz = Quiz(
        title=title,
        description=description,
        subject_id=subject_id,
        time_limit=time_limit,
        start_time=start_time,
        end_time=end_time
    )
    quiz.chapters.extend(chapters)  # Add chapters to the quiz
    db.session.add(quiz)
    db.session.commit()

    return jsonify({
        "message": "Quiz created successfully!",
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "subject_id": quiz.subject_id,
            "time_limit": quiz.time_limit,
            "start_time": quiz.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": quiz.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "chapters": [chapter.id for chapter in quiz.chapters] 
        }
    }), 201

@quiz_bp.route('/edit_quiz/<int:quiz_id>', methods=['PUT'])
@jwt_required()
@handle_exception
def edit_quiz(quiz_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    # Check if admin
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can edit quizzes.")
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        raise ValidationError(f"Quiz with ID {quiz_id} does not exist.")
    
    # Parse and update data
    data = request.json
    quiz.title = data.get('title', quiz.title)
    quiz.description = data.get('description', quiz.description)
    quiz.time_limit = data.get('time_limit', quiz.time_limit)
    
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    if start_time_str:
        try:
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            quiz.start_time = start_time
        except ValueError:
            raise ValidationError("Invalid date format for start_time. Use 'YYYY-MM-DD HH:MM:SS'.")

    if end_time_str:
        try:
            end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
            quiz.end_time = end_time
        except ValueError:
            raise ValidationError("Invalid date format for end_time. Use 'YYYY-MM-DD HH:MM:SS'.")

    # Ensure start_time is before end_time if both are provided
    if quiz.start_time and quiz.end_time and quiz.start_time >= quiz.end_time:
        raise ValidationError("Start time must be before end time.")
    
    db.session.commit()

    return jsonify({
        "message": "Quiz updated successfully!",
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "time_limit": quiz.time_limit,
            "start_time": quiz.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": quiz.end_time.strftime("%Y-%m-%d %H:%M:%S")
        }
    }), 200


@quiz_bp.route('/delete_quiz/<int:quiz_id>', methods=['DELETE'])
@jwt_required()
@handle_exception
def delete_quiz(quiz_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    # Check if admin
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can delete quizzes.")
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        raise ValidationError(f"Quiz with ID {quiz_id} does not exist.")

    db.session.delete(quiz)
    db.session.commit()

    return jsonify({"message": "Quiz deleted successfully!"}), 200
    
@quiz_bp.route('/list', methods=['GET'])
@jwt_required()
@handle_exception
#@cache.cached(timeout=3600, key_prefix='quiz_list')
def list_quizzes():
    subject_id = request.args.get('subject_id', type=int)
    chapter_id = request.args.get('chapter_id', type=int)
    page = request.args.get('page', 1, type=int)  
    size = request.args.get('size', 10, type=int)
    #print(f"Page: {page}, Size: {size}")  # Debugging
    if page < 1 or size < 1:
        raise ValidationError("Page and size must be positive integers.")

    query = Quiz.query
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if chapter_id:
        query = query.filter(Quiz.chapters.any(id=chapter_id))

    # Apply pagination
    paginated_quizzes = query.paginate(page=page, per_page=size, error_out=False)
    
    quiz_list = [{
        "id": quiz.id,
        "title": quiz.title,
        "subject_id": quiz.subject_id,
        "total_marks": quiz.total_marks,
        "chapters": [chapter.id for chapter in quiz.chapters] if quiz.chapters else []
    } for quiz in paginated_quizzes.items]

    return jsonify({
        "quizzes": quiz_list,
        "total_pages": paginated_quizzes.pages,
        "has_next": paginated_quizzes.has_next,
        "has_prev": paginated_quizzes.has_prev,
        "current_page": paginated_quizzes.page,
        "total_items": paginated_quizzes.total
    }), 200

@quiz_bp.route('/allquizzes', methods=['GET'])
@jwt_required()
@handle_exception
def all_quizzes():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    # Check if admin
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can view all quizzes.")

    query = Quiz.query.all()
       
    quiz_list = [{
        "id": quiz.id,
        "title": quiz.title,
        "subject_id": quiz.subject_id,
        "total_marks": quiz.total_marks,
        "chapters": [chapter.id for chapter in quiz.chapters] if quiz.chapters else []
    } for quiz in query]

    return jsonify(quiz_list), 200


@quiz_bp.route('/details/<int:quiz_id>', methods=['GET'])
@jwt_required()
@handle_exception
def get_quiz_details(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        raise ValidationError(f"Quiz with ID {quiz_id} does not exist.")

    return jsonify({
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "subject_id": quiz.subject_id,
            "subject": Subject.query.filter_by(id=quiz.subject_id).all()[0].name,
            "chapters": [chapter.id for chapter in quiz.chapters],
            "time_limit": quiz.time_limit,
            "total_marks": quiz.total_marks,  # Calculated dynamically
            "questions": [{
                "id": question.id,
                "text": question.text,
                "marks": question.marks
            } for question in quiz.questions]
        }
    }), 200


@quiz_bp.route('/microdetails/<int:quiz_id>', methods=['GET'])
@jwt_required()
@handle_exception
def get_quiz_microdetails(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        raise ValidationError(f"Quiz with ID {quiz_id} does not exist.")

    return jsonify({
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "subject": Subject.query.filter_by(id=quiz.subject_id).all()[0].name,
            "chapters": [Chapter.query.filter_by(id=chapter.id).all()[0].name for chapter in quiz.chapters],
            "duration": "Unlimited" if not quiz.time_limit else f"{quiz.time_limit // 60:02}:{quiz.time_limit % 60:02}",
            "total_marks": quiz.total_marks,  # Calculated dynamically
            "num_questions": quiz.questions.count()
        }
    }), 200


@quiz_bp.route('/upcoming-quizzes', methods=['GET'])
@jwt_required()
@handle_exception
@cache.cached(timeout=3600, key_prefix='upcoming_quizzes')
def get_upcoming_quizzes():
    user_id = get_jwt_identity()
    current_time = datetime.now(timezone.utc)
    
    try:
        # Get all quizzes that have at least one question and are within the valid time range
        quizzes = Quiz.query.filter(
            Quiz.questions.any(),
            Quiz.end_time >= current_time
        ).all()
        
        # Get quiz IDs the user has already attempted
        attempted_quiz_ids = {
            attempt.quiz_id 
            for attempt in QuizAttempt.query.filter_by(user_id=user_id).all()
        }
       
        # Filter out quizzes that the user has already attempted
        upcoming_quizzes = []
        for quiz in quizzes:
            if quiz.id not in attempted_quiz_ids:
                try:
                    # Ensure start_time and end_time are timezone-aware
                    start_time = quiz.start_time.replace(tzinfo=timezone.utc) if quiz.start_time.tzinfo is None else quiz.start_time
                    end_time = quiz.end_time.replace(tzinfo=timezone.utc) if quiz.end_time.tzinfo is None else quiz.end_time
                    
                    quiz_data = {
                        "id": quiz.id,
                        "title": quiz.title,
                        "subject": Subject.query.filter_by(id=quiz.subject_id).all()[0].name,
                        "description": quiz.description,
                        "num_questions": quiz.questions.count(),
                        "total_marks": quiz.total_marks,
                        "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
                        "duration": "Unlimited" if not quiz.time_limit else f"{quiz.time_limit // 60:02}:{quiz.time_limit % 60:02}",
                        "starts_in": "already started" if start_time <= current_time else (start_time - current_time).total_seconds(),
                        "ends_in": (end_time - current_time).total_seconds(),
                        "end_time": end_time.strftime("%Y-%m-%d %H:%M")
                    }
                    upcoming_quizzes.append(quiz_data)
                except Exception as e:
                    print(f"Error processing quiz {quiz.id}: {str(e)}")
                    continue

        return jsonify(upcoming_quizzes), 200
    
    except Exception as e:
        print(f"Error in get_upcoming_quizzes: {str(e)}")
        return jsonify({"error": "An internal error occurred"}), 500


@quiz_bp.route('/add_question', methods=['POST'])
@jwt_required()
@handle_exception
def add_question():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user or user.role != 'admin':
        raise ValidationError("Only admins can add questions.")

    data = request.json
    #print(f"Received data: {data}")  # Debugging

    quiz_id = data.get('quiz_id')
    text = data.get('text')
    marks = data.get('marks')
    negative_marks = data.get('negative_marks', 0.0)
    question_type = data.get('question_type', 'MCQ')
    correct_option_indices = data.get('correct_options')
    options = data.get('options')

    required_fields = ["quiz_id", "text", "marks", "options", "correct_options"]
    missing_fields = [field for field in required_fields if field not in data or data[field] in (None, "")]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")


    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        raise ValidationError(f"Quiz with ID {quiz_id} does not exist.")

    #print("Just before question creation") 
    # Create question
    question = Question(
        quiz_id=quiz_id,
        text=text,
        marks=marks,
        negative_marks=negative_marks,
        question_type=question_type,
        correct_options=[]
    )
    #print(f"Inserting question: quiz_id={quiz_id}, text={text}, marks={marks}, type={question_type}")
    db.session.add(question)
    try:
        db.session.flush()
        print("Question inserted successfully!")
    except Exception as e:
        print(f"Error during flush: {e}")
        db.session.rollback()
    

    #print(f"Created question ID: {question.id}")  # Debugging

    # Add options
    option_objs = [Option(text=option, question_id=question.id) for option in options]
    db.session.add_all(option_objs)
    db.session.flush()

    #print(f"Created options: {[(option.id, option.text) for option in option_objs]}")  # Debugging

    # Convert indices to actual option IDs
    try:
        correct_option_ids = [option_objs[i].id for i in correct_option_indices]
    except IndexError as e:
        print(f"IndexError: {e}")  # Debugging
        raise ValidationError("Invalid indices in 'correct_options'.")

    #correct_option_ids = [option_objs[i].id for i in correct_option_indices]
    question.correct_options = correct_option_ids

    #print(f"Final correct_options: {question.correct_options}")  # Debugging

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()  # Rollback transaction
        print(f"Database Commit Error: {e}")
        raise ValidationError("Database error while saving the question.")

    
    return jsonify({
        "message": "Question and options added successfully!",
        "question": {
            "id": question.id,
            "quiz_id": question.quiz_id,
            "text": question.text,
            "marks": question.marks,
            "negative_marks": question.negative_marks,
            "question_type": question.question_type,
            #"correct_options": question.correct_options,
            "options": [{"id": option.id, "text": option.text} for option in option_objs],
        },
    }), 201


@quiz_bp.route('/edit_question/<int:question_id>', methods=['PUT'])
@jwt_required()
@handle_exception
def edit_question(question_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can edit questions.")

    question = Question.query.get_or_404(question_id)

    # Parse request data
    data = request.json
    question.text = data.get('text', question.text)
    question.marks = data.get('marks', question.marks)
    question.negative_marks = data.get('negative_marks', question.negative_marks)
    question.question_type = data.get('question_type', question.question_type)
    question.correct_options = data.get('correct_options', question.correct_options)

    # Update options (optional)
    options = data.get('options')
    if options:
        # Clear existing options and add new ones
        question.options.clear()
        for option_text in options:
            question.options.append(Option(text=option_text, question=question))
    
    db.session.commit()
    return jsonify({"message": "Question updated successfully!"}), 200


@quiz_bp.route('/delete_question/<int:question_id>', methods=['DELETE'])
@jwt_required()
@handle_exception
def delete_question(question_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user or user.role != 'admin':
        raise ValidationError("Only admins can delete questions.")

    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()

    return jsonify({"message": "Question deleted successfully!"}), 200

@quiz_bp.route('/get_questions/<int:quiz_id>', methods=['GET'])
@jwt_required()
def get_questions(quiz_id):
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    # Paginate the query
    pagination = Question.query.filter_by(quiz_id=quiz_id).paginate(page=page, per_page=size, error_out=False)
    
    # Get paginated questions
    questions = pagination.items
    
    # Serialize response
    return jsonify({
        "questions": [{
            "id": question.id,
            "text": question.text,
            "marks": question.marks,
            "negative_marks": question.negative_marks,
            "question_type": question.question_type,
            "correct_options": question.correct_options,
            "options": [{"id": opt.id, "text": opt.text} for opt in question.options]
        } for question in questions],
        "total_pages": pagination.pages,
        "current_page": pagination.page,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    }), 200


@quiz_bp.route('/start_attempt/<int:quiz_id>', methods=['POST'])
@jwt_required()
@handle_exception
def start_quiz_attempt(quiz_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    now = datetime.now(timezone.utc)
    
    if not user:
        raise ValidationError("User not found.")

    quiz = Quiz.query.get_or_404(quiz_id)

    start_time = quiz.start_time.replace(tzinfo=timezone.utc) if quiz.start_time.tzinfo is None else quiz.start_time
    end_time = quiz.end_time.replace(tzinfo=timezone.utc) if quiz.end_time.tzinfo is None else quiz.end_time

    if not (start_time <= now <= end_time):
        raise ValidationError("Quiz is not available at the moment.")

    existing_attempt = QuizAttempt.query.filter_by(user_id=user.id, quiz_id=quiz_id).first()
    
    if existing_attempt:
        return jsonify({"message": "Quiz attempt already started.", "attempt_id": existing_attempt.id, "quiz_title": quiz.title, "time_limit": quiz.time_limit}), 200

    attempt = QuizAttempt(user_id=user.id, quiz_id=quiz_id, score=0)
    
    db.session.add(attempt)
    db.session.commit()

    return jsonify({"message": "Quiz attempt started.", "attempt_id": attempt.id, "quiz_title": quiz.title,"time_limit": quiz.time_limit}), 201

@quiz_bp.route('/submit_attempt/<int:attempt_id>', methods=['POST'])
@jwt_required()
@handle_exception
def submit_quiz_attempt(attempt_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user:
        raise ValidationError("User not found.")

    attempt = QuizAttempt.query.get_or_404(attempt_id)

    if attempt.user_id != user.id:
        raise ValidationError("Unauthorized access to this quiz attempt.")

    # Fetch answers from the request
    submitted_answers = request.json.get('answers', {})

    # Calculate the score
    score = 0
    correct_answers = {}
    for question_id, selected_options in submitted_answers.items():
        question = Question.query.get(question_id)
        if question:
            score += question.calculate_score(selected_options)
            correct_answers[question_id] = question.correct_options

    attempt.score = score
    db.session.commit()

    return jsonify({
        "message": "Quiz submitted successfully!", 
        "score": score,
        "total_marks": attempt.quiz.total_marks,
        "quiz_title": attempt.quiz.title,
        "correct_answers": correct_answers
    }), 200


@quiz_bp.route('/get_attempt_result/<int:attempt_id>', methods=['GET'])
@jwt_required()
@handle_exception
def get_attempt_result(attempt_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user:
        raise ValidationError("User not found.")

    attempt = QuizAttempt.query.get_or_404(attempt_id)

    if attempt.user_id != user.id:
        raise ValidationError("Unauthorized access to this quiz attempt.")

    return jsonify({
        "attempt_id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "score": attempt.score,
        "created_at": attempt.created_at.isoformat()
    }), 200

@quiz_bp.route('/user_attempts', methods=['GET'])
@jwt_required()
@handle_exception
def get_user_attempts():
    current_user_id = get_jwt_identity()
    attempts = QuizAttempt.query.filter_by(user_id=current_user_id).all()
    
    result = []
    for attempt in attempts:
        quiz = Quiz.query.get(attempt.quiz_id)
        result.append({
            "quiz_id": quiz.id,
            "quiz_title": quiz.title,
            "subject": Subject.query.filter_by(id=quiz.subject_id).all()[0].name,
            "attempt_id": attempt.id,
            "num_questions": quiz.questions.count(),
            "score": attempt.score,
            "total_marks": quiz.total_marks,
            "date": attempt.attempt_date.strftime("%Y-%m-%d %H:%M")
        })

    return jsonify(result), 200


@quiz_bp.route('/user/summary_stats', methods=['GET'])
@jwt_required()
@handle_exception
#@cache.cached(timeout=3600, key_prefix='user_summary')
def get_user_summary():
    user_id = get_jwt_identity()
    # print(f"User ID: {user_id}")
    
    # Fix the query to properly join tables and handle NULL values
    subject_scores = db.session.query(
        Subject.name,
        func.coalesce(func.avg(QuizAttempt.score), 0.0)  # Handle NULL values
    ).join(
        Quiz, Quiz.subject_id == Subject.id  # Explicit join condition
    ).join(
        QuizAttempt, QuizAttempt.quiz_id == Quiz.id  # Explicit join condition
    ).filter(
        QuizAttempt.user_id == user_id
    ).group_by(
        Subject.name
    ).all()
    
    # print(f"Subject Scores: {subject_scores}")

    monthly_attempts = db.session.query(
        func.strftime('%Y-%m', QuizAttempt.attempt_date).label('month'),
        func.count().label('count')
    ).filter(
        QuizAttempt.user_id == user_id
    ).group_by(
        'month'
    ).order_by(
        'month'
    ).all()

    #print(f"Monthly Attempts: {monthly_attempts}")


    return jsonify({
        "subject_scores": [
            {
                "subject": s[0],
                "avg_score": float(s[1]) if s[1] is not None else 0.0
            } for s in subject_scores
        ],
        "monthly_attempts": [
            {
                "month": m[0],
                "count": m[1]
            } for m in monthly_attempts
        ]
    })


@quiz_bp.route('/admin/top_quizzes', methods=['GET'])
@jwt_required()
@handle_exception
@cache.cached(timeout=3600, key_prefix='top_quizzes')
def top_quizzes():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user or user.role != 'admin':
        raise ValidationError("Only admins have this facility.")
    
    data = db.session.query(
        Quiz.title,
        func.count(QuizAttempt.id)
    ).join(QuizAttempt, Quiz.id == QuizAttempt.quiz_id
    ).group_by(Quiz.title).order_by(func.count(QuizAttempt.id).desc()).limit(5).all()

    return jsonify([
        {"quiz": d[0], "attempts": d[1]} for d in data
    ])

@quiz_bp.route('/admin/subject_avg_scores', methods=['GET'])
@jwt_required()
@handle_exception
@cache.cached(timeout=3600, key_prefix='subject_avg_scores')
def subject_avg_scores():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user or user.role != 'admin':
        raise ValidationError("Only admins have this facility.")

    total_marks_subquery = db.session.query(
        Question.quiz_id.label('quiz_id'),
        func.sum(Question.marks).label('total_marks')
    ).group_by(
        Question.quiz_id
    ).subquery()

    result = db.session.query(
        Subject.name.label('subject'),
        func.coalesce(func.avg(QuizAttempt.score/ total_marks_subquery.c.total_marks) * 100, 0.0).label('avg_score_percent')
    ).join(Quiz, Quiz.subject_id == Subject.id).join(
        QuizAttempt, QuizAttempt.quiz_id == Quiz.id
    ).join(
        total_marks_subquery, total_marks_subquery.c.quiz_id == Quiz.id
    ).group_by(
        Subject.name
    ).all()

    return jsonify([
        {
            "subject": row.subject,
            "avg_score": round(row.avg_score_percent or 0.0, 2)
        } for row in result
    ])

@quiz_bp.route('/export/all_csv', methods=['GET'])
@jwt_required()
@handle_exception

def export_all_quizzes_csv():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user or user.role != 'admin':
        raise ValidationError("Only admins have this facility.")

    attempts = db.session.query(QuizAttempt).join(Quiz).join(User).all()
    print(f"Fetched {len(attempts)} attempts for CSV export.")
    # print(attempts)

    # Generate CSV data in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['User ID', 'User Name', 'Quiz Title', 'Subject', 'Chapters', 'Total Marks', 'Attempt Date'])
    print("CSV header written.")

    for attempt in attempts:
        user_id = attempt.user_id
        #print(f"Processing attempt for user ID: {user_id}")
        user_name = User.query.get(user_id).full_name if user_id else 'N/A'
        #print(f"User name: {user_name}")
        quiz = Quiz.query.get(attempt.quiz_id)
        quiz_title = quiz.title if quiz else 'N/A'
        #print(f"Quiz title: {quiz_title}")
        subject = Subject.query.get(quiz.subject_id).name if quiz and quiz.subject_id else 'N/A'
        #print(f"Subject: {subject}")
        chapters = [Chapter.query.filter_by(id=chapter.id).all()[0].name for chapter in quiz.chapters]
        chapter_list = ', '.join(chapters)
        #print(f"Chapter list: {chapter_list}")
        score = attempt.score
        #print(f"Score: {score}")
        attempt_date = attempt.attempt_date.strftime("%Y-%m-%d %H:%M")
        writer.writerow([user_id, user_name, quiz_title, subject, chapter_list, score, attempt_date])

    print("CSV rows written.")
    # Prepare response
    output.seek(0)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    output.close()

    return send_file(
        mem,
        mimetype='text/csv',
        download_name='all_quizzes_export.csv',
        as_attachment=True
    )

@quiz_bp.route('/export/trigger', methods=['POST'])
@jwt_required()
@handle_exception
def trigger_export():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user or user.role != 'admin':
        raise ValidationError("Only admins have this facility.")

    # Here you would typically trigger a background task to generate the CSV
    # For simplicity, we'll just return a success message
    export_all_users_quiz_csv(current_user_id)
    return jsonify({"message": "Export job started successfully!"}), 200


