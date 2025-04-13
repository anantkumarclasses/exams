from flask import Blueprint

quiz_bp = Blueprint('quizzes', __name__)

from . import routes
