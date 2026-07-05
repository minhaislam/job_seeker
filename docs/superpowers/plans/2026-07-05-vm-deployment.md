# VM Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the job seeker FastAPI app to an Ubuntu VM at a subdomain with automatic HTTPS, using Docker Compose + Caddy as the reverse proxy.

**Architecture:** The app runs in a Docker container (no public ports). Caddy runs alongside it, terminates HTTPS, auto-provisions a Let's Encrypt cert, and proxies traffic to the app on the internal Docker network. All secrets live in `.env` on the VM only — never committed.

**Tech Stack:** Docker, Docker Compose v2, Caddy 2, Python 3.12-slim, FastAPI, uvicorn

## Global Constraints

- Python base image: `python:3.12-slim` (matches dev environment)
- No `--reload` flag in production uvicorn
- `.env` is never committed — already in `.gitignore`
- Caddy image: `caddy:2` (official)
- Docker Compose v2 syntax — no top-level `version:` key
- App is stateless — no database volumes needed
- LLM: OpenRouter or Anthropic only (no Ollama on VM)

---

### Task 1: Dockerfile

**Files:**
- Create: `Dockerfile`

**Interfaces:**
- Produces: Docker image that runs `uvicorn backend.main:app` on port 8000, with `backend/` and `frontend/` available at `/app/` (matching the relative paths in `main.py`)

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **Why this structure:** `main.py` uses relative paths `FileResponse("frontend/index.html")` and `StaticFiles(directory="frontend/static")`. Setting `WORKDIR /app` and copying both `backend/` and `frontend/` there makes these resolve correctly inside the container.

- [ ] **Step 2: Verify the image builds**

Run from repo root (requires Docker installed locally):
```bash
docker build -t jobseeker-test .
```
Expected: build completes with no errors, final line shows `Successfully built ...` or similar.

- [ ] **Step 3: Verify the container starts**

```bash
docker run --rm -e LLM_PROVIDER=openrouter -e OPENROUTER_API_KEY=test -p 8000:8000 jobseeker-test
```
Expected: uvicorn logs appear:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```
Open `http://localhost:8000` — the job seeker UI should load. Press Ctrl+C to stop.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile for production deployment"
```

---

### Task 2: docker-compose.yml + Caddyfile

**Files:**
- Create: `docker-compose.yml`
- Create: `Caddyfile`

**Interfaces:**
- Consumes: `Dockerfile` from Task 1 (the `app` service builds from it)
- Produces: `docker compose up -d` starts both services; Caddy proxies `https://<your-subdomain>` → `app:8000`

- [ ] **Step 1: Create `Caddyfile`**

```
# Edit this line — replace with your actual subdomain before deploying
jobs.yourdomain.com {
    reverse_proxy app:8000
}
```

> This is the only file that needs editing per-deployment. Caddy automatically handles TLS cert provisioning via Let's Encrypt, HTTP→HTTPS redirect, and HSTS headers. No other config is needed.

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
services:
  app:
    build: .
    env_file: .env
    networks:
      - jobseeker_net
    restart: unless-stopped

  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - jobseeker_net
    depends_on:
      - app
    restart: unless-stopped

networks:
  jobseeker_net:

volumes:
  caddy_data:
  caddy_config:
```

> `443/udp` enables HTTP/3 (QUIC) support in Caddy — harmless if the client doesn't support it.
> `caddy_data` persists the TLS certificate across container restarts.
> `caddy_config` persists Caddy's internal runtime config.
> The `app` service has no published ports — it is only reachable from within `jobseeker_net`.

- [ ] **Step 3: Validate compose syntax**

```bash
docker compose config
```
Expected: prints the merged/resolved compose config with no errors.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml Caddyfile
git commit -m "feat: add Docker Compose and Caddyfile for VM deployment"
```

---

### Task 3: VM bootstrap script

**Files:**
- Create: `deploy/setup.sh`

**Interfaces:**
- Produces: a script the user runs once on a fresh Ubuntu VM to install Docker and clone the repo; prints next-step instructions at the end

- [ ] **Step 1: Create `deploy/` directory and `setup.sh`**

```bash
#!/usr/bin/env bash
# Run once on a fresh Ubuntu VM to install Docker and clone the repo.
set -euo pipefail

REPO_URL="${1:-https://github.com/YOUR_USERNAME/job_seeker.git}"
INSTALL_DIR="$HOME/job_seeker"

echo "=== [1/4] Installing Docker dependencies ==="
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl

echo "=== [2/4] Adding Docker apt repository ==="
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "=== [3/4] Installing Docker ==="
sudo apt-get update -y
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

sudo usermod -aG docker "$USER"

echo "=== [4/4] Cloning repo ==="
git clone "$REPO_URL" "$INSTALL_DIR"

echo ""
echo "============================================"
echo " Setup complete! Next steps:"
echo "============================================"
echo ""
echo "1. Log out and back in (activates docker group for your user)"
echo ""
echo "2. cd $INSTALL_DIR"
echo ""
echo "3. Edit Caddyfile — replace 'jobs.yourdomain.com' with your subdomain:"
echo "   nano Caddyfile"
echo ""
echo "4. Create .env with your API keys:"
echo "   cp .env.example .env"
echo "   nano .env"
echo "   # Set LLM_PROVIDER=openrouter (or anthropic)"
echo "   # Fill in OPENROUTER_API_KEY or ANTHROPIC_API_KEY"
echo "   # Optionally fill in RAPIDAPI_KEY for JSearch"
echo ""
echo "5. Point an A record at this VM's public IP for your subdomain."
echo "   (Caddy won't provision the cert until DNS resolves.)"
echo ""
echo "6. Start the app:"
echo "   docker compose up -d"
echo ""
echo "7. Tail logs to confirm startup:"
echo "   docker compose logs -f"
echo ""
```

- [ ] **Step 2: Make the script executable**

```bash
chmod +x deploy/setup.sh
```

- [ ] **Step 3: Syntax-check the script**

```bash
bash -n deploy/setup.sh
```
Expected: no output (exit code 0 means no syntax errors).

- [ ] **Step 4: Commit**

```bash
git add deploy/setup.sh
git commit -m "feat: add VM bootstrap script"
```

---

## Post-deployment smoke test (run on the VM after DNS propagates)

- [ ] `docker compose ps` — both `app` and `caddy` show `running`
- [ ] `docker compose logs app` — no Python tracebacks on startup
- [ ] `docker compose logs caddy` — shows `certificate obtained successfully` for your subdomain
- [ ] Open `https://<your-subdomain>` in a browser — job seeker UI loads over HTTPS with a valid cert
- [ ] Search for a job — results appear (confirms the app container is healthy)
- [ ] Click a job card — scoring runs (confirms LLM API key in `.env` is working)

---

## Updating the app after changes

```bash
# On the VM, from the repo directory:
git pull
docker compose up -d --build
docker compose logs -f   # watch for successful restart
```
