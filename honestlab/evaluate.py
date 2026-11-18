"""Measurement: test one signal at one holding period on non-overlapping periods, and apply the
pre-registered pass rule.

What it measures for a signal: the rank correlation between the score and the next N days' return, the
return of each fifth of the ranking, and the top fifth minus the bottom fifth, on non-overlapping
periods so the t-statistics are honest.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .deflated import deflated_sharpe
from .ledger import log_trial, trial_count
from .signals import eligible, signals
from .universe import Panel

# Signal, primary horizon in trading days. Written down in research/prereg-001-sp500-pit.md before any was run.
PREREGISTERED = [("mom_12_1", 60), ("mom_6_1", 60), ("resid_mom_12_1", 60), ("reversal_5d", 5), ("low_vol_60", 20),
                 ("near_52w_high", 20)]
HALVES = (("2015-2020", "2015-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", "2026-12-31"))


def _stats(x: pd.Series, per_year: float) -> dict:
    x = x.dropna()
    n = len(x)
    if n < 3 or x.std() == 0:
        return {"n": n, "mean": float(x.mean()) if n else float("nan"), "t": float("nan"), "sharpe": float("nan")}
    return {"n": n, "mean": float(x.mean()), "t": float(x.mean() / (x.std() / math.sqrt(n))),
            "sharpe": float(x.mean() / x.std() * math.sqrt(per_year))}


def evaluate(score: pd.DataFrame, p: Panel, horizon: int, elig: pd.DataFrame, neutral: bool = True, q: int = 5,
             cost_bps: float = 10.0, start="2015-01-01") -> dict:
    """Test one signal at one holding period on non-overlapping periods.

    On each sample day the eligible stocks are ranked (within sector when neutral=True) and split into
    `q` groups. Each is bought at the next open and sold at the close `horizon` sessions after the sample
    day; a stock that stops trading inside the window is sold at its last price. Reported per period:
    the rank correlation with the forward return, the top group minus the bottom group, and the top group
    minus the average eligible stock (what a long-only account could capture)."""
    cal = p.close.index
    ff = p.close.ffill()
    fwd = ff.shift(-horizon) / p.open.shift(-1) - 1
    can_buy = p.open.shift(-1).notna()
    sec = p.sector.reindex(p.close.columns).fillna("Unknown")
    i0 = int(cal.searchsorted(pd.Timestamp(start)))
    rows, prev = [], {}
    for i in range(i0, len(cal) - horizon, horizon):
        s, f = score.iloc[i], fwd.iloc[i]
        ok = (elig.iloc[i] & s.notna() & can_buy.iloc[i] & f.notna()).to_numpy()
        if ok.sum() < 5 * q:
            continue
        x, y, g = s[ok], f[ok], sec[ok]
        if neutral:
            size = g.map(g.value_counts())
            g = g.where(size >= 2 * q, "Other")       # sectors too small to split are pooled
            rk = x.groupby(g).rank(pct=True)
        else:
            rk = x.rank(pct=True)
        bucket = np.minimum(np.ceil(rk * q), q).astype(int)
        top, bot = set(x.index[bucket == q]), set(x.index[bucket == 1])
        if not top or not bot:      # the score does not separate the stocks that day (all tied): nothing to hold
            continue
        row = {"date": cal[i], "n": int(ok.sum()), "ic": float(rk.rank().corr(y.rank())), "ls": float(y[bucket == q].mean() - y[bucket == 1].mean()),
               "top": float(y[bucket == q].mean() - y.mean()), "bottom": float(y[bucket == 1].mean() - y.mean()),
               "turn_top": 1 - len(top & prev["top"]) / len(top) if prev else 1.0,
               "turn_bot": 1 - len(bot & prev["bot"]) / len(bot) if prev else 1.0}
        for k in range(1, q + 1):
            row[f"q{k}"] = float(y[bucket == k].mean() - y.mean())
        prev = {"top": top, "bot": bot}
        rows.append(row)
    df = pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame()
    if df.empty:
        return {"horizon": horizon, "rows": df, "periods": 0}
    rt = cost_bps / 10_000
    df["ls_net"] = df["ls"] - rt * (df["turn_top"] + df["turn_bot"])
    df["top_net"] = df["top"] - rt * df["turn_top"]
    py = 252 / horizon
    out = {"horizon": horizon, "rows": df, "periods": len(df), "neutral": neutral, "stocks": float(df["n"].mean()),
           "ic": _stats(df["ic"], py), "ls": _stats(df["ls"], py), "ls_net": _stats(df["ls_net"], py),
           "top": _stats(df["top"], py), "top_net": _stats(df["top_net"], py), "bottom": _stats(df["bottom"], py),
           "quantiles": [float(df[f"q{k}"].mean()) * py for k in range(1, q + 1)], "turnover": float(df["turn_top"].iloc[1:].mean()),
           "halves": {name: _stats(df.loc[a:b, "ls"], py) for name, a, b in HALVES},
           "halves_top": {name: _stats(df.loc[a:b, "top"], py) for name, a, b in HALVES}}
    return out

def verdict(res: dict, dsr: float) -> tuple[bool, list[str]]:
    """The pre-registered pass rule. All four must hold."""
    why = []
    if not (res["ls"]["t"] >= 3.0):
        why.append(f"t {res['ls']['t']:+.1f} < 3.0")
    for name, h in res["halves"].items():
        if not (h["mean"] > 0 and h["t"] >= 1.5):
            why.append(f"{name}: t {h['t']:+.1f}")
    if not (dsr >= 0.95):
        why.append(f"deflated Sharpe {dsr:.2f} < 0.95")
    if not (res["ls_net"]["mean"] > 0):
        why.append("negative after costs")
    return (not why), why


def run_tests(p: Panel, cache: Path | None = None, tests=PREREGISTERED, neutral: bool = True, survivors_only: bool = False,
              start="2015-01-01") -> list[dict]:
    elig = eligible(p, survivors_only)
    sig = signals(p, elig)
    universe = "survivors" if survivors_only else "point-in-time"
    out = []
    for name, h in tests:
        res = evaluate(sig[name], p, h, elig, neutral=neutral, start=start)
        res.update(signal=name, universe=universe)
        if cache is not None and res["periods"]:
            log_trial(cache, {"signal": name, "horizon": h, "neutral": neutral, "universe": universe, "periods": res["periods"],
                              "ls_ann": res["ls"]["mean"] * 252 / h, "t": res["ls"]["t"], "sharpe": res["ls"]["sharpe"]})
        out.append(res)
    n = trial_count(cache) if cache is not None else trial_count(None) + len(out)
    sharpes = [r["ls"]["sharpe"] for r in out if r.get("periods")]
    for r in out:
        if r.get("periods"):
            r["trials"] = n
            r["dsr"] = deflated_sharpe(r["rows"]["ls"], r["horizon"], n, sharpes)
            r["passed"], r["why_not"] = verdict(r, r["dsr"])
    return out


def results_text(results: list[dict], title: str) -> str:
    L = [title, "  signal            hold  periods   rank IC (t)    top-bottom/yr (t)   after costs   top vs avg/yr (t)   "
                "2015-20 t  2021-26 t  deflated  verdict"]
    for r in results:
        if not r.get("periods"):
            L.append(f"  {r['signal']:<16} {r['horizon']:>4}d  no data")
            continue
        py = 252 / r["horizon"]
        hv = list(r["halves"].values())
        L.append(f"  {r['signal']:<16} {r['horizon']:>4}d  {r['periods']:>7}  {r['ic']['mean']:>+6.3f} ({r['ic']['t']:>+4.1f})  "
                 f"{r['ls']['mean'] * py:>+9.1%} ({r['ls']['t']:>+4.1f})  {r['ls_net']['mean'] * py:>+11.1%}  "
                 f"{r['top']['mean'] * py:>+9.1%} ({r['top']['t']:>+4.1f})  {hv[0]['t']:>+9.1f}  {hv[1]['t']:>+9.1f}  "
                 f"{r['dsr']:>8.2f}  " + ("PASS" if r["passed"] else "fail: " + "; ".join(r["why_not"])))
    if results and results[0].get("periods"):
        L.append(f"  Deflated for {results[0]['trials']} trials. Pass needs t >= 3.0 overall, t >= 1.5 in each half, "
                 "deflated Sharpe >= 0.95 and a positive result after costs.")
    return "\n".join(L)

