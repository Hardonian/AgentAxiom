from __future__ import annotations

import argparse, json
from pathlib import Path

from .contracts import Contract, evaluate_contract
from .evidence import write_bundle
from .models import Transcript

def main() -> int:
    parser = argparse.ArgumentParser(prog="agentaxiom")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check"); check.add_argument("transcript"); check.add_argument("contract"); check.add_argument("--evidence-dir", default="agentaxiom-evidence")
    args = parser.parse_args()
    if args.command == "check":
        transcript = Transcript.from_dict(json.loads(Path(args.transcript).read_text()))
        contract = Contract(**json.loads(Path(args.contract).read_text()))
        result = evaluate_contract(transcript, contract)
        write_bundle(args.evidence_dir, transcript, result)
        print(json.dumps({"passed": result.passed, "violations": result.violations}))
        return 0 if result.passed else 1
    return 2

if __name__ == "__main__": raise SystemExit(main())
