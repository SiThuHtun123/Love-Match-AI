"""End-to-end test for Love Match AI using Flask's test client.

Exercises the REAL app: register -> login -> upload real face photos ->
AI analysis -> results -> history -> rename -> hall of fame -> delete ->
error cases (no face / multiple faces) -> Japanese locale.
"""
import io
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "love_match_ai")
sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)

from app import app  # noqa: E402
from models import Candidate, Match, User, db  # noqa: E402

app.config["WTF_CSRF_ENABLED"] = False
app.config["TESTING"] = True

PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name} {extra}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {extra}")


def jpg_bytes(img):
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return io.BytesIO(buf.tobytes())


# ---- build test images from the real face --------------------------------
base = cv2.imread(os.path.join(HERE, "test_faces", "face1.jpg"))
assert base is not None, "test face missing"

cand1 = cv2.convertScaleAbs(base, alpha=1.0, beta=45)          # brighter
cand2 = cv2.flip(base, 1)                                      # mirrored
cand2 = cv2.convertScaleAbs(cand2, alpha=0.75, beta=-15)       # darker
cand3 = base.copy()                                            # identical -> twin flame
two_faces = np.hstack([base, cand1])                           # 2 faces -> reject
no_face = np.full((400, 400, 3), 120, dtype=np.uint8)          # gray block -> reject
cv2.rectangle(no_face, (60, 60), (340, 340), (0, 128, 255), -1)

client = app.test_client()

print("== 1. Landing page (logged out) ==")
r = client.get("/")
check("GET / returns 200", r.status_code == 200)
check("landing shows title", b"Love Match AI" in r.data)

print("== 2. Login required (no guest) ==")
r = client.get("/match", follow_redirects=False)
check("/match redirects to login", r.status_code == 302 and "/login" in r.headers["Location"])
r = client.get("/history", follow_redirects=False)
check("/history redirects to login", r.status_code == 302)
r = client.get("/hall-of-fame", follow_redirects=False)
check("/hall-of-fame redirects to login", r.status_code == 302)

print("== 3. Register ==")
r = client.post("/register", data={"username": "cupid_tester", "password": "secret123",
                                   "confirm": "secret123"}, follow_redirects=True)
check("register succeeds and logs in", r.status_code == 200 and b"cupid_tester" in r.data)
r = client.post("/register", data={"username": "x", "password": "secret123", "confirm": "secret123"})
# (already logged in -> redirected; validation tested via fresh client below)

fresh = app.test_client()
r = fresh.post("/register", data={"username": "x", "password": "secret123", "confirm": "secret123"},
               follow_redirects=True)
check("short username rejected", "3–20".encode("utf-8") in r.data)
r = fresh.post("/register", data={"username": "cupid_tester", "password": "secret123",
                                  "confirm": "secret123"}, follow_redirects=True)
check("duplicate username rejected", b"already taken" in r.data)

print("== 4. Logout / login ==")
r = client.get("/logout", follow_redirects=True)
check("logout works", r.status_code == 200)
r = client.post("/login", data={"username": "CUPID_TESTER", "password": "wrong"},
                follow_redirects=True)
check("wrong password rejected", b"Wrong username or password" in r.data)
r = client.post("/login", data={"username": "CUPID_TESTER", "password": "secret123"},
                follow_redirects=True)
check("login works (case-insensitive username)", b"Welcome back" in r.data)

print("== 5. The AI match (the core feature) ==")
data = {
    "my_name": "Tester",
    "my_photo": (jpg_bytes(base), "me.jpg"),
    "candidate_name_1": "Alex",
    "candidate_photo_1": (jpg_bytes(cand1), "alex.jpg"),
    "candidate_name_2": "Sam",
    "candidate_photo_2": (jpg_bytes(cand2), "sam.jpg"),
    "candidate_name_3": "Mirror Me",
    "candidate_photo_3": (jpg_bytes(cand3), "mirror.jpg"),
}
r = client.post("/analyze", data=data, content_type="multipart/form-data",
                follow_redirects=False)
check("analyze redirects to result", r.status_code == 302 and "/result/" in r.headers["Location"])
result_url = r.headers["Location"]

r = client.get(result_url)
check("result page renders", r.status_code == 200)
check("winner banner present", "Your best match".encode() in r.data)
check("breakdown present", b"AI analysis breakdown" in r.data)
check("funny reason shown on result page", r.data.count(b"rank-reason") >= 1
      or b"winner-reason" in r.data)

with app.app_context():
    m = Match.query.first()
    cands = Candidate.query.filter_by(match_id=m.id).order_by(Candidate.rank).all()
    check("match row created", m is not None)
    check("3 candidates stored", len(cands) == 3)
    scores = [c.score for c in cands]
    check("scores sorted desc", scores == sorted(scores, reverse=True), f"scores={scores}")
    twin = [c for c in cands if c.name == "Mirror Me"][0]
    check("identical photo -> 100% twin flame", twin.score == 100.0 and twin.band == "twin_flame",
          f"(got {twin.score}, {twin.band})")
    others = [c for c in cands if c.name != "Mirror Me"]
    check("non-identical scores in 15-98", all(15 <= c.score <= 98 for c in others),
          f"scores={[c.score for c in others]}")
    check("verdicts stored in both languages",
          all(c.verdict_en and c.verdict_ja for c in cands))
    check("funny reason stored in both languages",
          all(c.reason_en and c.reason_ja for c in cands))
    non_twin = [c for c in cands if c.name != "Mirror Me"]
    check("reason references a strength or red flag (mixed/gush/roast)",
          all(len(c.reason_en) > 30 for c in non_twin),
          f"len={[len(c.reason_en) for c in non_twin]}")
    check("photos saved on disk",
          all(os.path.isfile(os.path.join(APP_DIR, "static", c.photo)) for c in cands))
    match_id = m.id
    reason_en_snapshot = {c.name: c.reason_en for c in cands}

print("== 6. Determinism: same photos -> same scores ==")
data2 = {
    "my_name": "Tester",
    "my_photo": (jpg_bytes(base), "me.jpg"),
    "candidate_name_1": "Alex",
    "candidate_photo_1": (jpg_bytes(cand1), "alex.jpg"),
}
r = client.post("/analyze", data=data2, content_type="multipart/form-data")
with app.app_context():
    m2 = Match.query.order_by(Match.id.desc()).first()
    alex1 = Candidate.query.filter_by(name="Alex", match_id=match_id).first()
    alex2 = Candidate.query.filter_by(name="Alex", match_id=m2.id).first()
    check("same photo pair -> identical score", alex1.score == alex2.score,
          f"({alex1.score} vs {alex2.score})")
    second_match_id = m2.id

print("== 6b. Up to 10 candidates ==")
from config import Config as _Cfg  # noqa: E402
check("MAX_CANDIDATES is 10", _Cfg.MAX_CANDIDATES == 10, f"(got {_Cfg.MAX_CANDIDATES})")
big = {"my_name": "Tester", "my_photo": (jpg_bytes(base), "me.jpg")}
variants = [cand1, cand2, base, cv2.convertScaleAbs(base, alpha=1.1, beta=20),
            cv2.convertScaleAbs(base, alpha=0.9, beta=-20), cv2.flip(base, 1),
            cv2.convertScaleAbs(cand1, alpha=0.85, beta=10),
            cv2.convertScaleAbs(cand2, alpha=1.15, beta=5),
            cv2.convertScaleAbs(base, alpha=1.0, beta=30),
            cv2.convertScaleAbs(base, alpha=1.0, beta=-30)]
for i, v in enumerate(variants, start=1):
    big[f"candidate_name_{i}"] = f"C{i}"
    big[f"candidate_photo_{i}"] = (jpg_bytes(v), f"c{i}.jpg")
r = client.post("/analyze", data=big, content_type="multipart/form-data",
                follow_redirects=False)
check("10-candidate analyze redirects to result", r.status_code == 302 and "/result/" in r.headers["Location"])
big_match_url = r.headers["Location"]
with app.app_context():
    bm = Match.query.order_by(Match.id.desc()).first()
    bm_cands = Candidate.query.filter_by(match_id=bm.id).all()
    check("all 10 candidates stored", len(bm_cands) == 10, f"(got {len(bm_cands)})")
    check("ranks are 1..10 unique", sorted(c.rank for c in bm_cands) == list(range(1, 11)))
    check("all 10 have reasons", all(c.reason_en and c.reason_ja for c in bm_cands))
    big_match_id = bm.id
r = client.get(big_match_url)
check("10-candidate result page renders", r.status_code == 200 and r.data.count(b"rank-card") == 10)
# clean up the big match so later counts stay predictable
client.post(f"/match/{big_match_id}/delete", follow_redirects=True)

print("== 7. Validation errors ==")
r = client.post("/analyze", data={
    "my_photo": (jpg_bytes(two_faces), "group.jpg"),
    "candidate_photo_1": (jpg_bytes(cand1), "a.jpg"),
}, content_type="multipart/form-data", follow_redirects=True)
check("2-face photo rejected with funny message", b"one face per photo" in r.data)

r = client.post("/analyze", data={
    "my_photo": (jpg_bytes(base), "me.jpg"),
    "candidate_photo_1": (jpg_bytes(no_face), "block.jpg"),
}, content_type="multipart/form-data", follow_redirects=True)
check("no-face photo rejected", b"find a clear face" in r.data)

r = client.post("/analyze", data={"my_photo": (jpg_bytes(base), "me.jpg")},
                content_type="multipart/form-data", follow_redirects=True)
check("zero candidates rejected", b"at least one candidate" in r.data)

r = client.post("/analyze", data={
    "my_photo": (io.BytesIO(b"not an image"), "fake.jpg"),
    "candidate_photo_1": (jpg_bytes(cand1), "a.jpg"),
}, content_type="multipart/form-data", follow_redirects=True)
check("garbage file rejected", b"valid image" in r.data)

with app.app_context():
    check("failed analyses created no matches", Match.query.count() == 2)

print("== 8. History + rename (CRUD) ==")
r = client.get("/history")
check("history lists matches", r.data.count(b"history-card") == 2)
r = client.post(f"/match/{match_id}/rename", data={"title": "The Great Experiment"},
                follow_redirects=True)
check("rename works", b"The Great Experiment" in r.data)

print("== 9. Hall of Fame ==")
r = client.get("/hall-of-fame")
check("hall of fame renders", r.status_code == 200)
check("100% best score shown", b"100%" in r.data)
check("podium present", b"podium" in r.data)

print("== 10. Ownership protection ==")
fresh2 = app.test_client()
fresh2.post("/register", data={"username": "intruder", "password": "secret123",
                               "confirm": "secret123"})
r = fresh2.get(f"/result/{match_id}")
check("other user's match returns 404", r.status_code == 404)

print("== 11. Delete match (with file cleanup) ==")
with app.app_context():
    m2_photos = [c.photo for c in Match.query.get(second_match_id).candidates]
    m2_photos.append(Match.query.get(second_match_id).my_photo)
r = client.post(f"/match/{second_match_id}/delete", follow_redirects=True)
check("delete succeeds", b"deleted" in r.data)
with app.app_context():
    check("match gone from DB", db.session.get(Match, second_match_id) is None)
check("photo files removed from disk",
      not any(os.path.isfile(os.path.join(APP_DIR, "static", p)) for p in m2_photos))

print("== 12. Japanese locale ==")
r = client.get("/language/ja", follow_redirects=True)
r = client.get("/match")
check("JA: match page translated", "運命の相手を探す".encode() in r.data)
r = client.get("/history")
check("JA: history translated", "マイマッチ履歴".encode() in r.data)
r = client.get(f"/result/{match_id}")
check("JA: result page translated", "あなたのベストマッチ".encode() in r.data)
check("JA: verdict in Japanese", "。".encode() in r.data)
with app.app_context():
    any_reason_ja = Candidate.query.filter_by(match_id=match_id).first().reason_ja
check("JA: funny reason rendered in Japanese", any_reason_ja.encode() in r.data)
r = client.get("/language/en", follow_redirects=True)
r = client.get("/match")
check("switch back to EN works", b"Find your match" in r.data)

print("== 13. 404 handler ==")
r = client.get("/nonexistent")
check("custom 404 page", r.status_code == 404 and b"ghosted" in r.data)

print()
print(f"{'=' * 50}")
print(f"RESULTS: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
