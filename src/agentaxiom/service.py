"""Small Cloud Run-compatible HTTP surface for offline evaluation."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any

from .comparison import ComparisonPolicy, compare
from .contracts import Contract, evaluate_contract
from .evidence import write_bundle
from .exports import format_gcp_log_entry
from .models import Transcript


def _emit_gcp_log(entry: dict[str, Any]) -> None:
    print(json.dumps(entry, default=str), flush=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._html(files("agentaxiom.ui").joinpath("index.html").read_text(encoding="utf-8"))
            return
        if self.path != "/healthz":
            self.send_error(404)
            return
        self._reply(200, {"ok": True})

    def do_POST(self):
        if self.path not in {"/evaluate", "/compare"}:
            self.send_error(404)
            return
        try:
            if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                raise ValueError("Content-Type must be application/json")
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0:
                raise ValueError("request body is required")
            if size > 2_000_000:
                raise ValueError("request exceeds 2 MB")
            body = json.loads(self.rfile.read(size))
            if self.path == "/compare":
                result = compare(
                    Transcript.from_dict(body["baseline"]),
                    Transcript.from_dict(body["candidate"]),
                    ComparisonPolicy(**body.get("policy", {})),
                )
                self._reply(200, {"equivalent": result.equivalent, "regressions": result.regressions})
                return
            transcript = Transcript.from_dict(body["transcript"])
            transcript.invocation.trace_id = (
                transcript.invocation.trace_id or self.headers.get("X-Cloud-Trace-Context", "").split("/")[0] or None
            )
            result = evaluate_contract(transcript, Contract(**body["contract"]))
            if body.get("write_evidence"):
                write_bundle(os.environ.get("AGENTAXIOM_EVIDENCE_DIR", "/tmp/agentaxiom-evidence"), transcript, result)

            log_entry = format_gcp_log_entry(
                transcript,
                result,
                project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            )
            _emit_gcp_log(log_entry)

            self._reply(
                200,
                {
                    "passed": result.passed,
                    "violations": result.violations,
                    "prompt_hash": transcript.scenario.prompt_hash,
                    "trace_id": transcript.invocation.trace_id,
                },
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            _emit_gcp_log({
                "severity": "WARNING",
                "message": f"Bad evaluation request: {exc}",
                "component": "agentaxiom-evaluator",
            })
            self._reply(400, {"error": str(exc)})

    def _reply(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self, content):
        data = content.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'",
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def main() -> None:
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()


if __name__ == "__main__":
    main()
