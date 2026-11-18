"""Command line: python -m honestlab build | coverage | test [--survivors]

`build` needs the internet (Wikipedia and Yahoo) and the optional `yfinance` package: pip install "honest-backtest-lab[data]".
`coverage` and `test` work offline on the panel that `build` cached.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import evaluate, universe

DEFAULT_CACHE = Path(".cache")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m honestlab", description="A ruler, not a prophecy: measure whether a signal "
                                 "predicts returns on the S&P 500 as it was each day. It never trades and gives no trading signals.")
    ap.add_argument("action", choices=["build", "coverage", "test"],
                    help="build = download membership and prices (needs internet and yfinance, several minutes); "
                         "coverage = what is missing; test = the pre-registered signal tests")
    ap.add_argument("--survivors", action="store_true",
                    help="with `test`: also run today's members only (the survivorship-biased universe), to show the bias")
    ap.add_argument("--cache", default=str(DEFAULT_CACHE), help="folder for the downloaded panel and the local trial log (default: .cache)")
    args = ap.parse_args(argv)
    cache = Path(args.cache)
    if args.action == "build":
        p = universe.build(cache, universe.YahooSource(), sector_lookup=universe.yahoo_sector)
        print(universe.coverage_text(p))
        return 0
    p = universe.load(cache)
    if args.action == "coverage":
        print(universe.coverage_text(p))
    else:
        print(evaluate.results_text(evaluate.run_tests(p, cache), "Pre-registered signals, S&P 500 as it was each day, ranked within sector"))
        if args.survivors:
            print()
            print(evaluate.results_text(evaluate.run_tests(p, cache, survivors_only=True),
                                        "Same tests on today's members only (the survivorship-biased universe, for comparison)"))
    return 0
