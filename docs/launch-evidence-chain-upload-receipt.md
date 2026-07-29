# Launch Evidence Chain Upload Receipt

The launch evidence-chain workflow retains two artifacts for each successful exact-candidate run:

1. the validated chain receipt and non-secret validation summary;
2. a separate upload-provenance receipt.

The upload-provenance receipt binds the source chain receipt to the exact candidate SHA, repository, workflow name and SHA, workflow run ID and attempt, uploaded artifact ID, artifact name, GitHub artifact URL, and GitHub-provided artifact digest.

The workflow generates the upload receipt only after the primary artifact upload succeeds, then independently reconstructs and verifies the expected receipt before uploading it separately. Both artifacts are retained for 90 days.

Verification proves artifact upload provenance and source-receipt integrity only. It does not prove live evidence truth or freshness, provision infrastructure, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.

Do not include secrets, credentials, tester identities, private support content, request contents, uploaded evidence, private user data, or personal staff addresses in the source records, summaries, or receipts.
