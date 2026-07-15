"""Love Match AI — a (deliberately) funny AI compatibility web app.

School project for 先端クラウドシステム開発Ⅰ (問題2).

Flow: register/login (required — no guest access) → upload your photo +
1–5 candidate photos → MediaPipe Face Mesh extracts 14 real facial/photo
features per face → a deterministic "mix of both" formula turns them into
compatibility percentages → animated ranked results with funny verdicts →
matches are saved to your personal history / Hall of Fame (login-only).
"""
from __future__ import annotations

import json
import os
import uuid

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import Babel
from flask_babel import gettext as _
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFError, CSRFProtect
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func

import verdicts as V
from ai_engine import FaceError, compatibility, extract_features
from config import Config
from models import Candidate, Match, User, db

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    flash(_("Please log in first — love waits for no one! 💘"), "error")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
def get_locale():
    lang = session.get("lang")
    if lang in app.config["LANGUAGES"]:
        return lang
    return request.accept_languages.best_match(app.config["LANGUAGES"]) or "en"


babel = Babel(app, locale_selector=get_locale)


@app.context_processor
def inject_globals():
    locale = get_locale()
    return {
        "current_locale": locale,
        "analyzing_messages": V.ANALYZING[locale],
        "component_names": {k: v[locale] for k, v in V.COMPONENT_NAMES.items()},
        "band_emoji": V.BAND_EMOJI,
    }


@app.route("/language/<lang>")
def set_language(lang: str):
    if lang in app.config["LANGUAGES"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def save_photo(file_storage) -> str:
    """Normalize an uploaded image and save it under static/uploads/<user>/.

    Fixes EXIF rotation, converts to RGB JPEG, and resizes to max 900px.
    Returns the path relative to static/. Raises ValueError if not an image.
    """
    ext = (file_storage.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in app.config["ALLOWED_EXTENSIONS"]:
        raise ValueError("bad_extension")
    try:
        img = Image.open(file_storage.stream)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise ValueError("not_an_image")

    img.thumbnail((900, 900))
    user_dir = os.path.join(app.config["UPLOAD_FOLDER"], str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    img.save(os.path.join(user_dir, filename), "JPEG", quality=88)
    return f"uploads/{current_user.id}/{filename}"


def delete_photo(rel_path: str) -> None:
    path = os.path.join(app.static_folder, rel_path)
    if os.path.isfile(path):
        os.remove(path)


def face_error_message(err: FaceError, who: str) -> str:
    if err.reason == "multiple_faces":
        return _(
            "%(who)s: I see %(count)d people in this photo! I'm an AI, not a "
            "matchmaker for a whole party 🎉 — one face per photo, please!",
            who=who,
            count=err.count,
        )
    return _(
        "%(who)s: Hmm, I can't find a clear face in this photo. "
        "Try a brighter, front-facing one! 📷", who=who,
    )


def owned_match_or_404(match_id: int) -> Match:
    match = db.session.get(Match, match_id)
    if match is None or match.user_id != current_user.id:
        abort(404)
    return match


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("match"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("match"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if not (3 <= len(username) <= 20):
            flash(_("Username must be 3–20 characters."), "error")
        elif len(password) < 6:
            flash(_("Password must be at least 6 characters."), "error")
        elif password != confirm:
            flash(_("Passwords do not match."), "error")
        elif User.query.filter(func.lower(User.username) == username.lower()).first():
            flash(_("That username is already taken."), "error")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash(_("Welcome aboard, %(name)s! Time to find your match 💘", name=username), "success")
            return redirect(url_for("match"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("match"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter(func.lower(User.username) == username.lower()).first()
        if user and user.check_password(password):
            login_user(user)
            flash(_("Welcome back, %(name)s! 💖", name=user.username), "success")
            return redirect(url_for("match"))
        flash(_("Wrong username or password. Even the AI can't match those."), "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash(_("Logged out. Cupid will miss you! 👋"), "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# The matchmaking (login-only, beyond CRUD: real AI analysis)
# ---------------------------------------------------------------------------
@app.route("/match")
@login_required
def match():
    return render_template("match.html", max_candidates=app.config["MAX_CANDIDATES"])


@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    saved_paths: list[str] = []

    def fail(message: str):
        for p in saved_paths:
            delete_photo(p)
        flash(message, "error")
        return redirect(url_for("match"))

    # --- the user's own photo -------------------------------------------
    my_file = request.files.get("my_photo")
    my_name = (request.form.get("my_name") or "").strip()[:40] or _("Me")
    if my_file is None or my_file.filename == "":
        return fail(_("Please upload your own photo first! 📷"))
    try:
        my_path = save_photo(my_file)
        saved_paths.append(my_path)
        my_features = extract_features(os.path.join(app.static_folder, my_path))
    except ValueError:
        return fail(_("Your photo doesn't look like a valid image file."))
    except FaceError as err:
        return fail(face_error_message(err, _("Your photo")))

    # --- candidates (1–5) -------------------------------------------------
    candidates: list[dict] = []
    for i in range(1, app.config["MAX_CANDIDATES"] + 1):
        file = request.files.get(f"candidate_photo_{i}")
        if file is None or file.filename == "":
            continue
        name = (request.form.get(f"candidate_name_{i}") or "").strip()[:40]
        name = name or _("Candidate %(num)d", num=len(candidates) + 1)
        try:
            path = save_photo(file)
            saved_paths.append(path)
            features = extract_features(os.path.join(app.static_folder, path))
        except ValueError:
            return fail(_("%(who)s: that file doesn't look like a valid image.", who=name))
        except FaceError as err:
            return fail(face_error_message(err, name))
        candidates.append({"name": name, "photo": path, "features": features})

    if not candidates:
        return fail(_("Add at least one candidate — the AI can't matchmake thin air! 💨"))

    # --- score, rank, verdicts --------------------------------------------
    for cand in candidates:
        score, breakdown = compatibility(my_features, cand["features"])
        cand["score"] = score
        cand["breakdown"] = breakdown
    candidates.sort(key=lambda c: c["score"], reverse=True)

    m = Match(
        user_id=current_user.id,
        title="Match",  # placeholder; final title set after flush gives us the id
        my_name=my_name,
        my_photo=my_path,
        best_score=candidates[0]["score"],
    )
    db.session.add(m)
    db.session.flush()  # get m.id
    m.title = f"Match #{m.id}"

    for rank, cand in enumerate(candidates, start=1):
        verdict = V.pick_verdict(cand["score"], cand["name"])
        reason = V.make_reason(cand["score"], cand["name"], cand["breakdown"])
        db.session.add(
            Candidate(
                match_id=m.id,
                name=cand["name"],
                photo=cand["photo"],
                score=cand["score"],
                rank=rank,
                band=verdict["band"],
                verdict_en=verdict["en"],
                verdict_ja=verdict["ja"],
                reason_en=reason["en"],
                reason_ja=reason["ja"],
                breakdown_json=json.dumps(cand["breakdown"]),
            )
        )
    db.session.commit()
    return redirect(url_for("result", match_id=m.id, new=1))


@app.route("/result/<int:match_id>")
@login_required
def result(match_id: int):
    m = owned_match_or_404(match_id)
    is_ja = get_locale() == "ja"
    candidates = [
        {
            "obj": c,
            "verdict": c.verdict_ja if is_ja else c.verdict_en,
            "reason": c.reason_ja if is_ja else c.reason_en,
            "breakdown": json.loads(c.breakdown_json),
        }
        for c in m.candidates
    ]
    return render_template(
        "result.html",
        match=m,
        candidates=candidates,
        is_new=request.args.get("new") == "1",
    )


# ---------------------------------------------------------------------------
# History (CRUD) + Hall of Fame (login-only)
# ---------------------------------------------------------------------------
@app.route("/history")
@login_required
def history():
    matches = (
        Match.query.filter_by(user_id=current_user.id)
        .order_by(Match.created_at.desc())
        .all()
    )
    return render_template("history.html", matches=matches)


@app.route("/match/<int:match_id>/rename", methods=["POST"])
@login_required
def rename_match(match_id: int):
    m = owned_match_or_404(match_id)
    title = (request.form.get("title") or "").strip()[:60]
    if title:
        m.title = title
        db.session.commit()
        flash(_("Match renamed! ✏️"), "success")
    return redirect(request.referrer or url_for("history"))


@app.route("/match/<int:match_id>/delete", methods=["POST"])
@login_required
def delete_match(match_id: int):
    m = owned_match_or_404(match_id)
    delete_photo(m.my_photo)
    for c in m.candidates:
        delete_photo(c.photo)
    db.session.delete(m)
    db.session.commit()
    flash(_("Match deleted. The AI has already forgotten them. 🗑️"), "success")
    return redirect(url_for("history"))


@app.route("/hall-of-fame")
@login_required
def hall_of_fame():
    top = (
        Candidate.query.join(Match)
        .filter(Match.user_id == current_user.id)
        .order_by(Candidate.score.desc(), Candidate.id.asc())
        .limit(3)
        .all()
    )
    total_matches = Match.query.filter_by(user_id=current_user.id).count()
    total_candidates = (
        Candidate.query.join(Match).filter(Match.user_id == current_user.id).count()
    )
    avg_score = (
        db.session.query(func.avg(Candidate.score))
        .join(Match)
        .filter(Match.user_id == current_user.id)
        .scalar()
    )
    return render_template(
        "halloffame.html",
        top=top,
        total_matches=total_matches,
        total_candidates=total_candidates,
        avg_score=round(avg_score or 0, 1),
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404,
                           message=_("This page ghosted you. It's not here. 👻")), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500,
                           message=_("The AI fainted from too much love. Try again!")), 500


@app.errorhandler(413)
def too_large(e):
    flash(_("That photo is too large (max 8 MB per request). Try a smaller one!"), "error")
    return redirect(url_for("match"))


@app.errorhandler(CSRFError)
def csrf_error(e):
    flash(_("Your session expired — please try again."), "error")
    return redirect(request.referrer or url_for("index"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
