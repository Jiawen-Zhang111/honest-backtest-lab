"""Offline fixtures: a made-up market and made-up Wikipedia pages. Nothing here touches the network."""
import numpy as np
import pandas as pd
import pytest

import honestlab
from honestlab import ledger

CURRENT = """<table class="wikitable" id="constituents"><tr><th>Symbol</th><th>Security</th><th>GICS Sector</th><th>Sub</th><th>HQ</th>
<th>Date added</th><th>CIK</th><th>Founded</th></tr>
<tr><td><a href="x">AAA</a></td><td>Alpha</td><td>Energy</td><td>Oil</td><td>X</td><td>1990-01-02</td><td>1</td><td>1900</td></tr>
<tr><td>BRK.B</td><td>Berk</td><td>Financials</td><td>Ins</td><td>X</td><td>2010-02-16</td><td>2</td><td>1900</td></tr>
<tr><td>NEW</td><td>Newco</td><td>Energy</td><td>Oil</td><td>X</td><td>2026-03-02</td><td>3</td><td>2000</td></tr>
<tr><td>RET</td><td>Returner</td><td>Health Care</td><td>Bio</td><td>X</td><td>2024-01-05</td><td>4</td><td>1990</td></tr></table>"""
CHANGES = """<table class="wikitable sortable" id="changes"><tr><th rowspan="2">Effective Date</th><th colspan="2">Added</th>
<th colspan="2">Removed</th><th rowspan="2">Reason</th></tr><tr><th>Ticker</th><th>Security</th><th>Ticker</th><th>Security</th></tr>
<tr><td rowspan="2">March 2, 2026</td><td>NEW</td><td>Newco</td><td>OLD</td><td>Oldco</td><td>Market capitalization change.<sup>[1]</sup></td></tr>
<tr><td></td><td></td><td>GONE</td><td>Goneco</td><td>Acquired by Alpha.</td></tr>
<tr><td>June 1, 2025</td><td>OLD</td><td>Oldco</td><td>BUST</td><td>Bustco</td><td>Filed for bankruptcy.</td></tr>
<tr><td>January 5, 2024</td><td>RET</td><td>Returner</td><td></td><td></td><td>Re-added.</td></tr>
<tr><td>March 1, 2023</td><td></td><td></td><td>RET</td><td>Returner</td><td>Market capitalization change.</td></tr></table>"""


def make_bars(close, start="2021-01-04"):
    idx = pd.bdate_range(start, periods=len(close))
    c = pd.Series(close, index=idx, dtype=float)
    return pd.DataFrame({"Open": c.shift(1).fillna(c.iloc[0]), "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": 5e6}, index=idx)


def make_panel(n_stocks=60, n_days=900, seed=0):
    """A made-up market where `good` predicts the next 20 days and `noise` predicts nothing."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2014-01-02", periods=n_days)
    names = [f"S{k:02d}" for k in range(n_stocks)]
    sector = pd.Series([["Energy", "Financials", "Health Care"][k % 3] for k in range(n_stocks)], index=names)
    edge = np.repeat(rng.normal(0, 0.0015, (n_days // 20 + 1, n_stocks)), 20, axis=0)[:n_days]     # a persistent per-stock drift
    sector_wave = np.repeat(rng.normal(0, 0.004, (n_days // 20 + 1, 3)), 20, axis=0)[:n_days][:, [k % 3 for k in range(n_stocks)]]
    r = edge + sector_wave + rng.normal(0, 0.01, (n_days, n_stocks))
    close = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx, columns=names)
    openp = close.shift(1).fillna(100.0)
    vol = pd.DataFrame(5e6, index=idx, columns=names)
    bench = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100 * np.exp(np.cumsum(r.mean(axis=1))), "Volume": 1e8}, index=idx)
    p = honestlab.Panel(openp, close * 1.01, close * 0.99, close, vol, pd.DataFrame(True, index=idx, columns=names), sector, bench, {"bench": "SPY"})
    scores = {"good": pd.DataFrame(edge, index=idx, columns=names).shift(-1),            # knows the coming period's drift
              "noise": pd.DataFrame(rng.normal(size=(n_days, n_stocks)), index=idx, columns=names),
              # knows only which sector will lead; within a sector the order is random
              "sector_bet": (pd.DataFrame(sector_wave, index=idx, columns=names).shift(-1)
                             + rng.normal(0, 1e-6, (n_days, n_stocks)))}
    return p, scores


@pytest.fixture
def panel():
    return make_panel()


@pytest.fixture
def clean_ledger(tmp_path, monkeypatch):
    """Count attempts from a clean slate instead of the recorded ledger."""
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "no-ledger.jsonl")
    return tmp_path
