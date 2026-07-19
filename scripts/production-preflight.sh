#!/usr/bin/env bash
set -euo pipefail

failures=0

check_command() {
  local command_name="$1"
  if command -v "${command_name}" >/dev/null 2>&1; then
    printf 'PASS command: %s\n' "${command_name}"
  else
    printf 'FAIL command missing: %s\n' "${command_name}" >&2
    failures=$((failures + 1))
  fi
}

check_required() {
  local variable_name="$1"
  if [[ -n "${!variable_name:-}" ]]; then
    printf 'PASS variable set: %s\n' "${variable_name}"
  else
    printf 'FAIL variable missing: %s\n' "${variable_name}" >&2
    failures=$((failures + 1))
  fi
}

check_https() {
  local variable_name="$1"
  local value="${!variable_name:-}"
  if [[ "${value}" == https://* ]]; then
    printf 'PASS HTTPS URL: %s\n' "${variable_name}"
  else
    printf 'FAIL %s must be a non-empty HTTPS URL\n' "${variable_name}" >&2
    failures=$((failures + 1))
  fi
}

for command_name in git gh kubectl terraform curl docker; do
  check_command "${command_name}"
done

check_required RELEASE_SHA
check_required ROLLBACK_SHA
check_required PRODUCTION_API_URL
check_required PRODUCTION_WEB_URL
check_https PRODUCTION_API_URL
check_https PRODUCTION_WEB_URL

if [[ "${RELEASE_SHA:-}" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'PASS immutable release SHA format\n'
else
  printf 'FAIL RELEASE_SHA must be a 40-character lowercase commit SHA\n' >&2
  failures=$((failures + 1))
fi

if [[ "${ROLLBACK_SHA:-}" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'PASS immutable rollback SHA format\n'
else
  printf 'FAIL ROLLBACK_SHA must be a 40-character lowercase commit SHA\n' >&2
  failures=$((failures + 1))
fi

if [[ -n "${RELEASE_SHA:-}" && "${RELEASE_SHA}" == "${ROLLBACK_SHA:-}" ]]; then
  printf 'FAIL release and rollback SHAs must differ\n' >&2
  failures=$((failures + 1))
fi

if command -v git >/dev/null 2>&1 && [[ -n "${RELEASE_SHA:-}" ]]; then
  git fetch origin main --no-tags
  if git cat-file -e "${RELEASE_SHA}^{commit}" 2>/dev/null && git merge-base --is-ancestor "${RELEASE_SHA}" origin/main; then
    printf 'PASS release SHA is contained in origin/main\n'
  else
    printf 'FAIL release SHA is not a commit contained in origin/main\n' >&2
    failures=$((failures + 1))
  fi
  if [[ -n "${ROLLBACK_SHA:-}" ]] && git cat-file -e "${ROLLBACK_SHA}^{commit}" 2>/dev/null && git merge-base --is-ancestor "${ROLLBACK_SHA}" origin/main; then
    printf 'PASS rollback SHA is contained in origin/main\n'
  else
    printf 'FAIL rollback SHA is not a commit contained in origin/main\n' >&2
    failures=$((failures + 1))
  fi
fi

if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    printf 'PASS GitHub CLI authentication\n'
  else
    printf 'FAIL GitHub CLI is not authenticated\n' >&2
    failures=$((failures + 1))
  fi
fi

if command -v kubectl >/dev/null 2>&1; then
  if kubectl config current-context >/dev/null 2>&1; then
    printf 'PASS kubectl context configured\n'
  else
    printf 'FAIL kubectl context is not configured\n' >&2
    failures=$((failures + 1))
  fi
fi

if (( failures > 0 )); then
  printf 'Production preflight failed with %d issue(s).\n' "${failures}" >&2
  exit 1
fi

printf 'Production preflight passed. This does not authorize deployment until staging GO, workflow evidence, approvals, secrets, backup/restore, rollback, and observability gates are recorded.\n'
