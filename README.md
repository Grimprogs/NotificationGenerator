# Notification MVP — Setup & Deploy Guide

## Project Structure

```
mvp/
├── backend/
│   ├── main.py            ← FastAPI app
│   ├── requirements.txt
│   └── .env               ← your keys + file paths (never commit this)
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   └── main.jsx
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── vercel.json
    └── .env               ← VITE_API_URL
```

---

## STEP 1 — Run Backend Locally (test first)

```bash
cd backend
pip install -r requirements.txt

# edit .env — set your actual CSV paths + Gemini key
# then:
uvicorn main:app --reload --port 8000
```

Test it:
```
http://localhost:8000/notify/208135
```

You should get JSON with 5 notifications + user_profile.

---

## STEP 2 — Deploy Backend on Render (free)

1. Push the `backend/` folder to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Set:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn main:app --host 0.0.0.0 --port 10000`
5. Add Environment Variables in Render dashboard:
   - `GEMINI_API_KEY` = your key
   - `METADATA_FILE`  = path to CSV  ← see note below
   - `SCORE_FILE`     = path to CSV

> ⚠️ NOTE on CSV files:
> Render is a cloud server — it can't access your laptop.
> Two options:
> A) Upload CSVs to your GitHub repo (only if data is not sensitive)
>    then set paths like: `METADATA_FILE=metadata.csv`
> B) Upload CSVs to Google Drive / S3 and modify main.py to download them

6. After deploy, your backend URL will be:
   `https://your-service-name.onrender.com`

---

## STEP 3 — Deploy Frontend on Vercel

1. Push the `frontend/` folder to a GitHub repo
2. Go to https://vercel.com → New Project → Import repo
3. Framework: **Vite**
4. Add Environment Variable:
   - `VITE_API_URL` = `https://your-service-name.onrender.com`
5. Deploy

Your frontend will be live at:
`https://your-project.vercel.app`

---

## How It Works

```
User enters ID on Vercel site
        ↓
Frontend calls: GET /notify/{user_id}
        ↓
FastAPI backend (Render) reads both CSVs
        ↓
Merges + resolves user profile
        ↓
5 parallel Gemini API calls (async)
        ↓
Returns JSON:
  { notifications: [...5...], user_profile: {...} }
        ↓
Frontend shows notifications first, metadata below
```

---

## Local Dev (both together)

Terminal 1:
```bash
cd backend && uvicorn main:app --reload --port 8000
```

Terminal 2:
```bash
cd frontend && npm install && npm run dev
```

Frontend runs on http://localhost:5173
