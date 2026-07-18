# LionsForge AI Staging Acceptance Record

This record tracks Issue #29 for release candidate `c9a8d45c661eee531b744cba080444d914582e0f`. Do not include secret values, access tokens, kubeconfig content, credentials, or sensitive user data.

## Release identity

- Release candidate SHA: `c9a8d45c661eee531b744cba080444d914582e0f`
- Candidate source: `main`
- Acceptance status: `BLOCKED — AWS target, cost approval, infrastructure, and GitHub environment configuration pending`
- Staging deploy workflow run: Pending
- Staging API URL: Pending
- Staging web URL: Pending
- Acceptance date/time (UTC): Pending
- Acceptance owner: Brandon Papasan
- AWS account approval: Pending
- AWS region approval: Pending
- Estimated monthly cost approval: Pending
- Cost approval owner: Pending
- Previous deployable image SHA: Pending
- Database migration revision before deploy: Pending
- Database migration revision after deploy: Pending

## Automated validation

| Gate | Result | Run or evidence reference | Notes |
|---|---|---|---|
| Backend CI | Passed on PR head | PR #300 validation | Workflow also triggers on pushes to `main`; direct-push run evidence must be recorded before GO. |
| Frontend CI | Passed on PR head | PR #300 validation | Direct-push run evidence must be recorded before GO. |
| Security Gate | Passed on PR head | PR #300 validation | Direct-push run evidence must be recorded before GO. |
| Deployment Validation | Passed on PR head | PR #300 validation | Direct-push run evidence must be recorded before GO. |
| Terraform Staging Plan | Not run | | AWS target and OIDC plan role pending. |
| Terraform Staging Apply | Not run | | Requires reviewed plan, protected environment approval, and `APPLY-STAGING`. |
| Staging Deploy | Not run | | Infrastructure and GitHub environment pending. |
| Staging Frontend Deploy | Not run | | Infrastructure and GitHub environment pending. |
| Authenticated smoke test | Not run | | |
| OpenAI provider health | Not run | | Record only enabled/status/model metadata. |
| Mentor schema validation | Not run | | Do not copy sensitive conversation data. |

## Infrastructure readiness

| Check | Result | Owner | Notes |
|---|---|---|---|
| AWS account and region approved | Pending | Brandon Papasan | Required before billable execution. |
| Estimated monthly cost approved | Pending | | Include EKS, worker nodes, NAT Gateway, RDS, load balancers, storage, and data transfer. |
| Terraform remote-state bucket | Pending | | Bootstrap stack not applied. |
| GitHub OIDC plan/apply roles | Pending | | Separate least-privilege roles required. |
| `staging` environment configured | Pending | | Variables and secrets must be configured outside source control. |
| `staging-apply` protected environment configured | Pending | | Reviewer required. |
| Kubernetes cluster and namespace | Pending | | |
| Ingress, DNS, and HTTPS | Pending | | `api.staging.lionsforge.ai` and `staging.lionsforge.ai`. |
| PostgreSQL connectivity | Pending | | |
| Database backup and restore test | Pending | | |
| GHCR image-pull access | Pending | | |
| Error and latency observability | Pending | | |
| Acceptance user provisioned | Pending | | |

## Manual acceptance journey

All steps remain `Not run` until staging is deployed: Dashboard, Research, Mentor, Education, persistence, backup/restore, rollback, and defect review.

## Defects

No live staging defects have been assessed. Infrastructure absence is the current release blocker.

## Rollback evidence

- Previous image successfully identified: Pending
- Migration boundary reviewed: Pending
- Rollback command or workflow executed: No
- Service health restored after rollback: Not run
- Forward redeploy completed after rollback test: Not run

## Final decision

- Decision: `NO-GO`
- Decision owner: Brandon Papasan
- Decision timestamp (UTC): Pending final operator entry
- Reason: AWS target approval, cost approval, infrastructure provisioning, protected GitHub environments, deployments, live acceptance, and rollback verification are incomplete.
- Conditions for GO: Complete every pending item in `docs/staging-closeout-runbook.md` with no unresolved critical or high-severity defects.

> This preliminary NO-GO records the current blocked state only. It is not a permanent rejection of the release candidate.