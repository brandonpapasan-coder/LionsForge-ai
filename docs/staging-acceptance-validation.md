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

## GitHub Actions validation

After the completed record is committed under `docs/`, run the **Staging Acceptance Validate** workflow manually.

Provide:

- `record_path`: the repository-relative Markdown path, such as `docs/staging-acceptance-record.md`
- `release_sha`: the exact 40-character lowercase commit SHA recorded in that file

The workflow verifies that the release SHA exists, is an ancestor of `main`, exactly matches the record, and that the record path resolves safely inside the repository `docs/` directory.

It also queries GitHub Actions metadata for that exact SHA and requires successful completed runs for:

- Backend CI
- Frontend CI
- Security Gate
- Deployment Validation

The workflow then runs the record validator and writes a non-sensitive evidence table to the GitHub job summary, including workflow status, conclusion, and run ID.

Record the successful workflow run reference in the staging acceptance record. A successful run confirms exact-SHA CI evidence and internal record consistency. It does not independently prove that external staging infrastructure or manual acceptance evidence is genuine.

The local validator reads only the supplied Markdown file. The GitHub Actions workflow additionally reads GitHub Actions run metadata through the workflow token with read-only permissions. Neither path reads staging credentials, kubeconfig content, cloud secrets, or sensitive user data.
