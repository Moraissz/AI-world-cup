# Deploy Strategy — AI World Cup Agent

## Overview

The system has three logical layers, each with different deployment constraints:

```
WhatsApp ↔ Omni (WhatsApp bridge, needs persistent session)
               ↓
         Genie (agent orchestrator, needs tmux + postgres)
               ↓
         FastAPI (stateless HTTP, deployable anywhere)
               ↓
         api-sports.io (external, no deploy needed)
```

**Key constraint:** Omni uses Baileys to connect to WhatsApp. The WhatsApp session (auth files) must persist across restarts. This means Omni and Genie cannot run in ephemeral containers — they need a machine with persistent storage.

---

## Recommended: Oracle Cloud Always Free (everything free, nothing local)

**Why Oracle and not Railway/Render/Fly for Genie+Omni:**
Railway and Render free tiers use ephemeral storage — the WhatsApp session (Baileys auth files) is lost on every restart, forcing a re-scan of the QR code. Fly.io persistent volumes solve this but require a paid plan for the memory needed by Genie+Postgres. Oracle's Always Free tier is the only genuinely free option with real persistent storage.

**Oracle Always Free includes forever (no expiry, no credit card charge):**
- 4 ARM Ampere OCPUs + 24 GB RAM (more than enough for everything)
- 200 GB block storage (WhatsApp session persists)
- Public IP address

### Setup on Oracle Cloud

1. Create account at [cloud.oracle.com](https://cloud.oracle.com) (requires credit card for identity verification only — never charged for Always Free)
2. Create an Ampere A1 Compute instance: Ubuntu 22.04, ARM, 2 OCPUs, 4 GB RAM
3. SSH in and run:

```bash
# Install system deps
sudo apt update && sudo apt install -y python3-pip python3-venv curl git tmux

# Install Bun (for Omni)
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc

# Install Genie + Omni (follow their install docs)
# https://github.com/automagik-dev/genie
# https://github.com/automagik-dev/omni

# Install Claude Code (required by Genie)
npm install -g @anthropic-ai/claude-code
export ANTHROPIC_API_KEY=sk-ant-...    # add to ~/.bashrc

# Clone and setup project
git clone https://github.com/Moraissz/AI-world-cup.git
cd AI-world-cup
bash setup.sh

# Fill in .env
nano .env   # set FOOTBALL_API_KEY, OMNI_API_KEY

# Start everything
make start
genie omni handshake
genie agent register world-cup-specialist --dir agents/world-cup-specialist
omni instances list   # note <instance-id>
omni connect <instance-id> world-cup-specialist --mode turn-based --reply-filter all
make agent-spawn
```

4. Open Oracle firewall port 8000 (optional — only needed if exposing the API publicly):
   - In Oracle Console: Networking → VCN → Security Lists → Add Ingress Rule for port 8000

### FastAPI on Railway (optional split)

If you prefer Railway's deploy UX for the FastAPI layer:

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init && railway up
# Railway gives you: https://ai-world-cup-xxx.up.railway.app
```

Then update `.env` on the Oracle VM:
```env
API_BASE_URL=https://ai-world-cup-xxx.up.railway.app
```

The agent HEARTBEAT uses `${API_BASE_URL:-http://localhost:8000}` so no code change needed.

---

## Option A — Single VPS (paid, simplest)

All services on one machine. Simplest setup, easiest to share a phone number for evaluation.

**Minimum spec:** 1 vCPU, 1 GB RAM, 20 GB disk  
**Cost:** ~$4–6/month (DigitalOcean Basic, Hetzner CX11, Fly.io shared)

```
VPS
├── Omni (port 8882)       — WhatsApp bridge, stores session on disk
├── Genie (postgres 5432)  — agent orchestrator
├── FastAPI (port 8000)    — football data API
└── world-cup-specialist   — Claude agent, spawned by Genie
```

#### Setup on VPS

```bash
# 1. Install dependencies (Ubuntu 22.04)
curl -fsSL https://bun.sh/install | bash
curl -fsSL https://raw.githubusercontent.com/automagik-dev/genie/main/install.sh | bash
curl -fsSL https://raw.githubusercontent.com/automagik-dev/omni/main/install.sh | bash

# Install Claude Code (required for Genie)
npm install -g @anthropic-ai/claude-code

# 2. Clone repo
git clone https://github.com/Moraissz/AI-world-cup.git
cd AI-world-cup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in FOOTBALL_API_KEY, OMNI_API_KEY, and set ANTHROPIC_API_KEY

# 4. Start services
make start

# 5. Register agent (first time only)
genie omni handshake
genie agent register world-cup-specialist --dir agents/world-cup-specialist
omni instances list        # note <instance-id>
omni connect <instance-id> world-cup-specialist --mode turn-based --reply-filter all

# 6. Spawn agent
make agent-spawn
```

#### Expose the WhatsApp QR code

When first connecting, Omni generates a QR code. To scan it from the VPS:

```bash
# Option 1: print QR directly in terminal (if connected via SSH)
omni instances list   # check status
# Omni shows QR code in its own log output during startup

# Option 2: start Omni in foreground to see QR
omni start --foreground
```

---

### Option B — Split deploy (FastAPI in cloud, Genie+Omni local)

Use this if you already have a local machine that stays on, or want free cloud hosting for the API.

```
Railway / Render / Fly.io
└── FastAPI (port 8000) — public HTTPS URL

Local machine (stays on during evaluation window)
├── Omni (port 8882)
├── Genie (postgres 5432)
└── world-cup-specialist agent
```

#### Deploy FastAPI to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# From project root
railway init
railway up
# Railway gives you a public URL like https://ai-world-cup.up.railway.app
```

Update HEARTBEAT.md tool URL to use the Railway URL:
```bash
curl -s "https://ai-world-cup.up.railway.app/football/head-to-head?name_team_a=TEAM_A&name_team_b=TEAM_B"
```

Local setup (same as Option A steps 4–6, but without step 1).

---

### Option C — Local + ngrok (quickest for demo)

For a live demo without any cloud setup. Requires your local machine to stay on.

```bash
# Install ngrok (https://ngrok.com)
# Start services locally
make start

# Expose FastAPI (optional — only needed if sharing API publicly)
ngrok http 8000

# Register and spawn agent (same steps as Option A)
make agent-spawn
```

The WhatsApp number is tied to the Omni instance running locally. Share the number and keep the machine on during the evaluation window.

---

## Environment variables for production

```env
FOOTBALL_API_KEY=<your api-sports.io key>
OMNI_API_URL=http://localhost:8882
OMNI_API_KEY=<your omni key>
ANTHROPIC_API_KEY=<your anthropic key>  # required by Genie/Claude Code
```

On a VPS, set these in `.env` and also export `ANTHROPIC_API_KEY` in your shell profile:

```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc
source ~/.bashrc
```

---

## Keeping services alive

Use a process manager to restart services on crash or reboot.

### With systemd (Option A — VPS)

Create `/etc/systemd/system/world-cup.service`:

```ini
[Unit]
Description=AI World Cup Agent
After=network.target

[Service]
Type=forking
User=<your-user>
WorkingDirectory=/home/<your-user>/AI-world-cup
ExecStart=/usr/bin/make start
ExecStop=/usr/bin/make stop
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable world-cup
sudo systemctl start world-cup
```

### With tmux (any option — simpler)

```bash
# Start a persistent tmux session
tmux new-session -d -s world-cup
tmux send-keys -t world-cup 'cd ~/AI-world-cup && make start' Enter
tmux send-keys -t world-cup 'make agent-spawn' Enter

# Reconnect anytime
tmux attach -t world-cup
```

---

## Verifying the full end-to-end flow

```bash
# 1. Check all services
omni status             # apiStatus: reachable
genie ls                # world-cup-specialist: IDLE or ACTIVE
curl http://localhost:8000/docs

# 2. Test the API directly
curl -s "http://localhost:8000/football/head-to-head?name_team_a=Brazil&name_team_b=France" | python3 -m json.tool

# 3. Simulate a WhatsApp message (without WhatsApp)
genie agent send world-cup-specialist "Brazil vs Argentina who wins?"

# 4. Full WhatsApp test
# Send "Brazil vs Argentina" to the WhatsApp number
# Expect a response with historical stats + prediction within 30s
```

---

## Sharing the agent for evaluation

1. Make the GitHub repository public: `https://github.com/Moraissz/AI-world-cup`
2. Share the WhatsApp number connected to the Omni instance
3. Provide the evaluator with example queries:
   - "Brazil vs Argentina" (Portuguese or English both work)
   - "França contra Espanha quem ganha?"
   - "Who will win between Germany and Portugal?"

---

## Cost estimate

| Option | Monthly cost | Complexity |
|---|---|---|
| Option A (VPS — Hetzner CX11) | ~$4 | Low |
| Option A (VPS — DigitalOcean) | ~$6 | Low |
| Option B (Railway free tier + local) | $0 | Medium |
| Option C (local + ngrok) | $0 | Lowest |
