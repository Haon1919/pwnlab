# BlaqLiq

A self-hosted penetration testing lab platform. Spin up deliberately vulnerable Docker containers, attack them from a pre-tooled attacker container, optionally enable a deterministic detection system (war games mode), and use Gemini AI to generate custom scenarios or launch blind blackbox challenges.

```
blaqliq session start dvwa-beginner
blaqliq session start dvwa-hardened --wargame
blaqliq ai generate "PHP app with SQL injection and weak admin creds"
blaqliq ai blackbox
```

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Web UI](#web-ui)
- [Scenarios](#scenarios)
  - [Built-in Scenarios](#built-in-scenarios)
  - [Writing Your Own](#writing-your-own)
  - [YAML Schema](#yaml-schema)
- [War Games Mode](#war-games-mode)
- [AI Features](#ai-features)
  - [Scenario Generation](#scenario-generation)
  - [Blackbox Mode](#blackbox-mode)
- [Docker Boxes](#docker-boxes)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Plan Limits](#plan-limits)
- [Security Model](#security-model)
- [Development](#development)
- [Project Structure](#project-structure)

---

## Overview

BlaqLiq runs entirely on your own machine (or server). Each lab session gets:

- An **isolated Docker bridge network** with its own subnet (`10.100.{n}.0/24`)
- One or more **target containers** (vulnerable apps/services)
- An **attacker container** pre-loaded with pentesting tools
- Optionally, a **wargame sidecar** container that watches for detection events and scores your stealth

Sessions are time-limited (default 4 hours), fully isolated from each other, and torn down cleanly on stop.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Your Machine                        │
│                                                         │
│  ┌─────────┐   REST API   ┌──────────────────────────┐  │
│  │ blaqliq  │ ──────────── │  FastAPI Backend          │  │
│  │  CLI    │              │  SQLite · APScheduler     │  │
│  └─────────┘              └────────────┬─────────────┘  │
│                                        │ docker-py       │
│  ┌─────────┐   HTTP       ┌────────────▼─────────────┐  │
│  │ Browser │ ──────────── │  React Frontend (Vite)   │  │
│  └─────────┘              └──────────────────────────┘  │
│                                                         │
│  Per session:                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Docker bridge  10.100.N.0/24                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │   │
│  │  │ target-1 │  │ attacker │  │   sidecar    │  │   │
│  │  │ (dvwa)   │  │ (tools)  │  │ (detection)  │  │   │
│  │  └──────────┘  └──────────┘  └──────────────┘  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

- **Backend**: FastAPI (Python) — REST API, Docker SDK, Gemini integration, SQLite persistence
- **Frontend**: React + Vite — dashboard, scenario library, war games status, AI generator
- **CLI**: Click + Rich — thin client talking directly to the backend API
- **War games detection**: 100% deterministic at runtime (iptables logs + fail2ban + auditd). Gemini is only used at scenario *setup* time, never during gameplay.

---

## Prerequisites

- **Docker** (Engine 24+) with the Docker socket accessible
- **Docker Compose** v2
- **Python 3.11+** (for the CLI)
- **Node 20+** (only needed for frontend development; production uses the built image)

Pull the target images you plan to use before your first session:

```bash
make pull-targets
# or manually:
docker pull vulnerables/web-dvwa:latest
docker pull webgoat/goat-and-wolf:latest
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/yourname/blaqliq
cd blaqliq

# 2. Configure
cp .env.example .env
# Edit .env — at minimum change SECRET_KEY and FERNET_KEY

# 3. Start the stack (backend + frontend)
make dev

# 4. Install the CLI
make install-cli

# 5. Register and log in
blaqliq auth register
blaqliq auth login

# 6. List available scenarios
blaqliq session list

# 7. Start a lab
blaqliq session start dvwa-beginner
```

The backend API is at `http://localhost:8000` and the web UI at `http://localhost:3000`.

---

## CLI Reference

### Authentication

```bash
blaqliq auth register             # create account
blaqliq auth login                # login (saves token to ~/.blaqliq/config.yaml)
blaqliq auth logout
blaqliq auth whoami
blaqliq auth create-key --label ci   # create API key (shown once, never stored raw)
```

### Sessions

```bash
# List available scenarios
blaqliq session list

# Start a standard session
blaqliq session start dvwa-beginner

# Start with war games detection active
blaqliq session start dvwa-hardened --wargame

# Start a blackbox session (target is hidden)
blaqliq session start dvwa-beginner --blackbox

# Show all your sessions
blaqliq session status

# Show a specific session
blaqliq session status <session-id>

# Submit a flag
blaqliq session flag <session-id> "BLAQLIQ{...}" --objective flag-1

# Stop a session
blaqliq session stop <session-id>

# Convenience aliases (same as session start/stop)
blaqliq start dvwa-beginner
blaqliq stop <session-id>
```

Once a session is running, connect to the attacker container:

```bash
docker exec -it blaqliq-attacker-<session-id-prefix> bash
```

The target IP is printed on start and also set as an environment variable inside the attacker (`TARGET_DVWA_IP`, `TARGET_WEBGOAT_IP`, etc.).

### War Games

```bash
# Show detection status once
blaqliq wargame status <session-id>

# Live-refresh every 5 seconds (Ctrl+C to stop)
blaqliq wargame status <session-id> --watch
```

The stealth meter displays:

```
● Detection Level: CLEAN
Score: 4/100
████░░░░░░░░░░░░░░░░
Thresholds: CLEAN<10 | WARNING≥10 | DETECTED≥40 | BUSTED≥100
```

### AI

```bash
# Generate a scenario with Gemini
blaqliq ai generate "vulnerable SSH server with default creds and a backdoored FTP service"
blaqliq ai generate "PHP app with SQLi" --difficulty intermediate --tags web,sqli --wargame

# Start immediately after generating
blaqliq ai generate "..." --start

# Blackbox mode — target is hidden, discover it with nmap
blaqliq ai blackbox

# After stopping a blackbox session, reveal what the target was
blaqliq ai reveal <session-id>
```

### Config

The CLI stores its state in `~/.blaqliq/config.yaml`:

```yaml
api_url: http://localhost:8000
token: eyJ...
```

You can point the CLI at a remote server:

```bash
blaqliq auth login --url https://your-blaqliq-server.com
```

---

## Web UI

Start with `make dev`, then open `http://localhost:3000`.

| Page | What it shows |
|------|---------------|
| **Login / Register** | Account creation and auth |
| **Dashboard** | Active sessions (live-polling every 10s), quick-start hints, session history |
| **Scenario Library** | All scenarios with search, difficulty filter, Start / War Games buttons, AI Generator panel |
| **Active Session** | Session details, `docker exec` hint, flag submission |
| **Wargame View** | Live detection meter (5s auto-refresh), detection event log |

---

## Scenarios

### Built-in Scenarios

| ID | Name | Difficulty | Tags | Wargame |
|----|------|------------|------|---------|
| `dvwa-beginner` | DVWA: SQL Injection Fundamentals | beginner | web, sqli, xss | no |
| `webgoat-sqli` | WebGoat: SQL Injection Chain | intermediate | web, sqli, java | no |
| `metasploitable-vsftpd` | Metasploitable: vsftpd Backdoor | beginner | network, ftp, exploit | no |
| `dvwa-hardened` | DVWA: SQL Injection (Detection Active) | intermediate | web, sqli, stealth | **yes** |

### Writing Your Own

```bash
# Scaffold a new scenario template
make scenario NEW=my-custom-lab

# Edit it
vim scenarios/custom/my-custom-lab.yaml

# Run it
blaqliq session start my-custom-lab
```

Or upload via the API:

```bash
curl -X POST http://localhost:8000/scenarios \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@my-scenario.yaml"
```

### YAML Schema

Every scenario is a single YAML file. The full schema is documented in `scenarios/_schema.yaml`. Key fields:

```yaml
schema_version: "1.0"

metadata:
  id: "my-lab"                  # unique, kebab-case
  name: "My Lab"
  difficulty: "beginner"        # beginner | intermediate | advanced | expert
  tags: ["web", "sqli"]
  ai_generated: false

network:
  subnet: "10.100.{session_offset}.0/24"   # {session_offset} filled at runtime
  internal: true                            # true = no internet access (recommended)

targets:
  - id: "dvwa"
    image: "vulnerables/web-dvwa:latest"   # must be in BLAQLIQ_ALLOWED_TARGET_IMAGES
    ip: "10.100.{session_offset}.10"
    mem_limit: "512m"
    cpu_quota: 50000

attacker:
  tool_profile: "web"          # web | network | crypto | full
  kali: false                  # true requires pro+ plan

objectives:
  - id: "flag-1"
    description: "Exploit SQLi to retrieve admin creds"
    validation:
      method: "flag_string"
      value: "BLAQLIQ{your_flag_here}"

wargame: null   # see War Games section for the full block
```

**Security constraint**: the `image` field for every target must be in the `BLAQLIQ_ALLOWED_TARGET_IMAGES` whitelist (set in `.env`). This is enforced for both hand-written and AI-generated scenarios before any container is ever run.

---

## War Games Mode

War games adds a detection sidecar to your session. The sidecar watches for:

| Detection Type | Backend | Default Severity |
|----------------|---------|-----------------|
| Port scanning | iptables kernel log | warning |
| Brute force attempts | fail2ban | detected |
| Shell spawned by web process | auditd | **busted** (instant game over) |

Detection levels and score thresholds:

```
CLEAN    score < 10
WARNING  score ≥ 10   (+10 per iptables trigger)
DETECTED score ≥ 40   (+30 per fail2ban ban)
BUSTED   score ≥ 100  (+100 for any "busted" severity event — also instant)
```

The backend polls the sidecar's JSONL event stream every 5 seconds. No AI is involved at runtime — all detection is pattern-matching against the rules defined in the scenario YAML.

**Tips for staying clean:**

```bash
# Use slow/quiet nmap instead of aggressive
nmap -T1 -sV 10.100.N.10         # quiet
nmap -T4 --script vuln 10.100.N.10  # will trigger WARNING

# Avoid repeated login failures (triggers fail2ban → DETECTED)
# A single shell from apache/nginx → BUSTED immediately
```

---

## AI Features

AI features require a [Google Gemini API key](https://aistudio.google.com/app/apikey). The model used is `gemini-1.5-flash`.

Store your key on registration:

```bash
blaqliq auth register --gemini-key AIza...
```

Or pass it per-command:

```bash
blaqliq ai generate "..." --api-key AIza...
```

Keys are **Fernet-encrypted at rest** in the database. The raw key is never stored.

### Scenario Generation

Gemini is called **once at generation time** to produce a scenario YAML. The output is validated against the schema and image whitelist before being saved. If validation fails, the scenario is rejected — no containers are ever run from an invalid scenario.

```bash
blaqliq ai generate "Apache server running PHP 5.6 with remote code execution via file upload"
blaqliq ai generate "MySQL 5.5 exposed on network with root/root creds" --difficulty beginner --tags network,sql
blaqliq ai generate "XSS + CSRF chain in a Node.js app" --wargame --difficulty advanced
```

Generated scenarios are saved to your account and appear in the scenario library.

### Blackbox Mode

Blackbox mode picks a random wargame-capable scenario without revealing which one it is. The attacker container gets no `TARGET_*` environment variables. You must discover the target yourself.

```bash
blaqliq ai blackbox

# Inside attacker container:
nmap -sn 10.100.0.0/16   # discover the subnet
nmap -sV <discovered-ip>  # fingerprint services

# After you stop the session, reveal the answer:
blaqliq ai reveal <session-id>
```

---

## Docker Boxes

### Attacker Images

| Image | Description |
|-------|-------------|
| `blaqliq/attacker-base:latest` | Debian slim with tool profile `web` (nikto, dirb, sqlmap, curl, nmap) |
| `blaqliq/attacker-base:network` | + hydra, masscan, medusa, tcpdump |
| `blaqliq/attacker-base:crypto` | + hashcat, john, openssl |
| `blaqliq/attacker-kali:latest` | Full Kali Rolling (pro+ plan only) |

Build them:

```bash
make build-boxes       # builds all base + sidecar images
make build-kali        # builds Kali image (large, optional)
```

### Target Images

| Image | What it is |
|-------|------------|
| `vulnerables/web-dvwa:latest` | DVWA (Damn Vulnerable Web App) — SQLi, XSS, CSRF, etc. |
| `webgoat/goat-and-wolf:latest` | WebGoat — OWASP training app |
| `blaqliq/target-metasploitable-lite:latest` | Lightweight Metasploitable-style box (SSH, vsftpd, Apache) |

### Wargame Sidecar

`blaqliq/wargame-sidecar:latest` runs alongside the target on the session network. It:

1. Installs iptables logging rules (`BLAQLIQ-DETECT` chain)
2. Monitors fail2ban ban events
3. Tails auditd for shell-spawn events
4. Writes normalized JSONL to a shared Docker volume every 5 seconds

The backend's APScheduler task reads new JSONL lines, matches them against the scenario's detection rules, and updates the detection score in SQLite.

---

## API Reference

All endpoints accept `Authorization: Bearer <token>` or `X-API-Key: <key>`.

Interactive docs at `http://localhost:8000/docs` (Swagger UI).

```
GET  /health

POST /auth/register
POST /auth/token
GET  /auth/me
POST /auth/api-keys
GET  /auth/api-keys
DEL  /auth/api-keys/{id}

GET  /scenarios
POST /scenarios                    (upload YAML file)
GET  /scenarios/{id}
GET  /scenarios/{id}/yaml

POST /sessions                     { scenario_id, wargame, blackbox }
GET  /sessions
GET  /sessions/{id}
DEL  /sessions/{id}
POST /sessions/{id}/flag           { flag, objective_id }

POST /wargames                     { session_id }
GET  /wargames/{session_id}
GET  /wargames/{session_id}/events

POST /ai/generate-scenario         { prompt, difficulty, tags, wargame, gemini_api_key? }
POST /ai/blackbox                  { novel? }
GET  /ai/blackbox/{session_id}/reveal   (only after session stopped)
```

---

## Configuration

All config is via environment variables. Copy `.env.example` to `.env` and edit:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(must change)* | JWT signing key — use a random 32+ char string |
| `FERNET_KEY` | *(must change)* | Encryption key for Gemini API keys at rest |
| `BLAQLIQ_ALLOWED_TARGET_IMAGES` | dvwa, webgoat, msf-lite | Comma-separated image whitelist |
| `SESSION_TIMEOUT_HOURS` | `4` | Sessions older than this are auto-stopped |
| `DATABASE_URL` | `sqlite:///./blaqliq.db` | SQLite path (swap for Postgres in prod) |
| `JWT_EXPIRE_MINUTES` | `1440` | Token lifetime (24h) |
| `DEBUG` | `false` | Never `true` in production |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model for AI generation |

Generate secure keys:

```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# FERNET_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Plan Limits

BlaqLiq ships with three plan tiers (free by default). These are enforced server-side.

| | free | pro | enterprise |
|--|------|-----|------------|
| Concurrent sessions | 1 | 3 | 20 |
| AI scenario generations/month | 5 | 50 | unlimited |
| Kali attacker access | no | yes | yes |

To upgrade a user's plan directly in the database:

```bash
make db-shell
# or:
docker compose exec backend python3 -c "
from app.database import engine
from sqlmodel import Session, select
from app.models.user import User
with Session(engine) as db:
    u = db.exec(select(User).where(User.username == 'alice')).first()
    u.plan = 'pro'
    db.add(u); db.commit()
    print('Done')
"
```

---

## Security Model

BlaqLiq is designed to be self-hosted. A few things to understand before exposing it:

**Image whitelist**: Only images listed in `BLAQLIQ_ALLOWED_TARGET_IMAGES` can be used as targets. This is enforced in `scenario_loader.py` before any `docker run` call, including for Gemini-generated scenarios. Do not add production images to this list.

**Network isolation**: Every session gets its own Docker bridge network. By default `internal: true` in scenario YAML means containers have no internet access. Set `internal: false` only when a scenario explicitly requires it (e.g. downloading exploit dependencies).

**Container hardening**: Target containers run with `cap_drop: ALL` and `security_opt: no-new-privileges`. Resource limits (memory, CPU) are enforced even if the scenario YAML omits them.

**Capabilities**: Only the wargame sidecar gets `NET_ADMIN` (needed for iptables). The attacker gets `NET_ADMIN` optionally for packet crafting tools.

**Gemini keys**: Stored Fernet-encrypted in SQLite. The server's Fernet key is never stored in the database. Set a strong, unique `FERNET_KEY` in your `.env`.

**Do not expose to the internet without additional hardening** — this platform intentionally runs vulnerable software. Put it behind a VPN or firewall if you're running it on a server.

---

## Development

```bash
# Start the full stack with hot reload
make dev

# Backend only (with reload)
cd backend && uvicorn app.main:app --reload

# Frontend only
cd frontend && npm install && npm run dev

# CLI in editable mode
cd cli && pip install -e .

# Tail backend logs
make logs

# Full cleanup (removes all containers, networks, volumes)
make clean
```

Run the API test to verify the backend is up:

```bash
make test-api
```

### Adding a New Scenario

1. Scaffold: `make scenario NEW=my-lab`
2. Edit `scenarios/custom/my-lab.yaml`
3. Validate: `blaqliq session start my-lab` (the loader validates on start)
4. Add target flags to the YAML `objectives` block with `BLAQLIQ{...}` format
5. Optionally add a `wargame:` block (see `scenarios/wargame/dvwa-hardened.yaml` for reference)

### Adding a New Target Box

1. Create `boxes/target-mybox/Dockerfile`
2. Build: `docker build -t blaqliq/target-mybox:latest ./boxes/target-mybox/`
3. Add `blaqliq/target-mybox:latest` to `BLAQLIQ_ALLOWED_TARGET_IMAGES` in `.env`
4. Reference it in a scenario YAML

---

## Project Structure

```
blaqliq/
├── docker-compose.yml          # dev stack: backend + frontend + sqlite volume
├── Makefile                    # make dev, build, scenario, install-cli, clean
├── .env.example                # environment variable template
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app + lifespan + APScheduler
│       ├── config.py           # pydantic-settings
│       ├── database.py         # SQLite engine
│       ├── dependencies.py     # auth + plan limit dependencies
│       ├── models/             # User, APIKey, LabSession, Scenario, WargameState, DetectionEvent
│       ├── routers/            # auth, scenarios, sessions, wargames, ai
│       └── services/
│           ├── docker_manager.py    # all docker-py calls
│           ├── scenario_loader.py   # YAML parse + validate
│           ├── session_manager.py   # orchestrate sessions
│           ├── ai_service.py        # Gemini wrapper
│           └── wargame_engine.py    # deterministic detection pipeline
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── api/                # axios hooks (sessions, scenarios, wargames)
│       ├── components/         # ScenarioCard, WargameStatus, AIGenerator, Layout
│       ├── pages/              # Dashboard, ScenarioLibrary, ActiveSession, WargameView, Login
│       └── store/              # Zustand: authStore, sessionStore
│
├── cli/
│   └── blaqliq/
│       ├── main.py             # click group root
│       ├── config.py           # ~/.blaqliq/config.yaml
│       ├── api_client.py       # httpx wrapper
│       └── commands/           # auth, session, wargame, ai
│
├── boxes/
│   ├── attacker-base/          # Debian slim + tools by profile
│   ├── attacker-kali/          # kalilinux/kali-rolling
│   ├── target-dvwa/
│   ├── target-webgoat/
│   ├── target-metasploitable-lite/
│   └── wargame-sidecar/        # iptables + fail2ban + auditd → JSONL
│
├── scenarios/
│   ├── _schema.yaml            # canonical schema + documentation
│   ├── web/                    # dvwa-beginner, webgoat-sqli
│   ├── network/                # metasploitable-vsftpd
│   └── wargame/                # dvwa-hardened
│
└── wargames/
    ├── fail2ban/               # jail configs
    ├── auditd/                 # audit rules
    └── iptables/               # logging rule template
```

---

## License

MIT
