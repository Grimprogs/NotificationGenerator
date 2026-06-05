"""
Notification Pipeline v3
=========================
- Reads metadata CSV + scores CSV
- Merges by user_id
- Makes 5 INDEPENDENT Gemini calls
- Each call sees only raw user data — Gemini decides everything
- Saves all 5 to JSON + prints to terminal

Setup:
  pip install pandas openpyxl requests python-dotenv

  Mac/Linux  : export GEMINI_API_KEY=AIza...
  PowerShell : $env:GEMINI_API_KEY="AIza..."

Edit CONFIG below, then run:
  python notify_pipeline.py
"""

import os
import sys
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv() 
# ==================================================
# CONFIG — only edit this section
# ==================================================

METADATA_FILE = r"C:\Users\vivaa\OneDrive\Desktop\ZEEX HPNS\Event_details_and__clicksgoogle_analytics_202606031511.csv"
SCORE_FILE    = r"C:\Users\vivaa\OneDrive\Desktop\ZEEX HPNS\final_dataset_enriched.csv"

USER_ID    = 208135
OUTPUT_DIR = Path("outputs_v3")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

# ==================================================
# ID → LABEL MAPS  (extend to match your actual IDs)
# ==================================================

DISTRICT_MAP = {
    "1": "Mumbai",     "2": "Pune",       "3": "Nagpur",
    "4": "Nashik",     "5": "Aurangabad", "6": "Thane",
    "7": "Kolhapur",   "8": "Solapur",
}

PERSONAL_INCOME_MAP = {
    "1": "No income",          "2": "Below 5000 per month",
    "3": "5000-10000 per month","4": "10000-25000 per month",
    "5": "25000-50000 per month","6": "Above 50000 per month",
}

FAMILY_INCOME_MAP = {
    "1": "Below 1 lakh per year", "2": "1 to 3 lakh per year",
    "3": "3 to 6 lakh per year",  "4": "6 to 10 lakh per year",
    "5": "Above 10 lakh per year",
}

FAMILY_TYPE_MAP = {
    "1": "Sole Earner",   # carries entire family
    "2": "Co Earner",     # shares the load
    "3": "Partial Earner",# contributes but not main earner
}

BPL_MAP  = {"0": "No",  "1": "Yes"}

LANG_MAP = {
    "en": "English", "mr": "Marathi",
    "hi": "Hindi",   "pa": "Punjabi", "ml": "Malayalam",
}

SCHEME_CATALOGUE = [
    "PMAY-001", "PMJAY-002", "PMKISAN-003", "NREGA-004",
    "PMJDY-005", "SKILL-IND-006", "STARTUP-IND-007",
    "NSAP-008",  "SCHOLARSHIP-009", "UJJWALA-010",
]

# ==================================================
# ENV KEY
# ==================================================

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not GEMINI_KEY:
    sys.exit(
        "[ERROR] GEMINI_API_KEY not set.\n"
        "  Mac/Linux  : export GEMINI_API_KEY=AIza...\n"
        "  PowerShell : $env:GEMINI_API_KEY=\"AIza...\"\n"
    )

# ==================================================
# FILE + DATA HELPERS
# ==================================================

def read_file(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"[ERROR] File not found: {path}")
    return pd.read_csv(path, dtype=str) if path.endswith(".csv") else pd.read_excel(path, dtype=str)


def get_rows(df, uid, label):
    col = "user_id"
    if col not in df.columns:
        sys.exit(f"[ERROR] 'user_id' missing in {label}. Found: {df.columns.tolist()}")
    df[col] = df[col].astype(str).str.strip()
    rows = df[df[col] == str(uid).strip()]
    if rows.empty:
        sys.exit(f"[ERROR] user_id={uid} not found in {label}.\nSample IDs: {df[col].head(10).tolist()}")
    return rows


def aggregate(df):
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


def resolve(user: dict) -> dict:
    """Replace all ID fields with human-readable labels."""
    u = dict(user)
    u["district"]              = DISTRICT_MAP.get(str(u.get("district_id","")), u.get("district_id","Unknown"))
    u["personal_income"]       = PERSONAL_INCOME_MAP.get(str(u.get("personal_income_id","")), "Unknown")
    u["family_income"]         = FAMILY_INCOME_MAP.get(str(u.get("family_income_id","")), "Unknown")
    u["earner_role"]           = FAMILY_TYPE_MAP.get(str(u.get("family_type_id","")), "Unknown")
    u["bpl"]                   = BPL_MAP.get(str(u.get("bpl_category","0")), "No")
    u["language"]              = LANG_MAP.get(str(u.get("preferred_language","en")).strip(), "English")
    u["language_code"]         = str(u.get("preferred_language","en")).strip()
    u["available_scheme_ids"]  = ", ".join(SCHEME_CATALOGUE)
    return u

# ==================================================
# PROMPT  — pure user data, Gemini decides everything
# ==================================================

def build_prompt(u: dict, notification_number: int) -> str:
    return f"""
You are a warm, helpful friend who knows about government
schemes and wants to genuinely help citizens improve their lives.

You are NOT a government system. You are NOT a bot.
You write like a real person who cares — simple, warm,
direct, and human.

════════════════════════════════════════
THIS IS NOTIFICATION {notification_number} OF 5
Each of the 5 notifications for this user is generated
independently. Make this one feel completely fresh and
distinct — different angle, different hook, different scheme
if possible. Do not repeat what the other notifications
might say. Decide everything yourself based only on the
user data below.
════════════════════════════════════════

════════════════════════════════════════
USER DATA  (this is everything you know)
════════════════════════════════════════

user_id              : {u.get("user_id", "")}
name                 : {u.get("name", "")}
age                  : {u.get("age", "")}
location             : {u.get("district", "")}
language             : {u.get("language", "")} ({u.get("language_code","en")})

personal income      : {u.get("personal_income", "")}
family income        : {u.get("family_income", "")}
earner role          : {u.get("earner_role", "")}
below poverty line   : {u.get("bpl", "")}

primary app behavior : {u.get("primary_category", "")}
notification history : {u.get("notification_tag", "")}
notification clicks  : {u.get("notification_click", "")}
engagement time (ms) : {u.get("engagement_time_msec", "")}

content_score        : {u.get("content_score", "")}
scheme_score         : {u.get("scheme_score", "")}
job_score            : {u.get("job_score", "")}
service_score        : {u.get("service_score", "")}

mobile               : {u.get("mobile_no", "")}

available scheme IDs : {u.get("available_scheme_ids", "")}

════════════════════════════════════════
YOUR TASK
════════════════════════════════════════

Read all the data above carefully.
Understand this person's real life situation.
Decide what would genuinely help them right now.
Choose one scheme or service from available scheme IDs only.
Write one push notification that feels personally written
for them — not templated, not bureaucratic.

Rules:
- Write entirely in {u.get("language", "English")}
- Title: maximum 6 words
- Body: maximum 15 words
- No emojis, no hashtags, no rupee symbol in title
- Do not invent schemes outside the available list
- Sound like a friend, not a government notice

════════════════════════════════════════
OUTPUT — strict JSON only
No explanation. No markdown. No extra text.
════════════════════════════════════════

{{
  "notification_number"   : {notification_number},
  "user_id"               : "{u.get("user_id","")}",
  "title"                 : "max 6 words",
  "body"                  : "max 15 words",
  "language"              : "{u.get("language_code","en")}",
  "scheme_or_service_id"  : "one ID from available list",
  "tone_used"             : "e.g. Relieving / Encouraging / Urgent / Aspirational / Curiosity",
  "human_check"           : "yes or no — would a real friend send this?",
  "relevance_rationale"   : "one sentence — why this scheme for this person right now",
  "data_signals_used"     : "list the specific fields that drove your decision"
}}
"""

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
    clean = raw.strip()
    for fence in ("```json", "```"):
        clean = clean.removeprefix(fence)
    clean = clean.removesuffix("```").strip()
    return json.loads(clean)

# ==================================================
# SAVE
# ==================================================

def save(user_id, profile, runs, notifications):
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"output_{user_id}_{ts}.json"
    record = {
        "timestamp":     ts,
        "user_id":       user_id,
        "profile":       profile,
        "runs":          runs,        # each prompt + raw response
        "notifications": notifications,
    }
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False),encoding="utf-8"
)
    return out

# ==================================================
# PRINT
# ==================================================

W = 68
SEP = "─" * W

def section(title, body=""):
    print(f"\n{SEP}\n  {title}\n{SEP}")
    if body:
        print(body)

def print_notif(n):
    num = n.get("notification_number", "?")
    print(f"\n  ── Notification {num} {'─'*45}")
    print(f"  Tone     : {n.get('tone_used','')}")
    print(f"  Scheme   : {n.get('scheme_or_service_id','')}")
    print(f"  TITLE    : {n.get('title','')}")
    print(f"  BODY     : {n.get('body','')}")
    print(f"  Signals  : {n.get('data_signals_used','')}")
    print(f"  Why      : {n.get('relevance_rationale','')}")
    print(f"  Friend?  : {n.get('human_check','')}")

# ==================================================
# MAIN
# ==================================================

def main():
    print(f"\n{'═'*W}")
    print("  NOTIFICATION PIPELINE  v3")
    print(f"{'═'*W}")
    print(f"  User ID  : {USER_ID}")

    # Load + merge
    meta_df   = read_file(METADATA_FILE)
    score_df  = read_file(SCORE_FILE)
    meta_user = aggregate(get_rows(meta_df,  USER_ID, "metadata"))
    score_user= aggregate(get_rows(score_df, USER_ID, "scores"))
    user      = {**meta_user, **score_user}
    profile   = resolve(user)

    # Print profile
    section("USER PROFILE", "\n".join(f"  {k:<30} {v}" for k, v in profile.items()))

    # 5 independent calls
    notifications = []
    runs          = []

    section("GENERATING 5 INDEPENDENT NOTIFICATIONS")

    for i in range(1, 6):
        print(f"\n  [{i}/5] Calling Gemini...", end=" ", flush=True)
        prompt = build_prompt(profile, i)
        raw    = call_gemini(prompt)
        print("done.")

        try:
            notif = parse_json(raw)
        except json.JSONDecodeError:
            print(f"  [WARN] Could not parse JSON for notification {i}. Raw saved.")
            notif = {"notification_number": i, "raw": raw}

        notifications.append(notif)
        runs.append({"notification_number": i, "prompt": prompt, "raw_response": raw})

        print_notif(notif)

    # Save
    out = save(USER_ID, profile, runs, notifications)

    print(f"\n{'═'*W}")
    print(f"  All 5 saved → {out}")
    print(f"{'═'*W}\n")


if __name__ == "__main__":
    main()
