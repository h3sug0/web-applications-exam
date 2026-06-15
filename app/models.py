from datetime import datetime

from app import db


book_genres = db.Table(
    "book_genres",
    db.Column(
        "book_id",
        db.Integer,
        db.ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "genre_id",
        db.Integer,
        db.ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


collection_books = db.Table(
    "collection_books",
    db.Column(
        "collection_id",
        db.Integer,
        db.ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "book_id",
        db.Integer,
        db.ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(32), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)

    users = db.relationship("User", back_populates="role")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    role = db.relationship("Role", back_populates="users")
    reviews = db.relationship("Review", back_populates="user")
    collections = db.relationship(
        "Collection",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    page_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    genres = db.relationship(
        "Genre",
        secondary=book_genres,
        back_populates="books",
        passive_deletes=True,
    )
    cover = db.relationship(
        "Cover",
        back_populates="book",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    reviews = db.relationship(
        "Review",
        back_populates="book",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    collections = db.relationship(
        "Collection",
        secondary=collection_books,
        back_populates="books",
        passive_deletes=True,
    )


class Genre(db.Model):
    __tablename__ = "genres"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    books = db.relationship(
        "Book",
        secondary=book_genres,
        back_populates="genres",
        passive_deletes=True,
    )


class Cover(db.Model):
    __tablename__ = "covers"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    md5_hash = db.Column(db.String(32), nullable=False, index=True)
    book_id = db.Column(
        db.Integer,
        db.ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    book = db.relationship("Book", back_populates="cover")


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (
        db.UniqueConstraint("book_id", "user_id", name="uq_review_book_user"),
        db.CheckConstraint("rating BETWEEN 0 AND 5", name="ck_review_rating_range"),
    )

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(
        db.Integer,
        db.ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    book = db.relationship("Book", back_populates="reviews")
    user = db.relationship("User", back_populates="reviews")


class Collection(db.Model):
    __tablename__ = "collections"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    user = db.relationship("User", back_populates="collections")
    books = db.relationship(
        "Book",
        secondary=collection_books,
        back_populates="collections",
        passive_deletes=True,
    )
