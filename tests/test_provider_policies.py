import sys
import types

import pytest

from agentaxiom.models import Scenario, Turn
from agentaxiom.providers import (
    GeminiVertexClient,
    ProviderError,
    RetryPolicy,
    call_with_retry,
    classify_provider_error,
)


class FakeHTTPError(Exception):
    """Mimics google.genai / urllib HTTP errors: integer ``code`` attribute."""

    def __init__(self, code: int, status: str | None = None, request_id: str | None = None):
        super().__init__(f"HTTP {code}")
        self.code = code
        if status is not None:
            self.status = status
        if request_id is not None:
            self.request_id = request_id


class FakeResponse:
    text = '{"ok": true}'

    def model_dump(self, exclude_none=True):
        return {
            "candidates": [{"content": {"parts": [{"text": self.text}]}, "safety_ratings": []}],
            "usage_metadata": {"prompt_token_count": 10, "candidates_token_count": 5, "total_token_count": 15},
        }


@pytest.mark.parametrize(
    ("exc", "kind", "retryable"),
    [
        (FakeHTTPError(429), "rate_limited", True),
        (FakeHTTPError(408), "timeout", True),
        (FakeHTTPError(500), "server", True),
        (FakeHTTPError(503), "server", True),
        (FakeHTTPError(400), "invalid_request", False),
        (FakeHTTPError(401), "permission", False),
        (FakeHTTPError(403), "permission", False),
        (FakeHTTPError(404), "not_found", False),
        (FakeHTTPError(422), "client", False),
        (TimeoutError("deadline exceeded"), "timeout", True),
        (ConnectionResetError("peer reset"), "network", True),
        (ValueError("something else"), "unknown", False),
    ],
)
def test_classification_table(exc, kind, retryable):
    error = classify_provider_error(exc)
    assert (error.kind, error.retryable) == (kind, retryable)
    assert error.status == getattr(exc, "code", None)


def test_classification_preserves_provider_metadata():
    error = classify_provider_error(FakeHTTPError(429, status="RESOURCE_EXHAUSTED", request_id="req-1"))
    assert error.provider_code == "RESOURCE_EXHAUSTED"
    assert error.request_id == "req-1"
    assert error.to_dict()["kind"] == "rate_limited"


def test_unknown_errors_are_never_retried():
    calls = {"n": 0}

    def explode():
        calls["n"] += 1
        raise ValueError("mystery")

    with pytest.raises(ProviderError) as caught:
        call_with_retry(explode, policy=RetryPolicy(max_attempts=5), sleep=lambda _: None)
    assert caught.value.kind == "unknown"
    assert caught.value.attempts == 1
    assert calls["n"] == 1


def test_rate_limit_retries_then_succeeds():
    calls = {"n": 0}
    delays: list[float] = []
    retries: list[tuple[str, float]] = []

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise FakeHTTPError(429)
        return "ok"

    policy = RetryPolicy(max_attempts=3, initial_backoff_s=0.5, jitter=0.0)
    result = call_with_retry(
        flaky,
        policy=policy,
        on_retry=lambda error, delay: retries.append((error.kind, delay)),
        sleep=delays.append,
    )
    assert result == "ok"
    assert calls["n"] == 2
    assert retries == [("rate_limited", 0.5)]
    assert delays == [0.5]


def test_exhaustion_raises_normalized_error_with_attempt_count():
    calls = {"n": 0}

    def always_down():
        calls["n"] += 1
        raise FakeHTTPError(503)

    with pytest.raises(ProviderError) as caught:
        call_with_retry(always_down, policy=RetryPolicy(max_attempts=3, jitter=0.0), sleep=lambda _: None)
    assert caught.value.kind == "server"
    assert caught.value.attempts == 3
    assert calls["n"] == 3


def test_backoff_is_exponential_and_bounded():
    policy = RetryPolicy(initial_backoff_s=1.0, max_backoff_s=4.0, jitter=0.0)
    assert [policy.backoff_for(attempt) for attempt in (1, 2, 3, 10)] == [1.0, 2.0, 4.0, 4.0]


def test_backoff_jitter_stays_within_bounds():
    policy = RetryPolicy(initial_backoff_s=2.0, max_backoff_s=8.0, jitter=0.25)
    assert policy.backoff_for(1, rand=lambda: 0.0) == 1.5
    assert policy.backoff_for(1, rand=lambda: 1.0) == 2.5


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_attempts": 0},
        {"initial_backoff_s": 0},
        {"max_backoff_s": -1},
        {"jitter": 1.0},
        {"jitter": -0.1},
    ],
)
def test_retry_policy_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        RetryPolicy(**kwargs)


def install_fake_genai(monkeypatch, responses):
    calls = {"client_kwargs": [], "generate": 0}

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            item = responses[min(calls["generate"], len(responses) - 1)]
            calls["generate"] += 1
            if isinstance(item, Exception):
                raise item
            return item

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client_kwargs"].append(kwargs)
            self.models = FakeModels()

    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")
    genai_module.Client = FakeClient
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    return calls


def test_client_passes_timeout_as_http_options(monkeypatch):
    calls = install_fake_genai(monkeypatch, [FakeResponse()])
    client = GeminiVertexClient(model="gemini-2.5-flash", timeout_s=30.0)
    assert client.timeout_s == 30.0
    assert calls["client_kwargs"][0]["http_options"] == {"timeout": 30.0}


def test_client_defaults_to_no_http_options_override(monkeypatch):
    calls = install_fake_genai(monkeypatch, [FakeResponse()])
    GeminiVertexClient(model="gemini-2.5-flash")
    assert calls["client_kwargs"][0]["http_options"] is None


def test_client_retries_rate_limit_through_policy(monkeypatch):
    calls = install_fake_genai(monkeypatch, [FakeHTTPError(429), FakeResponse()])
    client = GeminiVertexClient(
        model="gemini-2.5-flash",
        generation={"response_mime_type": "application/json"},
        retry_policy=RetryPolicy(max_attempts=3, initial_backoff_s=0.001, jitter=0.0),
    )
    invocation = client.invoke(Scenario(name="policy-test", turns=[Turn(role="user", content="hello")]))
    assert calls["generate"] == 2
    assert invocation.structured_output == {"ok": True}
    assert invocation.token_usage == {"input": 10, "output": 5, "total": 15}


def test_client_non_retryable_error_surfaces_immediately(monkeypatch):
    calls = install_fake_genai(monkeypatch, [FakeHTTPError(400)])
    client = GeminiVertexClient(model="gemini-2.5-flash")
    with pytest.raises(ProviderError) as caught:
        client.invoke(Scenario(name="policy-test", turns=[Turn(role="user", content="hello")]))
    assert caught.value.kind == "invalid_request"
    assert caught.value.attempts == 1
    assert calls["generate"] == 1


def test_client_rejects_non_positive_timeout(monkeypatch):
    install_fake_genai(monkeypatch, [FakeResponse()])
    with pytest.raises(ValueError):
        GeminiVertexClient(model="gemini-2.5-flash", timeout_s=0)
