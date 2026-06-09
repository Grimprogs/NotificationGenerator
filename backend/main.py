"""
HPNS Backend v5
- Gemini freely picks source_bucket per notification
- source_bucket saved to Supabase
- delete-before-insert (one instance per user_id)
"""

import os, json, asyncio
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-pro:generateContent"
)

TABLE_USERS         = "users"
TABLE_SCHEMES       = "schemes"
TABLE_NOTIFICATIONS = "generated_notifications"

OUTPUT_DIR = Path("outputs_v5")

# ── MAPS ──────────────────────────────────────────────────────────────────────

DISTRICT_MAP = {
    "1":"Mumbai","2":"Pune","3":"Nagpur","4":"Nashik",
    "5":"Aurangabad","6":"Thane","7":"Kolhapur","8":"Solapur",
}
PERSONAL_INCOME_MAP = {
    "2":"Up to ₹10,000","3":"₹10,001–₹20,000","4":"₹20,001–₹30,000",
    "5":"₹30,001–₹40,000","6":"₹40,001–₹50,000","7":"₹50,001–₹75,000",
    "8":"₹75,001–₹1 Lakh","9":"₹1.01–₹1.5 Lakh","10":"₹1.51–₹2 Lakh",
    "11":"₹2.01–₹2.5 Lakh","12":"₹2.51–₹3 Lakh","13":"More than ₹3 Lakh",
    "14":"Prefer not to answer",
}
FAMILY_INCOME_MAP = {
    "2":"Up to ₹10,000","3":"₹10,001–₹20,000","4":"₹20,001–₹30,000",
    "5":"₹30,001–₹40,000","6":"₹40,001–₹50,000","7":"₹50,001–₹75,000",
    "8":"₹75,001–₹1 Lakh","9":"₹1.01–₹1.5 Lakh","10":"₹1.51–₹2 Lakh",
    "11":"₹2.01–₹2.5 Lakh","12":"₹2.51–₹3 Lakh","13":"More than ₹3 Lakh",
    "14":"Prefer not to answer",
}
FAMILY_TYPE_MAP = {"1":"Sole Earner","2":"Co Earner","3":"Partial Earner","4":"Partial Earner"}
BPL_MAP  = {"FALSE":"No","TRUE":"Yes","0":"No","1":"Yes"}
LANG_MAP = {
    "mr":"Marathi","hi":"Hindi","en":"English","pa":"Punjabi",
    "te":"Telugu","ta":"Tamil","as":"Assamese","ml":"Malayalam",
    "bn":"Bengali","kn":"Kannada","gu":"Gujarati","or":"Odia",
}

SEGMENTS = {
    "Content Reader":   {"segment_key":"content_reader",  "label":"Content Reader",  "color":"#3b82f6","is_best":False,"segment_pct":"45.8%","notification_responsive":"12.1%","traits":["High article clicks & views","Long engagement time"]},
    "High Converter":   {"segment_key":"high_converter",  "label":"High Converter",  "color":"#16a34a","is_best":True, "segment_pct":"18.0%","notification_responsive":"34.2%","traits":["Contact clicks & enquiries","Completed submissions"]},
    "Job Hunter":       {"segment_key":"job_hunter",      "label":"Job Hunter",      "color":"#d97706","is_best":False,"segment_pct":"16.3%","notification_responsive":"15.7%","traits":["Job card & option clicks","Job-focused browsing"]},
    "Scheme Seeker":    {"segment_key":"scheme_seeker",   "label":"Scheme Seeker",   "color":"#7c3aed","is_best":False,"segment_pct":"10.9%","notification_responsive":"9.8%", "traits":["Scheme & category clicks","Profile completion intent"]},
    "Service Explorer": {"segment_key":"service_explorer","label":"Service Explorer","color":"#b45309","is_best":False,"segment_pct":"8.9%", "notification_responsive":"14.3%","traits":["Service & sub-service clicks","Deep service navigation"]},
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def norm(v):
    if v is None: return ""
    s = str(v).strip()
    try:
        f = float(s)
        return str(int(f)) if f.is_integer() else s
    except: return s


def classify_segment(profile: dict) -> dict:
    raw = profile.get("primary_category","").strip().lower().replace("_"," ")
    lmap = {
        "content reader":"Content Reader","high converter":"High Converter",
        "job hunter":"Job Hunter","scheme seeker":"Scheme Seeker",
        "service explorer":"Service Explorer",
    }
    for k,v in lmap.items():
        if k in raw: return SEGMENTS[v]
    def f(x):
        try: return float(x)
        except: return 0.0
    scores = {
        "Content Reader":  f(profile.get("content_score",0)),
        "High Converter":  f(profile.get("scheme_score",0))+f(profile.get("service_score",0)),
        "Job Hunter":      f(profile.get("job_score",0)),
        "Scheme Seeker":   f(profile.get("scheme_score",0)),
        "Service Explorer":f(profile.get("service_score",0)),
    }
    return SEGMENTS[max(scores, key=scores.get)]


def resolve(u: dict) -> dict:
    p = {k: norm(v) for k, v in u.items()}
    p["district"]        = DISTRICT_MAP.get(p.get("district_id",""), "Unknown")
    p["personal_income"] = PERSONAL_INCOME_MAP.get(p.get("personal_income_id",""), "Unknown")
    p["family_income"]   = FAMILY_INCOME_MAP.get(p.get("family_income_id",""), "Unknown")
    p["earner_role"]     = FAMILY_TYPE_MAP.get(p.get("family_type_id",""), "Unknown")
    p["occupation"]      = p.get("occupation_id","Unknown")
    p["bpl"]             = BPL_MAP.get(p.get("bpl_category","").upper(), "Not Available")
    p["language"]        = LANG_MAP.get(p.get("preferred_language","en"), "English")
    p["language_code"]   = p.get("preferred_language","en").strip()
    return p

# ── SUPABASE ──────────────────────────────────────────────────────────────────

def get_sb() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY missing")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_user(uid: str) -> dict:
    sb  = get_sb()
    uid = str(uid).strip()
    res = sb.table(TABLE_USERS).select("*").eq("user_id", uid).execute()
    if not res.data:
        res = sb.table(TABLE_USERS).select("*").eq("user_id", f"{uid}.0").execute()
    if not res.data:
        raise ValueError(f"user_id={uid} not found")
    return res.data[0]


def fetch_schemes() -> list:
    sb  = get_sb()
    res = sb.table(TABLE_SCHEMES).select("id, name, slug").eq("is_active", True).execute()
    return res.data or []


def save_to_supabase(user_id: str, segment_key: str, notifications: list):
    sb = get_sb()
    try:
        uid_int = int(float(user_id))
    except:
        uid_int = user_id
    ts = datetime.now().isoformat()
    # delete old rows for this user
    sb.table(TABLE_NOTIFICATIONS).delete().eq("user_id", uid_int).execute()
    rows = [{
        "user_id":                uid_int,
        "generated_at":           ts,
        "segment_key":            segment_key,
        "notification_number":    n.get("notification_number"),
        "title":                  n.get("title",""),
        "body":                   n.get("body",""),
        "language":               n.get("language",""),
        "scheme_id":              n.get("scheme_id",""),
        "scheme_name":            n.get("scheme_name",""),
        "source_bucket":          n.get("source_bucket",""),
        "dependency_vector_used": n.get("dependency_vector_used",""),
        "attention_strategy":     n.get("attention_strategy",""),
        "relevance_rationale":    n.get("relevance_rationale",""),
    } for n in notifications]
    sb.table(TABLE_NOTIFICATIONS).insert(rows).execute()
    # Explicitly select back the inserted rows to guarantee we get the IDs
    res = sb.table(TABLE_NOTIFICATIONS).select("id, notification_number").eq("user_id", uid_int).order("id", desc=True).limit(len(notifications)).execute()
    return res.data or []

# ── PROMPT ────────────────────────────────────────────────────────────────────

BUCKET_PERSONAS = {
    "content_reader":   "Content Reader — focus on article discovery, informational hooks, awareness-first scheme recommendation",
    "high_converter":   "High Converter — action-first, CTA-heavy, minimal friction, speed-to-apply",
    "job_hunter":       "Job Hunter — employment, skilling, livelihood, income generation angle",
    "scheme_seeker":    "Scheme Seeker — direct welfare match, eligibility clarity, document readiness",
    "service_explorer": "Service Explorer — navigation, sub-services, utility access, government services angle",
}


def build_prompt(u: dict, schemes: list, n: int) -> str:
    catalogue  = "\n".join(f"  {s['id']} | {s['name']}" for s in schemes)
    bucket_ref = "\n".join(f"  {k} → {v}" for k,v in BUCKET_PERSONAS.items())

    return f"""You are the advanced hyper-personalization engine for A App's HPNS.
Map this citizen's signals to exactly ONE scheme and generate a high-conversion push notification.

════════════════════════════════════
NOTIFICATION {n} OF 5 — independent call. Fresh angle. Different scheme if possible.
════════════════════════════════════

[DEMOGRAPHIC]
User ID: {u.get("user_id","")} | Name: {u.get("name","")} | Age: {u.get("age","")} | Language: {u.get("language_code","en")}
Transliterate all names and proper nouns into the target language.

[FINANCIAL]
Personal Income: {u.get("personal_income","")} | Family Income: {u.get("family_income","")}
BPL: {u.get("bpl","")} | Earner Role: {u.get("earner_role","")}

[SOCIOPROFESSIONAL]
Occupation: {u.get("occupation","Unknown")} | Working Status: {u.get("working_status_id","")}

[APP TELEMETRY]
Primary Segment: {u.get("primary_category","")} | Tag: {u.get("notification_tag","")}
Engagement: {u.get("engagement_time_msec","")}ms | Clicks: {u.get("notification_click","")}
Scores → Content: {u.get("content_score","")} | Scheme: {u.get("scheme_score","")} | Job: {u.get("job_score","")} | Service: {u.get("service_score","")}

════════════════════════════════════
SCHEME CATALOGUE — pick exactly ONE:
{catalogue}
HARD GUARDRAIL: Use only exact id and name from list. Never hallucinate.

════════════════════════════════════
INTERPRETATION LOGIC:

DEPENDENCY VECTOR:
- Dependent Aspirational: personal income low/null + family income moderate/high → upskilling, loans
- Shared Household Distress: both incomes very low OR BPL=Yes → subsidies, cash transfers
- High Density Dilution: large household + low family income → per-member assistance
- Independent Pro: stable income → growth/investment schemes

ATTENTION STRATEGY:
- Fatigue Breakthrough: high engagement + high scores but clicks=0 → lead with name, undeniable value
- Swift Action Drive: Low Dwell + High Converter segment → compact, action-driven
- Educational Hook: default

LIFE STAGE:
- Age > 45 + physical job → health, insurance, pension
- Age < 28 → skilling, digital, growth

════════════════════════════════════
SOURCE BUCKET SELECTION:
Based on which angle best serves this user for THIS notification, choose the most appropriate bucket:
{bucket_ref}

You must pick whichever bucket creates the most relevant, compelling notification.
You are free to use any bucket — including the same one multiple times across the 5 calls if it's most relevant.

════════════════════════════════════
RULES:
- Write entirely in {u.get("language","English")} ({u.get("language_code","en")})
- Convert all names and personal things also to the given language explicitly and it should be strictly in the given language.
- Title: max 6 words. Body: max 15 words.

- Try and make the notification more catchy or interesting 
- use emojis and humour as much as you need to make it eye catching /funny / interesting
- Sound like a friend texting, not a government notice

OUTPUT — raw JSON only. No markdown. No preamble.

{{
  "notification_number"   : {n},
  "user_id"               : "{u.get("user_id","")}",
  "title"                 : "max 6 words",
  "body"                  : "max 15 words",
  "language"              : "{u.get("language_code","en")}",
  "scheme_id"             : "exact id from catalogue",
  "scheme_name"           : "exact name from catalogue",
  "source_bucket"         : "content_reader | high_converter | job_hunter | scheme_seeker | service_explorer",
  "dependency_vector_used": "Dependent Aspirational | Shared Household Distress | High Density Dilution | Independent Pro",
  "attention_strategy"    : "Fatigue Breakthrough | Swift Action Drive | Educational Hook",
  "relevance_rationale"   : "2-3 crisp bullet points explaining EXACTLY why this scheme and message fit this specific user. Start each bullet point with a '-'"
}}"""

# ── GEMINI ────────────────────────────────────────────────────────────────────

async def call_gemini(client: httpx.AsyncClient, prompt: str, n: int) -> dict:
    r = await client.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    r.raise_for_status()
    raw   = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:    return json.loads(clean)
    except: return {"notification_number": n, "raw": raw, "parse_error": True}

# ── FASTAPI ───────────────────────────────────────────────────────────────────

app = FastAPI(title="HPNS MVP v5")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def root(): return {"status": "ok"}


@app.get("/notify/{user_id}")
async def get_notifications(user_id: str):
    try:    raw_user = fetch_user(user_id)
    except ValueError as e: raise HTTPException(404, str(e))
    except RuntimeError as e: raise HTTPException(500, str(e))

    try:    schemes = fetch_schemes()
    except Exception as e: raise HTTPException(500, f"Schemes fetch failed: {e}")
    if not schemes: raise HTTPException(500, "No active schemes in 'schemes' table")

    profile = resolve(raw_user)
    segment = classify_segment(profile)

    async with httpx.AsyncClient() as client:
        notifications = list(await asyncio.gather(*[
            call_gemini(client, build_prompt(profile, schemes, n), n)
            for n in range(1, 6)
        ]))

    def get_scheme_url(scheme_name):
        initials = "".join(w[0] for w in scheme_name.split() if w.strip()).lower()
        return f"https://www.myscheme.gov.in/schemes/{initials}"

    for n in notifications:
        n["scheme_url"] = get_scheme_url(n.get("scheme_name", ""))

    try:
        inserted = save_to_supabase(user_id, segment["segment_key"], notifications)
        # Patch Supabase-assigned IDs back into notification dicts
        for notif in notifications:
            for row in inserted:
                if str(row.get("notification_number")) == str(notif.get("notification_number")):
                    notif["id"] = row.get("id")
                    break
    except Exception as e: print(f"[WARN] Supabase save failed: {e}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (OUTPUT_DIR / f"output_{user_id}_{ts}.json").write_text(
        json.dumps({"timestamp":ts,"user_id":user_id,"profile":profile,"notifications":notifications},
                   indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "user_id":       user_id,
        "generated_at":  datetime.now().isoformat(),
        "user_segment":  segment,
        "notifications": notifications,
        "user_profile": {
            "name":               profile.get("name",""),
            "age":                profile.get("age",""),
            "location":           profile.get("district",""),
            "language":           profile.get("language",""),
            "personal_income":    profile.get("personal_income",""),
            "family_income":      profile.get("family_income",""),
            "earner_role":        profile.get("earner_role",""),
            "bpl":                profile.get("bpl",""),
            "occupation_id":      profile.get("occupation_id",""),
            "working_status_id":  profile.get("working_status_id",""),
            "primary_category":   profile.get("primary_category",""),
            "notification_tag":   profile.get("notification_tag",""),
            "notification_clicks":profile.get("notification_click",""),
            "engagement_ms":      profile.get("engagement_time_msec",""),
            "content_score":      profile.get("content_score",""),
            "scheme_score":       profile.get("scheme_score",""),
            "job_score":          profile.get("job_score",""),
            "service_score":      profile.get("service_score",""),
        },
    }


@app.get("/dashboard")
def dashboard():
    try:
        sb  = get_sb()
        res = sb.table(TABLE_NOTIFICATIONS).select("*").order("generated_at", desc=True).execute()
        rows = res.data or []
        
        # Fetch user names for these notifications
        u_ids = list(set(r["user_id"] for r in rows if r.get("user_id")))
        user_names = {}
        if u_ids:
            users_res = sb.table(TABLE_USERS).select("user_id, name").in_("user_id", u_ids).execute()
            user_names = {str(u["user_id"]): u.get("name", "Unknown") for u in users_res.data}
            
    except Exception as e:
        raise HTTPException(500, str(e))

    grouped = {}
    for row in rows:
        uid = str(row["user_id"])
        if uid not in grouped:
            grouped[uid] = {
                "user_id":       uid,
                "name":          user_names.get(uid, "Unknown"),
                "segment_key":   row.get("segment_key",""),
                "generated_at":  row.get("generated_at",""),
                "notifications": [],
            }
        grouped[uid]["notifications"].append({
            "notification_number":   row.get("notification_number"),
            "title":                 row.get("title",""),
            "body":                  row.get("body",""),
            "scheme_id":             row.get("scheme_id",""),
            "scheme_name":           row.get("scheme_name",""),
            "scheme_url":            row.get("scheme_url",""),
            "source_bucket":         row.get("source_bucket",""),
            "dependency_vector_used":row.get("dependency_vector_used",""),
            "attention_strategy":    row.get("attention_strategy",""),
            "language":              row.get("language",""),
            "relevance_rationale":   row.get("relevance_rationale",""),
            "user_id":               row.get("user_id",""),
            "id":                    row.get("id"),
            "campaign_image":        row.get("campaign_image"),
        })
    return list(grouped.values())

@app.delete("/notification/{id}")
def delete_notification(id: int):
    try:
        sb = get_sb()
        res = sb.table(TABLE_NOTIFICATIONS).delete().eq("id", id).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── IMAGE GENERATION ──────────────────────────────────────────────────────────

IMAGEN_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/imagen-3.0-generate-002:predict"
)

@app.post("/generate-image")
async def generate_image(payload: dict):
    """Generate a personalized promotional image for a government scheme."""
    scheme_name   = payload.get("scheme_name", "")
    title         = payload.get("title", "")
    body          = payload.get("body", "")
    rationale     = payload.get("relevance_rationale", "")
    age           = payload.get("age", "")
    occupation    = payload.get("occupation", "")
    segment       = payload.get("segment", "")
    language      = payload.get("language", "English")

    # Map segment to visual theme
    theme_map = {
        "job_hunter":       "employment success, job interview, workplace, career certificate",
        "scheme_seeker":    "government scheme benefits, financial security, community support",
        "content_reader":   "education, reading, knowledge, digital access",
        "high_converter":   "business growth, entrepreneurship, small business owner",
        "service_explorer": "skill development, training center, certification, learning",
    }
    visual_theme = theme_map.get(segment, "positive life improvement, family wellbeing, financial security")

    prompt = f"""High-quality digital promotional poster for Axis My India government scheme campaign.

Scene: {visual_theme}. Show a realistic Indian person aged around {age or '30'}, {occupation or 'working professional'}, experiencing a positive life outcome after benefiting from a government scheme.

Scheme: {scheme_name}
Message: {title} — {body}

Design requirements:
- Realistic Indian people, warm and aspirational scene
- Professional advertising quality, modern clean layout
- Warm trustworthy colors, government-campaign style
- Show confidence, hope, achievement and family wellbeing
- Leave clean space at bottom for text overlay
- Include subtle "Axis My India" branding element in corner
- No political imagery, no government leader photos
- No excessive text in image
- High resolution digital poster style, 16:9 or portrait format

Focus on the positive future: what life looks like AFTER benefiting from this scheme."""

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                IMAGEN_URL,
                headers={"x-goog-api-key": GEMINI_KEY},
                json={
                    "instances": [{"prompt": prompt}],
                    "parameters": {"sampleCount": 1, "aspectRatio": "9:16"}
                },
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            predictions = data.get("predictions", [])
            if predictions and "bytesBase64Encoded" in predictions[0]:
                return {"image_b64": predictions[0]["bytesBase64Encoded"]}
            return {"error": "No image returned", "raw": data}
        except Exception as e:
            raise HTTPException(500, f"Image generation failed: {e}")

