import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from agentaxiom import (
    Contract,
    Invocation,
    ModelPricing,
    PricingCatalog,
    Scenario,
    Transcript,
    Turn,
    evaluate_contract,
    export_vertex_evaluation,
    format_gcp_log_entry,
    record_gemini,
)
from agentaxiom.evidence import redact
from agentaxiom.recorder import parse_turns_from_gemini_contents


def test_context_caching_contract_enforcement():
    scenario = Scenario("cache-test", [Turn("user", "Summarize 100-page doc")])

    # Case 1: Cache hit with 40,000 cached tokens
    cached_inv = Invocation(
        model="gemini-2.5-flash",
        region="us-central1",
        token_usage={"input": 45000, "output": 200, "cached": 40000},
    )
    contract = Contract(
        name="doc-cache-contract",
        require_context_cache=True,
        min_cached_tokens=30000,
    )
    result = evaluate_contract(Transcript(scenario, cached_inv), contract)
    assert result.passed

    # Case 2: Cache miss (0 cached tokens)
    uncached_inv = Invocation(
        model="gemini-2.5-flash",
        region="us-central1",
        token_usage={"input": 45000, "output": 200, "cached": 0},
    )
    fail_result = evaluate_contract(Transcript(scenario, uncached_inv), contract)
    assert not fail_result.passed
    kinds = [v["kind"] for v in fail_result.violations]
    assert "context_cache" in kinds
    assert "cached_tokens" in kinds


def test_thinking_tokens_budget():
    scenario = Scenario("thinking-test", [Turn("user", "Solve complex logic riddle")])
    inv = Invocation(
        model="gemini-2.5-flash",
        region="us-central1",
        thought_text="Step 1... Step 2...",
        token_usage={"input": 100, "output": 1500, "thoughts": 1200},
    )
    # Passed when thinking is within budget
    pass_contract = Contract("think-ok", max_thinking_tokens=2000)
    assert evaluate_contract(Transcript(scenario, inv), pass_contract).passed

    # Failed when thinking exceeds budget
    fail_contract = Contract("think-fail", max_thinking_tokens=500)
    fail_result = evaluate_contract(Transcript(scenario, inv), fail_contract)
    assert not fail_result.passed
    assert fail_result.violations[0]["kind"] == "thinking_budget"
    assert fail_result.violations[0]["actual"] == 1200


def test_multimodal_turns_and_gcs_parts():
    parts = [
        {"text": "Analyze this loan application."},
        {"file_data": {"file_uri": "gs://finance-bucket/loans/app_001.pdf", "mime_type": "application/pdf"}},
    ]
    turn = Turn(role="user", parts=parts)
    assert turn.effective_text == "Analyze this loan application."

    scenario = Scenario("multimodal", [turn])
    assert scenario.prompt_hash is not None

    parsed_turns = parse_turns_from_gemini_contents([{"role": "user", "parts": parts}])
    assert len(parsed_turns) == 1
    assert parsed_turns[0].parts[1]["file_data"]["file_uri"] == "gs://finance-bucket/loans/app_001.pdf"


def test_vertex_grounding_and_datastore_validation():
    scenario = Scenario("grounding", [Turn("user", "Company remote work policy")])
    inv = Invocation(
        model="gemini-2.5-flash",
        region="us-central1",
        citations=[{"uri": "https://intranet.corp.test/hr/remote-work"}],
        grounding={
            "grounding_supports": [{"confidence_score": 0.95}],
            "grounding_chunks": [
                {"retrieved_context": {"rag_corpus_id": "projects/123/locations/us/ragCorpora/company-kb"}}
            ],
        },
    )
    # Valid grounding sources
    good_contract = Contract(
        name="grounding-pass",
        min_grounding_score=0.90,
        allowed_grounding_sources=["intranet.corp.test", "projects/123/locations/us/ragCorpora/company-kb"],
    )
    assert evaluate_contract(Transcript(scenario, inv), good_contract).passed

    # Invalid datastore and insufficient score
    bad_contract = Contract(
        name="grounding-fail",
        min_grounding_score=0.99,
        allowed_grounding_sources=["https://unapproved.source.test"],
    )
    res = evaluate_contract(Transcript(scenario, inv), bad_contract)
    assert not res.passed
    kinds = [v["kind"] for v in res.violations]
    assert "grounding_score" in kinds
    assert "grounding_source" in kinds


def test_vertex_safety_category_filtering():
    scenario = Scenario("safety", [Turn("user", "Potentially hazardous instruction")])
    inv = Invocation(
        model="gemini-2.5-flash",
        region="us-central1",
        safety={
            "ratings": [
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "NEGLIGIBLE"},
            ]
        },
    )
    contract = Contract(
        name="safety-check",
        blocked_safety_categories=["HARM_CATEGORY_DANGEROUS_CONTENT"],
    )
    result = evaluate_contract(Transcript(scenario, inv), contract)
    assert not result.passed
    assert result.violations[0]["kind"] == "safety_category"
    assert result.violations[0]["category"] == "HARM_CATEGORY_DANGEROUS_CONTENT"


def test_pricing_with_context_caching_and_thinking():
    catalog = PricingCatalog(
        rates={
            "gemini-2.5-flash": ModelPricing(
                input_per_million_usd=0.30,
                output_per_million_usd=2.50,
                cached_read_per_million_usd=0.075,
                thinking_per_million_usd=2.50,
            )
        }
    )
    # 50,000 input tokens where 40,000 are cached (10,000 prompt @ 0.30/M, 40,000 cached @ 0.075/M)
    # 2,000 output tokens where 1,000 are thoughts
    usage = {"input": 50000, "cached": 40000, "output": 2000, "thoughts": 1000}
    cost = catalog.estimate("gemini-2.5-flash", usage)

    # 10,000 * 0.30 / 1M = 0.003
    # 40,000 * 0.075 / 1M = 0.003
    # 2,000 * 2.50 / 1M = 0.005
    # Total = 0.011
    assert cost == 0.011


def test_google_secret_redactions():
    data = {
        "oauth_token": "Bearer ya29.a0AfH6SMDh_fake_token_48924718972",
        "service_account": "audit-runner@my-project.iam.gserviceaccount.com",
        "nested": {
            "key": "AIzaSyD-fake_key_for_testing_12345678",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nsecret_bytes\n-----END RSA PRIVATE KEY-----",
        },
    }
    redacted = redact(data)
    assert "ya29" not in str(redacted)
    assert "gserviceaccount.com" not in str(redacted)
    assert "AIza" not in str(redacted)
    assert "BEGIN RSA PRIVATE KEY" not in str(redacted)
    assert redacted["nested"]["key"] == "[REDACTED]"
    assert redacted["service_account"] == "[REDACTED]"


def test_export_vertex_evaluation():
    t = Transcript(
        Scenario("test-eval", [Turn("user", "What is BigQuery?")]),
        Invocation(
            model="gemini-2.5-flash",
            region="us-central1",
            response_text="BigQuery is Google Cloud's serverless data warehouse.",
            token_usage={"input": 10, "output": 15},
        ),
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "eval.jsonl"
        export_vertex_evaluation(t, out_path)
        assert out_path.exists()
        lines = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
        assert len(lines) == 1
        assert lines[0]["prompt"] == "What is BigQuery?"
        assert "serverless data warehouse" in lines[0]["response"]


def test_cloud_logging_structured_entry():
    transcript = Transcript(
        Scenario("trace-test", [Turn("user", "Hello")]),
        Invocation(
            model="gemini-2.5-flash",
            region="us-central1",
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        ),
    )
    contract = Contract("sample-contract")
    res = evaluate_contract(transcript, contract)
    log_entry = format_gcp_log_entry(transcript, res, project_id="my-gcp-project")

    assert log_entry["severity"] == "INFO"
    expected_trace = "projects/my-gcp-project/traces/4bf92f3577b34da6a3ce929d0e0e4736"
    assert log_entry["logging.googleapis.com/trace"] == expected_trace
    assert log_entry["passed"] is True


def test_record_gemini_context_manager():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.text = '{"answer": "ok"}'
    fake_response.model_dump.return_value = {
        "candidates": [
            {
                "content": {"parts": [{"text": '{"answer": "ok"}'}]},
                "safety_ratings": [],
            }
        ],
        "usage_metadata": {
            "prompt_token_count": 25,
            "candidates_token_count": 10,
            "total_token_count": 35,
            "cached_content_token_count": 20,
        },
    }
    fake_client.models.generate_content.return_value = fake_response

    with record_gemini(fake_client, scenario_name="sdk-test") as rec:
        resp = fake_client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Hello Gemini",
            config={"response_mime_type": "application/json"},
        )
        assert resp == fake_response

    transcript = rec.transcript
    assert transcript.scenario.name == "sdk-test"
    assert transcript.scenario.turns[0].content == "Hello Gemini"
    assert transcript.invocation.structured_output == {"answer": "ok"}
    assert transcript.invocation.token_usage["cached"] == 20


def test_pytest_plugin_agent_contract_convenience(agent_contract):
    scenario = Scenario("fixture-test", [Turn("user", "test")])
    invocation = Invocation(
        model="gemini-2.5-flash",
        region="us-central1",
        response_text="passed",
    )
    t = Transcript(scenario, invocation)

    # Dictionary contract input works seamlessly
    res = agent_contract(t, {"name": "dict-contract"})
    assert res.passed


def test_bundled_assets():
    from agentaxiom.schemas import get_schema

    contract_schema = get_schema("contract.v1")
    assert contract_schema["title"] == "AgentAxiom Contract v1"

    transcript_schema = get_schema("transcript.v1")
    assert transcript_schema["title"] == "AgentAxiom Transcript v1"

    catalog = PricingCatalog.bundled()
    assert "gemini-2.5-flash" in catalog.rates
    assert catalog.rates["gemini-2.5-flash"].cached_read_per_million_usd == 0.075
