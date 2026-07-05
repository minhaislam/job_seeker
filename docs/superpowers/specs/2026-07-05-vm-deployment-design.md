---
name: vm-deployment
description: Deploy the job seeker FastAPI app to an Ubuntu VM under a subdomain using Docker Compose + Caddy for automatic HTTPS
metadata:
  type: project
---

# VM Deployment Design

**Date:** 2026-07-05
**Goal:** Deploy the job seeker app to an Ubuntu Linux VM, accessible via a subdomain with automatic HTTPS.

---

## Decisions

| Question | Decision |
|---|---|
| LLM on VM | No Ollama — use OpenRouter or Anthropic API via `.env` |
| VM OS | Ubuntu Linux |
| HTTPS | Yes — Let's Encrypt via Caddy (automatic) |
| Containerisation | Docker Compose |
| Reverse proxy | Caddy (automatic cert provisioning, no certbot cron) |
| Deployment trigger | Manual `git pull` + `docker compose up -d --build` |

---

## Repository additions

```
docker-compose.yml       — app + caddy services
Dockerfile               — builds the FastAPI app image
Caddyfile                — caddy reverse proxy + subdomain config
deploy/
  setup.sh               — one-time VM bootstrap (Docker install + repo clone)
```

`.env` is **never committed** — it is created manually on the VM from `.env.example`.

---

## Architecture

```
Internet
   │  443/80
   ▼
[Caddy container]  ──auto TLS (Let's Encrypt)──►  cert stored in caddy_data volume
   │  proxy → app:8000 (internal Docker network)
   ▼
[App container]  ─── reads .env (API keys)
  FastAPI + uvicorn, port 8000 (not exposed externally)
```

- Caddy is the **only** service with public ports (80, 443).
- The app container is reachable only from within the Docker network.
- HTTP traffic is auto-redirected to HTTPS by Caddy.

---

## Services (`docker-compose.yml`)

### `app`
- Built from `Dockerfile` in repo root
- Reads `.env` for `LLM_PROVIDER`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `RAPIDAPI_KEY`
- Internal port: `8000`
- No published ports

### `caddy`
- Image: `caddy:2`
- Published ports: `80`, `443`
- Reads `Caddyfile` (mounted as volume)
- Named volume `caddy_data` persists TLS certs across restarts

---

## DNS setup (one-time, manual)

In your DNS provider dashboard, add:

```
Type  Name                   Value
A     jobs.yourdomain.com    <VM public IP>
```

Replace `jobs.yourdomain.com` with your actual subdomain. Caddy will provision the cert automatically once DNS resolves.

---

## Deployment workflow

### First-time setup on VM

```bash
bash deploy/setup.sh          # install Docker, clone repo
cp .env.example .env
nano .env                     # fill in API keys
docker compose up -d          # start services
```

### Updating after code changes

```bash
git pull
docker compose up -d --build
```

No downtime: Caddy continues serving while the app container rebuilds.

---

## Files to create

### `Dockerfile`
- Base image: `python:3.12-slim`
- Install dependencies from `requirements.txt`
- Copy backend and frontend directories
- Entrypoint: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- No `--reload` in production

### `Caddyfile`
```
jobs.yourdomain.com {
    reverse_proxy app:8000
}
```
(Caddy handles TLS, HTTP→HTTPS redirect, and headers automatically.)

### `docker-compose.yml`
- Version: Compose v2 (no `version:` key needed)
- Services: `app`, `caddy`
- Network: single bridge network (`jobseeker_net`)
- Volumes: `caddy_data`, `caddy_config`
- `caddy` depends_on `app`

### `deploy/setup.sh`
- Install Docker via official apt repo
- Add current user to `docker` group
- `git clone` the repo
- Print next-steps instructions

---

## Out of scope

- CI/CD (GitHub Actions) — not needed, manual deploys only
- Ollama on VM — not needed, cloud LLM only
- Database — app is stateless (in-memory cache only)
- Authentication / access control — not in scope
