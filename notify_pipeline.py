"""
User Notification Prompt Pipeline (MVP)
========================================
Gemini's job here: given user scores + your campaign idea,
write the BEST PROMPT you should later feed into a notification model.

Output saved to: outputs/output_<user_id>_<timestamp>.json

Run:
python notify_pipeline.py
"""

import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


# ─────────────────────────────────────────────
# LOAD .env
# ─────────────────────────────────────────────

load_dotenv()


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

EXCEL_FILE = r"C:\Users\vivaa\OneDrive\Desktop\ZEEX HPNS\final_table.csv"

USER_ID = 208135

CAMPAIGN_IDEA = """
I want to send this user a push notification about government schemes
they qualify for but haven't explored yet.
The notification should feel personal based on their scores.
Keep it short and motivating.
"""

OUTPUT_DIR = Path("outputs")


# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

SEP = "─" * 58


# Load Gemini key from .env
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_KEY:
    sys.exit(
        "\n[ERROR] GEMINI_API_KEY not found in .env file\n"
    )


def load_user(file_path, user_id):

    # Auto-detect CSV vs Excel
    if file_path.lower().endswith(".csv"):
        df = pd.read_csv(file_path, dtype=str)

    elif file_path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(file_path, dtype=str)

    else:
        sys.exit(
            "[ERROR] Unsupported file type. Use CSV or Excel."
        )

    uid_col = next(
        (
            c
            for c in df.columns
            if "user" in c.lower()
            and "id" in c.lower()
        ),
        df.columns[0],
    )

    match = df[
        df[uid_col]
        .astype(str)
        .str.strip()
        == str(user_id).strip()
    ]

    if match.empty:
        sys.exit(
            f"[ERROR] user_id '{user_id}' not found."
        )

    return match.iloc[0].to_dict()


def build_meta_prompt(user: dict, idea: str) -> str:

    def safe_float(v):
        try:
            return float(v)
        except:
            return 0

    scores = {
        "content": safe_float(
            user.get("content_score", 0)
        ),

        "scheme": safe_float(
            user.get("scheme_score", 0)
        ),

        "job": safe_float(
            user.get("job_score", 0)
        ),

        "service": safe_float(
            user.get("service_score", 0)
        ),

        "conversion": safe_float(
            user.get("conversion_score", 0)
        ),
    }

    dominant = max(
        scores,
        key=scores.get
    )

    routing = {

        "content":
        """
Content Reader

Signals:
- article clicks
- article views
- engagement time normalized:
eng_norm=(user-min)/(max-min)*10

Strategy:
Convert information interest into action.
Recommend guides, awareness content,
explainers, eligibility content.
Avoid aggressive CTA.
""",

        "scheme":
        """
Scheme Seeker

Signals:
- scheme clicks
- category exploration
- profile completion intent

Strategy:
Recommend government schemes.
Highlight eligibility and benefits.
Use direct CTA.
""",

        "job":
        """
Job Hunter

Signals:
- job card clicks
- job option exploration

Strategy:
Recommend jobs, hiring,
employment schemes,
upskilling.
Urgency is acceptable.
""",

        "service":
        """
Service Explorer

Signals:
- service clicks
- sub-service usage
- deep navigation

Strategy:
Recommend government services.
Push completion.
Reduce friction.
""",

        "conversion":
        """
High Converter

Signals:
- enquiry completion
- submission completion
- contact actions

Strategy:
Push strongest CTA.
Prioritize conversion.
User likely to act.
"""
    }

    user_block = "\n".join(
        f"{k}: {v}"
        for k, v in user.items()
    )

    return f"""
You are a senior lifecycle marketing strategist
for a government services platform.

Generate ONLY a prompt.

USER DATA:
{user_block}

CAMPAIGN:
{idea.strip()}

SEGMENT DETECTED:
{dominant}

SEGMENT RULE:
{routing[dominant]}

Decision logic:

1.
Choose dominant segment
using scores.

2.
Use conversion_score
as secondary signal.

3.
If conversion_score > 0:
increase CTA strength.

4.
If notification_tag =
Not Responsive:
reduce pressure.
increase personalization.

5.
Generate ONE push notification prompt.

Requirements:
- personalized
- short
- actionable
- maximize click rate
- fit detected segment
- no hallucinated benefits
- government-safe language

Return only prompt.
"""

def call_gemini(prompt: str, api_key: str) -> str:

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    try:

        resp = requests.post(
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )

        if not resp.ok:

            print("\n[GEMINI ERROR]")
            print(resp.text)

            resp.raise_for_status()

        data = resp.json()

        return (
            data["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
            .strip()
        )

    except Exception as e:

        try:
            print("\n[FULL RESPONSE]")
            print(
                json.dumps(
                    resp.json(),
                    indent=2
                )
            )
        except:
            pass

        sys.exit(
            f"\n[ERROR] {str(e)}"
        )

def save_output(
    user_id,
    user_data,
    campaign_idea,
    meta_prompt,
    generated_prompt,
):

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    ts = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    out_file = (
        OUTPUT_DIR
        / f"output_{user_id}_{ts}.json"
    )

    record = {
        "timestamp": ts,
        "user_id": user_id,
        "user_data": user_data,
        "campaign_idea": campaign_idea,
        "meta_prompt_sent": meta_prompt,
        "generated_prompt": generated_prompt,
    }

    out_file.write_text(
        json.dumps(
            record,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return out_file


def section(title, body):

    print(
        f"\n{SEP}\n {title}\n{SEP}"
    )

    print(body)


def main():

    print("\n" + "═" * 58)

    print(
        " NOTIFICATION PROMPT PIPELINE"
    )

    print("═" * 58)

    print(
        f" File    : {EXCEL_FILE}"
    )

    print(
        f" User ID : {USER_ID}"
    )

    user = load_user(
        EXCEL_FILE,
        USER_ID,
    )

    section(
        "USER SCORES",
        "\n".join(
            f"{k:<35} {v}"
            for k, v in user.items()
        ),
    )

    section(
        "CAMPAIGN IDEA",
        CAMPAIGN_IDEA,
    )

    meta_prompt = build_meta_prompt(
        user,
        CAMPAIGN_IDEA,
    )

    print(
        "\nCalling Gemini...",
        end=" ",
        flush=True,
    )

    generated_prompt = call_gemini(
        meta_prompt,
        GEMINI_KEY,
    )

    print("done.")

    section(
        "GENERATED PROMPT",
        generated_prompt,
    )

    out = save_output(
        USER_ID,
        user,
        CAMPAIGN_IDEA,
        meta_prompt,
        generated_prompt,
    )

    print(
        f"\nOutput saved → {out}"
    )


if __name__ == "__main__":
    main()