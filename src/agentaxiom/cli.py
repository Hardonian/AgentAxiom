from __future__ import annotations

import argparse, json
from pathlib import Path

from .comparison import ComparisonPolicy, compare
from .contracts import Contract, evaluate_contract
from .evidence import write_bundle
from .minimize import minimize_conversation
from .models import Transcript

def main() -> int:
    parser = argparse.ArgumentParser(prog="agentaxiom")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check"); check.add_argument("transcript"); check.add_argument("contract"); check.add_argument("--evidence-dir", default="agentaxiom-evidence")
    diff = sub.add_parser("compare"); diff.add_argument("baseline"); diff.add_argument("candidate"); diff.add_argument("--policy")
    minimize = sub.add_parser("minimize"); minimize.add_argument("transcript"); minimize.add_argument("contract"); minimize.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "check":
        transcript = Transcript.from_dict(json.loads(Path(args.transcript).read_text()))
        contract = Contract(**json.loads(Path(args.contract).read_text()))
        result = evaluate_contract(transcript, contract)
        write_bundle(args.evidence_dir, transcript, result)
        print(json.dumps({"passed": result.passed, "violations": result.violations}))
        return 0 if result.passed else 1
    if args.command == "compare":
        baseline = Transcript.from_dict(json.loads(Path(args.baseline).read_text()))
        candidate = Transcript.from_dict(json.loads(Path(args.candidate).read_text()))
        policy = ComparisonPolicy(**json.loads(Path(args.policy).read_text())) if args.policy else ComparisonPolicy()
        result = compare(baseline, candidate, policy)
        print(json.dumps({"equivalent": result.equivalent, "regressions": result.regressions}))
        return 0 if result.equivalent else 1
    if args.command == "minimize":
        recorded = Transcript.from_dict(json.loads(Path(args.transcript).read_text()))
        contract = Contract(**json.loads(Path(args.contract).read_text()))
        if evaluate_contract(recorded, contract).passed:
            print(json.dumps({"error": "refusing to minimize a passing transcript"}))
            return 2
        minimized = minimize_conversation(recorded, lambda trace: not evaluate_contract(trace, contract).passed)
        Path(args.output).write_text(json.dumps(minimized.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"turns_before": len(recorded.scenario.turns), "turns_after": len(minimized.scenario.turns), "output": args.output}))
        return 0
    return 2

if __name__ == "__main__": raise SystemExit(main())
