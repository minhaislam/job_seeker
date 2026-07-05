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
