# backend/app/tasks/monthly_report.py
from ..celery_app import celery
from flask_mail import Message

from app.models import User, QuizAttempt
from datetime import datetime, timezone


def calculate_rank(user_id, quiz_id):
    # Get all attempts for the given quiz
    attempts = QuizAttempt.query.filter(
        QuizAttempt.quiz_id == quiz_id
    ).order_by(QuizAttempt.score.desc()).all()

    # Iterate through the sorted attempts to find the user's rank
    for rank, attempt in enumerate(attempts, start=1):
        if attempt.user_id == user_id:
            return rank

    return None  # Return None if the user has no attempts for the quiz

@celery.task
def send_monthly_reports():
    from app import create_app
    from app.extensions import mail, db
    app = create_app()
    with app.app_context():
        first_day = datetime.now(timezone.utc).replace(day=1)
        users = User.query.all()

        for user in users:
            attempts = QuizAttempt.query.filter(
                QuizAttempt.user_id == user.id,
                QuizAttempt.attempt_date >= first_day
            ).all()

            total = len(attempts)
            avg_score = sum([a.score for a in attempts]) / total if total else 0

            # Generate HTML for the email
            html = f"""
                <h2>Monthly Activity Report - {user.full_name}</h2>
                <p>Total quizzes taken: {total}</p>
                <p>Average Score: {avg_score:.2f}</p>
                <ul>
            """
            for attempt in attempts:
                rank = calculate_rank(user.id, attempt.quiz_id)
                html += f"<li>{attempt.quiz.title} - {attempt.score} (Rank: {rank})</li>"

            html += "</ul>"

            msg = Message(
                subject=f"{user.full_name}'s Monthly Activity Report",
                recipients=[user.email],
                html=html
            )
            mail.send(msg)
