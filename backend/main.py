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
  Root Dir : backend
  Build    : pip install -r requirements.txt
  Start    : uvicorn main:app --host 0.0.0.0 --port 10000

Env vars:
  GEMINI_API_KEY
  SUPABASE_URL
  SUPABASE_KEY   ← service_role key
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

# Supabase tables
TABLE_USERS         = "users"           # single Excel → one table
TABLE_SCHEMES       = "schemes"         # scheme catalogue from Excel
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
    "2": "Up to ₹10,000",
    "3": "₹10,001 to ₹20,000",
    "4": "₹20,001 to ₹30,000",
    "5": "₹30,001 to ₹40,000",
    "6": "₹40,001 to ₹50,000",
    "7": "₹50,001 to ₹75,000",
    "8": "₹75,001 to ₹1 Lakh",
    "9": "₹1.01 Lakh to ₹1.5 Lakh",
    "10": "₹1.51 Lakh to ₹2 Lakh",
    "11": "₹2.01 Lakh to ₹2.5 Lakh",
    "12": "₹2.51 Lakh to ₹3 Lakh",
    "13": "More than ₹3 Lakh",
    "14": "Prefer not to answer",
}
FAMILY_INCOME_MAP = {
    "2": "Up to ₹10,000",
    "3": "₹10,001 to ₹20,000",
    "4": "₹20,001 to ₹30,000",
    "5": "₹30,001 to ₹40,000",
    "6": "₹40,001 to ₹50,000",
    "7": "₹50,001 to ₹75,000",
    "8": "₹75,001 to ₹1 Lakh",
    "9": "₹1.01 Lakh to ₹1.5 Lakh",
    "10": "₹1.51 Lakh to ₹2 Lakh",
    "11": "₹2.01 Lakh to ₹2.5 Lakh",
    "12": "₹2.51 Lakh to ₹3 Lakh",
    "13": "More than ₹3 Lakh",
    "14": "Prefer not to answer",
}
FAMILY_TYPE_MAP = {"2":"Partial Earner","3":"Partial Earner","4":"Partial Earner"}
BPL_MAP         = {"FALSE":"No","TRUE":"Yes"}
LANG_MAP = {
    "mr": "Marathi",
    "hi": "Hindi",
    "en": "English",
    "pa": "Punjabi",
    "te": "Telugu",
    "ta": "Tamil",
    "as": "Assamese",
    "ml": "Malayalam",
    "bn": "Bengali",
    "kn": "Kannada",
    "gu": "Gujarati",
    "or": "Odia",
}
# ──────────────────────────────────────────────
# SEGMENT DEFINITIONS
# ──────────────────────────────────────────────

SEGMENTS = {
    "Content Reader": {
        "segment_key":"content_reader","label":"Content Reader",
        "traits":["High article clicks & views","Long engagement time","12.1% notification responsive"],
        "notification_responsive":"12.1%","segment_pct":"45.8%","color":"#3b82f6","is_best":False,
    },
    "High Converter": {
        "segment_key":"high_converter","label":"High Converter",
        "traits":["Contact clicks & enquiries","Completed submissions","34.2% notification responsive"],
        "notification_responsive":"34.2%","segment_pct":"18.0%","color":"#16a34a","is_best":True,
    },
    "Job Hunter": {
        "segment_key":"job_hunter","label":"Job Hunter",
        "traits":["Job card & option clicks","Job-focused browsing","15.7% notification responsive"],
        "notification_responsive":"15.7%","segment_pct":"16.3%","color":"#92400e","is_best":False,
    },
    "Scheme Seeker": {
        "segment_key":"scheme_seeker","label":"Scheme Seeker",
        "traits":["Scheme & category clicks","Profile completion intent","9.8% notification responsive"],
        "notification_responsive":"9.8%","segment_pct":"10.9%","color":"#7c3aed","is_best":False,
    },
    "Service Explorer": {
        "segment_key":"service_explorer","label":"Service Explorer",
        "traits":["Service & sub-service clicks","Deep service navigation","14.3% notification responsive"],
        "notification_responsive":"14.3%","segment_pct":"8.9%","color":"#b45309","is_best":False,
    },
}


def classify_segment(profile: dict) -> dict:
    def f(x):
        try: return float(x)
        except: return 0.0

    raw = profile.get("primary_category", "").strip().lower().replace("_", " ")
    label_map = {
        "content reader":   "Content Reader",
        "high converter":   "High Converter",
        "job hunter":       "Job Hunter",
        "scheme seeker":    "Scheme Seeker",
        "service explorer": "Service Explorer",
    }
    for key, label in label_map.items():
        if key in raw:
            return SEGMENTS[label]

    scores = {
        "Content Reader":   f(profile.get("content_score", 0)),
        "High Converter":   f(profile.get("scheme_score", 0)) + f(profile.get("service_score", 0)),
        "Job Hunter":       f(profile.get("job_score", 0)),
        "Scheme Seeker":    f(profile.get("scheme_score", 0)),
        "Service Explorer": f(profile.get("service_score", 0)),
    }
    return SEGMENTS[max(scores, key=scores.get)]

# ──────────────────────────────────────────────
# SUPABASE
# ──────────────────────────────────────────────

def get_sb() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY missing")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_user(uid: str) -> dict:
    sb  = get_sb()
    res = sb.table(TABLE_USERS).select("*").eq("user_id", uid).execute()
    if not res.data:
        raise ValueError(f"user_id={uid} not found in table '{TABLE_USERS}'")
    return res.data[0]

def fetch_schemes() -> list[dict]:
    """Fetch all active schemes from Supabase schemes table."""
    sb  = get_sb()
    res = sb.table(TABLE_SCHEMES).select("id, name").eq("is_active", True).execute()
    return res.data or []


'''def save_to_supabase(user_id: str, segment_key: str, notifications: list):
    sb  = get_sb()
    ts  = datetime.now().isoformat()
    sb.table(TABLE_NOTIFICATIONS) \
        .delete() \
        .eq("user_id", user_id) \
        .execute()
    
    rows = [{
        "user_id":               user_id,
        "generated_at":          ts,
        "segment_key":           segment_key,
        "notification_number":   n.get("notification_number"),
        "title":                 n.get("title", ""),
        "body":                  n.get("body", ""),
        "language":              n.get("language", ""),
        "scheme_id":             n.get("scheme_id", ""),
        "scheme_name":           n.get("scheme_name", ""),
        "dependency_vector_used":n.get("dependency_vector_used", ""),
        "attention_strategy":    n.get("attention_strategy", ""),
        "relevance_rationale":   n.get("relevance_rationale", ""),
    } for n in notifications]
    sb.table(TABLE_NOTIFICATIONS).insert(rows).execute()'''
def save_to_supabase(user_id: str, segment_key: str, notifications: list):

    sb = get_sb()
    ts = datetime.now().isoformat()

    user_id = str(user_id)

    # DELETE OLD NOTIFICATIONS FOR THIS USER
    deleted = (
        sb.table(TABLE_NOTIFICATIONS)
        .delete()
        .eq("user_id", user_id)
        .execute()
    )

    print("Deleted rows:", deleted.data)

    rows = [{
        "user_id": user_id,
        "generated_at": ts,
        "segment_key": segment_key,
        "notification_number": n.get("notification_number"),

        "title": n.get("title", ""),
        "body": n.get("body", ""),
        "language": n.get("language", ""),

        "scheme_id": n.get("scheme_id", ""),
        "scheme_name": n.get("scheme_name", ""),

        "dependency_vector_used":
            n.get("dependency_vector_used", ""),

        "attention_strategy":
            n.get("attention_strategy", ""),

        "relevance_rationale":
            n.get("relevance_rationale", ""),
    } for n in notifications]

    inserted = (
        sb.table(TABLE_NOTIFICATIONS)
        .insert(rows)
        .execute()
    )

    print("Inserted:", len(inserted.data))
# ──────────────────────────────────────────────
# PROFILE RESOLVER
# ──────────────────────────────────────────────

def normalize_id(v):
    if v is None:
        return ""

    s = str(v).strip()

    try:
        # converts "3.0" → "3"
        if float(s).is_integer():
            return str(int(float(s)))
    except:
        pass

    return s


def resolve(u: dict):

    # normalize everything first
    p = {k: normalize_id(v) for k, v in u.items()}
    # district
    p["district"] = DISTRICT_MAP.get(
        p.get("district_id"),
        "Unknown"
    )

    # personal income
    p["personal_income"] = PERSONAL_INCOME_MAP.get(
        p.get("personal_income_id"),
        "Unknown"
    )

    # family income
    p["family_income"] = FAMILY_INCOME_MAP.get(
        p.get("family_income_id"),
        "Unknown"
    )

    # earner role
    p["earner_role"] = FAMILY_TYPE_MAP.get(
        p.get("family_type_id"),
        "Unknown"
    )

    # BPL
    p["bpl"] = BPL_MAP.get(
        p.get("bpl_category", "").upper(),
        "Not Available"
    )

    # language
    p["language"] = LANG_MAP.get(
        p.get("preferred_language"),
        "English"
    )
    p["language_code"]   = p.get("preferred_language","en").strip()
    return p

# ──────────────────────────────────────────────
# PROMPT  (new advanced prompt)
# ──────────────────────────────────────────────

def build_prompt(u: dict, schemes: list[dict], n: int) -> str:
    # Build catalogue string: "id | name" per line
    catalogue = "\n".join(f"  {s['id']} | {s['name']}" for s in schemes)

    return f"""You are the advanced hyper-personalization engine for A App's Hyper-Personalized Notification System (HPNS). Your objective is to map a citizen's multi-dimensional demographic and behavioral matrix to exactly ONE scheme from the approved master catalog, outputting a high-conversion push notification payload.

You are NOT a rigid bureaucratic portal. You write like a trusted, wise, and supportive friend sending an empathetic WhatsApp message—warm, conversational, practical, and direct.

════════════════════════════════════════
THIS IS NOTIFICATION {n} OF 5 — fully independent call.
Create a completely unique angle and choose a different scheme if possible.
════════════════════════════════════════

1. THE COMPLETE SIGNAL INPUT MATRIX

[DEMOGRAPHIC CONTEXT]
User ID: {u.get("user_id","")} | Name: {u.get("name","")} | Age: {u.get("age","")} | Language: {u.get("language_code","en")}
Transliterate all personal names, place names, and proper nouns also into the given language strictly.
[FINANCIAL & DEPENDENCY MATRIX]
Personal Income: {u.get("personal_income","")}
Family Income: {u.get("family_income","")}
Poverty Index — BPL: {u.get("bpl","")}
Household Structure: {u.get("earner_role","")}

[SOCIOPROFESSIONAL CLASSIFICATION]
Occupation ID: {u.get("occupation_id","")}
Working Status ID: {u.get("working_status_id","")}

[APP TELEMETRY & ATTENTION LOGS]
Dominant Segment: {u.get("primary_category","")}
Historical Response Tag: {u.get("notification_tag","")}
Engagement: {u.get("engagement_time_msec","")} ms | Notification Clicks: {u.get("notification_click","")}
Content Score: {u.get("content_score","")} | Scheme Score: {u.get("scheme_score","")} | Job Score: {u.get("job_score","")} | Service Score: {u.get("service_score","")}

2. MASTER GROUND-TRUTH CATALOGUE
Select exactly ONE scheme matching both demographic eligibility and implicit intent:
{catalogue}
HARD GUARDRAIL: Use only the exact 'id' and 'name' from the list above. Never hallucinate.

3. INTERPRETATION LOGIC

STEP 1 — DEPENDENCY VECTOR:
- Dependent/Aspirational: personal income low/null AND family income high/moderate → upskilling, certifications, loans
- Shared Household Distress: both incomes extremely low OR BPL=Yes → subsidies, food security, cash transfers
- High Density Dilution: large household + low/moderate family income → scale-based household assistance
- Independent Pro: stable income, moderate engagement → growth or investment schemes

STEP 2 — ATTENTION STRATEGY:
- High Exploration, Zero Response (high engagement + high scores but notification_click=0) → Fatigue Breakthrough: lead title with name, undeniable value
- Low Dwell, High Converter → Swift Action Drive: compact, action-driven, brief
- Default → Educational Hook

STEP 3 — LIFE STAGE:
- Age > 45 + physical occupation → health protection, insurance, pension, tool subsidies
- Age < 28 → competitive growth, digital access, skill accelerators

4. RULES
- Write entirely in {u.get("language","English")} ({u.get("language_code","en")})
- Title: max 6 words. Body: max 15 words.
- No emojis, no hashtags, no rupee symbol in title
- No bureaucratic jargon. Sound like a friend.

OUTPUT — strict raw JSON only. No markdown. No preamble.

{{
  "notification_number"   : {n},
  "user_id"               : "{u.get("user_id","")}",
  "title"                 : "max 6 words in {u.get("language","English")}",
  "body"                  : "max 15 words in {u.get("language","English")}",
  "language"              : "{u.get("language_code","en")}",
  "scheme_id"             : "exact id from catalogue",
  "scheme_name"           : "exact name from catalogue",
  "dependency_vector_used": "Dependent Aspirational | Shared Household Distress | High Density Dilution | Independent Pro",
  "attention_strategy"    : "Fatigue Breakthrough | Swift Action Drive | Educational Hook",
  "relevance_rationale"   : "one sentence linking dependency gap, attention behavior, age, occupation to chosen scheme"
}}"""

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
# FASTAPI
# ──────────────────────────────────────────────

app = FastAPI(title="HPNS Notification MVP")

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

    # 1. fetch user
    try:
        raw_user = fetch_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 2. fetch schemes from Supabase
    try:
        schemes = fetch_schemes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schemes fetch failed: {e}")
    if not schemes:
        raise HTTPException(status_code=500, detail="No active schemes found in 'schemes' table")

    # 3. resolve + classify
    profile = resolve(raw_user)
    segment = classify_segment(profile)

    # 4. 5 parallel Gemini calls
    async with httpx.AsyncClient() as client:
        notifications = list(await asyncio.gather(*[
            call_gemini(client, build_prompt(profile, schemes, n), n)
            for n in range(1, 6)
        ]))

    # 5. save to Supabase
    try:
        save_to_supabase(user_id, segment["segment_key"], notifications)
    except Exception as e:
        print(f"[WARN] Supabase save failed: {e}")

    # 6. local backup
    save_json(user_id, profile, notifications)

    # 7. return
    return {
        "user_id":       user_id,
        "generated_at":  datetime.now().isoformat(),
        "user_segment":  segment,
        "notifications": notifications,
        "user_profile": {
            "name":              profile.get("name",""),
            "age":               profile.get("age",""),
            "location":          profile.get("district",""),
            "language":          profile.get("language",""),
            "personal_income":   profile.get("personal_income",""),
            "family_income":     profile.get("family_income",""),
            "earner_role":       profile.get("earner_role",""),
            "bpl":               profile.get("bpl",""),
            "occupation_id":     profile.get("occupation_id",""),
            "working_status_id": profile.get("working_status_id",""),
            "primary_category":  profile.get("primary_category",""),
            "notification_tag":  profile.get("notification_tag",""),
            "notification_clicks":profile.get("notification_click",""),
            "engagement_ms":     profile.get("engagement_time_msec",""),
            "content_score":     profile.get("content_score",""),
            "scheme_score":      profile.get("scheme_score",""),
            "job_score":         profile.get("job_score",""),
            "service_score":     profile.get("service_score",""),
        },
    }


@app.get("/dashboard")
def dashboard():
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

    grouped = {}
    for row in rows:
        uid = row["user_id"]
        if uid not in grouped:
            grouped[uid] = {
                "user_id":      uid,
                "segment_key":  row.get("segment_key",""),
                "generated_at": row.get("generated_at",""),
                "notifications": [],
            }
        grouped[uid]["notifications"].append({
            "notification_number":   row.get("notification_number"),
            "title":                 row.get("title",""),
            "body":                  row.get("body",""),
            "scheme_id":             row.get("scheme_id",""),
            "scheme_name":           row.get("scheme_name",""),
            "dependency_vector_used":row.get("dependency_vector_used",""),
            "attention_strategy":    row.get("attention_strategy",""),
            "language":              row.get("language",""),
            "relevance_rationale":   row.get("relevance_rationale",""),
        })
    return list(grouped.values())
