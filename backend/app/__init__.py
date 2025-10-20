import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_object=None):
    app = Flask(__name__, static_folder='../frontend/src', static_url_path='/')
    # Configurable via env vars
    app.config.from_mapping(
        SECRET_KEY = os.environ.get('SECRET_KEY','dev-secret-change-me'),
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL','sqlite:///db.sqlite3'),
        SQLALCHEMY_TRACK_MODIFICATIONS = False,
        JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY','jwt-secret-change-me')
    )
    if config_object:
        app.config.from_object(config_object)
    db.init_app(app)
    jwt.init_app(app)

    # register blueprints
    from .routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app
