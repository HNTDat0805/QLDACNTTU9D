# Project Context & Agent Guidelines

## 1. Overview
This repository is a full-stack web application based on the FastAPI Full Stack Template. It features a Python FastAPI backend with SQLModel, PostgreSQL, and Alembic, paired with a modern React 19 TypeScript frontend bundled via Vite and Tailwind CSS.

- **Backend**: FastAPI + SQLModel + Alembic + Pydantic v2 (managed with `uv`).
- **Frontend**: React 19 + TypeScript + Vite + TanStack Router & Query + Tailwind CSS v4 (managed with `bun`).
- **Emails**: React Email templates (`packages/react-email`).
- **Infrastructure**: Docker Compose (PostgreSQL, Mailpit, Traefik, Adminer).

---

## 2. Repository Structure

```
├── backend/                  # FastAPI Python backend (Python >=3.14, uv workspace)
│   ├── app/
│   │   ├── alembic/          # Alembic database migrations
│   │   ├── api/              # API router and endpoint definitions
│   │   │   ├── routes/       # Endpoint handlers (items, users, login, etc.)
│   │   │   └── deps.py       # Dependency injection (Current user, DB session)
│   │   ├── core/             # Configuration, security, DB engine
│   │   ├── crud.py           # Database CRUD helper functions
│   │   ├── models.py         # SQLModel database tables and Pydantic schemas
│   │   └── main.py           # FastAPI application entrypoint
│   ├── tests/                # Pytest backend test suite
│   ├── scripts/              # Helper scripts (prestart.sh, test.sh, lint.sh, format.sh)
│   └── pyproject.toml        # Backend dependencies and tool configurations
├── frontend/                 # React TypeScript frontend (Vite, Bun)
│   ├── src/
│   │   ├── client/           # Auto-generated API client (OpenAPI TS)
│   │   ├── components/       # Reusable UI components (Radix UI, Common)
│   │   ├── hooks/            # Custom React hooks (auth, query hooks)
│   │   ├── routes/           # TanStack Router file-based pages
│   │   ├── main.tsx          # Application entrypoint
│   │   └── routeTree.gen.ts  # Auto-generated route tree
│   └── package.json          # Frontend dependencies and scripts
├── packages/
│   └── react-email/          # Transactional email templates using React Email
├── compose.yml               # Base Docker Compose configuration
├── compose.override.yml      # Local development Docker overrides
├── compose.deploy.yml        # Production Docker deployment configuration
├── .env                      # Local development environment configuration
└── pyproject.toml            # Root workspace config (uv & prek)
```

---

## 3. Environment & Services

Key local services and endpoints:
- **Frontend Dev Server**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Swagger / OpenAPI Docs**: http://localhost:8000/docs
- **Mailpit Web UI (Email Testing)**: http://localhost:8025
- **Mailpit SMTP Server**: `localhost:1025`
- **Adminer (DB Web Admin)**: http://localhost:8080 (when started via compose)

---

## 4. Common Commands & Workflows

### 4.1 Running Supporting Services
Start PostgreSQL and Mailpit using Docker Compose:
```bash
docker compose up -d db mailpit
```

### 4.2 Backend Workflow (from `backend/`)
- **Install dependencies**:
  ```bash
  uv sync
  ```
- **Run pre-start migrations & seed data**:
  ```bash
  uv run bash scripts/prestart.sh
  # Or on Windows PowerShell:
  # uv run alembic upgrade head
  # uv run python app/initial_data.py
  ```
- **Start development server**:
  ```bash
  uv run fastapi dev
  ```
- **Run tests**:
  ```bash
  uv run pytest
  ```
- **Linting & Formatting**:
  ```bash
  uv run ruff check app --fix
  uv run ruff format app
  uv run mypy app
  ```
- **Create new DB migration**:
  ```bash
  uv run alembic revision --autogenerate -m "Add new table or column"
  uv run alembic upgrade head
  ```

### 4.3 Frontend Workflow (from root or `frontend/`)
- **Install dependencies**:
  ```bash
  bun install
  ```
- **Start Vite dev server**:
  ```bash
  bun run dev
  # Or from root: bun run --filter frontend dev
  ```
- **Regenerate API client from OpenAPI**:
  Run while the backend server is running on http://localhost:8000:
  ```bash
  cd frontend && bun run generate-client
  ```
- **Linting**:
  ```bash
  bun run lint
  ```
- **Run Playwright end-to-end tests**:
  ```bash
  cd frontend && bun run test
  ```
- **Build frontend (outputs to `backend/app/frontend` to be served by FastAPI)**:
  ```bash
  cd frontend && bun run build
  ```

### 4.4 Email Templates Workflow
- **Develop email templates**:
  ```bash
  bun run email:dev
  ```
- **Export email HTML/text**:
  ```bash
  bun run email:export
  ```

### 4.5 Workspace-wide Linting (`prek`)
- **Run all pre-commit hooks manually**:
  ```bash
  uv run prek run --all-files
  ```

---

## 5. Coding Standards & Conventions

1. **Backend (Python)**:
   - Python 3.14+ target.
   - Use SQLModel for database models and Pydantic schemas. Keep models centralized or modular in `backend/app/models.py`.
   - Maintain strict typing (`mypy --strict`). Avoid untyped parameters and `Any` when possible.
   - Place database operations in `backend/app/crud.py` or modular services.
   - Inject dependencies (e.g. database session, current active user) using `fastapi.Depends` and `backend/app/api/deps.py`.
   - Never log sensitive credentials or commit secrets.

2. **Frontend (TypeScript & React)**:
   - Functional components with React 19 hooks.
   - File-based routing with `@tanstack/react-router`. Routes are declared in `frontend/src/routes/`.
   - Data fetching and mutations using `@tanstack/react-query` and the generated client in `frontend/src/client/`.
   - Style using Tailwind CSS v4 and Radix UI primitives.
   - Ensure clean formatting with Biome (`bun run lint`).

3. **Database Changes**:
   - Any modification to database models in `models.py` must be accompanied by a new Alembic migration script in `backend/app/alembic/versions/`.
   - Verify migrations using `uv run alembic upgrade head`.
