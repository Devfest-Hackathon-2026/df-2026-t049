import argparse
import json
from pathlib import Path

from .bots import BOTS, validate_config
from .server import run_match, compare_matches
from .scoring import score_record


def main():
    parser = argparse.ArgumentParser(description="SIMULATED DATA: deterministic logistics competition")
    parser.add_argument("--scenario", choices=("fixture", "events"), default="fixture")
    parser.add_argument("--seed", type=int, help="Event scenario seed; default 11")
    parser.add_argument("--bot", choices=(*BOTS, "custom"), default="nearest")
    parser.add_argument("--config", type=Path, help="Three-rule JSON config; requires --bot custom or --compare")
    parser.add_argument("--compare", action="store_true", help="Compare both Bots across public seeds 11, 22, 33")
    parser.add_argument("--rescore", type=Path, help="Recalculate scores from a saved JSON match")
    parser.add_argument("--output", type=Path, help="Write JSON match or comparison report")
    args = parser.parse_args()
    config = None
    if args.config:
        if args.rescore or (not args.compare and args.bot != "custom"):
            parser.error("--config requires --bot custom or --compare")
        try:
            config = validate_config(json.loads(args.config.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            parser.error(f"Cannot read strategy config: {exc}")
    if args.bot == "custom" and config is None:
        parser.error("--bot custom requires --config")
    if args.rescore and (args.compare or args.seed is not None):
        parser.error("--rescore cannot be combined with --compare or --seed")
    if args.compare and args.seed is not None:
        parser.error("--compare uses the fixed public seed set; omit --seed")
    if args.seed is not None and args.scenario != "events":
        parser.error("--seed requires --scenario events")
    if args.rescore:
        try:
            result = score_record(json.loads(args.rescore.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            parser.error(f"Cannot rescore record: {exc}")
        print(json.dumps(result, sort_keys=True))
    elif args.compare:
        result = compare_matches(config)
        rows, ranking = result["matches"], result["ranking"]
        print("SIMULATED DATA | public seed comparison")
        for row in rows:
            print(f"seed={row['seed']} bot={row['bot']} score={row['score']['total']:.6f} "
                  f"metrics={row['score']['metrics']}")
        print(json.dumps(ranking, sort_keys=True))
    else:
        params = {"scenario": [args.scenario], "bot": [args.bot],
                  "seed": [str(args.seed if args.seed is not None else 11 if args.scenario == "events" else 0)]}
        if config:
            params.update({key: [value] for key, value in config.items()})
        try:
            result = run_match(params)
        except ValueError as exc:
            parser.error(str(exc))
        print(f"SIMULATED DATA | {result['scenario_version']} | seed {result['seed']} | {args.bot}")
        for row in result["log"]:
            accepted = sum(a["accepted"] for a in row["actions"])
            delivered = sum(d["quantity"] for d in row["deliveries"])
            print(f"turn={row['turn']:02d} dispatches={accepted} delivered={delivered} "
                  f"stock={row['state']['depot']['stock']} events={len(row['events'])}")
        print(json.dumps({"summary": result["summary"], "score": result["score"]}, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
