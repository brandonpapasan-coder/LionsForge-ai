#!/usr/bin/env bash
set -euo pipefail

errors=0
warnings=0

pass() { printf 'PASS  %s\n' "$1"; }
warn() { printf 'WARN  %s\n' "$1"; warnings=$((warnings + 1)); }
fail() { printf 'FAIL  %s\n' "$1"; errors=$((errors + 1)); }

required_commands=(git gh kubectl terraform curl)
for command_name in "${required_commands[@]}"; do
  if command -v "$command_name" >/dev/null 2>&1; then
    pass "command available: $command_name"
  else
    fail "missing required command: $command_name"
  fi
done

release_sha="${RELEASE_SHA:-}"
if [[ "$release_sha" =~ ^[0-9a-f]{40}$ ]]; then
  pass "RELEASE_SHA is an immutable 40-character lowercase SHA"
else
  fail "RELEASE_SHA must be a 40-character lowercase commit SHA"
fi

for variable_name in STAGING_API_URL STAGING_WEB_URL AWS_REGION TF_STATE_BUCKET; do
  value="${!variable_name:-}"
  if [[ -n "$value" ]]; then
    pass "$variable_name is set"
  else
    fail "$variable_name is not set"
  fi
done

for url_variable in STAGING_API_URL STAGING_WEB_URL; do
  value="${!url_variable:-}"
  if [[ "$value" =~ ^https://[^[:space:]]+$ ]]; then
    pass "$url_variable uses HTTPS"
  elif [[ -n "$value" ]]; then
    fail "$url_variable must be a non-empty HTTPS URL"
  fi
done

if [[ -n "$release_sha" ]] && git cat-file -e "${release_sha}^{commit}" 2>/dev/null; then
  pass "release commit exists in the local repository"
  if git merge-base --is-ancestor "$release_sha" origin/main 2>/dev/null; then
    pass "release commit is contained in origin/main"
  else
    fail "release commit is not contained in origin/main"
  fi
else
  warn "release commit could not be verified locally; fetch origin before deployment"
fi

if gh auth status >/dev/null 2>&1; then
  pass "GitHub CLI authentication is active"
else
  fail "GitHub CLI is not authenticated"
fi

if kubectl config current-context >/dev/null 2>&1; then
  pass "kubectl has an active context"
else
  fail "kubectl has no active context"
fi

if terraform version >/dev/null 2>&1; then
  pass "Terraform is executable"
fi

printf '\nPreflight result: %d error(s), %d warning(s).\n' "$errors" "$warnings"
if (( errors > 0 )); then
  exit 1
fi
