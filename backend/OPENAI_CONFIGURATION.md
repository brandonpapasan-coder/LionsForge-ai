# OpenAI Provider Configuration

LionsForge AI uses the OpenAI Responses API for optional mentor generation. The deterministic mentor fallback remains available when the provider is disabled or unavailable.

## Environment variables

- `OPENAI_API_KEY`: Project-scoped OpenAI API key. Leave unset to disable the provider.
- `OPENAI_MODEL`: Responses API model identifier. The application default is `gpt-5.5`, but production deployments should set this explicitly.
- `OPENAI_TIMEOUT_SECONDS`: Request timeout in seconds. Default: `30`.
- `OPENAI_MAX_RETRIES`: Maximum SDK retries for retryable transient failures. Default: `2`.

## Production guidance

- Store `OPENAI_API_KEY` in the deployment secret manager. Never commit it to the repository, container image, logs, or client-side configuration.
- Use a dedicated project key with the minimum operational access needed by LionsForge AI.
- Set the model explicitly in every deployed environment and validate the selected model in a controlled smoke test before release.
- Do not use routine readiness probes to make billable generation requests. Provider health reporting is based on configuration and observed request outcomes.
- Model output is constrained by a strict JSON Schema and then validated again with Pydantic before it enters the mentor pipeline.
- Authentication, invalid-model, malformed-output, and schema failures fall back without retrying at the application layer. The OpenAI SDK performs only the configured bounded retries for retryable transient failures.
- Logs must never contain API keys or raw user prompts. Provider failures are logged by category only.

## Health states

- `disabled`: No API key is configured.
- `configured`: Credentials and model settings are present, but no successful request has been observed in the current process.
- `healthy`: The most recent generation completed and passed schema validation.
- `degraded`: A transient provider, timeout, rate-limit, or malformed-output failure occurred.
- `misconfigured`: Authentication, model, or structured-output configuration was rejected.
