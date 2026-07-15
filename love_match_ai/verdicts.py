"""Funny verdicts, analyzing messages, and AI-component display names.

Everything here is DATA — add more verdict lines any time, in both languages,
and the app will pick them up automatically. Each score band has several
verdicts; one is chosen deterministically per candidate (same match always
shows the same line).
"""
import hashlib

# ---------------------------------------------------------------------------
# Score bands: (minimum score, band key). Checked top-down.
# ---------------------------------------------------------------------------
BANDS = [
    (100, "twin_flame"),   # special: identical photo detected
    (90, "soulmate"),
    (80, "sparks"),
    (70, "smitten"),
    (60, "promising"),
    (50, "maybe"),
    (40, "complicated"),
    (30, "awkward"),
    (20, "yikes"),
    (0, "run"),
]

BAND_EMOJI = {
    "twin_flame": "🪞",
    "soulmate": "💖",
    "sparks": "💘",
    "smitten": "😍",
    "promising": "💛",
    "maybe": "🤞",
    "complicated": "🤔",
    "awkward": "😬",
    "yikes": "💔",
    "run": "💀",
}

VERDICTS = {
    "twin_flame": {
        "en": [
            "Wait… is that YOU?! Self-love is important too 💅",
            "100% match. Suspiciously perfect. Mirrors don't count!",
            "Twin flame detected. Or the same photo. Probably the same photo.",
        ],
        "ja": [
            "ちょっと待って…それ、あなたでは？！ 自分磨きも大事です💅",
            "100%マッチ。怪しいほど完璧。鏡はカウント外です！",
            "ツインフレーム検出。もしくは同じ写真。たぶん同じ写真。",
        ],
    },
    "soulmate": {
        "en": [
            "Wedding bells are ringing 🔔 Book the venue!",
            "Soulmate energy detected. The AI is literally blushing.",
            "Destiny called — it says you two are a done deal.",
            "This is the plot of a romance movie. Roll credits. 🎬",
        ],
        "ja": [
            "結婚式の鐘が鳴っています🔔 式場を予約しましょう！",
            "ソウルメイトのエネルギーを検出。AIも思わず赤面中。",
            "運命から電話です——「この二人はもう決まり」とのこと。",
            "これは恋愛映画のプロットです。エンドロールへどうぞ🎬",
        ],
    },
    "sparks": {
        "en": [
            "Sparks are flying! ✨ Somebody call the fire department.",
            "Strong match — you'd survive a road trip together.",
            "The AI ships you two. Hard.",
            "Great chemistry. Lab-tested, Cupid-approved.",
        ],
        "ja": [
            "火花が散っています！✨ 消防署に通報レベル。",
            "強力なマッチ——一緒に長旅しても大丈夫なタイプ。",
            "AIはこの二人を全力で推しています。",
            "素晴らしい相性。ラボ検証済み、キューピッド公認。",
        ],
    },
    "smitten": {
        "en": [
            "Officially smitten. 😍 The AI caught you staring.",
            "Very promising! You'd definitely split dessert.",
            "The AI approves. Cautiously optimistic, but approves.",
            "Strong potential — this could go the distance. 🏃💨",
        ],
        "ja": [
            "完全にメロメロ😍 AIはあなたの熱視線を見逃しません。",
            "かなり有望！デザートを分け合える仲です。",
            "AIは承認します。慎重ながらも前向きに承認。",
            "強い可能性——これは長続きするかも🏃💨",
        ],
    },
    "promising": {
        "en": [
            "Solid match — you'd share fries 🍟 (the ultimate test).",
            "Promising! Just don't talk about pineapple pizza yet.",
            "Decent vibes. A second date is scientifically advisable.",
            "There's potential here. Water it daily. 🌱",
        ],
        "ja": [
            "堅実なマッチ——ポテトをシェアできる仲🍟（究極のテスト）。",
            "有望です！パイナップルピザの話題はまだ禁止。",
            "悪くない雰囲気。二回目のデートは科学的に推奨されます。",
            "可能性アリ。毎日水やりを忘れずに🌱",
        ],
    },
    "maybe": {
        "en": [
            "Maybe? 🤞 The AI is cautiously shrugging.",
            "There's a spark… or was that static electricity?",
            "Not bad, not great. A solid 'we'll see.'",
            "The AI gives this a hesitant thumbs… sideways. 👉",
        ],
        "ja": [
            "たぶん？🤞 AIは慎重に肩をすくめています。",
            "火花が…いや、それただの静電気かも？",
            "悪くない、けど良くもない。堅実な「様子見」。",
            "AIの評価は、ためらいがちの…横向きサム👉",
        ],
    },
    "complicated": {
        "en": [
            "It's… complicated. 🤔 Like IKEA instructions.",
            "50/50. Flip a coin, but make it romantic.",
            "The AI needs a coffee before commenting further.",
            "Could work! In an alternate universe. Maybe two.",
        ],
        "ja": [
            "うーん…複雑です🤔 IKEAの説明書レベル。",
            "五分五分。コインで決めましょう、ロマンチックに。",
            "AIはコメントの前にコーヒーが必要みたいです。",
            "うまくいくかも！別の宇宙でなら。たぶん二つ先の。",
        ],
    },
    "awkward": {
        "en": [
            "Oof, awkward. 😬 The AI looked away politely.",
            "This is giving 'we matched by accident' energy.",
            "The vibes are… present. Barely. But present.",
            "You'd run out of things to say by minute three.",
        ],
        "ja": [
            "うっ、気まずい😬 AIは礼儀正しく目をそらしました。",
            "「間違えてマッチしちゃった」感が漂っています。",
            "雰囲気は…一応あります。かろうじて。でも一応。",
            "3分で会話のネタが尽きるタイプの二人です。",
        ],
    },
    "yikes": {
        "en": [
            "Yikes. The AI physically cringed. 💔",
            "You'd argue about which way the toilet paper goes.",
            "Compatibility not found. Have you tried turning it off and on?",
            "The stars said no. Then they blocked you.",
        ],
        "ja": [
            "うわっ。AIが思わずのけぞりました💔",
            "トイレットペーパーの向きで喧嘩するタイプの二人です。",
            "相性が見つかりません。再起動を試しましたか？",
            "星占いの答えはNO。その後ブロックされました。",
        ],
    },
    "run": {
        "en": [
            "Run. Just run. 💀",
            "The AI has notified your emergency contact.",
            "This match is a crime against romance. The AI called the police.",
            "0 stars. Would not ship. Refund requested.",
        ],
        "ja": [
            "逃げて。とにかく逃げて💀",
            "AIがあなたの緊急連絡先に通報しておきました。",
            "このマッチは恋愛に対する犯罪です。AIは警察を呼びました。",
            "星0個。推せません。返金を要求します。",
        ],
    },
}

# Messages that rotate on the "Analyzing love…" screen.
ANALYZING = {
    "en": [
        "Consulting Cupid… 💘",
        "Reading their aura… 🔮",
        "Measuring smile chemistry… 😊",
        "Calculating destiny… ✨",
        "Interviewing the stars… 🌟",
        "Checking vibe frequencies… 📡",
        "Cross-referencing love databases… 💾",
        "Almost there… hearts are racing… 💓",
    ],
    "ja": [
        "キューピッドに相談中…💘",
        "オーラを読み取り中…🔮",
        "笑顔の相性を測定中…😊",
        "運命を計算中…✨",
        "星たちにインタビュー中…🌟",
        "バイブスの周波数を確認中…📡",
        "恋愛データベースと照合中…💾",
        "もうすぐ…胸が高鳴っています…💓",
    ],
}

# Display names for the AI breakdown components.
COMPONENT_NAMES = {
    "smile_sync": {"en": "Smile Sync", "ja": "笑顔シンクロ率"},
    "eye_sparkle": {"en": "Eye Sparkle Match", "ja": "瞳のきらめき度"},
    "vibe_harmony": {"en": "Vibe Harmony", "ja": "バイブス調和"},
    "energy_balance": {"en": "Energy Balance", "ja": "エネルギーバランス"},
    "tilt_chemistry": {"en": "Head-Tilt Chemistry", "ja": "首かしげケミストリー"},
    "face_shape_contrast": {"en": "Face-Shape Contrast", "ja": "顔型コントラスト"},
    "warmth_spark": {"en": "Warmth Spark", "ja": "ぬくもりスパーク"},
    "lip_balance": {"en": "Lip Balance", "ja": "唇バランス"},
}


# ---------------------------------------------------------------------------
# Funny "reason" generator
#
# For each candidate we look at their real breakdown: the HIGHEST-scoring
# component is their "strength", the LOWEST is their "red flag". Depending on
# the overall score tier we GUSH (all praise), give a MIXED good/bad combo,
# or ROAST (all teasing). Everything is deterministic (same match -> same
# reason) and driven by the actual AI feature values.
# ---------------------------------------------------------------------------

# Per-component phrases. "good" = why it's a plus; "bad" = why it's a red flag.
COMPONENT_PHRASES = {
    "smile_sync": {
        "good": {
            "en": ["your smiles are dangerously in sync 😊",
                   "you grin on the exact same wavelength",
                   "your smiles could power a small city 💡"],
            "ja": ["二人の笑顔が危険なほどシンクロしていて😊",
                   "まったく同じ波長で微笑んでいて",
                   "その笑顔は小さな街を照らせるほどで💡"],
        },
        "bad": {
            "en": ["one of you smiles like a villain 😈",
                   "your smiles are having a disagreement",
                   "the smile chemistry filed for divorce"],
            "ja": ["どちらかの笑顔が悪役っぽくて😈",
                   "二人の笑顔が意見の相違を起こしていて",
                   "笑顔のケミストリーが離婚届を出していて"],
        },
    },
    "eye_sparkle": {
        "good": {
            "en": ["your eyes sparkle in perfect harmony ✨",
                   "the eye contact game is elite",
                   "your gazes basically high-five each other"],
            "ja": ["瞳のきらめきが完璧に調和していて✨",
                   "アイコンタクト力がエリート級で",
                   "二人の視線がハイタッチしていて"],
        },
        "bad": {
            "en": ["one of you looks half-asleep 😴",
                   "your eyes are staring in different decades",
                   "the sparkle levels are… uneven"],
            "ja": ["どちらかが半分寝ていて😴",
                   "視線が違う時代を見つめていて",
                   "きらめきレベルが…不均衡で"],
        },
    },
    "vibe_harmony": {
        "good": {
            "en": ["your vibes match like they were made together 🎶",
                   "the overall aura is suspiciously compatible",
                   "you radiate the same cozy energy"],
            "ja": ["雰囲気がまるでセットのように合っていて🎶",
                   "全体のオーラが怪しいほど相性抜群で",
                   "同じほっこりエネルギーを放っていて"],
        },
        "bad": {
            "en": ["your vibes never even said hello 👋",
                   "the auras are in completely different genres",
                   "one gives sunshine, the other gives Monday morning"],
            "ja": ["雰囲気が挨拶すら交わしていなくて👋",
                   "オーラのジャンルが全く違っていて",
                   "片方は太陽、もう片方は月曜の朝で"],
        },
    },
    "energy_balance": {
        "good": {
            "en": ["your energy levels balance each other out ⚖️",
                   "you'd calm each other down perfectly",
                   "the yin-yang energy is immaculate"],
            "ja": ["エネルギーが見事に釣り合っていて⚖️",
                   "お互いを完璧に落ち着かせられて",
                   "陰陽のバランスが完璧で"],
        },
        "bad": {
            "en": ["the energy levels are wildly out of whack ⚡",
                   "one of you is caffeine, the other is a nap",
                   "the vibe thermostat is broken"],
            "ja": ["エネルギーの差が激しすぎて⚡",
                   "片方はカフェイン、もう片方は昼寝で",
                   "雰囲気の温度調節が壊れていて"],
        },
    },
    "tilt_chemistry": {
        "good": {
            "en": ["your head tilts are in adorable agreement 🥰",
                   "you lean the same charming way",
                   "the tilt chemistry is textbook romance"],
            "ja": ["首のかしげ方が可愛く一致していて🥰",
                   "同じ魅力的な角度に傾いていて",
                   "首かしげケミストリーがお手本級で"],
        },
        "bad": {
            "en": ["your head tilts are heading opposite ways 🤨",
                   "you two lean like arguing bookends",
                   "the tilt angles refuse to cooperate"],
            "ja": ["首の傾きが正反対を向いていて🤨",
                   "喧嘩中のブックエンドみたいに傾いていて",
                   "首の角度が協力を拒否していて"],
        },
    },
    "face_shape_contrast": {
        "good": {
            "en": ["your face shapes contrast in that opposites-attract way 🧲",
                   "you're different enough to keep it interesting",
                   "the face-shape yin-yang is *chef's kiss*"],
            "ja": ["顔型が「正反対も魅力」的に対照的で🧲",
                   "飽きさせない程よい違いがあって",
                   "顔型の陰陽がまさに絶品で"],
        },
        "bad": {
            "en": ["your face shapes are basically at war 🛡️",
                   "the face geometry couldn't agree on anything",
                   "one round, one sharp — the AI is confused"],
            "ja": ["顔型がほぼ戦争状態で🛡️",
                   "顔の幾何学が何一つ合意できず",
                   "片方は丸、片方は鋭角——AIは混乱中で"],
        },
    },
    "warmth_spark": {
        "good": {
            "en": ["your photo warmth creates an instant spark 🔥",
                   "the color temperatures flirt beautifully",
                   "you glow in complementary tones"],
            "ja": ["写真のぬくもりが一瞬で火花を生んでいて🔥",
                   "色温度が美しく戯れていて",
                   "補い合う色合いで輝いていて"],
        },
        "bad": {
            "en": ["one photo is warm, the other is a freezer ❄️",
                   "the warmth spark short-circuited",
                   "the color moods clash like plaid on stripes"],
            "ja": ["片方は暖色、もう片方は冷凍庫で❄️",
                   "ぬくもりスパークがショートしていて",
                   "色の雰囲気がチェック柄×ストライプ級に衝突していて"],
        },
    },
    "lip_balance": {
        "good": {
            "en": ["your lip proportions balance out nicely 💋",
                   "the pout ratio is romantically aligned",
                   "your smiles frame each other perfectly"],
            "ja": ["唇のバランスが良い感じに整っていて💋",
                   "ぷっくり比率がロマンチックに揃っていて",
                   "お互いの笑顔を完璧に引き立てていて"],
        },
        "bad": {
            "en": ["the lip balance is a little lopsided 😅",
                   "one pout is doing all the work",
                   "the mouth math just doesn't add up"],
            "ja": ["唇のバランスが少し偏っていて😅",
                   "片方のぷっくりだけが頑張っていて",
                   "口元の計算が合わなくて"],
        },
    },
}

# Reason tiers: (min score, mode, opener_en, opener_ja).
# mode: "gush" = strength only, "mixed" = strength + red flag, "roast" = red flag only.
REASON_TIERS = [
    (90, "gush",
     "The AI is obsessed with this one — {good}. Basically flawless. 💖",
     "AIはこのマッチに夢中——{good}。ほぼ完璧です💖"),
    (75, "gush",
     "So much going for you two: {good}. The AI approves enthusiastically! 😍",
     "良いところだらけ：{good}。AIも大興奮で承認！😍"),
    (60, "mixed",
     "Good news: {good}. Bad news: {bad}. But hey, nobody's perfect. 😉",
     "良い知らせ：{good}。悪い知らせ：{bad}。まあ、完璧な人はいませんよね😉"),
    (45, "mixed",
     "On the plus side, {good}. On the other hand, {bad}. Proceed with snacks. 🍿",
     "良い点は、{good}。一方で、{bad}。おやつを片手にどうぞ🍿"),
    (30, "roast",
     "The AI searched hard and mostly found that {bad}. Yikes. 😬",
     "AIは頑張って探しましたが、主に{bad}という結果に。うーん😬"),
    (0, "roast",
     "Where do we start… {bad}. The AI recommends staying friends. Distant ones. 💀",
     "どこから話せば…{bad}。AIは「友達のまま」を推奨。それも遠い友達を💀"),
]


def _pick(seq, seed):
    return seq[seed % len(seq)]


def make_reason(score: float, name: str, breakdown: dict) -> dict:
    """Build a deterministic funny reason from the real breakdown.

    breakdown: {component_key: int percent}. Returns {"en":..., "ja":...}.
    """
    if not breakdown:
        return {"en": "", "ja": ""}

    # strongest & weakest real components
    best_key = max(breakdown, key=lambda k: breakdown[k])
    worst_key = min(breakdown, key=lambda k: breakdown[k])

    seed = int(hashlib.md5(f"reason:{int(score)}:{name}".encode()).hexdigest(), 16)

    # pick tier by score
    mode, tmpl_en, tmpl_ja = "mixed", REASON_TIERS[-1][2], REASON_TIERS[-1][3]
    for minimum, m, te, tj in REASON_TIERS:
        if score >= minimum:
            mode, tmpl_en, tmpl_ja = m, te, tj
            break

    out = {}
    for lang, tmpl in (("en", tmpl_en), ("ja", tmpl_ja)):
        good = _pick(COMPONENT_PHRASES[best_key]["good"][lang], seed)
        bad = _pick(COMPONENT_PHRASES[worst_key]["bad"][lang], seed >> 3)
        out[lang] = tmpl.format(good=good, bad=bad)
    return out


def band_for_score(score: float) -> str:
    for minimum, key in BANDS:
        if score >= minimum:
            return key
    return "run"


def pick_verdict(score: float, name: str, band: str | None = None) -> dict:
    """Deterministically pick one verdict line (per language) for a candidate.

    Uses md5 (stable across runs) so the same match always shows the same
    verdict, but different candidates/scores get variety.
    """
    band = band or band_for_score(score)
    seed = int(hashlib.md5(f"{int(score)}:{name}".encode("utf-8")).hexdigest(), 16)
    return {
        "band": band,
        "en": VERDICTS[band]["en"][seed % len(VERDICTS[band]["en"])],
        "ja": VERDICTS[band]["ja"][seed % len(VERDICTS[band]["ja"])],
    }
