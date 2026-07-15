"""Database models for Love Match AI (SQLite via Flask-SQLAlchemy)."""
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    matches = db.relationship(
        "Match", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Match(db.Model):
    """One 'Find my match' run: the user's photo vs 1-5 candidates."""

    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(60), nullable=False)
    my_name = db.Column(db.String(40), nullable=False, default="Me")
    my_photo = db.Column(db.String(255), nullable=False)  # path relative to static/
    best_score = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    candidates = db.relationship(
        "Candidate",
        backref="match",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Candidate.rank",
    )

    @property
    def winner(self):
        return self.candidates[0] if self.candidates else None


class Candidate(db.Model):
    """One candidate photo inside a match, with its AI compatibility result."""

    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False, index=True)
    name = db.Column(db.String(40), nullable=False)
    photo = db.Column(db.String(255), nullable=False)  # path relative to static/
    score = db.Column(db.Float, nullable=False)
    rank = db.Column(db.Integer, nullable=False)  # 1 = best match
    band = db.Column(db.String(20), nullable=False)  # verdict band key
    verdict_en = db.Column(db.String(200), nullable=False)
    verdict_ja = db.Column(db.String(200), nullable=False)
    reason_en = db.Column(db.String(400), nullable=False, default="")
    reason_ja = db.Column(db.String(400), nullable=False, default="")
    breakdown_json = db.Column(db.Text, nullable=False, default="{}")
