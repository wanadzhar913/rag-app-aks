.PHONY: check-env-file up up-build down down-volumes logs ps ingest upload \
       backend-logs ingestion-logs \
       migrate migrate-heads migrate-current migrate-history \
       migrate-create migrate-stamp migrate-downgrade \
       kube-dev kube-prod kube-local kube-diff-local kube-diff-dev kube-diff-prod

# ---------- Docker Compose (local development) ----------

ENVIRONMENT ?= development
ENV_FILE := ./envs/.env.$(ENVIRONMENT)
COMPOSE := ENV_FILE=$(ENV_FILE) docker compose --env-file $(ENV_FILE)
BACKEND_DIR := services/backend
ALEMBIC := cd $(BACKEND_DIR) && ENVIRONMENT=$(ENVIRONMENT) uv run python -m alembic

check-env-file:
	@test -f "$(ENV_FILE)" || (echo "missing env file: $(ENV_FILE)" && exit 1)

up: check-env-file
	$(COMPOSE) up -d

up-build: check-env-file
	$(COMPOSE) up --build -d

down: check-env-file
	$(COMPOSE) down

down-volumes: check-env-file
	$(COMPOSE) down -v

logs: check-env-file
	$(COMPOSE) logs -f

backend-logs: check-env-file
	$(COMPOSE) logs -f backend

ingestion-logs: check-env-file
	$(COMPOSE) logs -f ingestion-worker

ps: check-env-file
	$(COMPOSE) ps

upload:
	@test -n "$(PDF)" || (echo "usage: make upload PDF=path/to/file.pdf" && exit 1)
	@curl -s -X POST http://localhost:8080/api/v1/documents/upload \
		-F "file=@$(PDF)" | python3 -m json.tool

# ---------- Alembic / Migrations ----------

migrate:
	@$(ALEMBIC) upgrade head

migrate-heads:
	@$(ALEMBIC) heads

migrate-current:
	@$(ALEMBIC) current

migrate-history:
	@$(ALEMBIC) history

migrate-create:
	@test -n "$(MESSAGE)" || (echo "usage: make migrate-create MESSAGE=\"describe change\"" && exit 1)
	@$(ALEMBIC) revision --autogenerate -m "$(MESSAGE)"

migrate-stamp:
	@test -n "$(REV)" || (echo "usage: make migrate-stamp REV=head" && exit 1)
	@$(ALEMBIC) stamp "$(REV)"

migrate-downgrade:
	@test -n "$(REV)" || (echo "usage: make migrate-downgrade REV=-1" && exit 1)
	@$(ALEMBIC) downgrade "$(REV)"

# ---------- Kubernetes / Kustomize ----------

kube-local:
	kubectl apply -k deploy/k8s/overlays/local

kube-dev:
	kubectl apply -k deploy/k8s/overlays/development

kube-prod:
	kubectl apply -k deploy/k8s/overlays/production

kube-diff-local:
	kubectl diff -k deploy/k8s/overlays/local

kube-diff-dev:
	kubectl diff -k deploy/k8s/overlays/development

kube-diff-prod:
	kubectl diff -k deploy/k8s/overlays/production
