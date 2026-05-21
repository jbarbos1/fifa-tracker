from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from flask_migrate import Migrate
import os

db = SQLAlchemy()
load_dotenv()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate.init_app(app, db)

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_size": 5,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ing": True,
    }

    from .routes import main
    from . import models
    app.register_blueprint(main)

    from .admin_routes import admin
    app.register_blueprint(admin, url_prefix='/admin')

    from app.jobs.scheduler import start_jobs
    start_jobs(app)

    return app
