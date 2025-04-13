# backend/app/tasks/reminders.py
from app.celery_app import celery
from flask_mail import Message
from app.models import User, Quiz
from datetime import datetime, timezone, timedelta

@celery.task
def send_daily_reminders():
    from app import create_app
    from app.extensions import mail, db
    app = create_app()
    with app.app_context():
        now = datetime.now(timezone.utc)
        new_quiz_cutoff = now - timedelta(days=1)

        users = User.query.all()
        for user in users:
            # Find new quizzes added in last 1 day
            new_quizzes = Quiz.query.filter(Quiz.created_at >= new_quiz_cutoff).all()

            if new_quizzes:
                quiz_titles = '\n'.join([q.title for q in new_quizzes])
                msg = Message(
                    subject="New Quizzes Added - Don't Miss Out!",
                    recipients=[user.email],
                    body=f"Hi {user.full_name},\n\nNew quizzes were added:\n\n{quiz_titles}\n\nCheck and attempt them!"
                )
                mail.send(msg)
