import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

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
