.PHONY: dev build stop logs clean install-cli build-boxes scenario help

# ─────────────────────────────────────────────────────────
# BlaqLiq Makefile
# ─────────────────────────────────────────────────────────

help:
	@echo "BlaqLiq - Docker Security Lab Platform"
	@echo ""
	@echo "Usage:"
	@echo "  make dev          Start backend + frontend in dev mode"
	@echo "  make build        Build all Docker images"
	@echo "  make build-boxes  Build attacker and target box images"
	@echo "  make stop         Stop all services"
	@echo "  make logs         Tail backend logs"
	@echo "  make clean        Remove all containers, volumes, networks"
	@echo "  make install-cli  Install blaqliq CLI tool"
	@echo "  make scenario NEW=<name>  Create a new scenario YAML template"
	@echo ""
	@echo "Examples:"
	@echo "  make dev"
	@echo "  make scenario NEW=my-custom-sqli"
	@echo "  make build-boxes"

dev:
	@echo "Starting BlaqLiq development stack..."
	@cp -n .env.example .env 2>/dev/null || true
	docker compose up --build -d
	@echo ""
	@echo "Services:"
	@echo "  Backend API:  http://localhost:8000"
	@echo "  Frontend:     http://localhost:3000"
	@echo "  API Docs:     http://localhost:8000/docs"
	@echo ""
	@echo "Logs: make logs"
	@echo "Stop: make stop"

build:
	docker compose build

build-boxes:
	@echo "Building attacker-base image..."
	docker build -t blaqliq/attacker-base:latest ./boxes/attacker-base/
	@echo "Building attacker-base (web profile)..."
	docker build --build-arg TOOL_PROFILE=web -t blaqliq/attacker-base:web ./boxes/attacker-base/
	@echo "Building attacker-base (network profile)..."
	docker build --build-arg TOOL_PROFILE=network -t blaqliq/attacker-base:network ./boxes/attacker-base/
	@echo "Building wargame-sidecar..."
	docker build -t blaqliq/wargame-sidecar:latest ./boxes/wargame-sidecar/
	@echo "Building metasploitable-lite target..."
	docker build -t blaqliq/target-metasploitable-lite:latest ./boxes/target-metasploitable-lite/
	@echo "Done! Built images:"
	@docker images | grep blaqliq

build-kali:
	@echo "Building Kali attacker (large download, may take a while)..."
	docker build -t blaqliq/attacker-kali:latest ./boxes/attacker-kali/

stop:
	docker compose down

logs:
	docker compose logs -f backend

clean:
	@echo "Stopping and removing all BlaqLiq resources..."
	docker compose down -v --remove-orphans
	docker rm -f $$(docker ps -aq --filter "label=blaqliq=true") 2>/dev/null || true
	docker network rm $$(docker network ls -q --filter "label=blaqliq=true") 2>/dev/null || true
	docker volume rm $$(docker volume ls -q --filter "label=blaqliq=true") 2>/dev/null || true
	@echo "Clean complete"

install-cli:
	@echo "Installing blaqliq CLI..."
	cd cli && pip install -e .
	@echo "Done! Run: blaqliq --help"

scenario:
	@if [ -z "$(NEW)" ]; then echo "Usage: make scenario NEW=scenario-name"; exit 1; fi
	@mkdir -p scenarios/custom
	@cat > scenarios/custom/$(NEW).yaml << 'EOF'
schema_version: "1.0"
metadata:
  id: "$(NEW)"
  name: "$(NEW)"
  difficulty: "beginner"
  tags: ["web"]
  ai_generated: false

network:
  subnet: "10.100.{session_offset}.0/24"
  internal: true

targets:
  - id: "target"
    image: "vulnerables/web-dvwa:latest"
    ip: "10.100.{session_offset}.10"
    mem_limit: "512m"
    cpu_quota: 50000

attacker:
  tool_profile: "web"
  kali: false

objectives:
  - id: "flag-1"
    description: "Capture the flag"
    validation:
      method: "flag_string"
      value: "BLAQLIQ{$(NEW)_pwned}"

wargame: null
EOF
	@echo "Created scenarios/custom/$(NEW).yaml"
	@echo "Edit it, then: blaqliq session start $(NEW)"

pull-targets:
	@echo "Pulling target images (this may take a while)..."
	docker pull vulnerables/web-dvwa:latest
	docker pull webgoat/goat-and-wolf:latest
	@echo "Done"

backend-shell:
	docker compose exec backend bash

db-shell:
	docker compose exec backend python3 -c "from app.database import engine; from sqlmodel import text; \
	with engine.connect() as c: print(c.execute(text('SELECT * FROM user')).fetchall())"

test-api:
	@echo "Testing API health..."
	curl -s http://localhost:8000/health | python3 -m json.tool
