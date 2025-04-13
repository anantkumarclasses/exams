from flask import Blueprint

subject_bp = Blueprint('subjects', __name__)

from . import routes
