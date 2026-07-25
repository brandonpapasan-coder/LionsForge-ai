import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "staging_preflight.py"
SPEC = spec_from_file_location("staging_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_configuration = MODULE.validate_configuration


def valid_values() -> dict[str, str]:
    return {
        "AWS_REGION": "us-east-1",
        "TF_STATE_BUCKET": "lionsforge-staging-tfstate",
        "AWS_TERRAFORM_PLAN_ROLE_ARN": "arn:aws:iam::123456789012:role/lionsforge-staging-plan",
        "AWS_TERRAFORM_APPLY_ROLE_ARN": "arn:aws:iam::123456789012:role/lionsforge-staging-apply",
        "STAGING_API_URL": "https://api.staging.example.com",
        "STAGING_WEB_URL": "https://app.staging.example.com",
    }


def test_valid_configuration_is_normalized():
    result = validate_configuration(valid_values())
    assert result == {
        "aws_region": "us-east-1",
        "state_bucket": "lionsforge-staging-tfstate",
        "api_origin": "https://api.staging.example.com",
        "web_origin": "https://app.staging.example.com",
    }


@pytest.mark.parametrize("region", ["us_east_1", "US-EAST-1", "us-east", "local"])
def test_invalid_aws_region_is_rejected(region):
    values = valid_values()
    values["AWS_REGION"] = region
    with pytest.raises(RuntimeError, match="AWS_REGION"):
        validate_configuration(values)


@pytest.mark.parametrize(
    "key,value",
    [
        ("AWS_TERRAFORM_PLAN_ROLE_ARN", "plan-role"),
        ("AWS_TERRAFORM_APPLY_ROLE_ARN", "arn:aws:iam::123:role/apply"),
    ],
)
def test_invalid_role_arn_is_rejected(key, value):
    values = valid_values()
    values[key] = value
    with pytest.raises(RuntimeError, match=key):
        validate_configuration(values)


def test_plan_and_apply_roles_must_differ():
    values = valid_values()
    values["AWS_TERRAFORM_APPLY_ROLE_ARN"] = values["AWS_TERRAFORM_PLAN_ROLE_ARN"]
    with pytest.raises(RuntimeError, match="must be different"):
        validate_configuration(values)


@pytest.mark.parametrize("bucket", ["LionsForge-State", "lionsforge..state", "other-state", "lionsforge_unsafe"])
def test_invalid_state_bucket_is_rejected(bucket):
    values = valid_values()
    values["TF_STATE_BUCKET"] = bucket
    with pytest.raises(RuntimeError, match="TF_STATE_BUCKET"):
        validate_configuration(values)


@pytest.mark.parametrize(
    "url",
    [
        "http://api.staging.example.com",
        "https://user:pass@api.staging.example.com",
        "https://api.staging.example.com/health",
        "https://api.staging.example.com?debug=true",
        "https://localhost",
        "https://127.0.0.1",
        "https://api.internal",
        "https://api.staging.example.com:8443",
    ],
)
def test_unsafe_api_origin_is_rejected(url):
    values = valid_values()
    values["STAGING_API_URL"] = url
    with pytest.raises(RuntimeError, match="STAGING_API_URL"):
        validate_configuration(values)


def test_api_and_web_hosts_must_be_distinct():
    values = valid_values()
    values["STAGING_WEB_URL"] = "https://api.staging.example.com/"
    with pytest.raises(RuntimeError, match="distinct hosts"):
        validate_configuration(values)
