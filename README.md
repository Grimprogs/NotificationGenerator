# Notification MVP — Supabase + FastAPI + Vercel

## Architecture

```
Vercel (React frontend)
        ↓  GET /notify/{user_id}
Render (FastAPI backend)
        ↓  reads user data
Supabase (Postgres database)
        ↓  stores generated notifications
Gemini API (5 parallel calls)
```

---

## STEP 1 — Set up Supabase (one time)

1. Go to https://supabase.com → New Project
2. Go to **SQL Editor** and run this to create all 3 tables:

```sql
-- Table 1: metadata (from your metadata CSV)
create table user_metadata (
  id                  bigserial primary key,
  user_id             text,
  name                text,
  age                 text,
  district_id         text,
  primary_category    text,
  notification_tag    text,
  preferred_language  text,
  mobile_no           text,
  bpl_category        text,
  personal_income_id  text,
  family_income_id    text,
  family_type_id      text
);

-- Table 2: scores (from your final_table CSV)
create table user_scores (
  id                    bigserial primary key,
  user_id               text,
  primary_category      text,
  notification_response text,
  content_score         numeric,
  scheme_score          numeric,
  job_score             numeric,
  service_score         numeric,
  engagement_time_msec  numeric,
  notification_click    numeric
);

-- Table 3: generated notifications (auto-saved by backend)
create table generated_notifications (
  id                   bigserial primary key,
  user_id              text,
  generated_at         timestamptz,
  notification_number  int,
  title                text,
  body                 text,
  language             text,
  scheme_or_service_id text,
  tone_used            text,
  human_check          text,
  relevance_rationale  text,
  data_signals_used    text
);
```

3. Import your CSVs:
   - Go to **Table Editor** → `user_metadata` → **Insert** → **Import CSV**
   - Do the same for `user_scores` (your final_table.csv)

4. Get your keys:
   - **Project URL**: Settings → API → Project URL
   - **Service Role Key**: Settings → API → service_role (secret)

---

## STEP 2 — Run backend locally (test first)

```bash
cd backend
pip install -r requirements.txt
```

Edit `.env`:
```
GEMINI_API_KEY=AIza...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
```

```bash
uvicorn main:app --reload --port 8000
# test: http://localhost:8000/notify/208135
```

---

## STEP 3 — Deploy backend on Render

1. Push `backend/` to GitHub (no CSV files needed anymore)
2. render.com → New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port 10000`
5. Environment Variables (add all 3):
   - `GEMINI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

---

## STEP 4 — Deploy frontend on Vercel

1. Push `frontend/` to GitHub
2. vercel.com → New Project → Import
3. Framework: **Vite**
4. Add env var: `VITE_API_URL=https://your-render-url.onrender.com`
5. Deploy

---

## What gets saved where

| Data | Where |
|------|-------|
| User metadata | Supabase `user_metadata` table |
| User scores | Supabase `user_scores` table |
| Generated notifications | Supabase `generated_notifications` table |
| Backup JSON | `outputs_v3/output_{user_id}_{timestamp}.json` (local only) |

