# 💘 Love Match AI

A (deliberately) funny AI web application: upload your photo and 1–5 candidate
photos, and the AI ranks who is most "compatible" with you — with percentages,
funny verdicts, and a dramatic animated reveal.

> ⚠️ **This is a joke app.** Real romantic compatibility cannot be predicted
> from faces. However, every number IS produced by genuine AI face analysis
> (MediaPipe Face Mesh), which makes it fun *and* explainable.

School project for **先端クラウドシステム開発Ⅰ（問題2）**.

---

## How to run

Requires **Python 3.10** (3.13 is too new for the AI libraries).

```bash
# 1. create a virtual environment
python -m venv venv

# 2. activate it
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. install dependencies
pip install -r requirements.txt

# 4. run
python app.py
```

Open **http://127.0.0.1:5000** in a browser.
The SQLite database (`instance/lovematch.db`) is created automatically on
first run. Everything runs **offline** — no API keys, no internet needed
(all fonts/JS libraries are self-hosted in `static/`).

## How to use

1. **Sign up / log in** (required — there is no guest access).
2. **New Match** → upload *your* photo, then add **1–5 candidate** photos
   (names optional). One clear face per photo!
3. Press **Find My Match!** — the AI analyzes every face and reveals
   the ranked results with compatibility percentages and funny verdicts.
4. Results are saved automatically: see **History** (view / rename / delete)
   and the **Hall of Fame** (your all-time top scores + stats).
5. Language can be switched anytime: **EN / 日本語** (top-right).

## The AI model

- **Model:** MediaPipe **Face Mesh** — a facial-landmark regression model
  that predicts **478 3D landmarks** per face (plus MediaPipe Face Detection
  for the one-face-per-photo validation). Runs locally on CPU, ~0.2 s/face.
- **Input data:** the uploaded photos.
- **What it predicts:** the landmark positions, from which the app computes
  14 real features per face — smile ratio, eye openness, eyebrow raise,
  face shape, lip fullness, head tilt, nose offset, symmetry, and photo
  features (brightness, warmth, saturation, sharpness, detection confidence).
- **Compatibility score:** a deterministic "mix of both" formula —
  some components reward *similarity* (Smile Sync, Vibe Harmony…), others
  reward *difference* ("opposites attract": Face-Shape Contrast, Warmth
  Spark…). Same photos → same score, always. Uploading your own photo as a
  candidate is detected and scores 100% ("twin flame" 🪞).

## Login-only features (beyond table CRUD)

- The **AI matchmaking analysis** itself
- **Match history** with rename/delete (CRUD on `matches`/`candidates`)
- **Hall of Fame** — personal all-time ranking + statistics

## Database (SQLite, custom schema)

| Table        | Contents                                                        |
|--------------|-----------------------------------------------------------------|
| `users`      | id, username, password_hash (werkzeug), created_at              |
| `matches`    | id, user_id, title, my_name, my_photo, best_score, created_at   |
| `candidates` | id, match_id, name, photo, score, rank, band, verdicts, breakdown |

## Project structure

```
love_match_ai/
├── app.py           # Flask routes (auth, analyze, history, hall of fame)
├── ai_engine.py     # MediaPipe feature extraction + compatibility scoring
├── verdicts.py      # funny verdicts / analyzing messages (EN+JA, editable!)
├── models.py        # SQLAlchemy models (users, matches, candidates)
├── config.py        # configuration
├── babel.cfg        # i18n extraction config
├── requirements.txt
├── translations/ja/ # Japanese translations (Flask-Babel)
├── templates/       # Jinja2 templates
└── static/          # CSS animations, JS, self-hosted font & confetti, uploads
```

## Adding more funny verdicts

Open `verdicts.py` and add lines to any band in `VERDICTS` (both `en` and
`ja`). The app picks them up automatically — no other changes needed.
