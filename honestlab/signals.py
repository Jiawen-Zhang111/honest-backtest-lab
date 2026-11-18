"""Who could have been chosen on each day (`eligible`) and the six price signals under test (`signals`).

Each signal is a score where higher should mean a better stock, and every value uses only that day's
close and earlier.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .universe import Panel

MIN_ADV = 20_000_000


def eligible(p: Panel, survivors_only: bool = False) -> pd.DataFrame:
    """Stocks that could have been chosen on each day: index members that day, a year of price history,
    and enough trading that day's month to pass the liquidity rule. survivors_only=True instead uses
    today's members for every past day (the biased universe, kept only to measure the bias)."""
    c = p.close
    adv = (c * p.volume).rolling(20).mean()
    if survivors_only:
        mem = pd.DataFrame(np.tile(p.member.iloc[-1].to_numpy(), (len(c), 1)), index=c.index, columns=p.member.columns)
    else:
        mem = p.member
    return mem.reindex(columns=c.columns).fillna(False).astype(bool) & (c.notna().rolling(252).sum() >= 252) & (adv >= MIN_ADV)



def signals(p: Panel, elig: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Each signal as a score where higher should mean a better stock. Every value uses only that day's
    close and earlier."""
    c = p.close
    r = c.pct_change(fill_method=None)
    mkt = p.bench["Close"].pct_change(fill_method=None).reindex(c.index)
    beta = r.rolling(252, min_periods=200).cov(mkt).div(mkt.rolling(252, min_periods=200).var(), axis=0)
    resid = r - beta.shift(1).mul(mkt, axis=0)   # what the stock did beyond its usual share of the market's move
    rs = resid.shift(21)
    mom6 = c.shift(21) / c.shift(126) - 1
    return {
        "mom_12_1": c.shift(21) / c.shift(252) - 1,
        "mom_6_1": mom6,
        "resid_mom_12_1": rs.rolling(231, min_periods=200).sum() / (rs.rolling(231, min_periods=200).std() * np.sqrt(231)),
        "reversal_5d": -(c / c.shift(5) - 1),
        "low_vol_60": -r.rolling(60).std(),
        "near_52w_high": c / c.rolling(252).max() - 1,
    }
