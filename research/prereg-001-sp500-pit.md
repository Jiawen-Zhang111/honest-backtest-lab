> Published verbatim from the private research repository.

# Pre-registration 001: seven price signals on the point-in-time S&P 500

Written and committed on 2026-11-16, **before** any of these tests was run on the point-in-time data.
The git history is the proof of order: this file's commit comes before the commit that records results.

## Why this exists

Steps 1 and 2 of `research/ALPHA_ROADMAP.md`: get an honest baseline on a universe without survivorship
bias, wider than the 29- and 223-stock lists, with sector bets removed. Rule H24 of the same roadmap:
fix the questions and the pass rule first, then look.

## What has already been seen (so nobody is fooled about how fresh this is)

About 25 rule and signal variants were tried informally between 2026-11-12 and 2026-11-16, all on
**today's** stock lists (29, 223 and 397 stocks), mostly 2021-2026. From those:

- the agent's composite score had a slightly negative rank correlation with returns at 5-60 days;
- 6-month momentum was positive only at about 120 days;
- 5-day reversal and dip buying showed nothing;
- low volatility was negative.

So these hypotheses are not naive, 2021-2026 is not untouched for them, and there is **no pristine
historical holdout**. The real confirmation is forward: anything that passes becomes a shadow signal in
the evening `collect` step and is judged on data that does not exist yet. Nothing here leads to a trade.

The point-in-time universe itself has not been tested: at the time of writing its membership pages had
been downloaded and parsed, no prices for it had been downloaded, and no signal had been evaluated on it.

## Data

- Universe: the S&P 500 as it was on each day, rebuilt from the public change record (Wikipedia,
  "List of S&P 500 companies" and "Historical components of the S&P 500").
- Prices: Yahoo, adjusted. **Known gap:** Yahoo has no prices for most companies that were acquired or
  failed. Coverage is reported with the results. Demoted companies that still trade are included.
- Eligible on a day: a member that day, 252 consecutive daily bars, and 20-day average dollar volume
  of at least $20M measured on that day.
- Fixes applied before testing: a symbol whose prices begin after it left the index is discarded (the
  symbol was reused); history before a one-day jump above +300% is discarded (relisting artefact).

## Method (identical for every signal)

- Sample days: every `h` trading days from 2015-01-02, so holding periods do not overlap.
- Ranking: within GICS sector; sectors with fewer than 10 eligible stocks are pooled.
- Five groups by rank. Buy at the next open, sell at the close `h` sessions after the sample day.
  A stock that stops trading inside the window is sold at its last price.
- Primary number: top group minus bottom group, equal weight, mean per period, with a t-statistic
  across the non-overlapping periods.
- Costs: 10 basis points per round trip, charged on the turnover of both groups.

## The seven tests

| # | Signal (higher score should mean higher return) | Holding period |
|---|---|---|
| 1 | `mom_12_1`: return from 12 months ago to 1 month ago | 60 days |
| 2 | `mom_6_1`: return from 6 months ago to 1 month ago | 60 days |
| 3 | `resid_mom_12_1`: 12-1 momentum of the return left after removing the stock's market beta, scaled by its volatility | 60 days |
| 4 | `reversal_5d`: minus the last 5 days' return | 5 days |
| 5 | `low_vol_60`: minus the 60-day volatility of daily returns | 20 days |
| 6 | `near_52w_high`: price relative to its 52-week high | 20 days |
| 7 | `agent_score`: the agent's own composite score, ranked within the point-in-time universe | 10 days |

Exact definitions are in `swing_agent/lab.py` (`signals`, `evaluate`, `PREREGISTERED`), committed with this file.

## Pass rule (all four required)

1. t-statistic of top-minus-bottom at least **3.0** over 2015-2026.
2. Positive with t at least **1.5** in **each** half: 2015-2020 and 2021-2026.
3. Deflated Sharpe ratio at least **0.95**, deflating for every trial: the 25 informal ones plus every
   test logged by the lab (these seven and the comparison runs below).
4. Still positive after costs.

A signal that fails is recorded as failed. It is not re-tuned and re-tested on this data.

## Secondary analyses (decided now; they count as trials but cannot rescue a failed signal)

- The same seven tests on **today's members only**, to measure how much survivorship bias changes the answer.
- The top group against the average eligible stock, which is what a long-only account can actually capture.
- The agent's two rule sets (swing, and long-hold momentum), unchanged, backtested on the point-in-time
  universe and on today's members, 2015-2026, to see what is left of the "picking edge".

## What will be done with the result

- Pass: add as a shadow signal in `collect`. No trading change without a separate decision by the owner.
- Fail: record it in `INSTRUCTIONS.md`. Stop spending effort on that signal with this data.
- Either way: report the coverage gap and say plainly how much it could matter.
