from flask import request, jsonify
from app.services.auth_service import register_user, login_user
from app.utils.exceptions import handle_exception
from . import auth_bp


@auth_bp.route('/register', methods=['POST'])
@handle_exception
def register():
    data = request.json
    response = register_user(
        email=data['email'],
        password=data['password'],
        full_name=data['full_name'],
        qualification=data['qualification'],
        dob=data['dob']
    )
    return jsonify(response), 201

@auth_bp.route('/login', methods=['POST'])
@handle_exception
def login():
    data = request.json
    response = login_user(data['email'], data['password'])
    return jsonify(response), 200
    
@auth_bp.route('/debug', methods=['GET'])
def debug_jwt():
    return {"message": "JWT is working!"}
