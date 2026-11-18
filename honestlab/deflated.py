"""The deflated Sharpe ratio: how good a result looks after allowing for how many things were tried."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd


def deflated_sharpe(x: pd.Series, horizon: int, n_trials: int, trial_sharpes: list[float] | None = None) -> float:
    """Probability that the true Sharpe ratio is above zero after allowing for `n_trials` attempts
    (Bailey and Lopez de Prado). With many attempts the best one is expected to look good by luck alone;
    this asks whether the observed Sharpe beats that expected lucky maximum. Above 0.95 is the usual bar."""
    x = x.dropna()
    t = len(x)
    if t < 8 or x.std() == 0 or n_trials < 1:
        return float("nan")
    py = 252 / horizon
    sr = x.mean() / x.std()                                   # per period
    z = (x - x.mean()) / x.std(ddof=0)
    skew, kurt = float((z ** 3).mean()), float((z ** 4).mean())
    var_ann = 1 / (t / py)                                    # variance of an annualised Sharpe estimate under no skill
    if trial_sharpes and len([s for s in trial_sharpes if s == s]) > 2:
        var_ann = max(var_ann, float(np.nanvar(trial_sharpes, ddof=1)))
    nd, g = NormalDist(), 0.5772156649
    n = max(n_trials, 2)
    sr0 = math.sqrt(var_ann) * ((1 - g) * nd.inv_cdf(1 - 1 / n) + g * nd.inv_cdf(1 - 1 / (n * math.e))) / math.sqrt(py)
    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-12))
    return float(nd.cdf((sr - sr0) * math.sqrt(t - 1) / denom))

