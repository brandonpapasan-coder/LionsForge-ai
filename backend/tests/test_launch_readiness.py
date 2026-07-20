def test_launch_readiness_uses_conservative_external_defaults(client):
    response = client.get("/launch-readiness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["contract_version"] == "1.0"
    assert payload["overall_status"] == "blocked_external_evidence"
    assert payload["release_candidate"] == "validated-main-candidate"

    keys = [gate["key"] for gate in payload["gates"]]
    assert keys == [
        "repository_validation_controls",
        "staging_acceptance",
        "production_controls",
        "policy_and_support",
        "controlled_beta",
        "general_availability",
    ]

    repository_gate = payload["gates"][0]
    assert repository_gate["category"] == "repository"
    assert repository_gate["status"] == "available"

    external_gates = payload["gates"][1:]
    assert all(gate["category"] == "external" for gate in external_gates)
    assert all(gate["status"] == "unverified" for gate in external_gates)
    assert [gate["issue"] for gate in external_gates] == [29, 401, 402, 403, 400]

    notice = payload["interpretation_notice"]
    assert "not proof" in notice
    assert "controlled beta" in notice
    assert "general-availability" in notice


def test_launch_readiness_is_deterministic(client):
    first = client.get("/launch-readiness").json()
    second = client.get("/launch-readiness").json()
    assert first == second
