"""
Notification MVP — FastAPI Backend
====================================
Runs locally or on Render.com

Local run:
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8000

Render:
  Build command : pip install -r requirements.txt
  Start command : uvicorn main:app --host 0.0.0.0 --port 10000
"""

import os, sys, json, asyncio
from pathlib import Path
from datetime import datetime

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# CONFIG  (set these in .env or Render env vars)
# ──────────────────────────────────────────────

METADATA_FILE = os.getenv("METADATA_FILE", r"C:\Users\vivaa\OneDrive\Desktop\ZEEX HPNS\metadata.csv")
SCORE_FILE    = os.getenv("SCORE_FILE",    r"C:\Users\vivaa\OneDrive\Desktop\ZEEX HPNS\final_table.csv")
GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL    = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

if not GEMINI_KEY:
    print("[WARN] GEMINI_API_KEY not set — requests will fail")

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
# DATA HELPERS
# ──────────────────────────────────────────────

def read_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path, dtype=str) if path.endswith(".csv") else pd.read_excel(path, dtype=str)


def get_rows(df: pd.DataFrame, uid: str, label: str) -> pd.DataFrame:
    col = "user_id"
    if col not in df.columns:
        raise ValueError(f"'user_id' column missing in {label}")
    df[col] = df[col].astype(str).str.strip()
    rows = df[df[col] == uid.strip()]
    if rows.empty:
        raise ValueError(f"user_id={uid} not found in {label}")
    return rows


def aggregate(df: pd.DataFrame) -> dict:
    out = {}
    for c in df.columns:
        vals = df[c].dropna().tolist()
        if not vals:
            continue
        try:
            nums = [float(v) for v in vals]
            out[c] = round(sum(nums) / len(nums), 2)
        except:
            out[c] = max(set(vals), key=vals.count)
    return out


def resolve(u: dict) -> dict:
    p = dict(u)
    p["district"]             = DISTRICT_MAP.get(str(p.get("district_id","")), p.get("district_id","Unknown"))
    p["personal_income"]      = PERSONAL_INCOME_MAP.get(str(p.get("personal_income_id","")), "Unknown")
    p["family_income"]        = FAMILY_INCOME_MAP.get(str(p.get("family_income_id","")), "Unknown")
    p["earner_role"]          = FAMILY_TYPE_MAP.get(str(p.get("family_type_id","")), "Unknown")
    p["bpl"]                  = BPL_MAP.get(str(p.get("bpl_category","0")), "No")
    p["language"]             = LANG_MAP.get(str(p.get("preferred_language","en")).strip(), "English")
    p["language_code"]        = str(p.get("preferred_language","en")).strip()
    p["available_scheme_ids"] = ", ".join(SCHEME_CATALOGUE)
    return p

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
below, create a completely unique notification with a
fresh angle, different scheme if possible, different hook.
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
# GEMINI ASYNC CALL
# ──────────────────────────────────────────────

async def call_gemini_async(client: httpx.AsyncClient, prompt: str, n: int) -> dict:
    r = await client.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    # strip markdown fences if any
    clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"notification_number": n, "raw": raw, "parse_error": True}

# ──────────────────────────────────────────────
# FASTAPI APP
# ──────────────────────────────────────────────

app = FastAPI(title="Notification MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten after deploy
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Notification MVP backend running"}


@app.get("/notify/{user_id}")
async def get_notifications(user_id: str):
    try:
        meta_df  = read_csv(METADATA_FILE)
        score_df = read_csv(SCORE_FILE)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        meta_user  = aggregate(get_rows(meta_df,  user_id, "metadata"))
        score_user = aggregate(get_rows(score_df, user_id, "scores"))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    user    = {**meta_user, **score_user}
    profile = resolve(user)

    # fire 5 calls in parallel
    async with httpx.AsyncClient() as client:
        tasks = [
            call_gemini_async(client, build_prompt(profile, n), n)
            for n in range(1, 6)
        ]
        notifications = await asyncio.gather(*tasks)

    # ── RESPONSE FORMAT ──────────────────────────────────────
    # notifications first, then metadata below
    return {
        "user_id"       : user_id,
        "generated_at"  : datetime.now().isoformat(),
        "notifications" : list(notifications),          # 5 items, top
        "user_profile"  : {                             # metadata below
            "name"              : profile.get("name",""),
            "age"               : profile.get("age",""),
            "location"          : profile.get("district",""),
            "language"          : profile.get("language",""),
            "personal_income"   : profile.get("personal_income",""),
            "family_income"     : profile.get("family_income",""),
            "earner_role"       : profile.get("earner_role",""),
            "bpl"               : profile.get("bpl",""),
            "primary_category"  : profile.get("primary_category",""),
            "notification_tag"  : profile.get("notification_tag",""),
            "notification_clicks": profile.get("notification_click",""),
            "engagement_ms"     : profile.get("engagement_time_msec",""),
            "content_score"     : profile.get("content_score",""),
            "scheme_score"      : profile.get("scheme_score",""),
            "job_score"         : profile.get("job_score",""),
            "service_score"     : profile.get("service_score",""),
        },
    }
