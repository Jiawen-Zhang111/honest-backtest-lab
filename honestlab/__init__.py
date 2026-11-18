"""honestlab: a ruler, not a prophecy. It measures whether a backtest is lying to you; it gives no trading signals."""
from .deflated import deflated_sharpe
from . import deflated, evaluate, signals   # submodules; `honestlab.evaluate.evaluate` and `honestlab.signals.signals` are the functions
from .evaluate import HALVES, PREREGISTERED, results_text, run_tests, verdict
from .ledger import LEDGER, PRIOR_TRIALS, log_trial, trial_count
from .signals import MIN_ADV, eligible
from .universe import (Panel, YahooSource, assemble, build, coverage_text, load, membership, parse_changes,
                       parse_current, yahoo_sector)

__all__ = ["HALVES", "LEDGER", "MIN_ADV", "PREREGISTERED", "PRIOR_TRIALS", "Panel", "YahooSource", "assemble", "build",
           "coverage_text", "deflated", "deflated_sharpe", "eligible", "evaluate", "load", "log_trial", "membership", "parse_changes",
           "parse_current", "results_text", "run_tests", "signals", "trial_count", "verdict", "yahoo_sector"]
__version__ = "0.1.0"
