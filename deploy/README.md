# Deploy (`deploy`)

## a) System architecture
- `deploy/k8s/base`: reusable app manifests (backend + ingestion service primitives).
- `deploy/k8s/overlays/local`: local stack with in-cluster dependencies for fast dev.
- `deploy/k8s/overlays/development` and `production`: cloud-ready overlays using external secrets and managed services.
- `deploy/argocd`: Argo CD app-of-apps entrypoints to sync cluster state from Git.

## b) Setup commands
```bash
# Preview local overlay
make kube-diff-local

# Apply local overlay
make kube-local

# Preview/apply cloud overlays
make kube-diff-dev && make kube-dev
make kube-diff-prod && make kube-prod
```

## c) Why these technologies
- **Kustomize**: keep one base and environment-specific patches without duplicating YAML.
- **Argo CD**: continuous reconciliation so cluster state matches Git (GitOps).
- **External Secrets pattern**: avoids storing sensitive values in repo manifests.
