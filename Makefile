.PHONY: up up-build down down-volumes logs ps ingest \
       backend-logs ingestion-logs \
       kube-dev kube-prod kube-local kube-diff-local

# ---------- Docker Compose (local development) ----------

ENVIRONMENT ?= development

up:
	ENVIRONMENT=$(ENVIRONMENT) docker compose up -d

up-build:
	ENVIRONMENT=$(ENVIRONMENT) docker compose up --build -d

down:
	docker compose down

down-volumes:
	docker compose down -v

logs:
	docker compose logs -f

backend-logs:
	docker compose logs -f backend

ingestion-logs:
	docker compose logs -f ingestion-worker

ps:
	docker compose ps

upload:
	@test -n "$(PDF)" || (echo "usage: make upload PDF=path/to/file.pdf" && exit 1)
	@curl -s -X POST http://localhost:8080/api/v1/documents/upload \
		-F "file=@$(PDF)" | python3 -m json.tool

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
