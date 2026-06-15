import hashlib
import os
import uuid
from datetime import datetime
from functools import wraps

import bleach
import markdown
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app import db
from app.models import Book, Cover, Genre, Review


books_bp = Blueprint("books", __name__)

PER_PAGE = 10
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union(
    {
        "p",
        "br",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "pre",
        "code",
        "blockquote",
        "ul",
        "ol",
        "li",
        "strong",
        "em",
        "hr",
    }
)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash("Для выполнения данного действия необходимо пройти процедуру аутентификации", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user.role.slug not in roles:
                flash("У вас недостаточно прав для выполнения данного действия", "danger")
                return redirect(url_for("books.index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def markdown_to_safe_html(text):
    raw_html = markdown.markdown(
        text or "",
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html5",
    )
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes={}, strip=True)


def rating_label(value):
    return {
        5: "отлично",
        4: "хорошо",
        3: "удовлетворительно",
        2: "неудовлетворительно",
        1: "плохо",
        0: "ужасно",
    }.get(int(value), "без оценки")


@books_bp.app_template_filter("markdown")
def markdown_filter(text):
    return markdown_to_safe_html(text)


@books_bp.app_context_processor
def inject_book_helpers():
    return {
        "rating_label": rating_label,
        "current_year": datetime.now().year,
    }


@books_bp.route("/")
def index():
    page = max(request.args.get("page", 1, type=int), 1)

    pagination = (
        db.session.query(
            Book,
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .outerjoin(Review)
        .group_by(Book.id)
        .order_by(Book.year.desc(), Book.id.desc())
        .paginate(page=page, per_page=PER_PAGE, error_out=False)
    )
    books = [
        {"book": book, "avg_rating": avg_rating, "review_count": review_count}
        for book, avg_rating, review_count in pagination.items
    ]

    return render_template("index.html", pagination=pagination, books=books)


@books_bp.route("/books/create", methods=["GET", "POST"])
@roles_required("admin")
def create_book():
    genres = Genre.query.order_by(Genre.name).all()

    if request.method == "POST":
        form = book_form_data()
        selected_genres = request.form.getlist("genres")
        ok, error = validate_book_form(form, selected_genres, require_cover=True)

        if ok:
            try:
                book = Book(
                    title=form["title"],
                    description=form["description"],
                    year=int(form["year"]),
                    publisher=form["publisher"],
                    author=form["author"],
                    page_count=int(form["page_count"]),
                )
                book.genres = Genre.query.filter(Genre.id.in_(selected_genres)).all()
                db.session.add(book)
                db.session.flush()

                save_cover(book, request.files["cover"])
                db.session.commit()

                flash("Книга успешно добавлена", "success")
                return redirect(url_for("books.book_detail", book_id=book.id))
            except Exception:
                db.session.rollback()
                flash("При сохранении данных возникла ошибка. Проверьте корректность введённых данных.", "danger")
        else:
            flash(error, "danger")

        return render_template(
            "book_form_page.html",
            mode="create",
            book=form,
            genres=genres,
            selected_genres=selected_genre_ids(selected_genres),
        )

    return render_template(
        "book_form_page.html",
        mode="create",
        book={},
        genres=genres,
        selected_genres=[],
    )


@books_bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@roles_required("admin", "moderator")
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    genres = Genre.query.order_by(Genre.name).all()

    if request.method == "POST":
        form = book_form_data()
        selected_genres = request.form.getlist("genres")
        ok, error = validate_book_form(form, selected_genres, require_cover=False)

        if ok:
            try:
                book.title = form["title"]
                book.description = form["description"]
                book.year = int(form["year"])
                book.publisher = form["publisher"]
                book.author = form["author"]
                book.page_count = int(form["page_count"])
                book.genres = Genre.query.filter(Genre.id.in_(selected_genres)).all()
                db.session.commit()

                flash("Данные книги успешно обновлены", "success")
                return redirect(url_for("books.book_detail", book_id=book.id))
            except Exception:
                db.session.rollback()
                flash("При сохранении данных возникла ошибка. Проверьте корректность введённых данных.", "danger")
        else:
            flash(error, "danger")

        return render_template(
            "book_form_page.html",
            mode="edit",
            book=form,
            genres=genres,
            selected_genres=selected_genre_ids(selected_genres),
        )

    return render_template(
        "book_form_page.html",
        mode="edit",
        book=book,
        genres=genres,
        selected_genres=[genre.id for genre in book.genres],
    )


@books_bp.route("/books/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    user_review = None
    collections = []

    if g.user:
        user_review = Review.query.filter_by(book_id=book.id, user_id=g.user.id).first()
        if g.user.role.slug == "user":
            collections = g.user.collections

    return render_template(
        "book_detail.html",
        book=book,
        reviews=book.reviews,
        user_review=user_review,
        collections=collections,
    )


@books_bp.route("/covers/<path:filename>")
def cover_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@books_bp.route("/books/<int:book_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    filename = book.cover.filename if book.cover else None

    try:
        db.session.delete(book)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("При удалении книги возникла ошибка", "danger")
        return redirect(url_for("books.index"))

    if filename and Cover.query.filter_by(filename=filename).count() == 0:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(path):
            os.remove(path)

    flash("Книга успешно удалена", "success")
    return redirect(url_for("books.index"))


@books_bp.route("/books/<int:book_id>/reviews/create", methods=["GET", "POST"])
@roles_required("admin", "moderator", "user")
def create_review(book_id):
    book = Book.query.get_or_404(book_id)
    existing_review = Review.query.filter_by(book_id=book.id, user_id=g.user.id).first()

    if existing_review:
        flash("Вы уже оставили рецензию на эту книгу", "warning")
        return redirect(url_for("books.book_detail", book_id=book.id))

    if request.method == "POST":
        rating = request.form.get("rating", type=int)
        text = request.form.get("text", "").strip()

        if rating is None or rating < 0 or rating > 5 or not text:
            flash("При сохранении рецензии возникла ошибка. Проверьте корректность введённых данных.", "danger")
            return render_template("review_form.html", book=book, rating=rating, text=text)

        try:
            review = Review(book=book, user=g.user, rating=rating, text=text)
            db.session.add(review)
            db.session.commit()
            flash("Рецензия успешно добавлена", "success")
            return redirect(url_for("books.book_detail", book_id=book.id))
        except Exception:
            db.session.rollback()
            flash("При сохранении рецензии возникла ошибка. Проверьте корректность введённых данных.", "danger")

    return render_template("review_form.html", book=book, rating=5, text="")


@books_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@roles_required("admin", "moderator")
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    book_id = review.book_id
    db.session.delete(review)
    db.session.commit()
    flash("Рецензия удалена", "success")
    return redirect(url_for("books.book_detail", book_id=book_id))


def book_form_data():
    return {
        "title": request.form.get("title", "").strip(),
        "description": request.form.get("description", "").strip(),
        "year": request.form.get("year", "").strip(),
        "publisher": request.form.get("publisher", "").strip(),
        "author": request.form.get("author", "").strip(),
        "page_count": request.form.get("page_count", "").strip(),
    }


def validate_book_form(form, selected_genres, require_cover):
    required = ["title", "description", "year", "publisher", "author", "page_count"]
    if any(not form[field] for field in required):
        return False, "При сохранении данных возникла ошибка. Проверьте корректность введённых данных."

    try:
        year = int(form["year"])
        pages = int(form["page_count"])
    except ValueError:
        return False, "При сохранении данных возникла ошибка. Проверьте корректность введённых данных."

    if year < 1 or year > datetime.now().year or pages < 1:
        return False, "При сохранении данных возникла ошибка. Проверьте корректность введённых данных."

    if not selected_genres:
        return False, "Выберите хотя бы один жанр"

    if require_cover:
        cover = request.files.get("cover")
        if not cover or not cover.filename:
            return False, "Загрузите обложку книги"
        if cover.mimetype not in ALLOWED_COVER_TYPES:
            return False, "Обложка должна быть изображением JPEG, PNG, WEBP или GIF"

    return True, None


def selected_genre_ids(values):
    return [int(value) for value in values if str(value).isdigit()]


def save_cover(book, cover_file):
    data = cover_file.read()
    md5_hash = hashlib.md5(data).hexdigest()
    existing_cover = Cover.query.filter_by(md5_hash=md5_hash).first()

    if existing_cover:
        filename = existing_cover.filename
    else:
        extension = os.path.splitext(secure_filename(cover_file.filename))[1].lower() or ".img"
        filename = f"{uuid.uuid4().hex}{extension}"

    cover = Cover(
        filename=filename,
        mime_type=cover_file.mimetype,
        md5_hash=md5_hash,
        book=book,
    )
    db.session.add(cover)
    db.session.flush()

    if not existing_cover:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        with open(path, "wb") as file:
            file.write(data)
