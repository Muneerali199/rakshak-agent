# Deploying RAKSHAK-NET (so the workbench works live)

The frontend is a Vite SPA on **Vercel**; the backend is a **FastAPI** service that must be
hosted separately (Render). Once both are up and `VITE_API_URL` points at the backend, anyone
visiting the Vercel URL can open `/workbench` and use it.

> Git note: the repo root is this `app/` directory (`app/.git`), pushed to
> `github.com/Muneerali199/rakshak-agent`. Vercel builds the repo root as the Vite app; the
> backend lives at `backend/` inside the repo. Commit the new files
> (`render.yaml`, `vercel.json`, `.env.example`, `backend/api/main.py`) before deploying.

## 1. Backend on Render (free)

1. Push to GitHub.
2. Render dashboard → **New → Blueprint** → select this repo. It reads `render.yaml`
   (service `rakshak-api`, root `backend`, start `uvicorn api.main:app --host 0.0.0.0 --port $PORT`).
3. After the first deploy, note the URL, e.g. `https://rakshak-api.onrender.com`.
4. In the service's **Environment**, set:
   - `ALLOWED_ORIGINS = https://<your-vercel-app>.vercel.app` (your production URL)
   - `ALLOWED_ORIGIN_REGEX = https://.*\.vercel\.app` (optional — lets preview deploys work too)
5. Verify: open `https://<render-url>/api/health` → `{"status":"ok","nodes":...,"edges":...}`.
   (Free tier sleeps when idle; the first hit after sleep cold-starts in ~1–2s while it
   regenerates the seed-42 benchmark, then stays warm.)

## 2. Frontend on Vercel

1. Import the same repo (root = `app/`). Framework preset: **Vite**. Build `pnpm build`, output `dist`.
2. Project **Settings → Environment Variables**: `VITE_API_URL = https://<your-render-url>`
   (no trailing slash). Redeploy so the value is baked into the build.
3. `vercel.json` adds an SPA rewrite so `/workbench` resolves on direct load / refresh.

## 3. Verify end-to-end
- Visit the Vercel URL → landing page → click **Open Case Workbench** (Hero, or the VisualProof /
  Footer CTA).
- The workbench top-right status dot should be green (**live**), not the red **API offline** banner.
- Entities load in the left rail; selecting one renders the graph; clicking an edge opens evidence.

## Local development (unchanged)
```
# terminal 1 — backend
cd app/backend && pip install -r api/requirements.txt && uvicorn api.main:app --reload --port 8000
# terminal 2 — frontend (pnpm-native; never npm)
cd app && pnpm install && pnpm dev      # http://localhost:5173  → /workbench
```
With `VITE_API_URL` unset, the client defaults to `http://localhost:8000`.
