# backend/app/tasks/csv_exports.py
from app.celery_app import celery
from flask_mail import Message
import csv
from io import StringIO


@celery.task
def export_user_quiz_csv(user_id):
    from app import create_app
    from app.extensions import mail, db
    app = create_app()
    with app.app_context():
        from app.models import User, QuizAttempt, Quiz, Chapter
        user = User.query.get(user_id)
        attempts = QuizAttempt.query.filter_by(user_id=user_id).all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Quiz ID', 'Chapter ID(s)', 'Date of Quiz', 'Score', 'Remarks'])

        for a in attempts:
            chapter_ids = ', '.join(str(c.id) for c in a.quiz.chapters)
            writer.writerow([a.quiz.id, chapter_ids, a.timestamp.date(), a.score, ''])

        msg = Message(
            subject='Your Quiz Report CSV',
            recipients=[user.email],
            body='Attached is your quiz history export.',
        )
        msg.attach('quiz_report.csv', 'text/csv', output.getvalue())
        mail.send(msg)


@celery.task
def export_all_users_quiz_csv(admin_id):
    from app import create_app
    from app.extensions import mail, db
    app = create_app()
    with app.app_context():
        from app.models import User, QuizAttempt, Quiz, Subject, Chapter
        from sqlalchemy import func

        attempts = db.session.query(QuizAttempt).join(Quiz).join(User).all()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['User ID', 'User Name', 'Quiz Title', 'Subject', 'Chapters', 'Total Marks', 'Attempt Date'])
        for attempt in attempts:
            user_id = attempt.user_id
            user_name = User.query.get(user_id).full_name if user_id else 'N/A'
            quiz = Quiz.query.get(attempt.quiz_id)
            quiz_title = quiz.title if quiz else 'N/A'
            subject = Subject.query.get(quiz.subject_id).name if quiz and quiz.subject_id else 'N/A'
            chapters = [Chapter.query.filter_by(id=chapter.id).all()[0].name for chapter in quiz.chapters]
            chapter_list = ', '.join(chapters)
            score = attempt.score
            attempt_date = attempt.attempt_date.strftime("%Y-%m-%d %H:%M")
            writer.writerow([user_id, user_name, quiz_title, subject, chapter_list, score, attempt_date])

        admin = User.query.get(admin_id)
        msg = Message(
            subject='Export of All Users Quiz Performance',
            recipients=[admin.email],
            body='Attached is the CSV file for user performance.',
        )
        msg.attach('all_users_performance.csv', 'text/csv', output.getvalue())
        mail.send(msg)

