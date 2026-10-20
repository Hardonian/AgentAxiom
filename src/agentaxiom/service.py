"""Small Cloud Run-compatible HTTP surface for offline evaluation."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contracts import Contract, evaluate_contract
from .evidence import write_bundle
from .models import Transcript


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/healthz":
            self.send_error(404); return
        self._reply(200, {"ok": True})

    def do_POST(self):
        if self.path != "/evaluate":
            self.send_error(404); return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 2_000_000: raise ValueError("request exceeds 2 MB")
            body = json.loads(self.rfile.read(size))
            transcript = Transcript.from_dict(body["transcript"])
            result = evaluate_contract(transcript, Contract(**body["contract"]))
            if body.get("write_evidence"):
                write_bundle(body.get("evidence_dir", "/tmp/agentaxiom-evidence"), transcript, result)
            self._reply(200, {"passed": result.passed, "violations": result.violations, "prompt_hash": transcript.scenario.prompt_hash})
        except (KeyError, TypeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})

    def _reply(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def log_message(self, format, *args): pass

def main() -> None:
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()

if __name__ == "__main__": main()
