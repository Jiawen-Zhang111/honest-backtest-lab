"""The trial ledger: every test already run, so the count of attempts survives a new computer or a deleted
data folder. New attempts are added when their results are recorded."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

PRIOR_TRIALS = 25   # rule and signal variants tried informally before the lab existed (decisions log, 2026-11-12 to 11-16)
# Every test already run on real data, kept in the repository (path relative to this package).
LEDGER = Path(__file__).resolve().parent.parent / "research" / "trial-ledger.jsonl"


def log_trial(cache: Path, entry: dict) -> None:
    with open(Path(cache) / "trials.jsonl", "a") as f:
        f.write(json.dumps({"when": datetime.now().isoformat(timespec="seconds"), **entry}) + "\n")


def trial_count(cache: Path | None) -> int:
    """How many different things have been tried so far: the informal ones before the lab existed, the
    recorded ledger, and anything run on this computer since. Running the same test again is not a new attempt."""
    seen = set()
    for f in ([LEDGER] + ([Path(cache) / "trials.jsonl"] if cache is not None else [])):
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            try:
                e = json.loads(line)
                seen.add((e.get("signal"), e.get("horizon"), e.get("neutral"), e.get("universe")))
            except ValueError:
                continue
    return PRIOR_TRIALS + len(seen)

