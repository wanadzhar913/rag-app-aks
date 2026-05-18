# Harness Engineering with Malaysian Road Transport Legal Researcher Agents on AKS (Azure Kubernetes Service)

This repository now includes a GitOps-oriented Azure deployment layout for the FastAPI backend and ingestion worker.

## What makes a good Harness?



## Deployment Layout

- `infra/terraform/bootstrap/`: creates the remote-state resource group, storage account, and container.
- `infra/terraform/platform/`: provisions AKS, ACR, PostgreSQL Flexible Server, Blob Storage, Key Vault, ingress, Argo CD, External Secrets, and the S3-compatible gateway VM.
- `infra/terraform/environments/{dev,prod}/`: environment composition and example inputs.
- `deploy/k8s/base/`: app-only Kubernetes base manifests.
- `deploy/k8s/overlays/{local,development,production}/`: local and Azure-backed app overlays.
- `deploy/platform/overlays/{development,production}/`: platform manifests such as the Key Vault-backed `ClusterSecretStore` and RabbitMQ.
- `deploy/argocd/`: root and child Argo CD applications.
- `.github/workflows/`: CI, ACR image publishing, and image-promotion workflows.

## GitOps Flow

1. Terraform provisions Azure resources and bootstraps Argo CD plus cluster add-ons.
2. Apply either `deploy/argocd/root-application-development.yaml` or `deploy/argocd/root-application-production.yaml` once so each AKS cluster only manages its own environment.
3. GitHub Actions builds and pushes images to ACR.
4. The promotion workflow updates Kustomize image tags, and Argo CD syncs the matching environment.

## Notes

- `development` and `production` overlays no longer deploy in-cluster PostgreSQL or MinIO.
- Secrets are expected to come from Azure Key Vault via External Secrets.
- The local overlay keeps PostgreSQL, RabbitMQ, and MinIO for developer parity.
- Replace `replace-me.azurecr.io` in the Azure-backed overlays with the ACR login server created by Terraform before syncing them.

# Resources

- [What is an Agent Harness? and How to build a great one!](https://www.youtube.com/watch?v=nWzXyjXCoCE) e.g., while loop, skills (markdown-based) & tools, built-in skills, system prompt assembly, permission & safety, sub-agents, context management, session persistence, lifecycle hooks
- [Awesome Cursor Rules](https://github.com/PatrickJS/awesome-cursorrules/tree/main/rules/py-fast-api)
- Skills (for [progressive disclosure](https://docs.claude-mem.ai/progressive-disclosure#what-is-progressive-disclosure))
  - [Statute Analysis by Rafael Fryc](https://github.com/lawvable/awesome-legal-skills/tree/main/skills%2Fstatute-analysis-rafal-fryc)
  - [Canned Responses by Anthropic](https://github.com/lawvable/awesome-legal-skills/tree/main/skills/canned-responses-anthropic)
- Can someone help me understand, the use/need for an OCR engine when using something like granite-docling? ([docling-project/docling#2726](https://github.com/docling-project/docling/discussions/2726))