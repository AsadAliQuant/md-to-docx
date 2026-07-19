# Deployment Guide

Two separate deploys — the backend went first because the frontend needs its
live URL baked in at build time.

| Piece | What | Where | Live URL |
|---|---|---|---|
| Backend | Flask + Pandoc (`app.py`, `Dockerfile`) | Google Cloud Run, project `proud-hook-472715-k9`, region `us-central1` | `https://md-to-docx-635200713390.us-central1.run.app` |
| Frontend | Astro static site (`frontend/`) | Cloudflare Pages, project `free-md-to-docx` | `https://free-md-to-docx.pages.dev` |

There used to be 4 additional Cloudflare Pages projects serving an identical
build under different names (`md-to-docx`, `md-to-docx-free`,
`free-md-to-docx-free`, `md-to-docx-free-converter`) — these were parallel
name options from the initial setup, not staging/prod variants. They've been
deleted to avoid duplicate-content SEO issues and to keep deploys simple;
`free-md-to-docx` is now the single canonical frontend.

To redeploy the frontend after a change:
```bash
cd frontend && npm run build
npx wrangler pages deploy dist --project-name=free-md-to-docx
```

Both are deployed and verified end-to-end (upload → convert → download works
through the live frontend URL, and CORS is locked to it).

---

## Step 1 — Backend: Cloud Run

```bash
gcloud auth login
gcloud config set project proud-hook-472715-k9
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud run deploy md-to-docx \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=2 \
  --memory=512Mi \
  --cpu=1 \
  --concurrency=4 \
  --set-env-vars=ALLOWED_ORIGINS=https://free-md-to-docx.pages.dev
```

Run from the repo root. Verify: `curl https://md-to-docx-635200713390.us-central1.run.app/health` → `{"pandoc": true}`.

## Step 2 — Point the frontend at the backend

```bash
cd frontend
echo "PUBLIC_API_URL=https://md-to-docx-635200713390.us-central1.run.app" > .env.production
```

Astro inlines `PUBLIC_*` vars at build time, so this must exist before `npm run build`.

## Step 3 — Frontend: Cloudflare Pages

```bash
cd frontend
npm run build
npx wrangler pages deploy dist --project-name=free-md-to-docx
```

**Gotcha:** on a project's *first-ever* deploy, `wrangler pages deploy` may
prompt to auto-migrate to the newer Workers-based Pages platform — it adds an
`@astrojs/cloudflare` SSR adapter, unused KV/Images bindings, and rewrites
`package.json`/`astro.config.mjs`, none of which this static site needs. If
that happens, undo it and redeploy with `--force` to stay on plain static
Pages (this is what we ended up doing):
```bash
npx wrangler pages project create free-md-to-docx --production-branch=main
npx wrangler pages deploy dist --project-name=free-md-to-docx --force
```
Once the project exists, subsequent deploys don't need `--force`.

## Step 4 — CORS lock-down (already done, env-var only, no rebuild)

Only one frontend origin exists now, so this is a single value — no comma
escaping needed:
```bash
gcloud run services update md-to-docx \
  --region us-central1 \
  --project=proud-hook-472715-k9 \
  --update-env-vars="ALLOWED_ORIGINS=https://free-md-to-docx.pages.dev"
```

To allow another URL later (e.g. a custom domain), pass a comma-separated
list instead — since the value would then contain commas, use the `^;^`
prefix so gcloud's own `KEY=VAL,KEY=VAL` parsing for `--update-env-vars`
doesn't misread it as multiple keys:
```bash
--update-env-vars="^;^ALLOWED_ORIGINS=https://free-md-to-docx.pages.dev,https://yourdomain.com"
```
`--update-env-vars` replaces the named var's value entirely, it doesn't append.

---

## Redeploying later

- **Backend changed** (`app.py`, `Dockerfile`, `requirements.txt`): re-run the
  Step 1 command from the repo root. Existing env vars persist automatically.
- **Frontend changed** (`frontend/src/**`): re-run Step 3's build + deploy —
  no `--force` needed now that the Pages project exists.

## Accounts / projects in play

- GCP project: `proud-hook-472715-k9` ("My First Project") — reused rather
  than creating a fresh project, because this account's project-creation
  quota was maxed at 6/6 and a soft-deleted project (`certain-horizon-303207`,
  which had no billing and no real resources) still counts against quota for
  30 days.
- Cloudflare account: `Asadamyn@gmail.com's Account` — a different account
  than wrangler was originally logged into. Switch with `npx wrangler logout`
  then `npx wrangler login` if you need to change which account owns this again.
