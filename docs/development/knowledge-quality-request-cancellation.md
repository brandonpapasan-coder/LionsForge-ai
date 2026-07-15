# Knowledge Quality Request Cancellation

The Knowledge Quality Dashboard now treats scope changes as a latest-request-wins workflow.

## Behavior

- Starting a new dashboard request aborts the previous request.
- Aborted requests cannot update data, errors, or loading state.
- Unmounting the dashboard aborts active project-discovery and dashboard requests.
- The scope selector remains available during refresh so users can change scope without waiting for a slow response.

## Regression coverage

Frontend tests cover rapid scope changes, stale responses that finish late, and unmount cancellation.
