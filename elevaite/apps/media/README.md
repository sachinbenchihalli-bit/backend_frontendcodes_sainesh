# Media Planning App – Features and Code Organization

This README summarizes the media planning experience spanning the frontend (apps/media) and backend (python_apps/media_backend).

## 1) Feature Set and Chatbot Capabilities
- Conversational media planning
  - Natural-language prompts to generate media plan summaries and recommendations
  - Streams responses via Server-Sent Events (SSE) for responsive UX
  - Combines filters + semantic search (search planner) to find relevant brand/campaign references before planning
  - If data is not relevant/available, replies fall back to industry best practices with a brief explanation
- Targeting configurations
  - CRUD user-specific targeting presets used in IOs/placements
- Insertion Orders (IO) and documentation
  - Generates IO documentation (PDF) and stores links
  - Destinations: Google Workspace or Salesforce (via connector)
  - Stores an IO success message into the session as a bot message
- Salesforce integration
  - Fetch Accounts and Opportunities for form dropdowns
  - IO creation through a Salesforce connector; returns Lightning record link + PDF link
  - Maintains mapping between internal insertion order and Salesforce IO ID
- Campaign scaffolding
  - Create/update campaigns with Kevel ID + Salesforce IO linkage, including placements/targeting
- Session and feedback
  - Create/list sessions, fetch full session details (with queries)
  - Voting and free-text feedback endpoints
- Prompting and grounding
  - See python_apps/media_backend/prompts/prompts.py (media_plan_v2…v7) for instructions used by the planner
  - Prompts require the model to explain search context and which brand results influenced the plan

## 2) Code Organization – Frontend (apps/media)
- Framework and layout
  - Next.js (App Router) with Tailwind
  - app/layout.tsx: wraps SessionProvider, theme provider, ChatContext, and AppLayout
  - app/page.tsx: main chat page (ChatbotWindow + ChatbotInput)
- Chat/session state
  - app/ui/contexts/ChatContext.tsx
    - Manages sessions (create/list/load), selected session, and message flow
    - Sends POST to backend SSE endpoint to stream bot responses
    - Adds user/bot messages, handles votes/feedback, tracks IO creation success messages
- Backend calls
  - app/lib/actions.tsx: legacy helpers (fetchChatbotResponse, sendChatMessage)
  - app/lib/salesforceApi.ts: fetch Salesforce Accounts/Opportunities via backend
  - app/lib/targetingConfigApi.ts: targeting configurations CRUD via backend
- IO UI
  - app/components/GenerateIOForm.tsx: guided IO creation; connects dropdowns + targeting selector to backend endpoints
- Configuration
  - Uses env: NEXT_PUBLIC_MEDIA_BACKEND_URL (see .env.frontend for local defaults)

## 3) Code Organization – Backend (python_apps/media_backend)
- FastAPI app (main.py)
  - Inference (chat)
    - POST "/" — streams SSE chunks (llm_rag_inference.perform_inference)
  - Sessions
    - POST /session, GET /session/{id}, GET /session/{id}/full, GET /sessions/user/{user_id}, PUT /session/name, POST /session/{id}/flush
  - Feedback
    - POST /feedback, GET /feedback/{query_id}, GET /feedback/session/{session_id}
    - Voting endpoint present following the same pattern
  - Targeting configurations
    - GET/POST /targeting-configurations, GET/PUT/DELETE /targeting-configurations/{id}
  - Salesforce integration and IOs
    - GET /salesforce/accounts
    - GET /salesforce/opportunities-by-account/{account_id}
    - IO creation path: handled within the main POST flow; if SalesforceAccount and SalesforceOpportunityId are present, the app calls the Salesforce connector and returns Lightning + PDF links; success message is written to session history
    - IO update supports source=salesforce|google_drive with placement/targeting updates and convert_to_campaign flag
  - Campaigns
    - POST /campaigns/{kevel_id}/{salesforce_io_id}
    - PUT /campaigns/{campaign_id}
- LLM, search, prompts
  - llm_rag_inference.py: orchestrates RAG streaming
  - prompts/prompts.py: media planning prompt variants (media_plan_v2…v7)
  - search_planner.py, search_tools.py: multi-step strategy (filters + semantic) before plan generation
- Persistence
  - database_models.py: SQLAlchemy models (sessions, queries/steps, feedback, targeting configurations, insertion orders + Salesforce mapping, campaigns/placements)
  - db_connector.py, postgresql_session_manager.py: DB connectivity/session
  - migrations/: core tables, targeting, insertion orders, change tracking
- Services/integrations
  - services/insertion_order_service.py, services/insertion_order_db_service.py
  - services/google_drive.py, services/pdf_generator.py, oauth_handler.py
  - tools/budget_tool.py, tools/store_s3.py
- Tests and utilities
  - tests/: endpoints, search planner, Qdrant search
  - visualizer/: DB diagram tools
- Configuration notes
  - Frontend uses NEXT_PUBLIC_MEDIA_BACKEND_URL
  - Backend reads SALESFORCE_CONNECTOR_URL and related settings for Salesforce

---
For questions or changes, start with ChatContext (frontend) and main.py (backend), then follow the referenced lib/services modules.

## 4) Database Schema — what’s used and how
- Core chat/performance tables (created by migrations 003+):
  - sessions, queries, agent_execution_steps, feedback, related_queries
  - Written by this backend:
    - Chat SSE writes query rows and appends bot/user messages
    - Session endpoints create/list/update sessions and flush cache to DB
    - Feedback endpoints/voting write to feedback
  - Read by the performance app (python_apps/media_dashboard_backend) for overview charts/timelines

- Planning/IO/Campaign tables (created by migration 005):
  - insertion_orders, placements, status_changes
  - campaigns, campaign_placements
  - campaign_insertion_order_mapping
  - insertion_order_salesforce_mapping, insertion_order_google_drive_mapping
  - Used by:
    - IO creation flow (Google Workspace or Salesforce) to persist IO + mappings
    - Campaign scaffolding and placement details for downstream dashboards

- Change tracking (migration 006):
  - campaign_change_tracking table
  - Also enhances dashboard_campaigns_daily_view when present (adds creative/targeting columns)

- Dashboard views and daily metrics (maintained by Adopt backend scripts):
  - campaign_daily_metrics (TABLE): per-day metrics inserted by adopt backend ingestion script
    - File: python_apps/adopt_backend/scripts/ingest_synthetic_data.py
  - dashboard_campaigns_view, dashboard_insertion_orders_view, dashboard_campaigns_daily_view (VIEWS)
    - File: python_apps/adopt_backend/scripts/implement_hybrid_schema_v2.py
  - This media backend is compatible with those views; migration 006 updates the daily view to include creative/targeting if present

Summary: media planning writes chat/session/feedback and IO/campaign/placement data. The performance app reads sessions/queries/feedback directly; campaign performance time series comes from campaign_daily_metrics inserted by the adopt ingestion pipeline, surfaced via the dashboard_* views.

## 5) Webhook integrations — Salesforce updates (IO/campaign status)
- Incoming updates endpoint
  - POST /insertion-orders/{order_id}/update?source=salesforce|google_drive
  - Resolves the actual IO via insertion_order_salesforce_mapping when source=salesforce
  - Updates IO fields (status, owners, emails, objective, links), writes status_changes entries, and applies placement updates (including convert_to_campaign and targeting_config)
- Data models
  - webhook_models.py defines Salesforce approval payload schemas and responses for future/alternative webhook flows
- Outbound to Salesforce (during IO creation)
  - If the IO destination is Salesforce, main flow calls SALESFORCE_CONNECTOR_URL to create the record and stores the returned Lightning link
  - On success, backend also writes a bot success message to queries for session continuity
