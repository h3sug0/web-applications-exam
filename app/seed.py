from app import db
from app.models import Genre, Role, User
from werkzeug.security import generate_password_hash


def seed_db():
    roles = [
        ("admin", "Администратор", "Суперпользователь с полным доступом к системе."),
        ("moderator", "Модератор", "Редактирует книги и модерирует рецензии."),
        ("user", "Пользователь", "Оставляет рецензии и формирует подборки книг."),
    ]
    for slug, name, description in roles:
        if not Role.query.filter_by(slug=slug).first():
            db.session.add(Role(slug=slug, name=name, description=description))

    genres = ["Роман", "Фантастика", "Научная литература", "История", "Поэзия", "Детектив"]
    for name in genres:
        if not Genre.query.filter_by(name=name).first():
            db.session.add(Genre(name=name))

    db.session.flush()

    users = [
        ("admin", "admin", "Админов", "Алексей", "Петрович", "admin"),
        ("moderator", "moderator", "Модеров", "Мария", "Ивановна", "moderator"),
        ("user", "user", "Читателев", "Иван", "Сергеевич", "user"),
    ]
    for login, password, last_name, first_name, middle_name, role_slug in users:
        if not User.query.filter_by(login=login).first():
            role = Role.query.filter_by(slug=role_slug).first()
            db.session.add(
                User(
                    login=login,
                    password_hash=generate_password_hash(password),
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name,
                    role=role,
                )
            )

    db.session.commit()
