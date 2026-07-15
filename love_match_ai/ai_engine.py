"""AI engine for Love Match AI.

Uses MediaPipe Face Mesh (a facial-landmark regression model, 478 landmarks)
plus OpenCV to extract REAL, measurable features from each photo:

    smile ratio, mouth openness, eye openness, eyebrow raise, face shape,
    lip fullness, head tilt, nose offset (yaw), symmetry,
    brightness, warmth, saturation, sharpness, detection confidence

The compatibility score is a deterministic "mix of both" formula:
some components reward SIMILARITY (smile sync, vibe harmony…), others
reward DIFFERENCE ("opposites attract": face-shape contrast, warmth spark…).
Same two photos always produce the same score.

This is intentionally a JOKE application — real romantic compatibility
cannot be predicted from faces — but every number comes from genuine
face analysis, which is what we explain in the presentation.
"""
from __future__ import annotations

import math

import cv2
import mediapipe as mp
import numpy as np

mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh


class FaceError(Exception):
    """Raised when a photo cannot be used (no face / multiple faces)."""

    def __init__(self, reason: str, count: int = 0):
        super().__init__(reason)
        self.reason = reason  # "no_face" | "multiple_faces" | "unreadable"
        self.count = count


# --- MediaPipe Face Mesh landmark indices we use -------------------------
L_CHEEK, R_CHEEK, FOREHEAD, CHIN = 234, 454, 10, 152
MOUTH_L, MOUTH_R = 61, 291
LIP_UP_IN, LIP_LO_IN, LIP_UP_OUT, LIP_LO_OUT = 13, 14, 0, 17
L_EYE_OUT, L_EYE_IN, L_EYE_TOP, L_EYE_BOT = 33, 133, 159, 145
R_EYE_IN, R_EYE_OUT, R_EYE_TOP, R_EYE_BOT = 362, 263, 386, 374
L_BROW, R_BROW = 105, 334
NOSE_TIP = 1


def _dist(pts, a, b):
    return math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1])


def count_faces(img_bgr) -> tuple[int, float]:
    """Return (number of faces, best detection confidence).

    Runs BOTH MediaPipe detection models — model 0 (short-range, big
    close-up faces) and model 1 (full-range, smaller/distant faces) —
    and keeps the result that found more faces. This catches both selfie
    close-ups and photos where the face is small in the frame.
    """
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    best_count, best_conf = 0, 0.0
    for model in (0, 1):
        with mp_face_detection.FaceDetection(
            model_selection=model, min_detection_confidence=0.5
        ) as fd:
            res = fd.process(rgb)
        if res.detections and len(res.detections) > best_count:
            best_count = len(res.detections)
            best_conf = max(d.score[0] for d in res.detections)
    return best_count, best_conf


def extract_features(image_path: str) -> dict:
    """Analyze one photo and return its feature dict.

    Raises FaceError if the photo is unreadable, has no face,
    or contains more than one face (one clear face per photo!).
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FaceError("unreadable")
    h, w = img.shape[:2]

    n_faces, det_conf = count_faces(img)
    if n_faces == 0:
        raise FaceError("no_face")
    if n_faces > 1:
        raise FaceError("multiple_faces", count=n_faces)

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    with mp_face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.4,
    ) as fm:
        res = fm.process(rgb)
    if not res.multi_face_landmarks:
        raise FaceError("no_face")

    lm = res.multi_face_landmarks[0].landmark
    pts = [(p.x * w, p.y * h) for p in lm]

    face_w = _dist(pts, L_CHEEK, R_CHEEK) or 1.0
    face_h = _dist(pts, FOREHEAD, CHIN) or 1.0

    # -- geometric features (from the 478 landmarks) ----------------------
    smile = _dist(pts, MOUTH_L, MOUTH_R) / face_w
    mouth_open = _dist(pts, LIP_UP_IN, LIP_LO_IN) / face_h
    eye_open_l = _dist(pts, L_EYE_TOP, L_EYE_BOT) / (_dist(pts, L_EYE_OUT, L_EYE_IN) or 1.0)
    eye_open_r = _dist(pts, R_EYE_TOP, R_EYE_BOT) / (_dist(pts, R_EYE_IN, R_EYE_OUT) or 1.0)
    eye_open = (eye_open_l + eye_open_r) / 2
    brow_raise = (
        _dist(pts, L_BROW, L_EYE_TOP) + _dist(pts, R_BROW, R_EYE_TOP)
    ) / 2 / face_h
    face_ratio = face_w / face_h
    lip_full = (
        _dist(pts, LIP_UP_OUT, LIP_UP_IN) + _dist(pts, LIP_LO_IN, LIP_LO_OUT)
    ) / face_h
    # head roll: angle of the line between the two outer eye corners
    dy = pts[R_EYE_OUT][1] - pts[L_EYE_OUT][1]
    dx = pts[R_EYE_OUT][0] - pts[L_EYE_OUT][0]
    tilt_deg = math.degrees(math.atan2(dy, dx or 1e-6))
    # yaw proxy: how far the nose tip is from the horizontal face center
    face_cx = (pts[L_CHEEK][0] + pts[R_CHEEK][0]) / 2
    nose_offset = (pts[NOSE_TIP][0] - face_cx) / face_w
    symmetry = abs(_dist(pts, L_CHEEK, NOSE_TIP) - _dist(pts, R_CHEEK, NOSE_TIP)) / face_w

    # -- photo "vibe" features (whole image) ------------------------------
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    means = img.reshape(-1, 3).mean(axis=0)  # B, G, R
    brightness = float(gray.mean())
    warmth = float((means[2] - means[0]) / 255.0)  # R minus B
    saturation = float(hsv[:, :, 1].mean())
    sharpness = float(math.log10(cv2.Laplacian(gray, cv2.CV_64F).var() + 1.0))

    return {
        "det_conf": round(float(det_conf), 3),
        "smile": round(smile, 4),
        "mouth_open": round(mouth_open, 4),
        "eye_open": round(eye_open, 4),
        "brow_raise": round(brow_raise, 4),
        "face_ratio": round(face_ratio, 4),
        "lip_full": round(lip_full, 4),
        "tilt_deg": round(tilt_deg, 2),
        "nose_offset": round(nose_offset, 4),
        "symmetry": round(symmetry, 4),
        "brightness": round(brightness, 1),
        "warmth": round(warmth, 4),
        "saturation": round(saturation, 1),
        "sharpness": round(sharpness, 3),
    }


# ---------------------------------------------------------------------------
# Compatibility scoring — "mix of both"
# ---------------------------------------------------------------------------
def _sim(a: float, b: float, scale: float) -> float:
    """1.0 when identical, 0.0 when the difference reaches `scale`."""
    return 1.0 - min(abs(a - b) / scale, 1.0)


def _diff(a: float, b: float, scale: float) -> float:
    """0.0 when identical, 1.0 when the difference reaches `scale`."""
    return min(abs(a - b) / scale, 1.0)


def _exaggerate(c: float, factor: float = 1.55) -> float:
    """Push component values away from 0.5 so results feel more dramatic."""
    return max(0.0, min(1.0, 0.5 + (c - 0.5) * factor))


# (component key, weight, kind) — kinds: similarity-rewarding vs difference-rewarding
WEIGHTS = {
    "smile_sync": 0.17,
    "eye_sparkle": 0.12,
    "vibe_harmony": 0.15,
    "energy_balance": 0.12,
    "tilt_chemistry": 0.08,
    "face_shape_contrast": 0.13,   # opposites attract!
    "warmth_spark": 0.12,          # opposites attract!
    "lip_balance": 0.11,           # opposites attract!
}


def compatibility(me: dict, cand: dict) -> tuple[float, dict]:
    """Deterministic compatibility score (15–98) + per-component breakdown.

    Special case: a photo identical to the user's own scores 100
    ("twin flame" — probably the same photo!).
    """
    # identical-photo detection
    keys = ("smile", "eye_open", "face_ratio", "brightness", "warmth")
    if all(abs(me[k] - cand[k]) < 1e-6 for k in keys):
        return 100.0, {k: 100 for k in WEIGHTS}

    comps = {
        # similarity-rewarding
        "smile_sync": _sim(me["smile"], cand["smile"], 0.12),
        "eye_sparkle": _sim(me["eye_open"], cand["eye_open"], 0.15),
        "vibe_harmony": 0.5 * _sim(me["brightness"], cand["brightness"], 80)
        + 0.5 * _sim(me["saturation"], cand["saturation"], 70),
        "energy_balance": _sim(me["brow_raise"], cand["brow_raise"], 0.05),
        "tilt_chemistry": _sim(me["tilt_deg"], cand["tilt_deg"], 14),
        # difference-rewarding ("opposites attract")
        "face_shape_contrast": _diff(me["face_ratio"], cand["face_ratio"], 0.16),
        "warmth_spark": _diff(me["warmth"], cand["warmth"], 0.22),
        "lip_balance": _diff(me["lip_full"], cand["lip_full"], 0.05),
    }
    comps = {k: _exaggerate(v) for k, v in comps.items()}

    raw = sum(WEIGHTS[k] * comps[k] for k in WEIGHTS)
    stretched = max(0.0, min(1.0, (raw - 0.30) / 0.45))
    score = round(15 + 83 * stretched, 0)

    breakdown = {k: int(round(v * 100)) for k, v in comps.items()}
    return float(score), breakdown
