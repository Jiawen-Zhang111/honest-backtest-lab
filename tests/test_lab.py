"""The lab exists to stop a backtest lying. These tests pin the three protections: a point-in-time
universe, no use of future data, and statistics that discount for luck."""
import json

import numpy as np
import pandas as pd
import pytest

import honestlab
from honestlab import deflated_sharpe, eligible, ledger, universe, verdict
from honestlab import evaluate as ev
from honestlab import signals as sg

from conftest import CHANGES, CURRENT, make_bars, make_panel


def test_membership_is_rebuilt_as_it_was_each_day():
    cur, chg = universe.parse_current(CURRENT), universe.parse_changes(CHANGES)
    assert list(cur["ticker"]) == ["AAA", "BRK-B", "NEW", "RET"] and cur["sector"][0] == "Energy"
    assert len(chg) == 5 and list(chg["date"].dt.strftime("%Y-%m-%d"))[:2] == ["2026-03-02", "2026-03-02"]   # the date cell spans two rows
    assert chg.iloc[1]["removed"] == "GONE" and chg.iloc[1]["added"] == "" and "[1]" not in chg.iloc[0]["reason"]
    cal = pd.bdate_range("2022-12-01", "2026-06-30")
    m = universe.membership(list(cur["ticker"]), chg, cal)
    on = lambda t, d: bool(m.at[pd.Timestamp(d), t])
    assert on("AAA", "2022-12-01") and on("AAA", "2026-06-30")
    assert not on("NEW", "2026-02-27") and on("NEW", "2026-03-02")                           # joins on its date, not before
    assert on("GONE", "2026-02-27") and not on("GONE", "2026-03-02")                         # bought out: gone from that day
    assert not on("OLD", "2025-05-30") and on("OLD", "2025-06-02") and not on("OLD", "2026-03-02")   # in, then demoted
    assert on("BUST", "2025-05-30") and not on("BUST", "2025-06-02")
    assert on("RET", "2023-02-28") and not on("RET", "2023-06-01") and on("RET", "2024-01-05")       # left and came back
    assert not on("RET", "2024-01-04") and on("RET", "2026-06-30")


def test_symbols_are_read_cleanly_even_from_untidy_cells():
    assert [universe._sym(x) for x in ("aapl", " BRK.B ", "BF.B", "GOOGL")] == ["AAPL", "BRK-B", "BF-B", "GOOGL"]
    assert universe._sym("""HTTPS://WWW-NYSE-COM/QUOTE/XASE:TMP</A>"}]]}'>TMP""") == "TMP"     # a cell whose markup did not strip cleanly
    assert universe._sym("") == ""


def test_assemble_keeps_losers_and_rejects_bad_data():
    cur, chg = universe.parse_current(CURRENT), universe.parse_changes(CHANGES)
    n = len(pd.bdate_range("2021-01-04", "2026-06-30"))
    flat = make_bars(np.full(n, 100.0))
    reused = make_bars(np.full(60, 20.0), start="2026-04-01")                  # "GONE" now belongs to a different company
    relisted = flat.copy()
    relisted.loc["2023-06-01":, ["Open", "High", "Low", "Close"]] *= 50      # a 4,900% one-day jump: not a real return
    px = {"AAA": flat, "BRK-B": flat, "NEW": flat, "OLD": flat * 0.5, "GONE": reused, "RET": relisted}
    p = universe.assemble(cur, chg, px, flat, "2021-06-01", sector_lookup=lambda t: "Technology")
    assert "OLD" in p.close.columns and "GONE" not in p.close.columns and "BUST" not in p.close.columns
    assert p.close["RET"].first_valid_index() == pd.Timestamp("2023-06-01")
    assert p.sector["OLD"] == "Information Technology" and p.sector["AAA"] == "Energy"
    m = p.meta
    assert m["with_prices"] == 5 and set(m["missing"]) == {"GONE", "BUST"} and m["missing_by_reason"] == {"acquired": 1, "failed": 1}
    assert m["left_the_index"] == 3 and m["left_with_prices"] == 1 and len(m["notes"]) == 2 and p.sector["RET"] == "Health Care"
    text = universe.coverage_text(p)
    assert "Missing entirely: 2" in text and "acquired 1" in text


def test_a_real_signal_passes_and_noise_does_not(panel):
    p, sc = panel
    elig = eligible(p)
    assert not elig.iloc[:251].any().any() and elig.iloc[300].all()                        # a year of history is required first
    good = ev.evaluate(sc["good"], p, 20, elig, start="2015-01-01")
    noise = ev.evaluate(sc["noise"], p, 20, elig, start="2015-01-01")
    assert good["ic"]["mean"] > 0.1 and good["ls"]["t"] > 5 and good["top"]["mean"] > 0 > good["bottom"]["mean"]
    assert good["quantiles"] == sorted(good["quantiles"])                                   # returns rise group by group
    assert abs(noise["ls"]["t"]) < 3 and abs(noise["ic"]["mean"]) < 0.05
    assert good["rows"].index.to_series().diff().dt.days.min() >= 26                       # periods do not overlap
    d_good = deflated_sharpe(good["rows"]["ls"], 20, 32)
    d_noise = deflated_sharpe(noise["rows"]["ls"], 20, 32)
    assert d_good > 0.99 and d_noise < 0.9
    assert verdict(noise, d_noise)[0] is False


def test_more_attempts_means_a_higher_bar(panel):
    p, sc = panel
    elig = eligible(p)
    good = ev.evaluate(sc["good"], p, 20, elig, start="2015-01-01")
    noise = ev.evaluate(sc["noise"], p, 20, elig, start="2015-01-01")
    s = good["rows"]["ls"].iloc[:12] * 0.2 + noise["rows"]["ls"].iloc[:12]
    assert deflated_sharpe(s, 20, 2) > deflated_sharpe(s, 20, 20) > deflated_sharpe(s, 20, 200)
    assert np.isnan(deflated_sharpe(s.iloc[:5], 20, 10))        # too short to say anything


def test_sector_ranking_removes_a_pure_sector_bet(panel):
    p, sc = panel
    elig = eligible(p)
    raw = ev.evaluate(sc["sector_bet"], p, 20, elig, neutral=False, start="2015-01-01")
    neutral = ev.evaluate(sc["sector_bet"], p, 20, elig, neutral=True, start="2015-01-01")
    assert raw["ls"]["t"] > 5                                                               # looks like a great signal
    assert abs(neutral["ls"]["t"]) < 3 and abs(neutral["ls"]["mean"]) < raw["ls"]["mean"] / 4   # it was only a sector call


def test_returns_use_the_next_open_and_delisted_stocks_are_not_dropped():
    p, _ = make_panel(n_stocks=30, n_days=400)
    elig = eligible(p)
    i = 300
    day = p.close.index[i]
    p.open.iloc[i + 1] = p.close.iloc[i] * 2            # every stock gaps up 100% overnight: the signal day's buyer misses it
    p.close.iloc[i + 21:, 0] = np.nan                    # one stock stops trading during the window
    p.open.iloc[i + 21:, 0] = np.nan
    score = pd.DataFrame(0.0, index=p.close.index, columns=p.close.columns)
    score.iloc[i] = np.arange(30)
    res = ev.evaluate(score, p, 40, elig, neutral=False, start=str(day.date()))
    row = res["rows"].loc[day]
    assert row["n"] == 30                                 # the stock that later delisted is still counted
    f = p.close.ffill().iloc[i + 40] / p.open.iloc[i + 1] - 1
    assert f.max() < 0.5                                  # nobody gets the overnight jump
    assert f.iloc[0] == pytest.approx(p.close.iloc[i + 20, 0] / p.open.iloc[i + 1, 0] - 1)   # sold at its last price
    assert row["ls"] == pytest.approx(f.iloc[24:].mean() - f.iloc[:6].mean())


def test_signals_never_look_ahead():
    p, _ = make_panel(n_stocks=30, n_days=600)
    before = sg.signals(p, eligible(p))
    q = honestlab.Panel(p.open.copy(), p.high.copy(), p.low.copy(), p.close.copy(), p.volume.copy(), p.member, p.sector, p.bench.copy(), p.meta)
    cut = 500
    q.close.iloc[cut + 1:] *= 3                           # change the future
    q.open.iloc[cut + 1:] *= 3
    q.bench.iloc[cut + 1:, q.bench.columns.get_loc("Close")] *= 3
    after = sg.signals(q, eligible(q))
    assert set(before) == {name for name, _ in honestlab.PREREGISTERED} and len(before) == 6
    for name in before:
        a, b = before[name].iloc[: cut + 1], after[name].iloc[: cut + 1]
        assert a.notna().sum().sum() > 0 and np.allclose(a.fillna(0), b.fillna(0)), name


def test_survivors_only_uses_todays_members_for_every_day():
    p, _ = make_panel(n_stocks=30, n_days=400)
    p.member.iloc[:350, 20:] = False                      # ten stocks joined late
    assert not eligible(p).iloc[300, 20:].any() and eligible(p, survivors_only=True).iloc[300].all()


def test_constants_are_the_pre_registered_ones():
    assert honestlab.PRIOR_TRIALS == 25 and honestlab.MIN_ADV == 20_000_000 and len(honestlab.PREREGISTERED) == 6


def test_runs_log_trials_and_the_same_test_is_not_counted_twice(clean_ledger):
    p, _ = make_panel(n_stocks=60, n_days=700)
    tmp = clean_ledger
    out = honestlab.run_tests(p, tmp, tests=[("mom_6_1", 20), ("reversal_5d", 5)])
    assert [r["signal"] for r in out] == ["mom_6_1", "reversal_5d"] and all("dsr" in r and "passed" in r for r in out)
    assert honestlab.trial_count(tmp) == honestlab.PRIOR_TRIALS + 2
    honestlab.run_tests(p, tmp, tests=[("mom_6_1", 20)])               # the same test again is not a new attempt
    assert honestlab.trial_count(tmp) == honestlab.PRIOR_TRIALS + 2
    honestlab.run_tests(p, tmp, tests=[("mom_6_1", 20)], survivors_only=True)   # another universe is
    assert honestlab.trial_count(tmp) == honestlab.PRIOR_TRIALS + 3
    text = honestlab.results_text(out, "t")
    assert "mom_6_1" in text and "Deflated for" in text


def test_the_recorded_ledger_counts_and_is_not_counted_twice(tmp_path):
    """Tests already run on real data are kept in the repository, so a new computer starts from the true count."""
    recorded = [json.loads(x) for x in ledger.LEDGER.read_text().splitlines() if x.strip()]
    keys = {(e["signal"], e["horizon"], e["neutral"], e["universe"]) for e in recorded}
    assert len(keys) == len(recorded) >= 20
    assert {(n, h, True, "point-in-time") for n, h in honestlab.PREREGISTERED} <= keys
    assert honestlab.trial_count(None) == honestlab.trial_count(tmp_path) == honestlab.PRIOR_TRIALS + len(keys)
    honestlab.log_trial(tmp_path, recorded[0])                         # re-running a recorded test on this computer
    assert honestlab.trial_count(tmp_path) == honestlab.PRIOR_TRIALS + len(keys)
    honestlab.log_trial(tmp_path, {"signal": "something_new", "horizon": 5, "neutral": True, "universe": "point-in-time"})
    assert honestlab.trial_count(tmp_path) == honestlab.PRIOR_TRIALS + len(keys) + 1


def test_ledger_path_is_relative_to_the_package():
    assert ledger.LEDGER.parts[-3:] == ("lab", "research", "trial-ledger.jsonl") or ledger.LEDGER.parts[-2:] == ("research", "trial-ledger.jsonl")
    assert ledger.LEDGER.exists()


def test_cli_help_is_offline_and_exits_zero():
    from honestlab import cli

    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    assert e.value.code == 0
