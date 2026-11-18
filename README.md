# honest-backtest-lab

**A ruler, not a prophecy.** This measures whether a backtest is lying to you. It gives no trading signals,
places no orders and touches no account.

Full write-up: https://jiawenzhang2.substack.com/p/my-stock-pickers-ranking-score-was

## Three ways a backtest lies

**Survivorship.** Testing on today's index members means testing on the companies that survived and grew.
Here the universe on each past day is the S&P 500 *as it was that day*, rebuilt from the public record of
additions and removals. Liquidity is judged on that day too.

**Hidden bets.** A raw momentum score mostly says "own whatever sector is hot". Scores are ranked within each
sector, so what is measured is stock selection, not a sector bet.

**Multiple testing.** Try enough ideas and one will look good by luck. Every test is logged, the tests to be
run are written down first (`research/prereg-001-sp500-pit.md`), and the deflated Sharpe ratio discounts each
result for the number of things that were tried.

For each signal it reports the rank correlation between the score and the next N days' return, the return of
each fifth of the ranking, and the top fifth minus the bottom fifth, on non-overlapping periods so the
t-statistics are honest. The pass rule, fixed in advance, needs all four: t >= 3.0 overall, t >= 1.5 and
positive in each half of the sample (2015-2020, 2021-2026), deflated Sharpe >= 0.95, and positive after costs.

## Quick start

```bash
pip install -e ".[data]"          # pandas, numpy, and yfinance for the download step
python -m honestlab build         # needs the internet (Wikipedia + Yahoo); several minutes; caches to .cache/
python -m honestlab coverage      # what is missing from the free data
python -m honestlab test          # the pre-registered signal tests
python -m honestlab test --survivors   # also on today's members only, to see the bias
```

`coverage` and `test` run offline on the cached panel. Tests for the package itself never touch the network:

```bash
pip install -e ".[test]" && python -m pytest -q
```

The code is small: `universe.py` (point-in-time membership and the price panel), `signals.py`, `evaluate.py`,
`deflated.py`, `ledger.py` (every attempt so far, so a repeated test is not counted twice).
`templates/prereg-template.md` is an empty pre-registration to copy.

## What it found (S&P 500, 2015-01-02 to 2026-11-13)

Point-in-time universe, ranked within sector, five groups, buy next open, 10 basis points per round trip,
deflated for 32 trials. None passed. Full tables: `research/results-001-sp500-pit.md`.

| Signal | Hold | Top minus bottom per year (t) | Deflated Sharpe | Verdict |
|---|---:|---:|---:|---|
| 12-1 month momentum | 60d | +1.5% (+0.4) | 0.03 | fail |
| 6-1 month momentum | 60d | +1.5% (+0.4) | 0.03 | fail |
| Residual momentum (beta removed) | 60d | +3.1% (+0.7) | 0.07 | fail |
| 5-day reversal | 5d | +10.3% (+2.3) | 0.49 | fail |
| Low volatility | 20d | -4.1% (-0.9) | 0.00 | fail |
| Near 52-week high | 20d | -2.9% (-0.6) | 0.00 | fail |
| The author's own composite score (not included in this repo) | 10d | -2.2% (-0.5) | 0.00 | fail |

Survivorship, measured: holding today's S&P 500 members equally since 2015 "made" 17.0% a year. Holding the
index as it really was each day made 12.1%. RSP, the real equal-weight fund, made 10.8%.

## Honest limits

- **Free data has holes.** Yahoo deletes the history of companies that stop trading. Of 773 stocks that were
  members since June 2013, 601 have usable prices; 172 are missing entirely, mostly buyouts. 77% of member-days
  had a price in 2015, 99% in 2026.
- **About 1 point a year of flattery is left.** The rebuild removes roughly four fifths of the bias against
  RSP (daily correlation 0.997), not all of it.
- **No clean holdout.** About 25 variants were tried informally on today's stock lists before the
  pre-registration was written. The pre-registration was committed before any test ran on the point-in-time
  data, but the earlier peeking is disclosed in it, and real confirmation can only come from forward data.
- **Price signals only.** Fundamentals, analyst data and earnings are not tested: there is no free
  point-in-time history.
- The rule backtests in the results file come from the author's private trading code and cannot be
  reproduced from this repository.

## Not investment advice

This is research code and an educational exercise. It is not investment advice, and a passing result would
not be a promise of anything.

## License

MIT. See `LICENSE`.
