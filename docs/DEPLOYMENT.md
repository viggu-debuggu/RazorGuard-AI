# RazorGuard AI — Deployment Guide

Deployment guide for **Render.com** (free tier compatible). Both the FastAPI backend
and Next.js frontend can be deployed as separate Render Web Services.

> [!NOTE]
> For a quick demo, Docker Compose on a single VM (e.g. a $6/month DigitalOcean droplet)
> is the simplest approach. The Render guide below covers a production-grade split deployment.

---

## Prerequisites

- GitHub repo forked/cloned and pushed to your own account
- Render.com account (free tier is sufficient for demo)
- A Gemini API key (optional — `LLM_PROVIDER=mock` works without it)

---

## Architecture on Render

```
[Render PostgreSQL] ← DATABASE_URL
        ↑
[Render Web Service: backend]  ←  Docker (./backend/Dockerfile)
        ↑
[Render Web Service: frontend] ←  Next.js (./frontend/Dockerfile)
        ↑
[Public Browser]
```

---

## Step 1 — PostgreSQL Database

1. In the Render dashboard, click **New → PostgreSQL**.
2. Name it `razorguard-db`, choose the free region.
3. Note the **Internal Database URL** — you'll use it as `DATABASE_URL` for the backend.

> [!IMPORTANT]
> The pgvector extension is **not** available on Render's free Postgres tier.
> The codebase automatically falls back to in-memory cosine similarity when pgvector
> is absent (`vector_store.py` dialect detection). The system is fully functional
> without pgvector — only the semantic policy search speed is affected.
> For full pgvector support, use a managed Postgres service that supports it
> (e.g. Supabase, Neon, or a self-hosted instance).

---

## Step 2 — Backend Web Service

1. Click **New → Web Service**.
2. Connect your GitHub repo.
3. Set:
   - **Root Directory**: `backend`
   - **Environment**: `Docker`
   - **Dockerfile path**: `./Dockerfile`
   - **Instance type**: Free (or Starter for better cold-start performance)

4. Set the following **Environment Variables**:

| Variable | Value | Required |
|---|---|---|
| `DATABASE_URL` | Internal DB URL from Step 1 | **Yes** |
| `SECRET_KEY` | Random 64-char string (e.g. `openssl rand -hex 32`) | **Yes** |
| `ENVIRONMENT` | `production` | **Yes** |
| `LLM_PROVIDER` | `gemini` or `mock` | **Yes** |
| `GEMINI_API_KEY` | Your Gemini API key | Only if `LLM_PROVIDER=gemini` |
| `ALLOWED_ORIGINS` | Your frontend URL (e.g. `https://razorguard-frontend.onrender.com`) | **Yes** |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Yes |
| `LOCAL_STORAGE_PATH` | `./data/storage` | Yes |

5. Set **Start Command** to:
   ```
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

6. Click **Deploy**. After the service is live, note the backend URL
   (e.g. `https://razorguard-backend.onrender.com`).

7. **Run the seeder** using the Render Shell (Web Service → Shell tab):
   ```bash
   python scripts/seed_data.py
   ```

---

## Step 3 — Frontend Web Service

1. Click **New → Web Service**.
2. Connect your GitHub repo.
3. Set:
   - **Root Directory**: `frontend`
   - **Environment**: `Docker`
   - **Dockerfile path**: `./Dockerfile`

4. Set the following **Environment Variables**:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | Your backend URL from Step 2 (e.g. `https://razorguard-backend.onrender.com`) |

5. Click **Deploy**. The frontend will be available at its Render URL.

---

## Step 4 — Verify

1. Navigate to `https://<your-frontend>.onrender.com`
2. Seed the database and login using the demo analyst account created by the seed script (see `scripts/seed.py` for credentials — demo-only, not a real account).
3. Confirm the three demo scenarios appear in the transaction list

---

## Alternative: Single-VM Docker Compose

For faster iteration (e.g. DigitalOcean Droplet, AWS EC2, or any Linux VM):

```bash
# On the VM
git clone https://github.com/viggu-debuggu/RazorGuard-AI.git
cd RazorGuard-AI
cp .env.example .env

# Edit .env:
# - Set SECRET_KEY to a strong random value
# - Set NEXT_PUBLIC_API_URL to http://<your-vm-ip>:8000
# - Set ALLOWED_ORIGINS to http://<your-vm-ip>:3000
# - Set GEMINI_API_KEY if using real LLM

docker compose up -d --build
docker compose exec backend python scripts/seed_data.py
```

Open `http://<your-vm-ip>:3000` in a browser.

---

## Required Environment Variables (Summary)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/razorguard_db` |
| `SECRET_KEY` | JWT signing secret (min 32 chars) | Dev fallback only — **must set in prod** |
| `ENVIRONMENT` | `development` / `production` | `development` |
| `LLM_PROVIDER` | `gemini` or `mock` | `mock` |
| `GEMINI_API_KEY` | Gemini API key | Optional |
| `ALLOWED_ORIGINS` | Comma-separated allowed CORS origins | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | Backend URL seen by the browser | `http://localhost:8000` |
| `EMBEDDING_MODEL_NAME` | Sentence transformer model name | `all-MiniLM-L6-v2` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime | `60` |
