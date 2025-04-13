from datetime import datetime, timezone
from app.extensions import db
from sqlalchemy import func, select

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Username field
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(50), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    role = db.Column(db.String(10), default='user', nullable=False)  # 'admin' or 'user'

    quiz_attempts = db.relationship('QuizAttempt', backref='user', cascade='all, delete-orphan')
    
    def serialize(self):
        return {
            "id": self.id,
            "name": self.full_name,
            "email": self.email,
            "role": self.role,
            "qualification": self.qualification if self.qualification else None,
            "dob": self.dob.isoformat() if self.dob else None
        }

    def __repr__(self):
        return f"<User(id={self.id}, name={self.full_name}, role={self.role})>"


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

    chapters = db.relationship('Chapter', backref='subject', cascade='all, delete-orphan')

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "chapters": [chapter.serialize() for chapter in self.chapters]
        }
    def __repr__(self):
        return f"<Subject(id={self.id}, name={self.name}, description={self.description[:50]})>"


quiz_chapters = db.Table(
    'quiz_chapters',
    db.Column('quiz_id', db.Integer, db.ForeignKey('quiz.id'), primary_key=True),
    db.Column('chapter_id', db.Integer, db.ForeignKey('chapter.id'), primary_key=True)
)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

    quizzes = db.relationship('Quiz', secondary=quiz_chapters, back_populates='chapters')

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "subject_id": self.subject_id
        }
    
    def __repr__(self):
        return f"<Chapter(id={self.id}, name={self.name}, subject={self.subject_id})>"


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)  # Associate with Subject
    time_limit = db.Column(db.Integer, nullable=True)  # Time in minutes, null for no limit
    start_time = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))  # When quiz starts
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)  # When quiz ends
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now(timezone.utc))

    # Relationships
    chapters = db.relationship('Chapter', secondary=quiz_chapters, back_populates='quizzes')
    questions = db.relationship('Question', backref='quiz', cascade='all, delete-orphan', lazy='dynamic')
    attempts = db.relationship('QuizAttempt', backref='quiz', cascade='all, delete-orphan')
    
    @property
    def total_marks(self):
        """Calculate total marks based on marks assigned to questions."""
        return sum(question.marks for question in self.questions)

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "subject_id": self.subject_id,
            "duration": self.time_limit,
            "total_marks": self.total_marks,
            "chapters": [chapter.serialize() for chapter in self.chapters],
            "num_of_questions": self.questions.count()
        }
    
    def __repr__(self):
        return f"<Quiz(id={self.id}, title={self.title}, subject_id={self.subject_id})>"


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Integer, nullable=False)  # Marks for a correct response
    negative_marks = db.Column(db.Float, nullable=False, default=0.0)  # Negative marks for incorrect options
    question_type = db.Column(db.Enum('MCQ', 'MSQ', name='question_type'), nullable=False, default='MCQ')
    correct_options = db.Column(db.JSON, nullable=False)  # Correct option(s), stored as JSON
    options = db.relationship('Option', backref='question', cascade='all, delete-orphan')

    def calculate_score(self, selected_options):
        """
        Calculate the score for the question based on selected options.
        Args:
            selected_options (list): List of selected option IDs.
        Returns:
            float: Score for the question.
        """
        print(selected_options)
        if not selected_options:
            return 0
        if self.question_type == 'MCQ':
            return self.marks if selected_options == self.correct_options[0] else -self.negative_marks
        elif self.question_type == 'MSQ':
            correct_set = set(self.correct_options or [])
            selected_set = set(selected_options)

            incorrect_selected = selected_set - correct_set
            if incorrect_selected:
                return 0
            
            correct_selected = correct_set & selected_set
            return len(correct_selected) * (self.marks / len(correct_set))
        return 0

      
    def __repr__(self):
        return f"<Question(id={self.id}, quiz_id={self.quiz_id}, text={self.text[:50]}, type={self.question_type})>"


class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Option(id={self.id}, question_id={self.question_id}, text={self.text[:50]})>"


class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    score = db.Column(db.Float, nullable=False, default=0)
    attempt_date = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

    def serialize(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "quiz_id": self.quiz_id,
            "quiz_title": self.quiz.title if self.quiz else None,
            "attempt_date": self.attempt_date.isoformat(),
            "score": self.score
        }
    def __repr__(self):
        return f"<QuizAttempt(id={self.id}, user_id={self.user_id}, quiz_id={self.quiz_id})>"

