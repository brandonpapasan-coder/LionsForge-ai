# Launch Evidence Chain Artifact Replay

This manual workflow independently replays a successful `Launch Evidence Chain Receipt` run after its artifacts have been retained.

Provide the exact protected-`main` candidate SHA and the originating workflow run ID. The workflow confirms the run completed successfully in the same repository, locates exactly one unexpired primary chain artifact and one unexpired upload-provenance artifact for that candidate, downloads both through authenticated GitHub API access, safely extracts their bounded expected contents, and reconstructs the upload-receipt bindings.

Replay verification checks the candidate, repository, workflow identity, workflow SHA, run ID, run attempt, artifact ID, artifact name, GitHub artifact URL, GitHub-provided artifact digest, source-receipt SHA-256 digest, byte size, and repository-only authorization scope.

The workflow fails closed on expired, missing, duplicated, malformed, symlinked, path-traversing, cross-run, cross-repository, cross-candidate, substituted, or drifted artifacts. A successful replay report is retained for 90 days.

A valid replay proves retained artifact provenance and integrity only. It does not verify live evidence truth or freshness, provision infrastructure, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.

Do not place secrets, credentials, tester identities, private support content, request contents, uploaded evidence, private user data, or personal staff addresses in artifacts or replay reports.
