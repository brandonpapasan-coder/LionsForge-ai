# Production Acceptance Record Validation

Run the production validator against the completed acceptance record before any final production release decision is accepted:

```bash
python scripts/validate_production_acceptance.py docs/production-acceptance-record.md
```

A valid record exits with status `0` and prints:

```text
VALID: production acceptance record is internally complete
```

An incomplete or inconsistent record exits with status `1` and prints deterministic findings. The validator requires:

- distinct exact 40-character lowercase release and rollback SHAs
- valid backend and frontend `sha256` image digests
- running backend and frontend digest verification marked `Yes`
- complete workflow, ownership, URL, staging evidence, and migration fields
- HTTPS API and web URLs
- every required release gate marked `Passed`
- every infrastructure and operational check marked `Passed`
- every critical user journey marked `Passed`
- complete rollback and forward-redeployment evidence marked `Yes`
- a `GO` or `NO-GO` decision with a named owner and UTC timestamp
- zero unresolved critical and high-severity defects for `GO`
- the required production provenance sign-off statement for `GO`

## GitHub Actions validation

After the completed record is committed under `docs/`, run the **Production Acceptance Validate** workflow manually.

Provide:

- `record_path`: the repository-relative Markdown path, normally `docs/production-acceptance-record.md`
- `release_sha`: the exact 40-character lowercase release SHA recorded in the file
- `rollback_sha`: the exact 40-character lowercase rollback SHA recorded in the file

The workflow rejects identical release and rollback SHAs, verifies that both commits exist and are ancestors of `main`, confirms that the inputs exactly match the record, and prevents path traversal outside the repository `docs/` directory.

It also verifies successful exact-SHA release gates and runs the production record validator. The job summary contains only non-sensitive release metadata and validation results.

A successful validation workflow confirms record consistency and repository-visible CI evidence. It does not independently prove that production infrastructure, rollback, restore, alerts, legal controls, or manual acceptance evidence are genuine. Those external results must be recorded by named operators without credentials or private user data.

## Tests

The validator test suite is located at:

```text
backend/tests/test_production_acceptance_validator.py
```

Run it with the backend test suite or directly with:

```bash
pytest backend/tests/test_production_acceptance_validator.py
```
