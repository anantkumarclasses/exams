from datetime import datetime
from app.utils.auth import hash_password, verify_password
from app.utils.token import generate_jwt
from app.extensions import db
from app.models import User
from app.utils.exceptions import ValidationError
from datetime import datetime
#from app.utils.email import send_email_verification

def register_user(email, password, full_name, qualification=None, dob=None, role='user'):
    if User.query.filter_by(email=email).first():
        raise ValidationError("Email is already registered.")
    
    new_user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        qualification=qualification,
        dob=datetime.strptime(dob, "%Y-%m-%d").date() if dob else None,
        role=role
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    # Send email verification if required
    #send_email_verification(email)
    return {"message": "User registered successfully!"}


def login_user(email, password):
    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(user.password_hash, password):
        raise ValidationError("Invalid credentials.")
    
    token = generate_jwt(user.id, user.email)
    
    return {
        "token": token,
        "role": user.role,
        "full_name": user.full_name
    }


