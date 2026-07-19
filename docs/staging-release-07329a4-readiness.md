# Staging Readiness — Release Candidate 07329a4

This record tracks non-secret readiness for the current release-candidate candidate. It does not replace `docs/staging-acceptance-record.md` and must not contain credentials, kubeconfig content, tokens, private user data, or secret values.

## Release identity

- Candidate SHA: `07329a468a542e9792d9f6eb8f4f513a94ca3e0c`
- Source branch: `main`
- Included product milestone: Research Validation Workspace through education-gap recommendations
- Status: Candidate only; not approved for staging deployment
- Launch epic: #400
- Staging blocker: #29

## Validation status

The pull request merged into this SHA passed Backend CI, Frontend CI, Security Gate, and Deployment Validation before merge. The candidate becomes deployable only after the exact SHA is verified on `main`, required workflow evidence is recorded, and the staging preflight passes.

| Requirement | Status | Evidence or owner |
|---|---|---|
| Exact SHA contained in `origin/main` | Pending | Run `scripts/staging-preflight.sh` from a fresh fetch. |
| Backend CI for accepted SHA | Pending | Record workflow run URL or ID. |
| Frontend CI for accepted SHA | Pending | Record workflow run URL or ID. |
| Security Gate for accepted SHA | Pending | Record workflow run URL or ID. |
| Deployment Validation for accepted SHA | Pending | Record workflow run URL or ID. |
| AWS account and region approved | Pending | Owner must record non-secret account alias/region and cost approval. |
| Terraform remote state bootstrapped | Pending | Record state bucket reference without credentials. |
| GitHub `staging` environment configured | Pending | Confirm variables and secret names only. |
| GitHub `staging-apply` environment protected | Pending | Confirm reviewer and OIDC roles. |
| EKS/RDS/namespace provisioned | Pending | Record Terraform apply run and outputs. |
| DNS and HTTPS active | Pending | `STAGING_API_URL` and `STAGING_WEB_URL` must use HTTPS. |
| Backup/restore access ready | Pending | Record operator and procedure reference. |
| Observability access ready | Pending | Record dashboard/alert references. |
| Acceptance user provisioned | Pending | Record only that it exists; never record credentials. |

## Operator preflight

From a trusted workstation with a fresh clone or fetch:

```bash
export RELEASE_SHA=07329a468a542e9792d9f6eb8f4f513a94ca3e0c
export STAGING_API_URL=https://api.staging.lionsforge.ai
export STAGING_WEB_URL=https://staging.lionsforge.ai
export AWS_REGION=<approved-region>
export TF_STATE_BUCKET=<approved-state-bucket-name>

git fetch origin main
bash scripts/staging-preflight.sh
```

Do not export secrets into shared shell history. Configure protected GitHub environment secrets directly through GitHub or an approved secrets-management process.

## Deployment authorization

Deployment remains blocked until every item below is true:

- [ ] The selected SHA is an exact 40-character commit contained in `origin/main`.
- [ ] All four required validation gates are recorded for the accepted SHA.
- [ ] Infrastructure and monthly cost approval are recorded.
- [ ] The staging cluster, database, namespace, ingress, DNS, TLS, registry access, backups, observability, and acceptance user exist.
- [ ] `scripts/staging-preflight.sh` exits successfully.
- [ ] A named owner authorizes immutable backend and frontend deployment with the same SHA.

After authorization, follow `docs/staging-closeout-runbook.md` and complete `docs/staging-acceptance-record.md`.