import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agentaxiom.service import Handler


def test_evaluate_endpoint_returns_contract_result_and_trace_id():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    payload = {
        "transcript": {
            "schema_version": "v1",
            "scenario": {"name": "service", "turns": [{"role": "user", "content": "hello"}]},
            "invocation": {"model": "offline", "region": "us"},
        },
        "contract": {"name": "pass"},
    }
    request = Request(
        f"http://127.0.0.1:{server.server_port}/evaluate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Cloud-Trace-Context": "abc123/1;o=1"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2) as response:
            result = json.loads(response.read())
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
    assert result == {"passed": True, "violations": [], "prompt_hash": result["prompt_hash"], "trace_id": "abc123"}


def test_root_serves_no_code_console():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=2) as response:
            page = response.read().decode()
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
    assert "Check your AI agent" in page


def test_api_requires_json_content_type_and_sets_no_store_headers():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    request = Request(f"http://127.0.0.1:{server.server_port}/evaluate", data=b"{}", method="POST")
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(request, timeout=2)
        assert error.value.code == 400
        assert error.value.headers["Cache-Control"] == "no-store"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
