from functools import wraps
from flask import jsonify

class ValidationError(Exception):
    def __init__(self, message):
        self.message = message

def handle_exception(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as ve:
            return jsonify({"error": ve.message}), 400
        except Exception as e:
            return jsonify({"error": "An internal error occurred."}), 500
    return wrapper

