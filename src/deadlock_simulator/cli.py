from __future__ import annotations

import argparse
import sys

from .logging_config import configure_logging
from .scenarios import SCENARIOS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deadlock-sim",
        description="Deadlock Simulator & DFS Detector (AOS Theme 6)",
    )
    parser.add_argument(
        "--scenario",
        default="deadlock",
        help=f"Scenario to run: {', '.join(SCENARIOS.keys())}",
    )
    parser.add_argument("--timeout", type=float, default=8.0, help="Resource wait timeout in seconds (> 0)")
    parser.add_argument("--check-interval", type=float, default=0.25, help="Detector interval in seconds (> 0)")
    parser.add_argument("--log-file", default="logs/simulation.log", help="Output log file path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logger = configure_logging(args.log_file)

    if args.scenario not in SCENARIOS:
        logger.error(
            f"Task: CLI | Invalid scenario '{args.scenario}'. Valid: {list(SCENARIOS.keys())} | Code: 2"
        )
        return 2

    if args.timeout <= 0 or args.check_interval <= 0:
        logger.error("Task: CLI | --timeout and --check-interval must be strictly positive | Code: 2")
        return 2

    scenario_fn = SCENARIOS[args.scenario]
    code, results = scenario_fn(timeout=args.timeout, check_interval=args.check_interval)
    logger.info(f"Task: System | Scenario '{args.scenario}' finished | Results={results} | Code: {code}")
    return code


if __name__ == "__main__":
    sys.exit(main())