"""The point-in-time universe: the S&P 500 as it was on each past day, rebuilt from the public record of
additions and removals (Wikipedia), joined to Yahoo prices and cached as one panel.

Known gap (free data): Yahoo keeps prices for companies that were dropped from the index but still
trade, which are most of the losers. It has no prices for most companies that were acquired or went
bankrupt. `coverage_text` reports how much is missing. Closing that gap needs paid data with delisted stocks.
"""
from __future__ import annotations

import html
import json
import pickle
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

WIKI_CURRENT = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_HISTORY = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"
# Companies demoted from the S&P 500 mostly land in these two indexes; their pages give the sector.
WIKI_SMALLER = ("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies", "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies")
YAHOO_TO_GICS = {"Technology": "Information Technology", "Financial Services": "Financials", "Healthcare": "Health Care",
                 "Consumer Cyclical": "Consumer Discretionary", "Consumer Defensive": "Consumer Staples",
                 "Basic Materials": "Materials", "Communication Services": "Communication Services", "Energy": "Energy",
                 "Industrials": "Industrials", "Utilities": "Utilities", "Real Estate": "Real Estate"}


def _fetch(url: str) -> str:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8")


def _grid(page: str, table_id: str) -> list[list[str]]:
    """A wiki table as rows of text, with row- and column-spanning cells repeated into every cell they cover."""
    m = re.search(r'<table[^>]*id="%s"[^>]*>(.*?)</table>' % re.escape(table_id), page, re.S)
    if not m:
        return []
    out, carry = [], {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S):
        cells = re.findall(r"<t[dh]([^>]*)>(.*?)</t[dh]>", row, re.S)
        line, col, k = [], 0, 0
        while k < len(cells) or col in carry:
            if col in carry:
                text, left = carry[col]
                line.append(text)
                if left > 1:
                    carry[col] = (text, left - 1)
                else:
                    del carry[col]
                col += 1
                continue
            attrs, body = cells[k]
            k += 1
            body = re.sub(r"<sup.*?</sup>", "", body, flags=re.S)
            text = html.unescape(re.sub(r"<.*?>", "", body)).replace("\xa0", " ").strip()
            rs = int((re.search(r'rowspan="?(\d+)', attrs) or [0, 1])[1])
            cs = int((re.search(r'colspan="?(\d+)', attrs) or [0, 1])[1])
            for _ in range(cs):
                line.append(text)
                if rs > 1:
                    carry[col] = (text, rs - 1)
                col += 1
        if line:
            out.append(line)
    return out


_SYMBOL = re.compile(r"[A-Z][A-Z0-9]{0,5}(?:[.-][A-Z]{1,2})?$")


def _sym(t: str) -> str:
    """A ticker as Yahoo spells it (BRK.B -> BRK-B). A cell whose markup did not strip cleanly (a few on the
    S&P 600 page carry a link with '>' inside an attribute) still ends with the symbol, so take that."""
    t = t.strip().upper()
    m = _SYMBOL.search(t)
    return (m.group(0) if m else t).replace(".", "-")


def parse_current(page: str) -> pd.DataFrame:
    rows = [r for r in _grid(page, "constituents") if len(r) >= 4 and r[0] not in ("Symbol", "")]
    return pd.DataFrame({"ticker": [_sym(r[0]) for r in rows], "name": [r[1] for r in rows], "sector": [r[2] for r in rows],
                         "added": [pd.to_datetime(r[5], errors="coerce") if len(r) > 5 else pd.NaT for r in rows]})


def parse_changes(page: str) -> pd.DataFrame:
    out = []
    for r in _grid(page, "changes"):
        if len(r) < 6:
            continue
        d = pd.to_datetime(r[0], errors="coerce")
        if pd.isna(d):
            continue
        out.append({"date": d.normalize(), "added": _sym(r[1]) if r[1] else "", "removed": _sym(r[3]) if r[3] else "", "reason": r[5]})
    return pd.DataFrame(out)


def membership(current: list[str], changes: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """True where a stock was in the index on that day. Rebuilt by walking the change record backward
    from today's members: undo each addition, restore each removal."""
    active: dict[str, pd.Timestamp | None] = {t: None for t in current}   # ticker -> date it left (None = still in)
    spans = []
    for r in changes.sort_values("date", ascending=False, kind="mergesort").itertuples():
        if r.added and r.added in active:
            spans.append((r.added, r.date, active.pop(r.added)))
        if r.removed and r.removed not in active:
            active[r.removed] = r.date
    spans += [(t, None, end) for t, end in active.items()]
    m = pd.DataFrame(False, index=calendar, columns=sorted({t for t, _, _ in spans}))
    for t, start, end in spans:
        sel = np.ones(len(calendar), bool)
        if start is not None:
            sel &= calendar >= start
        if end is not None:
            sel &= calendar < end
        m.loc[sel, t] = True
    return m


@dataclass
class Panel:
    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame
    member: pd.DataFrame
    sector: pd.Series
    bench: pd.DataFrame
    meta: dict = field(default_factory=dict)

    def prices(self) -> dict[str, pd.DataFrame]:
        out = {t: pd.DataFrame({"Open": self.open[t], "High": self.high[t], "Low": self.low[t], "Close": self.close[t],
                                "Volume": self.volume[t]}).dropna(subset=["Close"]) for t in self.close.columns}
        out[self.meta.get("bench", "SPY")] = self.bench
        return out



def _reason_kind(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ("bankrupt", "chapter 11", "fdic", "receivership", "seized")):
        return "failed"
    if any(k in t for k in ("acqui", "merg", "purchas", "private", "bought", "takeover", "buyout")):
        return "acquired"
    return "dropped"


def assemble(current: pd.DataFrame, changes: pd.DataFrame, px: dict[str, pd.DataFrame], bench: pd.DataFrame, start,
             sector_lookup=None) -> Panel:
    """Build the panel from already-downloaded pieces (kept apart from the downloads so it can be tested)."""
    cal = bench.index[bench.index >= pd.Timestamp(start)]
    mem = membership(list(current["ticker"]), changes, cal)
    mem = mem.loc[:, mem.any()]
    cur = set(current["ticker"])
    left = {t: mem.index[mem[t].to_numpy()][-1] for t in mem.columns if t not in cur}
    why = {}
    for r in changes.sort_values("date").itertuples():
        if r.removed:
            why[r.removed] = _reason_kind(r.reason)
    clean, notes = {}, []
    for t in mem.columns:
        df = px.get(t)
        if df is None or df.empty:
            continue
        df = df[~df.index.duplicated()].sort_index()
        if t in left and df.index[0] > left[t] - pd.Timedelta(days=30):
            # Either the symbol was reused by another company, or the data source has dropped a delisted
            # company's history and kept only a last stray bar. Both ways there is nothing usable.
            notes.append(f"{t}: no prices from while it was a member (delisted and removed by the data source, or the symbol was reused); not used")
            continue
        jump = df["Close"].pct_change()
        bad = jump[jump > 3.0]
        if len(bad):   # e.g. a relisting after bankruptcy: the earlier history is a different security
            notes.append(f"{t}: {bad.iloc[-1]:+.0%} one-day jump on {bad.index[-1].date()}; earlier history dropped")
            df = df.loc[bad.index[-1]:]
        clean[t] = df

    def wide(col):
        return pd.DataFrame({t: d[col] for t, d in clean.items()}).reindex(cal)

    have = sorted(clean)
    sector = current.set_index("ticker")["sector"].reindex(have)
    for t in [t for t in have if pd.isna(sector[t])]:
        s = sector_lookup(t) if sector_lookup else None
        sector[t] = YAHOO_TO_GICS.get(s, s) if s else "Unknown"
    close = wide("Close")
    mem = mem.reindex(columns=sorted(mem.columns))
    priced = (mem[have] & close[have].notna()).sum(axis=1)
    by_year = (priced.groupby(cal.year).sum() / mem.sum(axis=1).groupby(cal.year).sum()).round(3)
    missing = [t for t in mem.columns if t not in clean]
    meta = {"built": datetime.now().isoformat(timespec="seconds"), "start": str(cal[0].date()), "end": str(cal[-1].date()),
            "bench": "SPY", "ever_members": int(mem.shape[1]), "with_prices": len(have),
            "current_members": len(cur), "left_the_index": len(left),
            "left_with_prices": len([t for t in left if t in clean]),
            "missing_by_reason": pd.Series([why.get(t, "dropped") for t in missing]).value_counts().to_dict() if missing else {},
            "left_by_reason": pd.Series([why.get(t, "dropped") for t in left]).value_counts().to_dict() if left else {},
            "member_days_priced_by_year": {int(k): float(v) for k, v in by_year.items()}, "notes": notes, "missing": missing}
    return Panel(wide("Open"), wide("High"), wide("Low"), close, wide("Volume"), mem, sector, bench.reindex(cal), meta)


def build(cache: Path, source, start="2013-06-01", fetch=_fetch, sector_lookup=None, verbose=True) -> Panel:
    """Download the membership record and prices, and cache the panel in `cache` (several minutes)."""
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    current, changes = parse_current(fetch(WIKI_CURRENT)), parse_changes(fetch(WIKI_HISTORY))
    if len(current) < 400 or len(changes) < 100:
        raise SystemExit("lab: could not read the S&P 500 membership tables (page layout changed?).")
    known = {}
    for url in WIKI_SMALLER:            # sectors for companies that have left the S&P 500 but still trade
        try:
            other = parse_current(fetch(url))
            known.update(dict(zip(other["ticker"], other["sector"])))
        except Exception:
            pass
    first_choice = sector_lookup

    def sector_lookup(t):               # noqa: F811  (index pages first, then the optional fallback)
        return known.get(t) or (first_choice(t) if first_choice else None)
    bench = source.history(["SPY"], start=start)["SPY"]
    mem = membership(list(current["ticker"]), changes, bench.index)
    ever = sorted(mem.columns[mem.any()])
    if verbose:
        print(f"lab: {len(current)} current members, {len(changes)} recorded changes, {len(ever)} stocks were members at some point "
              f"since {bench.index[0].date()}; downloading prices...", flush=True)
    px = source.history(ever, start=start)
    p = assemble(current, changes, px, bench, start, sector_lookup)
    with open(cache / "panel.pkl", "wb") as f:
        pickle.dump(p, f)
    (cache / "meta.json").write_text(json.dumps(p.meta, indent=1))
    return p

def load(cache: Path) -> Panel:
    f = Path(cache) / "panel.pkl"
    if not f.exists():
        raise SystemExit(f"lab: no data in {cache}. Run `python -m honestlab build` first.")
    with open(f, "rb") as fh:
        return pickle.load(fh)


def coverage_text(p: Panel) -> str:
    m = p.meta
    L = [f"Point-in-time S&P 500, {m['start']} to {m['end']} (built {m['built']})",
         f"  Stocks that were members at some point: {m['ever_members']}; with usable prices: {m['with_prices']}.",
         f"  Still members today: {m['current_members']}. Left the index: {m['left_the_index']} "
         f"({', '.join(f'{k} {v}' for k, v in m['left_by_reason'].items())}); of those, {m['left_with_prices']} have prices.",
         f"  Missing entirely: {len(m['missing'])} ({', '.join(f'{k} {v}' for k, v in m['missing_by_reason'].items()) or 'none'}).",
         "  Share of member-days with a price, by year: " + ", ".join(f"{y}: {v:.0%}" for y, v in m["member_days_priced_by_year"].items()),
         "  What is missing is mostly companies that were bought out (usually at a premium) and a few that failed. "
         "Demoted companies that still trade, the main source of survivorship bias, are included."]
    if m["notes"]:
        L.append("  Data fixes: " + "; ".join(m["notes"][:8]) + (f"; and {len(m['notes']) - 8} more" if len(m["notes"]) > 8 else ""))
    return "\n".join(L)


def yahoo_sector(t: str) -> str | None:
    """Sector of a stock that has left the index (the membership page only lists sectors for current members)."""
    import yfinance as yf

    try:
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return (yf.Ticker(t).info or {}).get("sector")
    except Exception:
        return None


class YahooSource:
    """Free daily prices from Yahoo Finance via the optional `yfinance` package (adjusted for splits and dividends).
    `history` returns {ticker: DataFrame[Open, High, Low, Close, Volume]}."""

    name = "yfinance"
    COLS = ["Open", "High", "Low", "Close", "Volume"]

    def __init__(self):
        import yfinance  # noqa: F401  (fail early with a clear message if it is not installed)

    def history(self, tickers, start=None, end=None) -> dict[str, pd.DataFrame]:
        import yfinance as yf

        tickers = sorted(set(tickers))
        end_excl = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d") if end is not None else None
        start_s = pd.Timestamp(start).strftime("%Y-%m-%d") if start is not None else None
        frames = []
        for i in range(0, len(tickers), 40):     # chunks: one request per ticker at once can exceed the open-file limit
            part = yf.download(tickers[i:i + 40], start=start_s, end=end_excl, auto_adjust=True,
                               group_by="ticker", progress=False, threads=8)
            if part is not None and len(part):
                if not isinstance(part.columns, pd.MultiIndex):    # a single ticker comes back flat
                    part.columns = pd.MultiIndex.from_product([[tickers[i]], part.columns])
                frames.append(part)
        raw = pd.concat(frames, axis=1) if frames else pd.DataFrame()
        out = {}
        for t in tickers:
            try:
                df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            except KeyError:
                continue
            if not set(self.COLS).issubset(df.columns):
                continue
            df = df[self.COLS].dropna(subset=["Close"]).astype(float)
            idx = pd.to_datetime(df.index)
            if idx.tz is not None:
                idx = idx.tz_localize(None)
            df.index = idx.normalize()
            if len(df):
                out[t] = df
        return out
