# Staging Acceptance Record Validation

Run the repository validator against the completed acceptance record before a final release decision is accepted:

```bash
python scripts/validate_staging_acceptance.py docs/staging-acceptance-record.md
```

A valid record exits with status `0` and prints:

```text
VALID: staging acceptance record is internally complete
```

An incomplete or inconsistent record exits with status `1` and prints deterministic findings. The validator requires:

- an exact 40-character lowercase release commit SHA
- release identity and migration fields
- every automated release gate marked `Passed`
- every infrastructure readiness check marked `Passed`
- every manual acceptance step marked `Passed`
- complete rollback evidence marked `Yes`
- a `GO` or `NO-GO` decision with named owner and UTC timestamp
- zero unresolved critical and high-severity defects for `GO`
- the required sign-off statement for `GO`

The validator reads only the supplied Markdown file. It does not read environment variables, credentials, kubeconfig content, cloud APIs, or GitHub secrets. A successful validation confirms internal record completeness only; it does not independently prove that staging infrastructure or workflow evidence is genuine.
