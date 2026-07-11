# LionsForge AI Release Checklist

A release candidate is eligible for staging only when every required gate below is green.

## Automated gates

- Backend CI passes the full test suite.
- Frontend CI passes type checking and the production build.
- Deployment Validation applies all Alembic migrations from a clean database.
- The critical user journey test passes:
  - register and authenticate
  - load the Executive Dashboard
  - create a research project
  - create a research session
  - pass resolved project/session context to the AI Mentor
  - reopen the persisted mentor transcript
  - load the Education Hub
  - complete a lesson and persist progress
  - confirm dashboard aggregation reflects the workflow

## Security gates

- No secrets are committed to the repository.
- Authentication is required for Dashboard, Mentor, Research, and Education APIs.
- Cross-user access tests pass for persisted user data.
- Production uses a non-default JWT secret and HTTPS-only session cookies.
- Dependency and container vulnerability scans contain no unresolved critical findings.

## Operational gates

- Database backup and restore procedure is documented and tested.
- Health checks are configured for backend, frontend, and database services.
- Application errors and latency are observable in the staging environment.
- Rollback instructions identify the previous application image and database migration boundary.
- A named owner is assigned for each staging acceptance defect.

## Staging acceptance journey

1. Register a new test user.
2. Sign in and load the Executive Dashboard.
3. Create a research project and save notebook content.
4. Create and reopen a research session.
5. Open the AI Mentor from the Research Workspace.
6. Verify the Mentor receives resolved project, session, and notebook context.
7. Reopen the saved Mentor conversation and continue it.
8. Open the Education Hub, start a lesson, and complete it.
9. Sign out and sign back in.
10. Verify research, mentor, and education state persists.

## Release decision

- **GO:** all automated gates pass, no unresolved critical or high-severity defects remain, and the staging acceptance journey succeeds.
- **NO-GO:** any required gate fails, data persistence is unreliable, authentication isolation fails, or rollback cannot be executed safely.
