#!/usr/bin/env bash
set -euo pipefail

required_commands=(curl git gh)
for command_name in "${required_commands[@]}"; do
  command -v "${command_name}" >/dev/null 2>&1 || {
    echo "Missing required command: ${command_name}" >&2
    exit 1
  }
done

required_variables=(
  BETA_RELEASE_SHA
  BETA_API_URL
  BETA_WEB_URL
  BETA_MAX_USERS
  BETA_DAILY_AI_BUDGET_USD
  BETA_PER_USER_DAILY_REQUEST_LIMIT
  BETA_SUPPORT_OWNER
  BETA_INCIDENT_OWNER
)

for variable_name in "${required_variables[@]}"; do
  if [[ -z "${!variable_name:-}" ]]; then
    echo "Missing required variable: ${variable_name}" >&2
    exit 1
  fi
done

if ! [[ "${BETA_RELEASE_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "BETA_RELEASE_SHA must be an immutable 40-character lowercase commit SHA" >&2
  exit 1
fi

for url in "${BETA_API_URL}" "${BETA_WEB_URL}"; do
  case "${url}" in
    https://*) ;;
    *) echo "Beta URLs must use HTTPS: ${url}" >&2; exit 1 ;;
  esac
done

for integer_value in "${BETA_MAX_USERS}" "${BETA_PER_USER_DAILY_REQUEST_LIMIT}"; do
  if ! [[ "${integer_value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "User and request limits must be positive integers" >&2
    exit 1
  fi
done

if ! [[ "${BETA_DAILY_AI_BUDGET_USD}" =~ ^[0-9]+([.][0-9]{1,2})?$ ]] || [[ "${BETA_DAILY_AI_BUDGET_USD}" == "0" ]]; then
  echo "BETA_DAILY_AI_BUDGET_USD must be a positive dollar amount" >&2
  exit 1
fi

git fetch origin main --no-tags >/dev/null
git cat-file -e "${BETA_RELEASE_SHA}^{commit}"
git merge-base --is-ancestor "${BETA_RELEASE_SHA}" origin/main

gh auth status >/dev/null

curl --fail --silent --show-error --location "${BETA_API_URL}/health" >/dev/null
curl --fail --silent --show-error --location "${BETA_WEB_URL}/login" >/dev/null

cat <<SUMMARY
Controlled beta preflight passed.
Release SHA: ${BETA_RELEASE_SHA}
Maximum users: ${BETA_MAX_USERS}
Per-user daily request limit: ${BETA_PER_USER_DAILY_REQUEST_LIMIT}
Daily AI budget: USD ${BETA_DAILY_AI_BUDGET_USD}
Support owner: ${BETA_SUPPORT_OWNER}
Incident owner: ${BETA_INCIDENT_OWNER}
SUMMARY
