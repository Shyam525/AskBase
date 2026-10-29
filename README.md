# AskBase

AskBase is a permission-aware, evidence-grounded internal knowledge system for organizations.

It enables teams to organize institutional knowledge into isolated workspaces, upload documents across multiple formats, perform scoped search, ask natural-language questions, and receive verifiable answers strictly grounded in retrievable passages.

When available evidence is insufficient to answer a query truthfully, the system **explicitly abstains** rather than hallucinating unsupported claims.

---

## 🛠️ Tech Stack & Architecture

- **Runtime & Language**: [Python](https://www.python.org/) (>= 3.11) with strict static typing
- **Package & Environment Management**: [`uv`](https://docs.astral.sh/uv/) with locked dependencies (`uv.lock`)
- **Web API Framework**: [FastAPI](https://fastapi.tiangolo.com/) & [Starlette](https://www.starlette.io/)
- **Data Validation & Settings**: [Pydantic](https://docs.pydantic.dev/) v2 & [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) (fail-closed in production)
- **Database & Persistence**: [PostgreSQL](https://www.postgresql.org/) (>= 16) with [SQLAlchemy 2.x](https://www.sqlalchemy.org/) async engine & connection pooling
- **Database Migrations**: [Alembic](https://alembic.sqlalchemy.org/) version-controlled schema revisions
- **Security & Cryptography**: [Argon2id](https://github.com/hynek/argon2-cffi) for password hashing and [PyJWT](https://pyjwt.readthedocs.io/) for HMAC-SHA256 signed access tokens with issuer, audience, and expiry validation
- **Document Ingestion**: Multi-format text extraction ([`pypdf`](https://pypdf.readthedocs.io/), Markdown section parser, Plain text) with magic bytes verification and path traversal prevention
- **Testing & Quality**: [Pytest](https://docs.pytest.org/), [HTTPX](https://www.python-httpx.org/), [Ruff](https://astral.sh/ruff/) (linter & formatter), and [Mypy](https://mypy-lang.org/) (type checker)
- **Containerization**: Multi-stage Dockerfile and Docker Compose orchestration

---

## 📁 Repository Layout

```text
├── alembic/                       # Version-controlled database schema migrations
│   ├── versions/                  # Individual migration revisions
│   └── env.py                     # Async Alembic migration environment
├── docs/
│   ├── adr/
│   │   └── 0001-document-identity-and-duplicate-handling.md  # ADR on content-hash vs identity
│   └── migration/
│       └── legacy-inventory.md    # Documentation of legacy code removal & decisions
├── src/askbase/
│   ├── api/                       # HTTP API layer
│   │   ├── deps.py                # Dependencies (DB session, Auth, Workspace authorization)
│   │   ├── routers/               # Endpoint controllers (health, auth, workspaces, documents, search, qa)
│   │   └── schemas/               # Pydantic request and response schemas
│   ├── core/                      # Settings, Argon2 security, structured logging, error hierarchy
│   ├── db/                        # Database engine, session lifecycle, health probes
│   ├── models/                    # SQLAlchemy ORM models (User, Workspace, Document, Version, Chunk, etc.)
│   ├── repositories/              # Persistence and query layer
│   ├── services/                  # Business logic use cases (Auth, Workspace, Document, Q&A)
│   ├── ingestion/                 # File validation, magic bytes check, text extraction, chunking
│   ├── retrieval/                 # Scoped lexical, semantic, and hybrid search
│   ├── ai/                        # Embedding and grounded LLM synthesis providers
│   └── main.py                    # Application entrypoint with correlation and error handlers
├── tests/                         # Comprehensive automated test suite
├── docker-compose.yml             # Local PostgreSQL and API container definition
├── Dockerfile                     # Multi-stage production container build
├── pyproject.toml                 # Project metadata, dependencies, and tool settings
├── uv.lock                        # Deterministic package dependency lockfile
└── requests.http                  # Executable HTTP request collection
```

---

## 🚀 Getting Started

### 1. Prerequisites

Ensure you have the following installed:
- [Python](https://www.python.org/) (version 3.11 or higher, recommended 3.13)
- [`uv`](https://docs.astral.sh/uv/) (recommended fast package manager)
- [Docker](https://www.docker.com/) (optional, for local PostgreSQL via Docker Compose)

*Fallback without uv: Standard `python -m venv .venv` and `pip install -e ".[dev]"` can also be used.*

### 2. Installation

Clone the repository and sync the virtual environment using `uv`:

```bash
git clone https://github.com/Shyam525/AskBase.git
cd AskBase
uv sync --extra dev
```

### 3. Environment Configuration

Copy the example configuration file:

```bash
cp .env.example .env
```

Key environment configuration variables:

| Variable | Description | Default | Production Requirement |
| :--- | :--- | :--- | :--- |
| `NODE_ENV` | Environment (`development`, `test`, `production`) | `development` | Mandatory |
| `PORT` | HTTP port | `5000` | Optional |
| `DATABASE_URL` | PostgreSQL async connection string | PostgreSQL docker URL | Mandatory |
| `JWT_SECRET` | Access token signing secret | Dev fallback | $\ge 32$ chars, fails closed if omitted |
| `JWT_EXPIRES_IN_MINUTES` | Access token validity window | `15` | Default 15m |
| `STORAGE_DIR` | Local disk root for uploaded documents | `storage/documents` | Persistent volume |
| `EMBEDDING_PROVIDER` | Vector embedding engine (`fake`, `none`) | `fake` | Configurable |
| `AI_PROVIDER` | Grounded synthesis engine (`fake`, `extractive`) | `fake` | Configurable |

### 4. Running the Database (Docker Compose)

Start the PostgreSQL service in the background:

```bash
docker compose up -d postgres
```

### 5. Running Database Migrations

Apply database migrations to head:

```bash
uv run alembic upgrade head
```

### 6. Starting the Backend Server

- **Development Server** (with hot reload):
  ```bash
  uv run uvicorn askbase.main:app --reload --port 5000
  ```
- **Production Server**:
  ```bash
  uv run uvicorn askbase.main:app --host 0.0.0.0 --port 5000
  ```

---

## 📡 API Endpoints

### Health Probes
- `GET /` — Operational status metadata
- `GET /health/live` (alias `/health`) — Process liveness probe
- `GET /health/ready` (alias `/ready`) — Database connectivity probe (returns 200 or 503)

### Authentication & Sessions
- `POST /api/auth/register` — Onboard user and create primary tenant workspace
- `POST /api/auth/login` — Authenticate credentials and receive short-lived access token + refresh token
- `POST /api/auth/refresh` — Rotate refresh token and obtain new access token
- `POST /api/auth/logout` — Revoke active refresh session
- `GET /api/auth/me` — Retrieve current authenticated user profile and memberships

### Workspace Isolation & Roles
- `POST /api/workspaces` — Create new workspace boundary (creator becomes `owner`)
- `GET /api/workspaces` — List workspaces accessible to authenticated user
- `GET /api/workspaces/{id}` — Get workspace metadata (enforces tenant membership)
- `POST /api/workspaces/{id}/members` — Add member (`admin` or `owner` privilege required)
- `GET /api/workspaces/{id}/members` — List members
- `DELETE /api/workspaces/{id}/members/{user_id}` — Remove member

### Documents & Provenance
- `POST /api/workspaces/{id}/documents` — Ingest document (v1) with magic bytes check and hash detection
- `GET /api/workspaces/{id}/documents` — List active documents with latest version info
- `GET /api/workspaces/{id}/documents/{doc_id}` — Document details with full immutable version history
- `POST /api/workspaces/{id}/documents/{doc_id}/versions` — Append new version without altering historical snapshots
- `DELETE /api/workspaces/{id}/documents/{doc_id}` — Safe soft delete preserving citations and audit trails
- `GET /api/workspaces/{id}/documents/{doc_id}/versions/{v_id}/download` — Download exact historical binary

### Search & Evidence-Grounded Q&A
- `POST /api/workspaces/{id}/search` — Search workspace documents (`lexical`, `semantic`, or `hybrid`)
- `POST /api/workspaces/{id}/ask` — Ask question; returns evidence-backed answer with verifiable citations, or **explicitly abstains** when evidence is insufficient

---

## 🧪 Testing & Verification

Run the full automated test suite, linter, and static type checker:

```bash
# Run all automated tests
uv run pytest -v

# Run Ruff linter
uv run ruff check .

# Check code formatting
uv run ruff format --check .

# Run static type checker
uv run mypy src
```

---

## 🔒 Key Architectural Decisions

1. **Document Identity vs. Binary Equality (ADR 0001)**:
   A matching SHA-256 hash indicates identical bytes, but does not imply identical logical identity or user intent. AskBase calculates and exposes exact hash matches without automatically merging or deleting records. See [`docs/adr/0001-document-identity-and-duplicate-handling.md`](docs/adr/0001-document-identity-and-duplicate-handling.md).
2. **Version Immutability**:
   Uploading a newer version increments the version counter and stores a new immutable record. Historical versions and the passages cited in earlier answers are never mutated.
3. **Tenant & Workspace Scoping**:
   Authorization dependencies verify workspace membership on every request, ensuring zero horizontal data leaks across workspaces.
4. **Mandatory Abstention**:
   The Q&A engine strictly evaluates passage evidence before answering. Unsupported questions trigger explicit abstention instead of generative hallucination.

---

## 📄 License

Private - AskBase.