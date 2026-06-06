"""
Notification MVP — FastAPI + Supabase Backend
===============================================
- Reads user data from Supabase (replaces CSV files)
- Makes 5 parallel Gemini calls
- Saves generated notifications to Supabase
- Also saves to local outputs_v3/ JSON (kept as backup)

Local run:
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8000

Render:
  Build : pip install -r requirements.txt
  Start : uvicorn main:app --host 0.0.0.0 --port 10000
"""

import os, json, asyncio
from pathlib import Path
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# ENV
# ──────────────────────────────────────────────

SUPABASE_URL  = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY  = os.getenv("SUPABASE_KEY", "")   # use service_role key
GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

# Supabase table names — must match what you created
TABLE_USERS         = "users"               # single table — all columns from Excel
TABLE_NOTIFICATIONS = "generated_notifications"

OUTPUT_DIR = Path("outputs_v3")

# ──────────────────────────────────────────────
# ID → LABEL MAPS
# ──────────────────────────────────────────────

DISTRICT_MAP = {
    "1":"Mumbai","2":"Pune","3":"Nagpur","4":"Nashik",
    "5":"Aurangabad","6":"Thane","7":"Kolhapur","8":"Solapur",
}
PERSONAL_INCOME_MAP = {
    "1":"No income","2":"Below ₹5,000/month",
    "3":"₹5k–10k/month","4":"₹10k–25k/month",
    "5":"₹25k–50k/month","6":"Above ₹50k/month",
}
FAMILY_INCOME_MAP = {
    "1":"Below ₹1 lakh/year","2":"₹1–3 lakh/year",
    "3":"₹3–6 lakh/year","4":"₹6–10 lakh/year",
    "5":"Above ₹10 lakh/year",
}
FAMILY_TYPE_MAP = {"1":"Sole Earner","2":"Co Earner","3":"Partial Earner"}
BPL_MAP         = {"0":"No","1":"Yes"}
LANG_MAP        = {"en":"English","mr":"Marathi","hi":"Hindi","pa":"Punjabi","ml":"Malayalam"}

SCHEME_CATALOGUE = [
    "PMAY-001","PMJAY-002","PMKISAN-003","NREGA-004","PMJDY-005",
    "SKILL-IND-006","STARTUP-IND-007","NSAP-008","SCHOLARSHIP-009","UJJWALA-010",
]

# ──────────────────────────────────────────────
# SEGMENT METADATA
# ──────────────────────────────────────────────

SEGMENT_META = {
    "content_reader": {
        "label":                   "Content Reader",
        "traits":                  ["High article clicks & views", "Long engagement time"],
        "notification_responsive": "12.1%",
        "segment_pct":             "45.8%",
        "color":                   "#3b82f6",
        "is_best":                 False,
    },
    "high_converter": {
        "label":                   "High Converter",
        "traits":                  ["Contact clicks & enquiries", "Completed submissions"],
        "notification_responsive": "34.2%",
        "segment_pct":             "18.0%",
        "color":                   "#22c55e",
        "is_best":                 True,
    },
    "job_hunter": {
        "label":                   "Job Hunter",
        "traits":                  ["Job card & option clicks", "Job-focused browsing"],
        "notification_responsive": "15.7%",
        "segment_pct":             "16.3%",
        "color":                   "#f59e0b",
        "is_best":                 False,
    },
    "scheme_seeker": {
        "label":                   "Scheme Seeker",
        "traits":                  ["Scheme & category clicks", "Profile completion intent"],
        "notification_responsive": "9.8%",
        "segment_pct":             "10.9%",
        "color":                   "#8b5cf6",
        "is_best":                 False,
    },
    "service_explorer": {
        "label":                   "Service Explorer",
        "traits":                  ["Service & sub-service clicks", "Deep service navigation"],
        "notification_responsive": "14.3%",
        "segment_pct":             "8.9%",
        "color":                   "#ef4444",
        "is_best":                 False,
    },
}

# ──────────────────────────────────────────────
# SUPABASE CLIENT
# ──────────────────────────────────────────────

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set in environment")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ──────────────────────────────────────────────
# DATA FETCHER — single table
# ──────────────────────────────────────────────

def fetch_user_data(uid: str) -> dict:
    """Fetch one user row from the single `users` table."""
    sb  = get_supabase()
    res = (
        sb.table(TABLE_USERS)
        .select("*")
        .eq("user_id", uid)
        .execute()
    )
    if not res.data:
        raise ValueError(f"user_id={uid} not found in table '{TABLE_USERS}'")
    return res.data[0]

# ──────────────────────────────────────────────
# PROFILE RESOLVER
# ──────────────────────────────────────────────

def resolve(u: dict) -> dict:
    p = {k: str(v) if v is not None else "" for k, v in u.items()}
    p["district"]             = DISTRICT_MAP.get(p.get("district_id",""), p.get("district_id","Unknown"))
    p["personal_income"]      = PERSONAL_INCOME_MAP.get(p.get("personal_income_id",""), "Unknown")
    p["family_income"]        = FAMILY_INCOME_MAP.get(p.get("family_income_id",""), "Unknown")
    p["earner_role"]          = FAMILY_TYPE_MAP.get(p.get("family_type_id",""), "Unknown")
    p["bpl"]                  = BPL_MAP.get(p.get("bpl_category","0"), "No")
    p["language"]             = LANG_MAP.get(p.get("preferred_language","en").strip(), "English")
    p["language_code"]        = p.get("preferred_language","en").strip()
    p["available_scheme_ids"] = ", ".join(SCHEME_CATALOGUE)
    return p

# ──────────────────────────────────────────────
# SEGMENT CLASSIFIER
# ──────────────────────────────────────────────

def classify_segment(profile: dict) -> dict:
    """Return segment dict for this user.
    Priority: primary_category field → score comparison → fallback.
    """
    def safe_float(val):
        try:    return float(val or 0)
        except: return 0.0

    # 1. Try direct mapping from primary_category field
    raw = str(profile.get("primary_category", "")).strip().lower().replace(" ", "_")
    direct = {
        "content_reader":   "content_reader",
        "content":          "content_reader",
        "high_converter":   "high_converter",
        "converter":        "high_converter",
        "job_hunter":       "job_hunter",
        "job":              "job_hunter",
        "scheme_seeker":    "scheme_seeker",
        "scheme":           "scheme_seeker",
        "service_explorer": "service_explorer",
        "service":          "service_explorer",
    }
    for key, seg in direct.items():
        if key in raw:
            return {"segment_key": seg, **SEGMENT_META[seg]}

    # 2. Score comparison fallback
    scores = {
        "content_reader":   safe_float(profile.get("content_score")),
        "scheme_seeker":    safe_float(profile.get("scheme_score")),
        "job_hunter":       safe_float(profile.get("job_score")),
        "service_explorer": safe_float(profile.get("service_score")),
    }
    # High converter: high notification clicks + engagement
    n_clicks   = safe_float(profile.get("notification_click"))
    engagement = safe_float(profile.get("engagement_time_msec"))
    if n_clicks > 5 and engagement > 60000:
        scores["high_converter"] = n_clicks * 1000 + engagement * 0.1

    best = max(scores, key=scores.get)
    return {"segment_key": best, **SEGMENT_META[best]}

# ──────────────────────────────────────────────
# PROMPT BUILDER
# ──────────────────────────────────────────────

def build_prompt(u: dict, n: int) -> str:
    return f"""
You are a warm, helpful friend who knows about government
schemes and wants to genuinely help citizens improve their lives.

You are NOT a government system. You are NOT a bot.
You write like a real person who cares.

════════════════════════════════════
THIS IS NOTIFICATION {n} OF 5
This is a fully independent call. You have no memory of
the other 4 notifications. Based ONLY on the user data
below, create a completely unique notification — fresh
angle, different scheme if possible, different hook.
════════════════════════════════════

USER DATA:

user_id              : {u.get("user_id","")}
name                 : {u.get("name","")}
age                  : {u.get("age","")}
location             : {u.get("district","")}
language             : {u.get("language","")} ({u.get("language_code","en")})
personal income      : {u.get("personal_income","")}
family income        : {u.get("family_income","")}
earner role          : {u.get("earner_role","")}
below poverty line   : {u.get("bpl","")}
primary app behavior : {u.get("primary_category","")}
notification history : {u.get("notification_tag","")}
notification clicks  : {u.get("notification_click","")}
engagement time (ms) : {u.get("engagement_time_msec","")}
content_score        : {u.get("content_score","")}
scheme_score         : {u.get("scheme_score","")}
job_score            : {u.get("job_score","")}
service_score        : {u.get("service_score","")}
available scheme IDs : {u.get("available_scheme_ids","")}

TASK:
- Understand this person's real life from the data
- Choose one scheme from available_scheme_ids only
- Write one push notification that feels personally written
- Write entirely in {u.get("language","English")}
- Title: max 6 words. Body: max 15 words.
- No emojis, no hashtags, no rupee symbol in title
- Sound like a friend texting, not a government notice

OUTPUT — strict JSON only. No markdown. No explanation.

{{
  "notification_number"  : {n},
  "user_id"              : "{u.get("user_id","")}",
  "title"                : "max 6 words",
  "body"                 : "max 15 words",
  "language"             : "{u.get("language_code","en")}",
  "scheme_or_service_id" : "one ID from available list",
  "tone_used"            : "Relieving / Encouraging / Urgent / Aspirational / Curiosity",
  "human_check"          : "yes or no",
  "relevance_rationale"  : "one sentence why this scheme for this person",
  "data_signals_used"    : "list the fields that drove this decision"
}}
"""

# ──────────────────────────────────────────────
# GEMINI ASYNC
# ──────────────────────────────────────────────

async def call_gemini(client: httpx.AsyncClient, prompt: str, n: int) -> dict:
    r = await client.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"notification_number": n, "raw": raw, "parse_error": True}

# ──────────────────────────────────────────────
# SAVE — Supabase + local JSON
# ──────────────────────────────────────────────

def save_to_supabase(user_id: str, notifications: list):
    """Save all 5 notifications as rows in generated_notifications table."""
    sb = get_supabase()
    ts = datetime.now().isoformat()
    rows = []
    for n in notifications:
        rows.append({
            "user_id"              : user_id,
            "generated_at"         : ts,
            "notification_number"  : n.get("notification_number"),
            "title"                : n.get("title",""),
            "body"                 : n.get("body",""),
            "language"             : n.get("language",""),
            "scheme_or_service_id" : n.get("scheme_or_service_id",""),
            "tone_used"            : n.get("tone_used",""),
            "human_check"          : n.get("human_check",""),
            "relevance_rationale"  : n.get("relevance_rationale",""),
            "data_signals_used"    : n.get("data_signals_used",""),
        })
    sb.table(TABLE_NOTIFICATIONS).insert(rows).execute()


def save_to_json(user_id: str, profile: dict, notifications: list):
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"output_{user_id}_{ts}.json"
    out.write_text(json.dumps({
        "timestamp"    : ts,
        "user_id"      : user_id,
        "profile"      : profile,
        "notifications": notifications,
    }, indent=2, ensure_ascii=False))
    return out

# ──────────────────────────────────────────────
# FASTAPI
# ──────────────────────────────────────────────

app = FastAPI(title="Notification MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://zeex-ami-km1suy3tn-vivaanjain246-6796s-projects.vercel.app/"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok"}

def save_dashboard_bucket(
    profile,
    segment,
    notifications
):

    sb = get_supabase()

    row = {

        "user_id":
        profile["user_id"],

        "segment_key":
        segment["segment_key"],

        "generated_at":
        datetime.now().isoformat(),

        "name":
        profile.get("name"),

        "age":
        profile.get("age"),

        "location":
        profile.get("district"),

        "language":
        profile.get("language"),

        "personal_income":
        profile.get("personal_income"),

        "family_income":
        profile.get("family_income"),

        "earner_role":
        profile.get("earner_role"),

        "bpl":
        profile.get("bpl"),

        "primary_category":
        profile.get("primary_category"),

        "notification_tag":
        profile.get("notification_tag"),

        "notification_clicks":
        profile.get("notification_click"),

        "engagement_ms":
        profile.get("engagement_time_msec"),

        "content_score":
        profile.get("content_score"),

        "scheme_score":
        profile.get("scheme_score"),

        "job_score":
        profile.get("job_score"),

        "service_score":
        profile.get("service_score"),

        "notifications":
        notifications
    }

    (
        sb
        .table(
            "user_segment_dashboard"
        )
        .upsert(
            row,
            on_conflict="user_id"
        )
        .execute()
    )
@app.get("/notify/{user_id}")
async def get_notifications(user_id: str):

    # 1. fetch from Supabase
    try:
        raw_user = fetch_user_data(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 2. resolve IDs → labels
    profile = resolve(raw_user)

    # 3. classify segment
    segment = classify_segment(profile)
    # 4. 5 parallel Gemini calls
    async with httpx.AsyncClient() as client:
        notifications = list(await asyncio.gather(*[
            call_gemini(client, build_prompt(profile, n), n)
            for n in range(1, 6)
        ]))
        save_dashboard_bucket(profile,segment,notifications)

    # 5. save — Supabase + JSON
    try:
        save_to_supabase(user_id, notifications)
    except Exception as e:
        print(f"[WARN] Supabase save failed: {e}")

    save_to_json(user_id, profile, notifications)

    # 6. return — segment + notifications + profile
    return {
        "user_id"      : user_id,
        "generated_at" : datetime.now().isoformat(),
        "user_segment" : segment,
        "notifications": notifications,
        "user_profile" : {
            "name"               : profile.get("name",""),
            "age"                : profile.get("age",""),
            "location"           : profile.get("district",""),
            "language"           : profile.get("language",""),
            "personal_income"    : profile.get("personal_income",""),
            "family_income"      : profile.get("family_income",""),
            "earner_role"        : profile.get("earner_role",""),
            "bpl"                : profile.get("bpl",""),
            "primary_category"   : profile.get("primary_category",""),
            "notification_tag"   : profile.get("notification_tag",""),
            "notification_clicks": profile.get("notification_click",""),
            "engagement_ms"      : profile.get("engagement_time_msec",""),
            "content_score"      : profile.get("content_score",""),
            "scheme_score"       : profile.get("scheme_score",""),
            "job_score"          : profile.get("job_score",""),
            "service_score"      : profile.get("service_score",""),
        },
    }
@app.get("/dashboard")
def dashboard():

    sb = get_supabase()

    rows = (
        sb
        .table(
            "user_segment_dashboard"
        )
        .select("*")
        .execute()
    )

    return rows.data