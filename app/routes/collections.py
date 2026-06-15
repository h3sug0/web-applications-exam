from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func

from app import db
from app.models import Book, Collection
from app.routes.books import roles_required


collections_bp = Blueprint("collections", __name__, url_prefix="/collections")


@collections_bp.route("", methods=["GET", "POST"])
@roles_required("user")
def index():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Введите название подборки", "danger")
            return redirect(url_for("collections.index"))

        collection = Collection(title=title, user=g.user)
        db.session.add(collection)
        db.session.commit()
        flash("Подборка успешно добавлена", "success")
        return redirect(url_for("collections.index"))

    rows = (
        db.session.query(Collection, func.count(Book.id).label("book_count"))
        .outerjoin(Collection.books)
        .filter(Collection.user_id == g.user.id)
        .group_by(Collection.id)
        .order_by(Collection.id.desc())
        .all()
    )
    collections = [
        {"collection": collection, "book_count": book_count}
        for collection, book_count in rows
    ]
    return render_template("collections.html", collections=collections)


@collections_bp.route("/<int:collection_id>")
@roles_required("user")
def detail(collection_id):
    collection = Collection.query.filter_by(id=collection_id, user_id=g.user.id).first_or_404()
    return render_template("collection_detail.html", collection=collection, books=collection.books)


@collections_bp.route("/books/<int:book_id>/add", methods=["POST"])
@roles_required("user")
def add_book(book_id):
    book = Book.query.get_or_404(book_id)
    collection_id = request.form.get("collection_id", type=int)
    collection = Collection.query.filter_by(id=collection_id, user_id=g.user.id).first()

    if not collection:
        flash("Выберите подборку", "danger")
        return redirect(url_for("books.book_detail", book_id=book.id))

    if book not in collection.books:
        collection.books.append(book)
        db.session.commit()

    flash("Книга успешно добавлена в подборку", "success")
    return redirect(url_for("books.book_detail", book_id=book.id))
