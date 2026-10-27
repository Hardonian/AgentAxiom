from __future__ import annotations

import argparse
import json
from pathlib import Path

from .comparison import ComparisonPolicy, compare
from .contracts import Contract, evaluate_contract
from .evidence import write_bundle
from .exports import export_vertex_evaluation
from .minimize import minimize_conversation
from .models import Scenario, Transcript, Turn
from .service import main as serve


def main() -> int:
    parser = argparse.ArgumentParser(prog="agentaxiom")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("transcript")
    check.add_argument("contract")
    check.add_argument("--evidence-dir", default="agentaxiom-evidence")

    diff = sub.add_parser("compare")
    diff.add_argument("baseline")
    diff.add_argument("candidate")
    diff.add_argument("--policy")

    minimize = sub.add_parser("minimize")
    minimize.add_argument("transcript")
    minimize.add_argument("contract")
    minimize.add_argument("--output", required=True)

    record = sub.add_parser("record", help="record a live Gemini / Vertex response to a fixture")
    record.add_argument("--model", default="gemini-2.5-flash", help="Gemini or Vertex AI model name")
    record.add_argument("--prompt", required=True, help="User prompt to send")
    record.add_argument("--output", required=True, help="Path to write the transcript fixture")
    record.add_argument("--project", default=None, help="GCP project ID (enables Vertex AI mode)")
    record.add_argument("--location", default="us-central1", help="GCP location / region")
    record.add_argument("--scenario-name", default="cli-recorded", help="Scenario identifier")

    export_eval = sub.add_parser("export-eval", help="export transcripts to Vertex AI Evaluation format")
    export_eval.add_argument("transcript", help="Path to transcript JSON")
    export_eval.add_argument("--output", required=True, help="Output JSONL path for Vertex AI EvalTask")

    sub.add_parser("serve", help="start the plain-language browser console")

    args = parser.parse_args()

    if args.command == "serve":
        serve()
        return 0

    if args.command == "check":
        transcript = Transcript.from_dict(json.loads(Path(args.transcript).read_text(encoding="utf-8")))
        contract = Contract(**json.loads(Path(args.contract).read_text(encoding="utf-8")))
        result = evaluate_contract(transcript, contract)
        write_bundle(args.evidence_dir, transcript, result)
        print(json.dumps({"passed": result.passed, "violations": result.violations}))
        return 0 if result.passed else 1

    if args.command == "compare":
        baseline = Transcript.from_dict(json.loads(Path(args.baseline).read_text(encoding="utf-8")))
        candidate = Transcript.from_dict(json.loads(Path(args.candidate).read_text(encoding="utf-8")))
        policy = (
            ComparisonPolicy(**json.loads(Path(args.policy).read_text(encoding="utf-8")))
            if args.policy
            else ComparisonPolicy()
        )
        result = compare(baseline, candidate, policy)
        print(json.dumps({"equivalent": result.equivalent, "regressions": result.regressions}))
        return 0 if result.equivalent else 1

    if args.command == "minimize":
        recorded = Transcript.from_dict(json.loads(Path(args.transcript).read_text(encoding="utf-8")))
        contract = Contract(**json.loads(Path(args.contract).read_text(encoding="utf-8")))
        if evaluate_contract(recorded, contract).passed:
            print(json.dumps({"error": "refusing to minimize a passing transcript"}))
            return 2
        minimized = minimize_conversation(recorded, lambda trace: not evaluate_contract(trace, contract).passed)
        Path(args.output).write_text(json.dumps(minimized.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        print(
            json.dumps(
                {
                    "turns_before": len(recorded.scenario.turns),
                    "turns_after": len(minimized.scenario.turns),
                    "output": args.output,
                }
            )
        )
        return 0

    if args.command == "record":
        from .providers import GeminiVertexClient

        client = GeminiVertexClient(
            model=args.model,
            project=args.project,
            location=args.location,
        )
        scenario = Scenario(name=args.scenario_name, turns=[Turn(role="user", content=args.prompt)])
        invocation = client.invoke(scenario)
        transcript = Transcript(scenario=scenario, invocation=invocation)
        Path(args.output).write_text(json.dumps(transcript.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"recorded": args.output, "model": args.model, "tokens": invocation.token_usage}))
        return 0

    if args.command == "export-eval":
        transcript = Transcript.from_dict(json.loads(Path(args.transcript).read_text(encoding="utf-8")))
        out = export_vertex_evaluation(transcript, args.output)
        print(json.dumps({"exported": str(out), "scenario": transcript.scenario.name}))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
