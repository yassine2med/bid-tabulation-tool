"""Command line for the bid tabulation tool."""
from __future__ import annotations

import argparse
import json
import sys

from .tabulate import FILL_MODES, read_bids, render, tabulate


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(prog="bidtab", description=__doc__)
    parser.add_argument("csv", help="bids CSV with bidder, item, amount columns")
    parser.add_argument("--fill", choices=FILL_MODES, default="median",
                        help="how to price scope a bidder left out (default median)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit code."""
    args = build_parser().parse_args(argv)
    try:
        results = tabulate(read_bids(args.csv), args.fill)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([{"bidder": r.bidder, "total": r.total, "missing": r.missing,
                           "adjusted": r.adjusted} for r in results], indent=2))
    else:
        print(render(results))
    return 0
