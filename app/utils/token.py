import jwt
from datetime import datetime, timedelta
from flask import current_app

def generate_jwt(user_id, email):
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def decode_jwt(token):
    try:
        return jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

