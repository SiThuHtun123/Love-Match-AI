"""App configuration for Love Match AI."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # NOTE: fixed key is fine for a school project; use an env var in production.
    SECRET_KEY = "love-match-ai-school-project-2026"

    # Absolute path so the DB always lives in the app folder, no matter which
    # directory the app is launched from.
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "lovematch.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploaded photos (served from static so <img> tags can use them directly)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per request

    MAX_CANDIDATES = 10

    # i18n
    LANGUAGES = ["en", "ja"]
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_DIR, "translations")
