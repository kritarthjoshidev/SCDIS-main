# SCDIS - Smart Campus Decision Intelligence System

SCDIS is an AI-powered energy optimization and decision intelligence platform with:

- `backend`: FastAPI services for decisioning, monitoring, autonomous runtime, and model operations
- `frontend`: Next.js dashboard for live telemetry, AI decisions, events, alerts, and model controls

## Team

Matrix Shot  
AMD Hackathon Submission

## Tech Stack

- Backend: FastAPI, Uvicorn, scikit-learn, pandas, numpy
- Frontend: Next.js 16, React 19, TypeScript, Tailwind, Framer Motion
- Deployment: Netlify (frontend) + any always-on backend host (Render/Codesphere/Lightning/etc.)

## Repository Structure

```text
.
+-- backend/                 # FastAPI app and AI runtime
|   +-- app.py               # FastAPI entrypoint
|   +-- routes/              # API routes
|   +-- services/            # Runtime/monitoring services
|   +-- ai_engine/           # Forecast/RL/anomaly/retraining logic
|   +-- requirements.txt     # Python dependencies
+-- frontend/                # Next.js dashboard
|   +-- app/                 # App router pages
|   +-- components/          # UI components/tabs
|   +-- lib/api.ts           # Frontend API client
+-- render.yaml              # Render deployment blueprint
```

## Features

- Live laptop/edge telemetry monitoring
- Runtime modes: `LIVE_EDGE`, `SIMULATION`, `HYBRID`
- Scenario injection: `normal`, `peak_load`, `low_load`, `grid_failure`
- AI decision timeline and optimization insights
- Trusted telemetry pipeline:
  - strict payload validation (type + bounds)
  - anomaly spike/outlier filtering
  - quarantine of low-trust telemetry records
- Report generator:
  - full infrastructure report for `1 day`, `1 week`, `1 month`
  - includes executive summary, system health, performance, security, recommendations
  - supports detailed multi-page `PDF` export with embedded charts
- AI model actions:
  - Retrain model
  - View logs
  - Export weights
- Autonomous background runtime services

## Local Development

## Prerequisites

- Python `3.11+`
- Node.js `18+` (recommended `20+`)

## 1) Backend Setup

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies and run:

```bash
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8010 --reload
```

Use managed PostgreSQL (Neon/Supabase) by setting `DATABASE_URL` before starting backend:

Windows (PowerShell):

```bash
$env:DATABASE_URL="postgresql://<user>:<password>@<host>:5432/<db>?sslmode=require"
python -m uvicorn app:app --host 0.0.0.0 --port 8010 --reload
```

macOS/Linux:

```bash
export DATABASE_URL="postgresql://<user>:<password>@<host>:5432/<db>?sslmode=require"
python -m uvicorn app:app --host 0.0.0.0 --port 8010 --reload
```

Backend health:

```bash
curl http://localhost:8010/
curl http://localhost:8010/openapi.json
```

## 2) Frontend Setup

In a new terminal:

```bash
cd frontend
npm install
```

Set API base URL in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8010
```

Run frontend:

```bash
npm run dev
```

Open:

- Dashboard: `http://localhost:3000`
- Access portal (admin + org signup/login): `http://localhost:3000/access`

## API Docs

- Swagger UI: `http://localhost:8010/docs`
- OpenAPI JSON: `http://localhost:8010/openapi.json`

Telemetry trust endpoints:

- `POST /telemetry/assess` -> validate payload and return trust/anomaly report
- `POST /telemetry/ingest` -> ingest trusted telemetry or quarantine low-trust payload
- `GET /telemetry/latest` -> latest trusted telemetry snapshot
- `GET /telemetry/recent?limit=100` -> recent telemetry records
- `GET /monitoring/executive-kpis` -> energy/cost/carbon + forecast/anomaly KPI snapshot
- `GET /monitoring/report?window=1d|1w|1m&format=json|markdown` -> generate full report payload
- `GET /monitoring/report/download?window=1d|1w|1m&format=pdf|markdown|json` -> download report file

Enterprise auth + training lifecycle endpoints:

- `POST /enterprise/auth/register-organization` -> create organization + org admin account
- `POST /enterprise/auth/login-admin` -> admin login
- `POST /enterprise/auth/login-org` -> organization admin login
- `GET /enterprise/auth/me` -> session introspection
- `POST /training-data/ingest` -> push model training sample
- `POST /training-data/run-now` -> trigger manual training cycle
- `POST /training-data/auto-trainer/start` -> auto training scheduler
- `POST /training-data/auto-trainer/stop` -> stop auto scheduler
- `GET /training-data/stats` -> training queue + run stats

Default local admin bootstrap credentials:

- Email: `admin@scdis.local`
- Password: `admin123`

Use env vars `SCDIS_ADMIN_EMAIL` and `SCDIS_ADMIN_PASSWORD` to override.

## Managed DB (Neon/Supabase)

- Backend auto-detects DB in this order:
  - `DATABASE_URL`
  - `SUPABASE_DB_URL`
  - `NEON_DATABASE_URL`
  - fallback: local SQLite (`backend/data/enterprise_platform.db`)
- Recommended production setting:

```env
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db>?sslmode=require
```

## Security env (production)

Set these on backend host:

```env
ENVIRONMENT=production
SECRET_KEY=<strong-random-secret>
CORS_ALLOWED_ORIGINS=https://<your-netlify-site>.netlify.app
SCDIS_ADMIN_EMAIL=<your-admin-email>
SCDIS_ADMIN_PASSWORD=<strong-admin-password>
```

## Deployment

## Backend on Lightning AI

Use an always-on app/runtime (not notebook session) and deploy `backend` as service.

1. Push code to GitHub
2. Create new app/project on Lightning
3. Set **working directory** to `backend`
4. Build command:

```bash
pip install -r requirements.txt
```

5. Start command:

```bash
python -m uvicorn app:app --host 0.0.0.0 --port $PORT
```

6. Add env vars from "Security env (production)" + `DATABASE_URL`
7. Deploy and copy backend URL

## Backend on Render (Alternative)

This repo includes `render.yaml`.

1. In Render: `New` -> `Blueprint`
2. Select this repository
3. Render auto-creates `scdis-backend` using `render.yaml`
4. Add same production env vars as above
5. Deploy and copy backend URL

## Backend on Oracle Always Free VM (Alternative)

Use this detailed guide:

- `docs/deploy-oracle-vercel.md`

Quick path:

1. Create Oracle Always Free VM
2. Open ingress ports `22`, `80`, `443`
3. Clone repo on VM to `/opt/scdis`
4. Run:

```bash
bash backend/deploy/oracle_vm_setup.sh /opt/scdis ubuntu
```

(Use `opc` as the second argument on Oracle Linux images.)

## Frontend on Vercel

1. In Vercel: `New Project`
2. Import this repository
3. Set **Root Directory** to `frontend`
4. Add environment variable:

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-render-backend-url>
```

5. Deploy

## Frontend on Netlify

1. Import this repository in Netlify
2. Set build settings:
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/.next`
3. Add environment variable:

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-backend-url>
```

4. Deploy

## Backend Host Choice (if not Replit)

- Good from your list: `Codesphere`, `Lightning.ai` (always-on service style)
- Not recommended for production API hosting: `Google Colab`, `Kaggle Notebooks` (not meant for stable public backend uptime)

## Post-Deploy Checks

Replace `<backend-url>` and run:

```bash
curl https://<backend-url>/
curl -X POST https://<backend-url>/enterprise/auth/login-admin -H "Content-Type: application/json" -d "{\"email\":\"<admin-email>\",\"password\":\"<admin-password>\"}"
```

Then use returned `token` as bearer for protected APIs:

```bash
curl https://<backend-url>/monitoring/laptop/live-dashboard -H "Authorization: Bearer <token>"
curl -X POST https://<backend-url>/monitoring/ai-models/retrain -H "Authorization: Bearer <token>"
```

## Troubleshooting

- `API 404 {"detail":"Not Found"}` in UI:
  - Frontend is pointing to the wrong backend URL
  - Verify `NEXT_PUBLIC_API_BASE_URL`
  - Confirm route exists in `https://<backend>/openapi.json`
- Frontend changes not reflecting:
  - restart dev server after env changes
- Render cold start delay:
  - first request can take longer on free tier

## Notes

- Some runtime features depend on host machine telemetry and local model/data files.
- Monitoring, telemetry, orchestrator, and admin routes are bearer-token protected.
- For hackathon demo UX, `org_admin` can access most monitoring/training/orchestrator operations.
- Critical super-admin operations stay admin-only (`/admin/*` and enterprise organization management APIs).
- For production-grade persistence, use external storage for logs/artifacts (DB/S3/object storage), because ephemeral disk can reset on redeploy.
