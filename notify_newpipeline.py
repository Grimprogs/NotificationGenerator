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
# CONFIG
# ==================================================

METADATA_FILE = (
r"C:\Users\vivaa\OneDrive\Desktop\ZEEX HPNS\Event_details_and__clicksgoogle_analytics_202606031511.csv"
)

SCORE_FILE = (
r"C:\Users\vivaa\OneDrive\Desktop\ZEEX HPNS\final_table.csv"
)

USER_ID = 208135

OUTPUT_DIR = Path("outputs")

CAMPAIGN_IDEA = """
Send one personalized government notification.
"""

GEMINI_URL = (
"https://generativelanguage.googleapis.com/v1beta/"
"models/gemini-2.5-flash:generateContent"
)

GEMINI_KEY = os.getenv(
"GEMINI_API_KEY"
)

if not GEMINI_KEY:

    sys.exit(
        "[ERROR] Missing GEMINI_API_KEY"
    )


# ==================================================
# HELPERS
# ==================================================

def read_file(path):

    if path.endswith(".csv"):
        return pd.read_csv(
            path,
            dtype=str
        )

    return pd.read_excel(
        path,
        dtype=str
    )


def aggregate(df):

    result = {}

    for c in df.columns:

        vals = (
            df[c]
            .dropna()
            .tolist()
        )

        if not vals:
            continue

        try:

            nums = [
                float(v)
                for v in vals
            ]

            result[c] = round(
                sum(nums)
                /
                len(nums),
                2
            )

        except:

            result[c] = max(
                set(vals),
                key=vals.count
            )

    return result


def get_rows(df, uid):

    ID_COLUMN = "user_id"

    if ID_COLUMN not in df.columns:

        print("\nAvailable columns:\n")
        print(df.columns.tolist())

        sys.exit(
            f"\n[ERROR] Column '{ID_COLUMN}' not found"
        )

    # Convert both sides safely

    df[ID_COLUMN] = (
        df[ID_COLUMN]
        .astype(str)
        .str.strip()
    )

    uid = str(uid).strip()

    rows = df[
        df[ID_COLUMN]
        == uid
    ]

    if rows.empty:

        print("\nSample IDs:\n")

        print(
            df[ID_COLUMN]
            .head(20)
            .tolist()
        )

        sys.exit(
            f"\n[ERROR] user_id={uid} not found"
        )

    return rows


def build_user(metadata, scores):

    merged = {}

    merged.update(
        metadata
    )

    merged.update(
        scores
    )

    return merged


# ==================================================
# DECISION ENGINE
# ==================================================

def choose_segment(user):

    def f(x):

        try:
            return float(x)

        except:
            return 0

    behavior = {

        "content":
        f(
            user.get(
                "content_score",
                0
            )
        ),

        "scheme":
        f(
            user.get(
                "scheme_score",
                0
            )
        ),

        "job":
        f(
            user.get(
                "job_score",
                0
            )
        ),

        "service":
        f(
            user.get(
                "service_score",
                0
            )
        ),

        "conversion":
        f(
            user.get(
                "conversion_score",
                0
            )
        ),
    }

    winner = max(
        behavior,
        key=behavior.get
    )

    meta_bonus = {}

    region = str(
        user.get(
            "region",
            ""
        )
    ).lower()

    salary = str(
        user.get(
            "salary",
            ""
        )
    ).lower()

    notif = str(
        user.get(
            "notification_tag",
            ""
        )
    ).lower()

    meta_bonus[
        winner
    ] = 0

    if "responsive" in notif:

        meta_bonus[
            winner
        ] += 10

    if "low" in salary:

        meta_bonus[
            "scheme"
        ] = 5

    if region:

        meta_bonus[
            winner
        ] += 2

    return winner


# ==================================================
# PROMPT
# ==================================================
SCHEMES = {

    "service":[

    {
    "title":"Digital Certificate Services",
    "description":
    "Apply for government certificates and essential documents online."
    },

    {
    "title":"Citizen Service Portal",
    "description":
    "Access public services and applications digitally."
    },

    {
    "title":"Fast Track Documentation",
    "description":
    "Reduce paperwork and complete applications faster."
    },

    {
    "title":"Utility Service Enrollment",
    "description":
    "Register and manage government utility services."
    },

    {
    "title":"Government Helpdesk Access",
    "description":
    "Resolve service requests with guided support."
    },

    {
    "title":"Smart Citizen Dashboard",
    "description":
    "Track service applications and approvals."
    },

    {
    "title":"Priority Service Window",
    "description":
    "Complete important public services faster."
    },

    {
    "title":"Online Verification Services",
    "description":
    "Verify identity and records digitally."
    },

    {
    "title":"Single Window Government Access",
    "description":
    "Access multiple services through one platform."
    },

    {
    "title":"Essential Service Navigator",
    "description":
    "Discover services relevant to your needs."
    }
    ],


    "job":[

    {
    "title":"National Employment Program",
    "description":
    "Explore government-backed job opportunities."
    },

    {
    "title":"Skill Development Mission",
    "description":
    "Upskill with training and placement support."
    },

    {
    "title":"Youth Employment Drive",
    "description":
    "Discover jobs and career pathways."
    },

    {
    "title":"Public Sector Opportunity Portal",
    "description":
    "Access public recruitment opportunities."
    },

    {
    "title":"Career Acceleration Program",
    "description":
    "Build employable skills."
    },

    {
    "title":"Government Internship Network",
    "description":
    "Gain practical experience."
    },

    {
    "title":"Workforce Readiness Program",
    "description":
    "Prepare for employment."
    },

    {
    "title":"Regional Job Connect",
    "description":
    "Discover opportunities nearby."
    },

    {
    "title":"Apprenticeship Support Program",
    "description":
    "Earn and learn."
    },

    {
    "title":"Employment Growth Initiative",
    "description":
    "Get matched with opportunities."
    }
    ],


    "scheme":[

    {
    "title":"Income Support Initiative",
    "description":
    "Financial support for eligible citizens."
    },

    {
    "title":"Education Assistance Scheme",
    "description":
    "Support for academic goals."
    },

    {
    "title":"Healthcare Support Program",
    "description":
    "Improve healthcare access."
    },

    {
    "title":"Housing Benefit Program",
    "description":
    "Assistance for housing needs."
    },

    {
    "title":"Women Support Scheme",
    "description":
    "Targeted welfare benefits."
    },

    {
    "title":"Social Security Access",
    "description":
    "Expand welfare eligibility."
    },

    {
    "title":"Family Welfare Program",
    "description":
    "Support for households."
    },

    {
    "title":"Senior Citizen Benefits",
    "description":
    "Programs for senior support."
    },

    {
    "title":"Rural Development Initiative",
    "description":
    "Benefits for regional growth."
    },

    {
    "title":"Public Assistance Portal",
    "description":
    "Discover available schemes."
    }
    ],


    "content":[

    {
    "title":"Know Your Government Benefits",
    "description":
    "Learn opportunities available to you."
    },

    {
    "title":"Citizen Awareness Series",
    "description":
    "Discover useful programs."
    },

    {
    "title":"Government Learning Hub",
    "description":
    "Educational content."
    },

    {
    "title":"Public Knowledge Center",
    "description":
    "Guides and explainers."
    },

    {
    "title":"Benefits Explained",
    "description":
    "Understand available services."
    },

    {
    "title":"Smart Citizen Tips",
    "description":
    "Stay informed."
    },

    {
    "title":"Policy Simplified",
    "description":
    "Easy government updates."
    },

    {
    "title":"Opportunity Explorer",
    "description":
    "Learn before applying."
    },

    {
    "title":"Scheme Learning Guide",
    "description":
    "Understand benefits."
    },

    {
    "title":"Government Insights",
    "description":
    "Useful public information."
    }
    ],


    "conversion":[

    {
    "title":"Complete Your Application",
    "description":
    "Finish pending actions."
    },

    {
    "title":"Unlock Your Benefits",
    "description":
    "Take the next step."
    },

    {
    "title":"Claim Eligible Opportunities",
    "description":
    "Act now."
    },

    {
    "title":"Application Completion Center",
    "description":
    "Continue where you left off."
    },

    {
    "title":"Priority Opportunity Access",
    "description":
    "Limited availability."
    },

    {
    "title":"Quick Action Program",
    "description":
    "Fast completion."
    },

    {
    "title":"Ready To Apply",
    "description":
    "One step remaining."
    },

    {
    "title":"Your Benefits Are Waiting",
    "description":
    "Complete today."
    },

    {
    "title":"Instant Opportunity Access",
    "description":
    "Start now."
    },

    {
    "title":"Complete And Unlock",
    "description":
    "Take action."
    }
    ]

    }
def build_meta_prompt(user):

    segment = choose_segment(
        user
    )

    important = [

        "content_score",
        "scheme_score",
        "job_score",
        "service_score",
        "conversion_score",
        "region",
        "salary",
        "family",
        "notification_tag",
        "notification_click",
        "engagement_time_msec",
    ]

    available_schemes = SCHEMES.get(
        segment,
        []
    )

    scheme_text = "\n\n".join(

        [
            f"{i+1}. {s['title']}\n{s['description']}"

            for i, s

            in enumerate(
                available_schemes
            )

        ]

    )

    meta = []

    for k in important:

        if k in user:

            meta.append(
                f"{k}: {user[k]}"
            )

    metadata_block = "\n".join(
        meta
    )

    return f"""
You are an intelligent government
notification engine.

Generate output in EXACT format.

USER ID:
{user["user_id"]}

IMPORTANT USER DATA:

{metadata_block}

SELECTED CATEGORY:
{segment}

Decision rules:

Behavior scores dominate.

content_score → educational

scheme_score → schemes

job_score → jobs

service_score → services

conversion_score → CTA strength

Use metadata for personalization.

AVAILABLE SCHEMES:

{scheme_text}

Choose ONE scheme.

Notification requirements:

• personalized
• persuasive
• eye catching
• short
• maximize click rate
• avoid spam
• create curiosity
• encourage action
• mention scheme naturally

Heading:
maximum 8 words

Content:
maximum 25 words


Generate EXACTLY:

=================================

USER ID:
<id>

NOTIFICATION CATEGORY:
<category>

SELECTED SCHEME:
<scheme>

NOTIFICATION HEADING:
<heading>

NOTIFICATION CONTENT:
<body>

WHY THIS WAS CHOSEN:
<2 lines>

IMPORTANT METADATA USED:
<only important fields>

PROMPT SENT TO
NOTIFICATION MODEL:

<final prompt>

=================================

Do not output JSON.
Do not output markdown.
Do not explain.
"""

# ==================================================
# GEMINI
# ==================================================

def call_gemini(prompt):

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

    r = requests.post(
        GEMINI_URL,
        headers={
            "x-goog-api-key":
            GEMINI_KEY
        },
        json=payload
    )

    r.raise_for_status()

    return (
        r.json()
        ["candidates"][0]
        ["content"]["parts"][0]
        ["text"]
    )


# ==================================================
# MAIN
# ==================================================

meta = read_file(
    METADATA_FILE
)

score = read_file(
    SCORE_FILE
)

meta_rows = get_rows(
    meta,
    USER_ID
)

score_rows = get_rows(
    score,
    USER_ID
)

#print(
#    "\nMetadata rows:",
#    len(meta_rows)
#)
#
#print(
#    "Score rows:",
#    len(score_rows)
#)

meta_user = aggregate(
    meta_rows
)

score_user = aggregate(
    score_rows
)

user = build_user(
    meta_user,
    score_user
)

prompt = build_meta_prompt(
    user
)

result = call_gemini(
    prompt
)

OUTPUT_DIR = Path(
    "outputs_new"
)

def save_result(user_id, result):

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    ts = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    file = (
        OUTPUT_DIR
        /
        f"output_{user_id}_{ts}.txt"
    )

    with open(
        file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(result)

    return file
#print("\n")
#print("="*80)
#print(result)
#print("="*80)
out = save_result(
    USER_ID,
    result
)

print("\n")
print("="*80)
print(result)
print("="*80)

print(
    f"\nSaved → {out}"
)