# Internal Alpha Staging Execution Record

Tracks #29 and #461.

This record governs billable external staging provisioning and live Internal Alpha acceptance for LionsForge AI. It does not authorize production, public beta, general availability, live trading, brokerage, custody, portfolio execution, or automated market orders.

Do not place credentials, kubeconfig content, API keys, passwords, private user data, or secret values in this file, issue comments, workflow output, or pull-request comments.

## Decision

- Protected-main candidate SHA: `cd539d1eef52f1c46770a0f01b74ad0325ba5dca`
- Pre-merge gate-clean source SHA: `6cfc9e070f3b63717b4b6fa72250ea53abce9d9b`
- Infrastructure provider: `AWS`
- Region: `PENDING`
- Staging account identifier reference: `PENDING CONTROLLED REFERENCE`
- Operator: `PENDING`
- Review owner: `PENDING`
- Decision: **NO-GO**

Any pending, failed, unverified, mismatched, or unapproved mandatory item keeps this record at **NO-GO**.

## 1. Cost and authority

| Control | Evidence reference | Status |
|---|---|---|
| Expected monthly AWS staging cost reviewed | PENDING | NOT APPROVED |
| Billable provisioning approved | PENDING | NOT APPROVED |
| AWS account and region selected | PENDING | NOT VERIFIED |
| Infrastructure operator authorized | PENDING | NOT VERIFIED |
| `staging-apply` reviewer configured | PENDING | NOT VERIFIED |

## 2. Terraform remote state and identity

| Control | Evidence reference | Status |
|---|---|---|
| S3 remote-state bucket bootstrapped | PENDING | NOT EXECUTED |
| Bucket encryption enabled | PENDING | NOT VERIFIED |
| Bucket versioning enabled | PENDING | NOT VERIFIED |
| Public access blocked | PENDING | NOT VERIFIED |
| GitHub OIDC plan role configured | PENDING | NOT VERIFIED |
| GitHub OIDC apply role configured | PENDING | NOT VERIFIED |
| `AWS_REGION` variable configured | PENDING | NOT VERIFIED |
| `TF_STATE_BUCKET` variable configured | PENDING | NOT VERIFIED |
| Plan/apply role ARN variables configured | PENDING | NOT VERIFIED |

## 3. Reviewed Terraform execution

| Control | Evidence reference | Status |
|---|---|---|
| Terraform Staging Plan run completed | PENDING | NOT EXECUTED |
| Plan artifact reviewed | PENDING | NOT REVIEWED |
| Resource count and material changes reviewed | PENDING | NOT REVIEWED |
| Cost impact approved | PENDING | NOT APPROVED |
| Terraform Staging Apply used reviewed plan run ID | PENDING | NOT EXECUTED |
| Exact `APPLY-STAGING` confirmation used | PENDING | NOT VERIFIED |
| Apply record retained | PENDING | NOT VERIFIED |

## 4. Provisioned platform

| Dependency | Evidence reference | Status |
|---|---|---|
| Two-AZ VPC networking | PENDING | NOT VERIFIED |
| EKS cluster and managed nodes | PENDING | NOT VERIFIED |
| `lionsforge-staging` namespace | PENDING | NOT VERIFIED |
| Private PostgreSQL 16 RDS | PENDING | NOT VERIFIED |
| Database encryption and backups | PENDING | NOT VERIFIED |
| Database access restricted to approved workloads | PENDING | NOT VERIFIED |
| Ingress controller | PENDING | NOT INSTALLED |
| Certificate management | PENDING | NOT INSTALLED |
| GHCR image-pull access | PENDING | NOT VERIFIED |
| Observability access | PENDING | NOT VERIFIED |

## 5. DNS and HTTPS

| Endpoint | Required value | Evidence reference | Status |
|---|---|---|---|
| API | `https://api.staging.lionsforge.ai` | PENDING | NOT VERIFIED |
| Web | `https://staging.lionsforge.ai` | PENDING | NOT VERIFIED |
| API certificate | Valid trusted certificate | PENDING | NOT VERIFIED |
| Web certificate | Valid trusted certificate | PENDING | NOT VERIFIED |
| HTTP-to-HTTPS behavior | Approved redirect or rejection | PENDING | NOT TESTED |

## 6. GitHub environment configuration

### `staging` secrets

- `KUBE_CONFIG_STAGING`: `NOT VERIFIED`
- `STAGING_DATABASE_URL`: `NOT VERIFIED`
- `STAGING_JWT_SECRET_KEY`: `NOT VERIFIED`
- `STAGING_OPENAI_API_KEY`: `NOT VERIFIED`
- `STAGING_TEST_EMAIL`: `NOT VERIFIED`
- `STAGING_TEST_SECRET`: `NOT VERIFIED`

### `staging` variables

- `STAGING_API_URL`: `NOT VERIFIED`
- `STAGING_WEB_URL`: `NOT VERIFIED`
- `AWS_TERRAFORM_PLAN_ROLE_ARN`: `NOT VERIFIED`
- `AWS_REGION`: `NOT VERIFIED`
- `TF_STATE_BUCKET`: `NOT VERIFIED`

### `staging-apply` variables and protection

- `AWS_TERRAFORM_APPLY_ROLE_ARN`: `NOT VERIFIED`
- Required reviewer: `NOT VERIFIED`
- Environment protection rules: `NOT VERIFIED`

## 7. Immutable deployment

| Control | Evidence reference | Status |
|---|---|---|
| Backend staging deployment dispatched with exact main SHA | PENDING | NOT EXECUTED |
| Frontend staging deployment dispatched with exact main SHA | PENDING | NOT EXECUTED |
| Backend image digest recorded | PENDING | NOT VERIFIED |
| Frontend image digest recorded | PENDING | NOT VERIFIED |
| Backend deployed by digest | PENDING | NOT VERIFIED |
| Frontend deployed by digest | PENDING | NOT VERIFIED |
| Running backend digest matches registry evidence | PENDING | NOT VERIFIED |
| Running frontend digest matches registry evidence | PENDING | NOT VERIFIED |
| Database migration head matches candidate | PENDING | NOT VERIFIED |

## 8. Smoke and integrated acceptance

| Journey | Evidence reference | Result |
|---|---|---|
| API health and readiness | PENDING | NOT TESTED |
| Web login page and static assets | PENDING | NOT TESTED |
| Controlled account authentication | PENDING | NOT TESTED |
| Research project creation | PENDING | NOT TESTED |
| Evidence ingestion and provenance display | PENDING | NOT TESTED |
| Claim validation and quality assessment | PENDING | NOT TESTED |
| Research conclusion and export | PENDING | NOT TESTED |
| Knowledge memory and owner isolation | PENDING | NOT TESTED |
| Education Hub and mastery flow | PENDING | NOT TESTED |
| Mentor guidance and provider-failure behavior | PENDING | NOT TESTED |
| Executive and enterprise administration views | PENDING | NOT TESTED |
| Account closure and eligible data removal | PENDING | NOT TESTED |
| Live-execution and trading routes remain unavailable | PENDING | NOT TESTED |

## 9. Recovery and operations

| Exercise | Evidence reference | Result |
|---|---|---|
| Backend rollback to prior immutable digest | PENDING | NOT TESTED |
| Frontend rollback to prior immutable digest | PENDING | NOT TESTED |
| Database backup verification | PENDING | NOT TESTED |
| Database restore exercise | PENDING | NOT TESTED |
| Provider outage and timeout behavior | PENDING | NOT TESTED |
| Credential rotation procedure | PENDING | NOT TESTED |
| Alpha access suspension | PENDING | NOT TESTED |
| Alert routing and incident ownership | PENDING | NOT VERIFIED |

## 10. Final authorization

| Approval | Approver role | Date | Status |
|---|---|---|---|
| Cost and provisioning | Product owner | PENDING | NOT APPROVED |
| Infrastructure | Engineering or operations owner | PENDING | NOT APPROVED |
| Security | Security owner | PENDING | NOT APPROVED |
| Privacy and retention | Privacy or data owner | PENDING | NOT APPROVED |
| Internal Alpha support | Support owner | PENDING | NOT APPROVED |
| Release | Release owner | PENDING | NOT APPROVED |

## GO rule

Set this staging execution record to **GO** only when:

1. Billable provisioning is explicitly approved.
2. Terraform state, OIDC roles, protected environments, plan review, and apply evidence are complete.
3. The platform, database, ingress, DNS, HTTPS, registry access, and observability are verified.
4. Backend and frontend are deployed by immutable digest from the exact protected-main SHA.
5. All mandatory smoke and integrated acceptance journeys pass with traceable evidence.
6. Rollback, restore, provider-failure, credential-rotation, and access-suspension exercises pass.
7. No unresolved high or critical security, privacy, reliability, or data-integrity defect remains.
8. Every required approver signs the exact candidate record.

Until then, the decision remains **NO-GO**.
