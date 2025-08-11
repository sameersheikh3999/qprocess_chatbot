# QProcess Chatbot — Solution Overview

**Date:** 2025-08-11

## 1) System Overview
- **Frontend:** React SPA — `qprocess-chatbot-production-1-main/frontend`
- **Backend:** Django + Django REST Framework — `qprocess-chatbot-production-1-main/backend/chatbot`
- **DB:** SQL Server (via third-party Django backend)
- **AI:** Anthropic Claude Messages API (HTTP)
- **Infra assumption:** single web app + DB with outbound HTTPS to Anthropic.

### C4 Views (Mermaid)
- Context and Container diagrams are in `docs/diagrams/`.

## 2) Repo Structure (abbrev)
```text
repo_extract/
  ./
  qprocess-chatbot-production-1-main/
  qprocess-chatbot-production-1-main/backend/
  qprocess-chatbot-production-1-main/backend/chatbot/
  qprocess-chatbot-production-1-main/backend/chatbot/chatbot/
  qprocess-chatbot-production-1-main/backend/chatbot/chatbot/api/
  qprocess-chatbot-production-1-main/backend/chatbot/chatbot/api/views/
  qprocess-chatbot-production-1-main/backend/chatbot/chatbot/config/
  qprocess-chatbot-production-1-main/backend/chatbot/chatbot/management/
  qprocess-chatbot-production-1-main/backend/chatbot/chatbot/management/commands/
  qprocess-chatbot-production-1-main/backend/chatbot/chatbot/migrations/
  qprocess-chatbot-production-1-main/backend/chatbot/chatbot/services/
  qprocess-chatbot-production-1-main/backend/chatbot/database/
  qprocess-chatbot-production-1-main/database/
  qprocess-chatbot-production-1-main/frontend/
  qprocess-chatbot-production-1-main/frontend/public/
  qprocess-chatbot-production-1-main/frontend/src/
  qprocess-chatbot-production-1-main/scripts/
  ... (truncated)
```

## 3) Data & Control Flow
1. User interacts with the React UI; UI calls the Django API.
2. API validates, delegates to a services layer to:
   - Call Anthropic Messages API to extract normalized task parameters.
   - Validate and persist via stored procedure/ORM to the DB.
3. API returns normalized results to the UI.

## 4) External Dependencies & Contracts
- **Anthropic Messages API**: Use `x-api-key` and an explicit `anthropic-version` header.
- **Django REST Framework** for request/response and serializers.
- **DB backend** (for SQL Server, use `mssql-django`).

## 5) Configuration & Secrets
Create `.env` from `.env.example` (do not commit secrets).
- `CLAUDE_API_KEY` — provisioned by customer
- `CLAUDE_MODEL` — default set in code/services
- DB connection vars (name/user/password/host/port)
Inject env via your secret store/CI.

## 6) API Surface (current)
- `POST /api/chat/` — NL → structured params → DB
- `GET /api/users/` — user listing (if implemented)
- `POST /run-stored-procedure/` — admin/ops
(Verify exact paths in `urls.py`.)

## 7) Requirements (clarified)
**Functional**
- Parse NL into JSON schema: `TaskName, Assignees, Priority, DueDate, Recurrence, Items, Group, Notes`.
- Create a task via stored procedure.

**Non-functional**
- Deterministic schema (validate prior to DB writes).
- Observability and error handling with retries.
- Secure secret handling; no keys in logs.

## 8) Operational Runbook
**Backend**
```bash
cd qprocess-chatbot-production-1-main/backend/chatbot
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

**Frontend**
```bash
cd qprocess-chatbot-production-1-main/frontend
npm install
npm start
```

**Environment checks**
- Ensure DB connectivity and stored procedure presence.
- Set `CLAUDE_API_KEY` and test `/api/chat/` happy path.

## 9) Risks & Mitigations
- **LLM variability** → strict schema + validation + low temperature.
- **Driver compatibility** → pin tested versions; integration tests for SP calls.
- **Secrets leakage** → `.env` in `.gitignore`; use a secret store.

## 10) Decision Log
See ADRs under `docs/adr/`.

## 11) References
- Anthropic Messages API (auth/versioning/examples)
- C4 model overview
- Mermaid syntax
- Django REST Framework docs
- `mssql-django` (if SQL Server)
