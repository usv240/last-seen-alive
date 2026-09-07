from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from agentic_core.api import ApiHooks, MemoryApiKeyStore, create_app
from agentic_core.api.keys import authenticate_key, mint_key

PEPPER = b"a-test-pepper-with-enough-bytes"


async def integrations() -> dict[str, dict[str, object]]:
    return {"google_vertex_ai": {"ok": True}, "parallel_search": {"ok": False}}


async def latest_eval() -> dict[str, object]:
    return {"split": "held-out", "counts": {"false_confident": 0}}


def client() -> TestClient:
    app = create_app(
        title="Test API",
        key_store=MemoryApiKeyStore(),
        key_pepper=PEPPER,
        hooks=ApiHooks(integration_health=integrations, latest_evaluation=latest_eval),
    )
    return TestClient(app)


def test_judge_can_mint_key_without_email_and_call_api() -> None:
    api = client()
    minted = api.post("/v1/keys", json={"tier": "judge"})
    assert minted.status_code == 200
    key = minted.json()["data"]["key"]
    assert key.startswith("lsa_")

    evaluation = api.get("/v1/eval/latest", headers={"Authorization": f"Bearer {key}"})
    assert evaluation.status_code == 200
    assert evaluation.json()["data"]["counts"]["false_confident"] == 0


def test_evaluation_key_requires_email() -> None:
    response = client().post("/v1/keys", json={"tier": "evaluation"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "email_required"


def test_integration_health_is_public() -> None:
    response = client().get("/health/integrations")
    assert response.status_code == 200
    assert not response.json()["data"]["integrations"]["parallel_search"]["ok"]


def test_key_from_one_instance_authenticates_on_another() -> None:
    """The failure this design exists to prevent.

    Cloud Run runs several instances. A key held in one process's memory would
    401 everywhere else, so a judge who minted a key on the landing page would
    be told it was invalid. A signed key must verify on a server that has never
    seen it before.
    """
    minting_instance = client()
    key = minting_instance.post("/v1/keys", json={"tier": "judge"}).json()["data"]["key"]

    other_instance = client()  # separate app, separate store, same pepper
    response = other_instance.get("/v1/eval/latest", headers={"Authorization": f"Bearer {key}"})
    assert response.status_code == 200


def test_key_signed_with_another_pepper_is_rejected() -> None:
    foreign, _ = mint_key(tier="judge", pepper=b"a-different-service-pepper")
    assert authenticate_key(foreign, pepper=PEPPER) is None

    response = client().get("/v1/eval/latest", headers={"Authorization": f"Bearer {foreign}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


def test_tampered_key_is_rejected() -> None:
    key, _ = mint_key(tier="judge", pepper=PEPPER)
    payload, _, signature = key.removeprefix("lsa_").partition(".")
    forged = f"lsa_{payload[:-2]}xx.{signature}"
    assert authenticate_key(forged, pepper=PEPPER) is None


def test_expired_key_is_rejected(monkeypatch) -> None:
    key, record = mint_key(tier="judge", pepper=PEPPER)
    assert authenticate_key(key, pepper=PEPPER) is not None

    class Expired(datetime):
        @classmethod
        def now(cls, tz=None):
            return record.expires_at + timedelta(seconds=1)

    monkeypatch.setattr("agentic_core.api.keys.datetime", Expired)
    assert authenticate_key(key, pepper=PEPPER) is None


def test_missing_and_malformed_authorization_are_distinguishable() -> None:
    api = client()
    assert api.get("/v1/eval/latest").json()["error"]["code"] == "missing_api_key"
    assert (
        api.get("/v1/eval/latest", headers={"Authorization": "Bearer not-a-key"}).json()["error"][
            "code"
        ]
        == "invalid_api_key"
    )


def test_daily_limit_is_enforced_per_key() -> None:
    app = create_app(
        title="Test API",
        key_store=MemoryApiKeyStore(),
        key_pepper=PEPPER,
        hooks=ApiHooks(integration_health=integrations, latest_evaluation=latest_eval),
    )
    api = TestClient(app)
    key = api.post("/v1/keys", json={"tier": "judge"}).json()["data"]["key"]
    headers = {"Authorization": f"Bearer {key}"}
    record = authenticate_key(key, pepper=PEPPER)
    assert record is not None

    app.state.usage._counts[record.key_id] = record.daily_limit
    response = api.get("/v1/eval/latest", headers=headers)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "daily_limit_reached"


def test_expiry_and_limit_match_the_tier() -> None:
    _, record = mint_key(tier="judge", pepper=PEPPER)
    assert record.daily_limit == 2_000
    assert 59 <= (record.expires_at - datetime.now(UTC)).days <= 60

    _, evaluation = mint_key(tier="evaluation", pepper=PEPPER)
    assert evaluation.daily_limit == 500
    assert 29 <= (evaluation.expires_at - datetime.now(UTC)).days <= 30
