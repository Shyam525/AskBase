# Legacy Inventory & Migration Plan

## 1. Overview

AskBase previously existed in a bifurcated, transitional state across two distinct legacy backend prototypes:
1. **TypeScript / Express Monolith**: Contained the core application structure, Zod-based configuration parsing, structured error hierarchy, migration runner with PostgreSQL initial schema, and basic health endpoints.
2. **.NET 10 / ASP.NET Core API**: Contained EF Core entities (`Organization`, `User`, `RefreshToken`), tenant-scoped middleware, BCrypt password hashing, and JWT issuance endpoints (`/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/me`).

The objective is to consolidate these dual prototypes into a single, authoritative, production-grade Python backend built with FastAPI, SQLAlchemy 2.x, Alembic, and Pydantic Settings.

---

## 2. Inventory of Tracked Legacy Code

### 2.1 TypeScript Implementation
| File Path | Purpose | Fate |
| :--- | :--- | :--- |
| `src/config/index.ts` | Zod environment variable parsing and validation | **Removed**; translated to `askbase.core.settings` |
| `src/errors/index.ts` | Operational error hierarchy (`AppError`, `ValidationError`, etc.) | **Removed**; translated to `askbase.core.errors` |
| `src/middleware/error-handler.ts` | Global error-handling middleware & JSON response formatter | **Removed**; translated to FastAPI exception handlers |
| `src/middleware/validate.ts` | Express request schema validation | **Removed**; superseded by FastAPI/Pydantic validation |
| `src/modules/auth/crypto.ts` | BCrypt hashing & JWT signing/verification | **Removed**; replaced with Argon2 & PyJWT in `askbase.core.security` |
| `src/modules/health/health.routes.ts` | `/health` liveness and `/ready` readiness probes | **Removed**; translated to `askbase.api.routers.health` |
| `src/modules/users/user.types.ts` | User interface and DTO types | **Removed**; translated to SQLAlchemy models and Pydantic schemas |
| `src/modules/workspaces/workspace.types.ts` | Workspace and membership types (`owner`, `admin`, `member`) | **Removed**; translated to SQLAlchemy models and Pydantic schemas |
| `src/database/index.ts` | `pg` pool connection management and health ping | **Removed**; replaced by SQLAlchemy async engine in `askbase.db` |
| `src/database/migrator.ts` | Custom SQL migration runner with `schema_migrations` tracking | **Removed**; superseded by Alembic |
| `src/database/migrations/001_initial_schema.sql` | Initial SQL schema (users, workspaces, memberships) | **Removed**; converted to Alembic baseline migration |
| `src/database/migrate-cli.ts` | CLI script for applying migrations | **Removed**; replaced by `alembic upgrade head` |
| `src/app.ts` | Express application factory | **Removed**; replaced by FastAPI factory in `askbase.main` |
| `src/index.ts` | Server bootstrap and graceful shutdown handler | **Removed**; replaced by FastAPI lifespan & Uvicorn entrypoint |
| `package.json` / `package-lock.json` | Node.js dependency manifests | **Removed**; replaced by `pyproject.toml` and `uv.lock` |
| `tsconfig.json` / `tsconfig.build.json` | TypeScript compiler configuration | **Removed** |
| `vitest.config.ts` | Vitest runner configuration | **Removed**; replaced by `pytest` and `pyproject.toml` |
| `test/*.test.ts` | Vitest unit, validation, and migration tests | **Removed**; translated to comprehensive `pytest` suite |

### 2.2 .NET 10 Implementation
| File Path | Purpose | Fate |
| :--- | :--- | :--- |
| `AskBase.slnx` | Visual Studio Solution file | **Removed** |
| `src/AskBase.Api/AskBase.Api.csproj` | Web API project file | **Removed** |
| `src/AskBase.Api/Program.cs` | ASP.NET Core host configuration, DI, middleware pipeline | **Removed** |
| `src/AskBase.Api/Controllers/AuthController.cs` | Auth controller endpoints (`register`, `login`, `refresh`, `logout`, `me`) | **Removed**; translated to `askbase.api.routers.auth` |
| `src/AskBase.Api/Middleware/GlobalExceptionMiddleware.cs` | Central exception filter | **Removed**; handled by FastAPI exception handlers |
| `src/AskBase.Api/Middleware/TenantMiddleware.cs` | Resolves `tenant_id` from JWT claim into request scope | **Removed**; translated to FastAPI dependency `get_current_workspace` |
| `src/AskBase.Application/DTOs/AuthDtos.cs` | Auth request/response records | **Removed**; translated to Pydantic schemas |
| `src/AskBase.Application/Common/TenantContext.cs` | Scoped tenant identifier container | **Removed**; translated to FastAPI request state / dependencies |
| `src/AskBase.Application/Interfaces/IAuthService.cs` | Auth service interface | **Removed**; translated to Python service protocols/classes |
| `src/AskBase.Domain/Entities/Organization.cs` | Organization entity (name, slug, plan, seat limits) | **Removed**; consolidated with Workspace entity |
| `src/AskBase.Domain/Entities/User.cs` | User entity with Org foreign key | **Removed**; translated to `askbase.models.user.User` |
| `src/AskBase.Domain/Entities/RefreshToken.cs` | RefreshToken entity for persistent session revocation | **Removed**; translated to `askbase.models.token.RefreshToken` |
| `src/AskBase.Infrastructure/Data/AppDbContext.cs` | EF Core DbContext with multi-tenant query filter | **Removed**; translated to SQLAlchemy models and repository queries |
| `src/AskBase.Infrastructure/Services/AuthService.cs` | Registration, login, token rotation logic | **Removed**; translated to `askbase.services.auth` |
| `src/AskBase.Infrastructure/Migrations/*` | EF Core initial migrations | **Removed**; superseded by Alembic |

---

## 3. Valuable Behavioral Decisions Preserved

1. **Configuration Strictness**:
   - Environment variables validated at startup.
   - Production mode requires a JWT secret of at least 32 characters and fails closed if missing.
   - A safe local development fallback secret is permitted in `development` and `test` environments only.
2. **Standardized Error JSON Contract**:
   - Errors consistently return `{ "error": { "code": "...", "message": "...", "details": ... } }`.
   - Distinct operational error codes: `VALIDATION_ERROR` (400), `BAD_REQUEST` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409), `SERVICE_UNAVAILABLE` (503), `INTERNAL_SERVER_ERROR` (500).
   - Database constraint mapping: unique violation maps to 409 Conflict, foreign key violation maps to 400 Bad Request.
   - Internal stack traces and raw SQL errors are withheld from client responses.
3. **Health Probes**:
   - `/health/live` (and `/health` alias) confirms process responsiveness.
   - `/health/ready` (and `/ready` alias) executes a database health probe (`SELECT 1`), returning 200 with latency or 503 Service Unavailable when unreachable.
4. **Multi-Tenancy & Authorization Model**:
   - Workspaces serve as isolation boundaries.
   - Explicit membership roles: `owner`, `admin`, `member`.
   - All tenant resources (documents, versions, chunks, queries) must enforce workspace scoping and membership authorization at the dependency layer.
   - Cross-tenant access attempts are strictly rejected.
5. **Database Schema & Integrity**:
   - UUID primary keys generated by default.
   - Case-insensitive uniqueness enforcement for emails and workspace slugs (`LOWER(...)`).
   - Cascading deletes for dependent records where appropriate.
   - Foreign key indexing on lookup columns.
6. **Authentication Protocol**:
   - Registration creates workspace/organization and initializes the creator as admin/owner.
   - Access tokens are short-lived (15 minutes default) with HMAC-SHA256, explicit issuer, audience, and subject claims.
   - Refresh tokens are securely generated, stored in the database, and revocable on logout.
   - Password hashing upgraded from legacy bcrypt to modern Argon2id (`argon2-cffi`).

---

## 4. Net New Python Architecture Additions

The Python rebuild adds the core knowledge engine requirements not present in either prototype:
1. **Document Identity & Versioning**:
   - Logical document vs. immutable version separation.
   - Content hashing (SHA-256) per uploaded binary.
   - Explicit ADR detailing duplicate-handling strategies (`docs/adr/0001-document-identity-and-duplicate-handling.md`).
2. **Ingestion Pipeline**:
   - Multi-format text extraction (Plain text, Markdown with section awareness, PDF).
   - Safe file storage with path traversal protection and magic bytes format verification.
   - Configurable chunking preserving provenance (page numbers, section headings).
   - Status tracking with diagnosable error states.
3. **Evidence-Grounded Retrieval & Abstention**:
   - Full-text search (PostgreSQL `tsvector`/`tsquery` and portable test fallback).
   - Configurable embedding provider interface (`FakeEmbeddingProvider` for deterministic testing; semantic/hybrid path).
   - Question answering engine with verifiable citation mapping and strict abstention when evidence is insufficient.
