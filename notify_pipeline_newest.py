"""
Notification Pipeline v4
=========================
- Single Excel/CSV for users + single Excel/CSV for schemes
- New advanced prompt (dependency vector, attention strategy)
- 5 independent Gemini calls per user
- Saves to JSON + prints to terminal

Setup:
  pip install pandas openpyxl requests python-dotenv

  Mac/Linux  : export GEMINI_API_KEY=AIza...
  PowerShell : $env:GEMINI_API_KEY="AIza..."

Edit CONFIG below, then:
  python notify_pipeline_v4.py
"""

import os, sys, json, requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ==================================================
# CONFIG — edit these 3 lines only
# ==================================================

USERS_FILE   = r"C:\path\to\your\users.xlsx"
SCHEMES_FILE = r"C:\path\to\your\schemes.xlsx"
USER_ID      = 208135

OUTPUT_DIR   = Path("outputs_v4")
GEMINI_URL   = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

# ==================================================
# ID → LABEL MAPS
# ==================================================

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
# ==================================================
# GEMINI KEY
# ==================================================

GEMINI_KEY = os.environ.get("GEMINI_API_KEY","").strip()
if not GEMINI_KEY:
    sys.exit("[ERROR] GEMINI_API_KEY not set.")

# ==================================================
# FILE HELPERS
# ==================================================

def read_file(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"[ERROR] Not found: {path}")
    return pd.read_csv(path, dtype=str) if str(path).endswith(".csv") else pd.read_excel(path, dtype=str)


def get_user_row(df, uid):
    df["user_id"] = df["user_id"].astype(str).str.strip()
    rows = df[df["user_id"] == str(uid).strip()]
    if rows.empty:
        sys.exit(f"[ERROR] user_id={uid} not found.\nSample IDs: {df['user_id'].head(5).tolist()}")
    return rows.iloc[0].to_dict()


def load_schemes(df):
    """Return list of {id, name} for active schemes only."""
    active_col = next((c for c in df.columns if "active" in c.lower()), None)
    if active_col:
        df = df[df[active_col].astype(str).str.strip().isin(["1","true","True","TRUE","yes"])]
    return [{"id": str(r["id"]).strip(), "name": str(r["name"]).strip()}
            for _, r in df.iterrows() if r.get("id") and r.get("name")]

# ==================================================
# PROFILE RESOLVER
# ==================================================

def resolve(u: dict) -> dict:
    p = {k: str(v).strip() if v is not None and str(v) != "nan" else "" for k, v in u.items()}
    p["district"]        = DISTRICT_MAP.get(p.get("district_id",""), p.get("district_id","Unknown"))
    p["personal_income"] = PERSONAL_INCOME_MAP.get(p.get("personal_income_id",""), "Unknown")
    p["family_income"]   = FAMILY_INCOME_MAP.get(p.get("family_income_id",""), "Unknown")
    p["earner_role"]     = FAMILY_TYPE_MAP.get(p.get("family_type_id",""), "Unknown")
    p["bpl"]             = BPL_MAP.get(p.get("bpl_category","0"), "No")
    p["language"]        = LANG_MAP.get(p.get("preferred_language","en"), "English")
    p["language_code"]   = p.get("preferred_language","en")
    return p

# ==================================================
# PROMPT
# ==================================================

def build_prompt(u: dict, schemes: list, n: int) -> str:
    catalogue = "\n".join(f"  {s['id']} | {s['name']}" for s in schemes)
    return f"""You are the advanced hyper-personalization engine for A App's Hyper-Personalized Notification System (HPNS). Your objective is to map a citizen's multi-dimensional demographic and behavioral matrix to exactly ONE scheme from the approved master catalog, outputting a high-conversion push notification payload.

You are NOT a rigid bureaucratic portal. You write like a trusted, wise, and supportive friend sending an empathetic WhatsApp message—warm, conversational, practical, and direct.

════════════════════════════════════════
THIS IS NOTIFICATION {n} OF 5 — fully independent call.
Create a completely unique angle. Different scheme if possible.
════════════════════════════════════════

1. SIGNAL INPUT MATRIX

[DEMOGRAPHIC]
User ID: {u.get("user_id","")} | Name: {u.get("name","")} | Age: {u.get("age","")} | Language: {u.get("language_code","en")}

[FINANCIAL & DEPENDENCY]
Personal Income: {u.get("personal_income","")}
Family Income: {u.get("family_income","")}
BPL: {u.get("bpl","")} | Earner Role: {u.get("earner_role","")}

[SOCIOPROFESSIONAL]
Occupation ID: {u.get("occupation_id","")} | Working Status ID: {u.get("working_status_id","")}

[APP TELEMETRY]
Segment: {u.get("primary_category","")} | Tag: {u.get("notification_tag","")}
Engagement: {u.get("engagement_time_msec","")} ms | Clicks: {u.get("notification_click","")}
Content: {u.get("content_score","")} | Scheme: {u.get("scheme_score","")} | Job: {u.get("job_score","")} | Service: {u.get("service_score","")}

2. MASTER CATALOGUE — pick exactly ONE:
{catalogue}
HARD GUARDRAIL: Only use exact id and name from above. Never hallucinate.

3. INTERPRETATION LOGIC

STEP 1 — DEPENDENCY VECTOR:
- Dependent Aspirational: personal income low/null + family income moderate/high → upskilling, loans
- Shared Household Distress: both incomes low OR BPL=Yes → subsidies, food, cash transfers
- High Density Dilution: large household + low income → per-member scale assistance
- Independent Pro: stable income → growth/investment schemes

STEP 2 — ATTENTION STRATEGY:
- Fatigue Breakthrough: high engagement + high scores but clicks=0 → lead with name, undeniable value
- Swift Action Drive: low dwell + High Converter → compact, action-driven
- Educational Hook: default

STEP 3 — LIFE STAGE:
- Age > 45 + physical occupation → health, insurance, pension
- Age < 28 → skill, digital, growth

4. RULES
- Write entirely in {u.get("language","English")}
- Title: max 6 words. Body: max 15 words.
- No emojis, hashtags, rupee symbol in title
- Sound like a friend, not government notice

OUTPUT — raw JSON only. No markdown. No preamble.

{{
  "notification_number"    : {n},
  "user_id"                : "{u.get("user_id","")}",
  "title"                  : "max 6 words in {u.get("language","English")}",
  "body"                   : "max 15 words in {u.get("language","English")}",
  "language"               : "{u.get("language_code","en")}",
  "scheme_id"              : "exact id from catalogue",
  "scheme_name"            : "exact name from catalogue",
  "dependency_vector_used" : "Dependent Aspirational | Shared Household Distress | High Density Dilution | Independent Pro",
  "attention_strategy"     : "Fatigue Breakthrough | Swift Action Drive | Educational Hook",
  "relevance_rationale"    : "one sentence linking dependency gap, attention behavior, age, occupation to scheme"
}}"""

# ==================================================
# GEMINI CALL
# ==================================================

def call_gemini(prompt: str) -> str:
    r = requests.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def parse_json(raw: str) -> dict:
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(clean)

# ==================================================
# SAVE + PRINT
# ==================================================

def save(user_id, profile, notifications):
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"output_{user_id}_{ts}.json"
    out.write_text(json.dumps({
        "timestamp": ts, "user_id": user_id,
        "profile": profile, "notifications": notifications,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return out

SEP = "─" * 66

def print_notif(n):
    print(f"\n  ── Notification {n.get('notification_number','?')} {'─'*43}")
    print(f"  Scheme   : {n.get('scheme_name','')} [{n.get('scheme_id','')}]")
    print(f"  TITLE    : {n.get('title','')}")
    print(f"  BODY     : {n.get('body','')}")
    print(f"  Vector   : {n.get('dependency_vector_used','')}")
    print(f"  Strategy : {n.get('attention_strategy','')}")
    print(f"  Why      : {n.get('relevance_rationale','')}")

# ==================================================
# MAIN
# ==================================================

def main():
    print(f"\n{'═'*66}")
    print("  NOTIFICATION PIPELINE v4")
    print(f"{'═'*66}")
    print(f"  User ID : {USER_ID}")

    # load data
    users_df   = read_file(USERS_FILE)
    schemes_df = read_file(SCHEMES_FILE)

    user    = get_user_row(users_df, USER_ID)
    schemes = load_schemes(schemes_df)
    profile = resolve(user)

    if not schemes:
        sys.exit("[ERROR] No active schemes found in schemes file.")

    print(f"  Schemes loaded: {len(schemes)}")
    print(f"\n{SEP}")
    print("  USER PROFILE")
    print(SEP)
    for k, v in profile.items():
        if v:
            print(f"  {k:<30} {v}")

    print(f"\n{SEP}")
    print("  GENERATING 5 NOTIFICATIONS")
    print(SEP)

    notifications = []
    runs          = []

    for i in range(1, 6):
        print(f"\n  [{i}/5] Calling Gemini...", end=" ", flush=True)
        prompt = build_prompt(profile, schemes, i)
        raw    = call_gemini(prompt)
        print("done.")

        try:
            notif = parse_json(raw)
        except Exception:
            print(f"  [WARN] JSON parse failed for {i}")
            notif = {"notification_number": i, "raw": raw, "parse_error": True}

        notifications.append(notif)
        runs.append({"notification_number": i, "prompt": prompt, "raw_response": raw})
        print_notif(notif)

    out = save(USER_ID, profile, runs)
    print(f"\n{'═'*66}")
    print(f"  Saved → {out}")
    print(f"{'═'*66}\n")


if __name__ == "__main__":
    main()
