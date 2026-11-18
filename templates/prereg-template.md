# Pre-registration NNN: <what you will test, in one line>

Written and committed on <date>, **before** any of these tests was run on the data. The git history is the
proof of order: this file's commit must come before the commit that records results.

## Why this exists

One or two sentences: the question, and why you are fixing the questions and the pass rule before looking.

## What has already been seen

Be complete. List every informal try, quick plot or earlier backtest that touched this data or these ideas, roughly how
many variants, which periods, and what they showed. If there is no clean holdout sample, say so in plain words.

## Data

Universe, price source, known gaps, eligibility rule on a given day, and any cleaning applied before testing.

## Method (identical for every signal)

Sample days, ranking (and what is ranked within), number of groups, entry and exit timing, how stocks that stop
trading are handled, the primary number, and the cost assumption.

## The tests

| # | Signal (higher score should mean higher return) | Holding period |
|---|---|---|
| 1 | `name`: definition in one line | N days |

Point to the code that defines each signal exactly, committed with this file.

## Pass rule (all required)

Write the thresholds as numbers: t-statistic overall, t-statistic in each half of the sample, deflated Sharpe
ratio (counting every trial, informal ones included), and sign after costs. State that a failure is recorded
as a failure and is not re-tuned and re-tested on the same data.

## Secondary analyses

What else you will run, decided now. Say that they count as trials and cannot rescue a failed primary test.

## What will be done with the result

Pass: what happens next (for example, forward testing on data that does not exist yet). Fail: where it is
recorded and what you stop doing. Either way: how you will report the data gaps and how much they could matter.
