# Review queue comparison report proxy

This authenticated Next.js route forwards one explicit prior-snapshot JSON payload to the backend comparison-report export endpoint.

- The route does not persist uploaded snapshot JSON, comparison payloads, generated reports, or report digests.
- Backend status, JSON content type, attachment filename, and `X-Content-SHA256` are forwarded when present.
- Missing session state fails closed with HTTP 401.
- Upstream transport failure returns HTTP 503 without fabricating a report.

Report and snapshot digests verify artifact integrity only. Exported comparisons describe stored workflow-state changes and do not establish truth, confidence, importance, urgency, risk, resolution, validation evidence, advice, or recommended action.
