# Deployment & Environment Reference

## 1. Deployed Services & URLs

| Component | Provider | Live URL | Repository Branch |
|---|---|---|---|
| **Web Frontend** | Vercel | `https://watcha-plum.vercel.app` | `main` |
| **Backend API** | Render | `https://watcha-backend.onrender.com` | `main` |
| **Database & Auth** | Supabase | Managed Cloud Instance | N/A |

---

## 2. Local Development Commands

### Backend (`/backend`)
```bash
cd backend
# With Astral uv (recommended)
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Or standard virtualenv / pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (`/frontend`)
```bash
cd frontend
npm install
npm run dev
# Running on http://localhost:5173
```

---

## 3. Environment Variables

### Backend (`backend/.env`):
```env
# Server
PORT=8000
ENVIRONMENT=development  # or production
FRONTEND_URL=https://watcha-plum.vercel.app,http://localhost:5173

# Supabase
SUPABASE_URL=https://<project-id>.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Market Data Collectors
FINNHUB_API_KEY=<your_finnhub_key>
MARKETAUX_API_TOKEN=<your_marketaux_token>

# AI Engine
OPENROUTER_API_KEY=<your_openrouter_key>
OPENROUTER_MODEL=openrouter/free

# Notifications
TELEGRAM_BOT_TOKEN=<your_bot_father_token>
```

### Frontend (`frontend/.env`):
```env
VITE_SUPABASE_URL=https://<project-id>.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_BASE_URL=https://watcha-backend.onrender.com  # Optional in dev; defaults to localhost:8000 if omitted
```

---

## 4. Render Deployment Configuration (`render.yaml`)
```yaml
services:
  - type: web
    name: watcha-backend
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.0
```
*Note: Any commit pushed to `origin main` automatically triggers a redeploy on Render and Vercel.*
