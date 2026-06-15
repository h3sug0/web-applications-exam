import os

from flask import Flask, g, session
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
        static_folder="../static",
    )

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(base_dir, "library.db"),
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(base_dir, "uploads", "covers"),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.models import User
    from app.routes.auth import auth_bp
    from app.routes.books import books_bp
    from app.routes.collections import collections_bp

    @app.before_request
    def load_current_user():
        g.user = None
        user_id = session.get("user_id")
        if user_id:
            g.user = db.session.get(User, user_id)

    @app.context_processor
    def inject_helpers():
        return {
            "current_user": g.get("user"),
            "full_name": full_name,
            "can_edit_books": lambda: bool(
                g.user and g.user.role.slug in {"admin", "moderator"}
            ),
            "can_delete_books": lambda: bool(g.user and g.user.role.slug == "admin"),
            "can_manage_collections": lambda: bool(g.user and g.user.role.slug == "user"),
        }

    app.register_blueprint(books_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(collections_bp)

    register_cli(app)
    return app


def full_name(user):
    if not user:
        return ""
    return " ".join(
        part for part in [user.last_name, user.first_name, user.middle_name] if part
    )


def register_cli(app):
    @app.cli.command("seed-db")
    def seed_db_command():
        from app.seed import seed_db

        seed_db()
        print("Seed data has been added.")
