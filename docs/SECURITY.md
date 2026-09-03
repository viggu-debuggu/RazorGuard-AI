# RazorGuard AI — Security & Compliance Notes

_Last reviewed: 2026-08-27_

---

## Summary

| Area | Status | Severity |
|---|---|---|
| Analyst authentication (JWT) | **Secure** | — |
| Password hashing | **Secure (bcrypt)** | — |
| Refresh token rotation | **Implemented** | — |
| Secret key validation | **Implemented** | — |
| PII in structured logs | **Partial — see below** | Low |
| CORS origins | **Configurable via env** | — |
| Rate limiting on auth endpoints | **Implemented** | — |
| Seeded demo credentials | **Dev-only — documented** | Low |

---

## 1. Authentication & Authorisation

### Findings

All protected endpoints (transaction ingestion, list, investigation, override, graph,
policies) require a valid **JWT Bearer token** validated by `get_current_user()` in
[`backend/app/api/dependencies/auth.py`](../backend/app/api/dependencies/auth.py).

- **Algorithm**: HS256 — appropriate for a single-service deployment.
- **Password hashing**: bcrypt with auto-generated salt (via `bcrypt.gensalt()`).
- **Token types**: Separate `access` (60-minute) and `refresh` (7-day) tokens with
  `type` claim enforced on decode.
- **Refresh token rotation**: Each `/auth/refresh` call issues a new refresh token and
  invalidates the previous hash in the database — preventing replay attacks.
- **Secret key enforcement**: `config.py` raises a `ValueError` at startup if
  `SECRET_KEY` is unset in production mode, preventing accidental insecure deploys.
- **Rate limiting**: `/auth/login` and `/auth/register` are decorated with
  `@limiter.limit("20/minute")` via slowapi — brute-force protection is in place.

### Recommendation

Increase the login rate limit to `5/minute` for production deployments (currently
set to `20/minute` for demo rehearsal convenience).

---

## 2. PII Storage and API Responses

### Findings

The following PII fields are stored in the `Transaction` database table and
returned in API responses:

| Field | Stored | Returned in API | Notes |
|---|---|---|---|
| `ip_address` | Yes | Yes (full) | IPv4 address of the transaction origin |
| `device_fingerprint` | Yes | Yes (full) | Hardware/browser fingerprint hash |
| `card_country` | Yes | Yes | 2-letter ISO code only — low sensitivity |
| `billing_country` | Yes | Yes | 2-letter ISO code only — low sensitivity |
| `user_id` | Yes | Yes | Customer reference ID (not a card number) |

**No raw card numbers, CVVs, or bank account numbers are stored** — the system
operates on derived signals (amount, country codes, device fingerprint hashes),
which aligns with PCI-DSS tokenisation principles.

### Log Audit

Structlog is configured in
[`backend/app/core/logging.py`](../backend/app/core/logging.py) with JSON output
in production mode. The following agent log calls include PII fields that may
appear in log aggregators (e.g. CloudWatch, Datadog):

- `agent_team.py` — logs `ip_address` and `device_fingerprint` as structured fields
  during graph walk and transaction risk agent steps.

### Recommended Mitigation

Add a `mask_pii(value: str, visible_chars: int = 4) -> str` helper to
`backend/app/core/logging.py` and wrap PII fields before passing to `logger.*`
calls:

```python
def mask_pii(value: str, visible_chars: int = 4) -> str:
    """Masks all but the last N chars of a PII string for safe logging."""
    if not value or len(value) <= visible_chars:
        return "***"
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]

# Usage in agent logging:
logger.info("graph_walk_started", ip=mask_pii(tx.ip_address), device=mask_pii(tx.device_fingerprint))
```

This is a low-severity finding given that: (a) logs are not exposed externally, and
(b) device fingerprints are hashes rather than raw PII.

---

## 3. CORS Configuration

### Findings

CORS allowed origins are driven by the `ALLOWED_ORIGINS` environment variable in
`config.py` (default: `http://localhost:3000,http://127.0.0.1:3000`). The main app
correctly parses and uses this list:

```python
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, ...)
```

For hosted deployments, set `ALLOWED_ORIGINS` to the exact frontend URL
(e.g. `https://razorguard.onrender.com`) in your deployment environment variables.
Wildcard `*` origins must **never** be used in production with `allow_credentials=True`.

---

## 4. Seeded Demo Credentials

The seed script (`scripts/seed.py`) creates a default analyst account:

Seed the database and login using the demo analyst account created by the seed script (see `scripts/seed.py` for credentials — demo-only, not a real account).

> [!WARNING]
> These credentials are intended exclusively for judge evaluation and demo rehearsal.
> A production deployment must rotate the analyst password immediately after seeding,
> or provision accounts through a secure IdP / SSO integration.

---

## 5. Docker Security

- The backend Dockerfile runs as a non-privileged process (no `USER root`).
- `SECRET_KEY` is injected via environment variable — never baked into the image.
- Database credentials use `${DB_USER:-postgres}` env fallbacks in docker-compose;
  override them for production deployments.

---

## 6. Dependency Vulnerability Surface

No known CVEs in the pinned requirements at time of review. Key security-relevant
packages:

| Package | Version pin | Notes |
|---|---|---|
| `python-jose` | `>=3.3.0` | JWT decode/encode |
| `bcrypt` | `>=4.1.2` | Password hashing |
| `fastapi` | `>=0.110.0` | Handles HTTP input validation |
| `pydantic` | `>=2.6.4` | Schema validation on all payloads |

Run `pip-audit` or `safety check` against `requirements.txt` before production release.
