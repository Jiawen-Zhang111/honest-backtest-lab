> Published copy from the private research repository. Edits: internal account names replaced with neutral wording; the reproduce section rewritten for this repository. No number has been changed.

# Results 001: the honest baseline (roadmap steps 1 and 2)

Run on 2026-11-16, once, exactly as written in `research/prereg-001-sp500-pit.md` (committed before any
result existed). Nothing was re-tuned afterwards. Period tested: 2015-01-02 to 2026-11-13.

## The short version

1. **None of the seven signals passed.** The agent's own score has no ability to rank stocks on an honest
   universe (the top fifth did 2.2% a year *worse* than the bottom fifth; that is noise, not a real negative).
2. **Survivorship bias was large and is now measured.** Holding today's S&P 500 members equally since 2015
   "made" 17.0% a year. Holding the index as it really was each day made 12.1%. The real equal-weight
   S&P 500 fund (RSP) made 10.8%. Every earlier backtest in this project used today's lists.
3. **The one earlier "win" shrinks.** Long-hold momentum (the rules a paper account has run since 2026-11-13) looks
   like skill on today's members (+9.8% a year over a no-skill portfolio, t = 2.2) and like nothing
   special on the honest universe (+3.8% a year, t = 1.0), where it made 8.5% a year against 12.1% for
   simply holding everything, with a 35% drawdown.
4. **Free data fixes most of the bias, not all.** About 1 point a year of flattery is left (see Coverage).

## Coverage: what "point-in-time" means here and what is still missing

The S&P 500 was rebuilt day by day from the public change record (Wikipedia: "List of S&P 500 companies"
and "Historical components of the S&P 500"). Prices are Yahoo, adjusted.

| | |
|---|---:|
| Stocks that were members at some point since June 2013 | 773 |
| With usable prices | 601 |
| Left the index | 270 (dropped 140, acquired 127, failed 3) |
| ... of those, with prices | 98 |
| Missing entirely | 172 (acquired 121, dropped 48, failed 3) |
| Members on any one day | 503 to 510 |
| Eligible to be picked on an average day (member, one year of history, $20M a day traded) | 386 in 2015, 451 in 2020, 497 in 2026 |

Share of member-days that have a price: 2015 77%, 2016 81%, 2017 84%, 2018 86%, 2019 88%, 2020 90%,
2021 92%, 2022 94%, 2023 96%, 2024 96%, 2025 98%, 2026 99%.

Yahoo deletes a company's whole history when it stops trading. At least six companies that left in 2026
(among them EA, KVUE, WBD and QRVO) already have nothing but one stray bar. So the hole grows every time a
member is bought or fails, and free data cannot close it.

**Outside check.** The rebuilt index, held equally, returned 12.1% a year. RSP, the real fund that does
exactly that (after a 0.20% fee), returned 10.8%. Daily correlation 0.997. Year by year the rebuild is
0.7 to 2.2 points ahead in every year except 2026. Today's members held equally are 1.3 to 11.0 points
ahead of RSP every year. So the rebuild removes about four fifths of the bias in the benchmark and
leaves roughly 1 point a year. Read every number below with that in mind.

## The seven pre-registered tests

S&P 500 as it was each day, ranked within sector, five groups, buy next open, non-overlapping holding
periods, 10 basis points per round trip. "Top minus bottom" is the yearly return of the best fifth minus
the worst fifth. Pass needs all four: t at least 3.0, t at least 1.5 in each half, deflated Sharpe at
least 0.95, positive after costs. Deflated for 32 trials (25 informal ones before the lab, plus these seven).

| Signal | Hold | Periods | Rank IC (t) | Top minus bottom per year (t) | After costs | Top vs average per year (t) | 2015-20 t | 2021-26 t | Deflated Sharpe | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 12-1 month momentum | 60d | 49 | +0.006 (+0.2) | +1.5% (+0.4) | +1.2% | +1.2% (+0.6) | -0.6 | +1.2 | 0.03 | **fail** |
| 6-1 month momentum | 60d | 49 | +0.005 (+0.3) | +1.5% (+0.4) | +1.0% | +1.6% (+0.8) | +0.6 | +0.1 | 0.03 | **fail** |
| Residual momentum (beta removed) | 60d | 48 | +0.014 (+0.6) | +3.1% (+0.7) | +2.7% | +1.4% (+0.7) | -0.4 | +1.5 | 0.07 | **fail** |
| 5-day reversal | 5d | 597 | +0.014 (+2.5) | +10.3% (+2.3) | +2.4% | +5.0% (+2.0) | +2.0 | +1.1 | 0.49 | **fail** |
| Low volatility | 20d | 149 | +0.000 (+0.0) | -4.1% (-0.9) | -4.8% | -1.7% (-0.9) | -0.5 | -0.8 | 0.00 | **fail** |
| Near 52-week high | 20d | 149 | +0.004 (+0.3) | -2.9% (-0.6) | -3.8% | -0.8% (-0.4) | -0.4 | -0.6 | 0.00 | **fail** |
| **The agent's own score** | 10d | 298 | +0.004 (+0.4) | -2.2% (-0.5) | -3.7% | -0.5% (-0.2) | -0.4 | -0.3 | 0.00 | **fail** |

Reading it:

- **The agent's score** is what the rules analyst ranks on and what Claude is shown. Rank IC +0.004 is
  zero for practical purposes. This agrees with the earlier tests on the 29- and 223-stock lists.
- **Momentum**, in all three forms, shows nothing at a 60-day hold in large caps over this period.
- **Five-day reversal** came closest: +10.3% a year before costs. It trades every week, so costs take
  about 8 of those points, it was weaker in 2021-2026 (t = 1.1), and after allowing for the number of
  things tried it is a coin flip (0.49). It failed the rule set in advance and is recorded as failed.
- **Low volatility and near-the-high** point the wrong way.

## Secondary analysis 1: the same tests on today's members only

Declared in advance, to measure the bias. Deflated for 39 trials.

| Signal | Top minus bottom per year (t), honest | ... today's members | Top vs average per year (t), honest | ... today's members |
|---|---:|---:|---:|---:|
| 12-1 month momentum | +1.5% (+0.4) | +2.1% (+0.5) | +1.2% (+0.6) | **+3.6% (+1.8)** |
| 6-1 month momentum | +1.5% (+0.4) | +2.3% (+0.6) | +1.6% (+0.8) | **+3.6% (+1.8)** |
| Residual momentum | +3.1% (+0.7) | +2.9% (+0.7) | +1.4% (+0.7) | +1.8% (+0.9) |
| 5-day reversal | +10.3% (+2.3) | +10.7% (+2.3) | +5.0% (+2.0) | +6.4% (+2.4) |
| Low volatility | -4.1% (-0.9) | **-12.8% (-2.8)** | -1.7% (-0.9) | -4.4% (-2.3) |
| Near 52-week high | -2.9% (-0.6) | -7.8% (-1.8) | -0.8% (-0.4) | -1.9% (-1.0) |
| The agent's own score | -2.2% (-0.5) | -3.9% (-0.9) | -0.5% (-0.2) | -1.0% (-0.5) |

On today's members a buyer of the top momentum fifth appears to beat the average stock by 3.6% a year
(t = 1.8). On the honest universe it is 1.2% (t = 0.6). Low volatility looks strongly "wrong" on today's
members (-12.8%, t = -2.8) only because a list of survivors is full of volatile stocks that happened to win.
Both are artefacts of choosing the list with hindsight.

## Secondary analysis 2: the agent's rules, unchanged, on both universes

Rules layer only (no Claude: it would know the future), live exit rules, $10,000, 10 bps costs. "No-skill
portfolio" is the universe held equally at the strategy's own day-by-day exposure, so the gap to it is
stock selection and timing. The t-statistic is on the daily gap.

| Rules | Universe | Strategy per year | Max drawdown | Equal weight per year | No-skill portfolio per year | Edge per year (t) | Avg invested |
|---|---|---:|---:|---:|---:|---:|---:|
| Swing (main config as it is) | honest | +1.7% | -17% | +12.1% | +2.2% | -0.4% (-0.3) | 37% |
| | today's members | +3.0% | -16% | +17.0% | +4.0% | -0.9% (-0.6) | 37% |
| Swing, kill switch able to clear (126-day peak) | honest | +6.6% | -21% | +12.1% | +8.4% | -1.6% (-0.6) | 79% |
| | today's members | +8.7% | -21% | +17.0% | +12.2% | -3.2% (-1.3) | 79% |
| Long-hold momentum (paper account config) | honest | +8.5% | -35% | +12.1% | +5.3% | +3.8% (+1.0) | 69% |
| | today's members | +17.2% | -31% | +17.0% | +7.7% | **+9.8% (+2.2)** | 69% |

SPY over the same period: +13.5% a year, max drawdown -34%.

Reading it:

- **Swing rules: no picking edge**, slightly below a no-skill portfolio either way, within noise.
- **The main config froze.** Its 15% kill switch is measured from the all-time peak. In the simulation it
  tripped on 2020-03-09, the account was flat by 2020-03-19 and never bought again: 1,674 of 2,985 days
  in cash. That is the deadlock already listed in INSTRUCTIONS.md section 10, now seen over a long
  history. With the switch able to clear, the account stayed 79% invested and made 6.6% a year.
- **Long-hold momentum:** on today's members it looks like a real edge (t = 2.2) and matches the
  benchmark's return with a better drawdown. On the honest universe the edge is t = 1.0, the return is
  3.6 points a year below simply holding everything, and the drawdown is as deep as the market's.
  The decision of 2026-11-13 to run it on a paper account was based on today's-members lists. It is a paper
  account and a fair forward test, so this is not a reason to change it again, only to expect less from it.

## What this does and does not show

- It shows that with **price-only signals on large US stocks**, at the bar set in advance, there is no
  stock-picking edge here to find, and that the agent's score in particular carries no information.
- It does **not** show that the agent loses money. Its rules are roughly a no-skill portfolio with
  risk controls: lower drawdown, lower return.
- It does not test Claude (cannot be backtested fairly), fundamentals, analyst data or earnings (no
  free point-in-time history; the evening `collect` step is building the analyst history forward).
- About 1 point a year of survivorship flattery remains, and 23% of member-days in 2015 have no price.
  Missing companies are mostly buyouts (which tend to help holders) plus 51 that were dropped or failed
  and then vanished (which tend to hurt). The net effect on a long-short test is unknown but small
  next to the size of the failures above: no t-statistic is near the bar.

## Count of attempts

45 so far: 25 informal ones before the lab, 14 signal tests here (seven, on two universes) and 6 rule
backtests (three rule sets, on two universes). They are listed in `research/trial-ledger.jsonl`, which the
lab reads, so every future test is deflated for all of them. A new idea needs a new pre-registration file.

## Closing the data gap (prices checked on 2026-11-16; check again before buying)

| Source | Cost | Delisted stocks | Index membership history | Note |
|---|---|---|---|---|
| Norgate Data, US Stocks Platinum | US$630 a year, or $346.50 for 6 months | yes | yes | Its updater runs on Windows only; on a Mac it needs a Windows virtual machine |
| EODHD, its end-of-day plan | $19.99 a month | yes, per its FAQ | separate add-on, $29.99 a month | Web API, works from a Mac. Not needed for membership: the Wikipedia rebuild already matches RSP closely |
| Tiingo | about $30 a month (third-party figure) | not verified | no | |

Sources: norgatedata.com/stockmarketpackages.php, norgatedata.com/ndu-faq.php, eodhd.com/pricing,
eodhd.com/financial-academy/financial-faq/historical-stock-prices-for-delisted-companies,
businessquant.com/resources/eod-stock-data-apis.

Buying data is the owner's decision. Nothing in these results suggests it would turn a failure into a
pass. Its value would be to confirm a candidate that passes on the free rebuild first, and to go wider
than 500 stocks, where Yahoo's hole is much bigger.

## How to reproduce (on a computer that can reach Yahoo and Wikipedia)

From the root of this repository (`pip install -e ".[data]"` first):

```bash
python -m honestlab build              # several minutes: membership, prices, sectors
python -m honestlab coverage
python -m honestlab test --survivors
```

This reproduces the coverage numbers and the seven signal tests on both universes, except the author's own
composite score, which is not part of this repository. The rule backtests in Secondary analysis 2 (and the
trial-ledger rows for them) come from the author's private trading code and are not reproducible here; they
are kept as published.

Numbers will drift a little: Yahoo revises adjusted prices, drops delisted companies, and each run adds days.
