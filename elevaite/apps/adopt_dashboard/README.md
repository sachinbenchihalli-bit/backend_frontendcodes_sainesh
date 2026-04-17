## Adopt Dashboard — Frontend + Backend README

A compact guide to the Adopt Dashboard stack covering features, code organization, setup, and the exact scripts to run to get started.

---

### 1) Feature set (What this dashboard offers)
- Campaigns and Insertion Orders views driven by database views (dashboard_campaigns_view, dashboard_insertion_orders_view)
- Campaign metrics cards (Active, WIP, Paused, Total) with trend deltas
- Insertion order metrics (Approved, Pending Approval, Draft, Rejected, totals)
- Rich campaign performance API: daily time series, pacing (planned vs actual), CTR/CPA/ROAS, spend/budget aggregation
- Change tracking system: detects targeting, budget/spend (>7%), and creative swaps
- AI campaign optimization endpoints with tool execution, Qdrant RAG search, and Redis-backed caching
- API proxy from Next.js to FastAPI for clean CORS and consistent URLs
- CSV-driven synthetic data ingestion to quickly bootstrap dashboards

---

### 2) Code organization — Frontend (Next.js, TypeScript)
Location: apps/adopt_dashboard

Structure highlights
- app/ (Next.js App Router)
  - page.tsx, layout.tsx, globals.css
  - campaigns/, insertion-orders/, campaign-optimization/
  - api/proxy/[...path]/route.ts (API proxy to backend)
  - components/, hooks/, services/, utils/, types/
- next.config.mjs: transpiles @repo/ui, standalone output for Docker
- package.json: dev on port 3005, build/start scripts

API Proxy (env-driven backend host/port/protocol)
File: apps/adopt_dashboard/apphttp://localhost:8000/[...path]/route.ts
```ts
const BACKEND_HOST = process.env.BACKEND_HOST || 'backend';
const BACKEND_PORT = process.env.BACKEND_PORT || '3001';
const BACKEND_PROTOCOL = process.env.BACKEND_PROTOCOL || 'http';
// requests to http://localhost:8000/* forward to the FastAPI backend
```

Layout and Providers (apps/adopt_dashboard/app/layout.tsx)
```tsx
export default async function RootLayout({ children }) {
  const session = await auth();
  return (
    <SessionProvider session={session}>
      <ThemeProviderWrapper>
        <ReactQueryProvider>{children}</ReactQueryProvider>
      </ThemeProviderWrapper>
    </SessionProvider>
  );
}
```

Notes
- Styling via Tailwind + shared SCSS (@repo/sass-config). Dark mode supported via next-themes.
- Tables default to 10 per page, filters, case-insensitive search, status tabs, and responsive design (per team preferences).
- Campaign status: show “WIP” for work_in_progress in UI.

---

### 3) Code organization — Backend (FastAPI, asyncpg)
Location: python_apps/adopt_backend

Structure highlights
- app/
  - main.py (FastAPI app, CORS, routers, startup checks)
  - config.py (env-driven settings: DB, Redis, OpenAI, Qdrant)
  - database.py (asyncpg pool, query helpers)
  - routes/ (health, dashboard, campaigns, creatives, tasks, campaign_optimization)
  - services/ (openai_service, cache_service, kevel_service, etc.)
  - tools/ (qdrant_tools with search_similar_queries, tool registry)
  - models.py (Pydantic response models)
- scripts/ (schema + data setup)
  - implement_hybrid_schema_v2.py
  - ingest_synthetic_data.py
  - campaign_change_detector.py
  - other helpers (setup views, backups, embeddings, etc.)

Config (key settings) (python_apps/adopt_backend/app/config.py)
```python
class Settings(BaseSettings):
  db_host: str; db_port: int; db_user: str; db_password: str; db_name: str
  api_host: str; api_port: int; environment: str; reload: bool
  redis_host: str = "localhost"; redis_port: int = 6379; redis_password: str = ""; redis_db: int = 0
  openai_api_key: str = ""; openai_model: str = "gpt-4o-mini"
  qdrant_url: str = "http://3.101.65.253:5333"; qdrant_collection_name: str = "campaign_optimization_qa"
```

Qdrant Tool (simple "search similar queries") (python_apps/adopt_backend/app/tools/qdrant_tools.py)
```python
@register_tool
@function_schema
def search_similar_queries(query: str) -> str:
    # uses OpenAI embeddings + Qdrant; returns top 3 similar prompt/response pairs
```

---

### 4) Setup — database tables and first run

Prerequisites
- PostgreSQL 14+ reachable with credentials
- Python 3.10+ for backend scripts
- Node.js 18+ for frontend
- Redis (recommended) and OpenAI API key if using AI/Qdrant features

Recommended environment files

Backend .env (python_apps/adopt_backend/.env)
```ini
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_USERNAME=postgres  # some scripts use DB_USERNAME; set both for safety
DB_PASSWORD=12345
DB_NAME=creative_db

# API
API_HOST=0.0.0.0
API_PORT=3001
ENVIRONMENT=development
RELOAD=true
CORS_ORIGINS=["http://localhost:3005","http://localhost:3004","http://localhost:3000"]

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redispassword
REDIS_DB=0

# OpenAI / Qdrant
OPENAI_API_KEY=sk-...
QDRANT_URL=http://3.101.65.253:5333
QDRANT_COLLECTION_NAME=campaign_optimization_qa
```

Frontend .env.local (apps/adopt_dashboard/.env.local)
```ini
# Forward all http://localhost:8000/* to FastAPI backend
BACKEND_HOST=localhost
BACKEND_PORT=3001
BACKEND_PROTOCOL=http
```

Exact database setup order (run from repo root)
1) Create insertion order + campaign base tables (idempotent)
File: python_apps/media_backend/migrations/005_create_insertion_order_tables.py

2) Implement hybrid schema v2 (adds enhanced fields, daily metrics table, and dashboard views)
File: python_apps/adopt_backend/scripts/implement_hybrid_schema_v2.py

3) Create change tracking system (targeting columns, change table, daily view update)
File: python_apps/media_backend/migrations/006_create_change_tracking_system.py

4) (Optional) Ingest synthetic data to populate dashboards quickly
File: python_apps/adopt_backend/scripts/ingest_synthetic_data.py
```python
"""Usage: python scripts/ingest_synthetic_data.py [csv_file_path]"""
# Default CSV: python_apps/adopt_backend/uploads/Final_Synthetic_Data_August.csv
# Clears prior synthetic rows, inserts campaigns + placements + daily metrics
```
- Command examples:
  - python python_apps/adopt_backend/scripts/ingest_synthetic_data.py
  - python python_apps/adopt_backend/scripts/ingest_synthetic_data.py /path/to/your.csv

5) (Optional) Detect and store campaign changes (targeting/budget/creative)
File: python_apps/adopt_backend/scripts/campaign_change_detector.py
```python
# Usage: python campaign_change_detector.py [--days=30] [--dry-run]
# Saves rows to campaign_change_tracking unless --dry-run
```
- Command:
  - python python_apps/adopt_backend/scripts/campaign_change_detector.py --days=30
---

### 5) Running the apps
Backend (FastAPI)
- Install deps once: pip install -r python_apps/adopt_backend/requirements.txt
- Run dev server: python python_apps/adopt_backend/main.py
- Health check: GET http://localhost:3001/api/health

Frontend (Next.js)
- From apps/adopt_dashboard: npm install
- Dev server: npm run dev  (defaults to port 3005 per package.json)
- The frontend calls the backend via http://localhost:8000/* (configure BACKEND_* envs as above)

Docker (optional)
- Frontend Dockerfile: apps/adopt_dashboard/Dockerfile (script: npm run docker)
- Backend Dockerfile: python_apps/adopt_backend/Dockerfile

---

### 6) Key API endpoints (backend)
On startup, backend logs useful routes. Common ones:
- GET /api/health
- GET /api/dashboard/overview
- GET /api/campaigns, GET /api/campaigns/{id}
- GET /api/campaigns/{id}/pacing, /performance, /placements
- GET /api/insertion-orders, /api/insertion-orders/{id}, /api/insertion-orders/{id}/campaigns
- POST /api/campaign-optimization/{campaign_id} (AI optimize); plus /analyze, /cache-stats, /test-ai

---

### 7) Database schemas 
This stack reads primarily from database views (built over media backend tables) plus a few base tables for placements/tasks. Key relations:

- dashboard_campaigns_view (VIEW)
  - One row per campaign with aggregated metrics: impressions_delivered, clicks, conversions, spend, budget, cpm, cpc, ctr, roas, status, brand, created_at/updated_at
  - Includes descriptive fields used by UI (platform_channel, campaign_objective, targeting_type, audience_segment, geo, etc.)
  - Source: media backend campaign tables + placements + daily metrics

- dashboard_campaigns_daily_view (VIEW)
  - Daily snapshots for charts and range aggregations: metric_date, impressions_delivered, clicks, conversions, spend, ctr
  - Used for: /campaigns/{id}/performance and pacing calculations (planned vs actual)

- dashboard_insertion_orders_view (VIEW)
  - IO-level rollup: name, status, start/end dates, budget, spent, remaining, days_left, campaign_count, brand, roas, ctr, spend
  - Also surfaces identifiers and links (salesforce_io_id, media_plan_id)

- campaign_placements (TABLE)
  - Flight/placement rows tied to campaigns: start/end dates, booked/delivered impressions, clicks, ctr, budget, cpm, cpc
  - data_source marks synthetic vs production; frontend exposes these via /campaigns/{id}/placements

- dashboard_creatives (VIEW/TABLE)
  - Creative-level aggregations: name, impressions, clicks, conversions, ctr; frontend uses for “Top Performing Creatives”

- dashboard_todo_items (TABLE)
  - Lightweight Tasks list driving /tasks endpoint with priority/due_date/status

Notes
- Frontend “Campaigns” and “Insertion Orders” pages are driven by the dashboard_* views for consistency and speed.
- Synthetic data scripts populate campaigns, placements, and daily metrics, then the views expose clean aggregates aligned with UI requirements.

---

