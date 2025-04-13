from flask import Blueprint

chapter_bp = Blueprint('chapters', __name__)

from . import routes
