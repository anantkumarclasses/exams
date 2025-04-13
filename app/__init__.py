from flask import Flask
from app.extensions import db, migrate, jwt, mail, cache
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.blueprints.auth import auth_bp
from app.blueprints.subjects import subject_bp
from app.blueprints.chapters import chapter_bp
from app.blueprints.quizzes import quiz_bp
from app.blueprints.admin import admin_bp
from app.blueprints.user import user_bp
from app.tasks.scheduler import start_scheduler
from flask_caching import Cache


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")
    CORS(app)
    
    db.init_app(app)
    migrate.init_app(app,db)
    jwt.init_app(app)
    mail.init_app(app)
    cache.init_app(app)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(subject_bp, url_prefix='/subjects')
    app.register_blueprint(chapter_bp, url_prefix='/chapters')
    app.register_blueprint(quiz_bp, url_prefix='/quiz')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix="/user")

    #with app.app_context():
    #    if not hasattr(app, 'scheduler_started'):
    #        start_scheduler()
    #        app.scheduler_started = True

    @app.route("/")
    def index():
        return "Flask backend is up!"
    
    return app

