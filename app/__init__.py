import os

from dotenv import load_dotenv
from flask import Flask

from app.extensions import db, migrate

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)

    # ------------------------------------------------------------------ #
    # Config
    # ------------------------------------------------------------------ #
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///graham.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

    # ------------------------------------------------------------------ #
    # Extensions
    # ------------------------------------------------------------------ #
    db.init_app(app)
    migrate.init_app(app, db)

    # ------------------------------------------------------------------ #
    # Models
    # ------------------------------------------------------------------ #
    from app import models  # noqa: F401
    from app import models  # noqa: F401

    # ------------------------------------------------------------------ #
    # Blueprints
    # ------------------------------------------------------------------ #
    from app.routes import main
    app.register_blueprint(main)

    # Optional admin routes
    try:
        from app.admin_routes import admin
        app.register_blueprint(admin, url_prefix="/admin")
    except ImportError:
        pass

    # Optional background jobs
    try:
        from app.jobs.scheduler import start_jobs
        start_jobs(app)
    except ImportError:
        pass

    return app
