"""
Notification MVP — FastAPI + Supabase
======================================
Endpoints:
  GET /notify/{user_id}   → generate 5 notifications, save to Supabase
  GET /dashboard          → all saved records from Supabase

Local:
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8000

Render:
  Build : pip install -r requirements.txt
  Start : uvicorn main:app --host 0.0.0.0 --port 10000

Env vars needed (in .env or Render dashboard):
  GEMINI_API_KEY
  SUPABASE_URL
  SUPABASE_KEY   ← use service_role key
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

GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

# Supabase table names — must match what you created
TABLE_METADATA      = "user_metadata"
TABLE_SCORES        = "user_scores"
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
# SEGMENT DEFINITIONS  (matches your image exactly)
# ──────────────────────────────────────────────

SEGMENTS = {
    "Content Reader": {
        "segment_key":             "content_reader",
        "label":                   "Content Reader",
        "traits":                  ["High article clicks & views","Long engagement time","12.1% notification responsive"],
        "notification_responsive": "12.1%",
        "segment_pct":             "45.8%",
        "color":                   "#3b82f6",
        "is_best":                 False,
    },
    "High Converter": {
        "segment_key":             "high_converter",
        "label":                   "High Converter",
        "traits":                  ["Contact clicks & enquiries","Completed submissions","34.2% notification responsive"],
        "notification_responsive": "34.2%",
        "segment_pct":             "18.0%",
        "color":                   "#16a34a",
        "is_best":                 True,
    },
    "Job Hunter": {
        "segment_key":             "job_hunter",
        "label":                   "Job Hunter",
        "traits":                  ["Job card & option clicks","Job-focused browsing","15.7% notification responsive"],
        "notification_responsive": "15.7%",
        "segment_pct":             "16.3%",
        "color":                   "#92400e",
        "is_best":                 False,
    },
    "Scheme Seeker": {
        "segment_key":             "scheme_seeker",
        "label":                   "Scheme Seeker",
        "traits":                  ["Scheme & category clicks","Profile completion intent","9.8% notification responsive"],
        "notification_responsive": "9.8%",
        "segment_pct":             "10.9%",
        "color":                   "#7c3aed",
        "is_best":                 False,
    },
    "Service Explorer": {
        "segment_key":             "service_explorer",
        "label":                   "Service Explorer",
        "traits":                  ["Service & sub-service clicks","Deep service navigation","14.3% notification responsive"],
        "notification_responsive": "14.3%",
        "segment_pct":             "8.9%",
        "color":                   "#b45309",
        "is_best":                 False,
    },
}


def classify_segment(profile: dict) -> dict:
    """
    1. Use primary_category field if present
    2. Fallback: highest score wins
    """
    def f(x):
        try: return float(x)
        except: return 0.0

    raw = profile.get("primary_category", "").strip().lower().replace("_", " ")

    label_map = {
        "content reader":   "Content Reader",
        "content re":       "Content Reader",
        "high converter":   "High Converter",
        "high conv":        "High Converter",
        "job hunter":       "Job Hunter",
        "scheme seeker":    "Scheme Seeker",
        "service explorer": "Service Explorer",
    }
    for key, label in label_map.items():
        if key in raw:
            return SEGMENTS[label]

    # score-based fallback
    scores = {
        "Content Reader":   f(profile.get("content_score", 0)),
        "High Converter":   f(profile.get("scheme_score", 0)) + f(profile.get("service_score", 0)),
        "Job Hunter":       f(profile.get("job_score", 0)),
        "Scheme Seeker":    f(profile.get("scheme_score", 0)),
        "Service Explorer": f(profile.get("service_score", 0)),
    }
    winner = max(scores, key=scores.get)
    return SEGMENTS[winner]

# ──────────────────────────────────────────────
# SUPABASE
# ──────────────────────────────────────────────

def get_sb() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY missing")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_user(uid: str) -> dict:
    sb = get_sb()

    meta = sb.table(TABLE_METADATA).select("*").eq("user_id", uid).execute()
    if not meta.data:
        raise ValueError(f"user_id={uid} not found in {TABLE_METADATA}")

    scores = sb.table(TABLE_SCORES).select("*").eq("user_id", uid).execute()
    if not scores.data:
        raise ValueError(f"user_id={uid} not found in {TABLE_SCORES}")

    return {**meta.data[0], **_avg(scores.data)}


def _avg(rows: list) -> dict:
    if len(rows) == 1:
        return rows[0]
    out = {}
    for k in rows[0]:
        vals = [r[k] for r in rows if r[k] is not None]
        if not vals:
            continue
        try:
            nums = [float(v) for v in vals]
            out[k] = round(sum(nums) / len(nums), 2)
        except:
            out[k] = max(set(str(v) for v in vals), key=[str(v) for v in vals].count)
    return out


def save_to_supabase(user_id: str, segment_key: str, notifications: list):
    sb  = get_sb()
    ts  = datetime.now().isoformat()
    rows = [{
        "user_id":              user_id,
        "generated_at":         ts,
        "segment_key":          segment_key,
        "notification_number":  n.get("notification_number"),
        "title":                n.get("title", ""),
        "body":                 n.get("body", ""),
        "language":             n.get("language", ""),
        "scheme_or_service_id": n.get("scheme_or_service_id", ""),
        "tone_used":            n.get("tone_used", ""),
        "human_check":          n.get("human_check", ""),
        "relevance_rationale":  n.get("relevance_rationale", ""),
        "data_signals_used":    n.get("data_signals_used", ""),
    } for n in notifications]
    sb.table(TABLE_NOTIFICATIONS).insert(rows).execute()

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
# PROMPT
# ──────────────────────────────────────────────

def build_prompt(u: dict, n: int) -> str:
    return f"""
You are a warm, helpful friend who knows about government
schemes and wants to genuinely help citizens improve their lives.

You are NOT a government system. You are NOT a bot.
You write like a real person who cares.

════════════════════════════════════
THIS IS NOTIFICATION {n} OF 5
Fully independent call. No memory of other notifications.
Create a completely unique angle, different scheme if possible.
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
- Understand this person's real situation from the data
- Choose one scheme from available_scheme_ids only
- Write entirely in {u.get("language","English")}
- Title: max 6 words. Body: max 15 words.
- No emojis, no hashtags, no rupee symbol in title
- Sound like a friend, not a government notice

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
# GEMINI
# ──────────────────────────────────────────────

async def call_gemini(client: httpx.AsyncClient, prompt: str, n: int) -> dict:
    r = await client.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    r.raise_for_status()
    raw   = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"notification_number": n, "raw": raw, "parse_error": True}

# ──────────────────────────────────────────────
# LOCAL JSON BACKUP
# ──────────────────────────────────────────────

def save_json(user_id, profile, notifications):
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"output_{user_id}_{ts}.json"
    out.write_text(json.dumps({
        "timestamp": ts, "user_id": user_id,
        "profile": profile, "notifications": notifications,
    }, indent=2, ensure_ascii=False))

# ──────────────────────────────────────────────
# FASTAPI APP
# ──────────────────────────────────────────────

app = FastAPI(title="Notification MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/notify/{user_id}")
async def get_notifications(user_id: str):

    # 1. fetch from Supabase
    try:
        raw_user = fetch_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 2. resolve + classify
    profile = resolve(raw_user)
    segment = classify_segment(profile)

    # 3. 5 parallel Gemini calls
    async with httpx.AsyncClient() as client:
        notifications = list(await asyncio.gather(*[
            call_gemini(client, build_prompt(profile, n), n)
            for n in range(1, 6)
        ]))

    # 4. save to Supabase
    try:
        save_to_supabase(user_id, segment["segment_key"], notifications)
    except Exception as e:
        print(f"[WARN] Supabase save failed: {e}")

    # 5. local JSON backup
    save_json(user_id, profile, notifications)

    # 6. return — segment + notifications first, profile below
    return {
        "user_id":      user_id,
        "generated_at": datetime.now().isoformat(),
        "user_segment": segment,
        "notifications": notifications,
        "user_profile": {
            "name":                profile.get("name",""),
            "age":                 profile.get("age",""),
            "location":            profile.get("district",""),
            "language":            profile.get("language",""),
            "personal_income":     profile.get("personal_income",""),
            "family_income":       profile.get("family_income",""),
            "earner_role":         profile.get("earner_role",""),
            "bpl":                 profile.get("bpl",""),
            "primary_category":    profile.get("primary_category",""),
            "notification_tag":    profile.get("notification_tag",""),
            "notification_clicks": profile.get("notification_click",""),
            "engagement_ms":       profile.get("engagement_time_msec",""),
            "content_score":       profile.get("content_score",""),
            "scheme_score":        profile.get("scheme_score",""),
            "job_score":           profile.get("job_score",""),
            "service_score":       profile.get("service_score",""),
        },
    }


@app.get("/dashboard")
def dashboard():
    """
    Returns all saved notification records from Supabase.
    Groups by user_id so frontend can show segment buckets.
    """
    try:
        sb  = get_sb()
        res = (
            sb.table(TABLE_NOTIFICATIONS)
            .select("*")
            .order("generated_at", desc=True)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # group by user_id → list of records per user
    grouped = {}
    for row in rows:
        uid = row["user_id"]
        if uid not in grouped:
            grouped[uid] = {
                "user_id":     uid,
                "segment_key": row.get("segment_key",""),
                "generated_at":row.get("generated_at",""),
                "notifications": [],
            }
        grouped[uid]["notifications"].append({
            "notification_number":  row.get("notification_number"),
            "title":                row.get("title",""),
            "body":                 row.get("body",""),
            "tone_used":            row.get("tone_used",""),
            "scheme_or_service_id": row.get("scheme_or_service_id",""),
            "language":             row.get("language",""),
            "human_check":          row.get("human_check",""),
            "relevance_rationale":  row.get("relevance_rationale",""),
        })

    return list(grouped.values())
