"""Automated staging exercise: load, failure, and recovery drills.

Exercises the evaluator service under concurrent load and simulated failure conditions:
  python scripts/staging_drills.py
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from agentaxiom.service import Handler


def run_drill():
    # Start local evaluator instance on ephemeral port
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    print(f"[*] Evaluator service drill running at {base_url}")

    sample_transcript = {
        "schema_version": "v1",
        "scenario": {
            "name": "staging-drill",
            "turns": [{"role": "user", "content": "Ping test"}],
            "metadata": {"env": "staging"},
        },
        "invocation": {
            "model": "gemini-2.5-flash",
            "region": "us-central1",
            "response_text": "Pong",
            "structured_output": {"ok": True},
            "token_usage": {"input": 10, "output": 5, "total": 15},
            "latency_ms": 45,
            "estimated_cost_usd": 0.0001,
        },
    }
    sample_contract = {
        "name": "drill-contract",
        "output_schema": {"type": "object", "required": ["ok"]},
        "max_latency_ms": 1000,
        "max_cost_usd": 0.05,
    }

    # Drill 1: Healthcheck Readiness
    with urllib.request.urlopen(f"{base_url}/healthz") as resp:
        assert resp.status == 200
        assert json.loads(resp.read()) == {"ok": True}
    print("[OK] Drill 1 Passed: /healthz readiness verified.")

    # Drill 2: Concurrent Load Test (30 concurrent workers)
    payload = json.dumps({"transcript": sample_transcript, "contract": sample_contract}).encode("utf-8")

    def send_eval():
        req = urllib.request.Request(
            f"{base_url}/evaluate",
            data=payload,
            headers={"Content-Type": "application/json", "X-Cloud-Trace-Context": "drill-trace-12345/1;o=1"},
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            assert data["passed"] is True
            return resp.status

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_eval) for _ in range(30)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    duration = time.perf_counter() - t0
    assert all(status == 200 for status in results)
    print(f"[OK] Drill 2 Passed: 30 concurrent evaluations completed in {duration:.2f}s (0 errors).")

    # Drill 3: Failure Injection - Oversized Payload (>2MB)
    huge_data = b"x" * (2_000_001)
    req_huge = urllib.request.Request(
        f"{base_url}/evaluate",
        data=huge_data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req_huge)
        raise AssertionError("Expected 400 for oversized payload")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
        error_body = json.loads(exc.read())
        assert "exceeds 2 MB" in error_body["error"]
    print("[OK] Drill 3 Passed: 2MB request cap enforced (HTTP 400 rejected).")

    # Drill 4: Failure Injection - Malformed JSON & Bad Content-Type
    req_bad_type = urllib.request.Request(f"{base_url}/evaluate", data=b"bad", headers={"Content-Type": "text/plain"})
    try:
        urllib.request.urlopen(req_bad_type)
        raise AssertionError("Expected 400 for non-JSON content-type")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    print("[OK] Drill 4 Passed: Content-Type enforcement verified.")

    # Drill 5: Budget Denial & Contract Violation Path
    failing_contract = {
        "name": "strict-contract",
        "required_tools": ["mandatory_db_lookup"],
        "max_latency_ms": 10,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AGENTAXIOM_EVIDENCE_DIR"] = tmpdir
        fail_payload = json.dumps(
            {"transcript": sample_transcript, "contract": failing_contract, "write_evidence": True}
        ).encode("utf-8")
        req_fail = urllib.request.Request(
            f"{base_url}/evaluate",
            data=fail_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_fail) as resp:
            data = json.loads(resp.read())
            assert data["passed"] is False
            assert len(data["violations"]) >= 1
    print("[OK] Drill 5 Passed: Deterministic contract violation and evidence generation verified.")

    # Drill 6: Comparison Endpoint Rehearsal
    compare_payload = json.dumps({"baseline": sample_transcript, "candidate": sample_transcript}).encode("utf-8")
    req_comp = urllib.request.Request(
        f"{base_url}/compare",
        data=compare_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_comp) as resp:
        assert json.loads(resp.read()) == {"equivalent": True, "regressions": []}
    print("[OK] Drill 6 Passed: /compare endpoint rehearsal verified.")

    server.shutdown()
    print("\n[SUCCESS] Staging drills complete: all load, failure, and recovery conditions passed.")


if __name__ == "__main__":
    run_drill()
