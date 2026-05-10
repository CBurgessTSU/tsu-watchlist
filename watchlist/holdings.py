"""Fetch top-N ETF holdings from StockAnalysis.com.

Single source for all ETFs. StockAnalysis uses SvelteKit server-side rendering;
appending /__data.json to any page URL returns machine-readable JSON with all
page data. Holdings rows use reference-based deduplication: all string values
live in a flat data[] array and each row is a list of integer indices into that
array.

Ticker format in 's' field:
  $AAPL       → US-listed stock, strip '$'
  !TSX/WPM    → foreign-primary listing, keep ticker part after '/'
                 (filter.py stage-2 TV probe handles final US exchange check)
"""

import json
import subprocess
import urllib.request
from typing import Optional


_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _decode_ticker(raw: str) -> str:
    """Normalize StockAnalysis symbol format to a plain ticker string."""
    if raw.startswith("$"):
        return raw[1:]
    if raw.startswith("!") and "/" in raw:
        return raw.split("/", 1)[1]
    return raw


def _parse_sveltekit_holdings(payload: dict, n: int) -> list[dict]:
    """Extract top-N holdings rows from a SvelteKit __data.json payload."""
    for node in payload.get("nodes", []):
        data = node.get("data", [])
        if not data:
            continue
        for i, item in enumerate(data):
            if not isinstance(item, list) or len(item) < 3:
                continue
            if not isinstance(item[0], int) or item[0] >= len(data):
                continue
            first = data[item[0]]
            if not isinstance(first, dict):
                continue
            # Holdings rows have symbol 's', name 'n', weight 'as' keys
            if not any(k in first for k in ("s", "n", "w", "p")):
                continue
            holdings = []
            for row_idx in item[:n]:
                if not isinstance(row_idx, int) or row_idx >= len(data):
                    continue
                row = data[row_idx]
                if not isinstance(row, dict):
                    continue
                decoded = {
                    k: (data[v] if isinstance(v, int) and v < len(data) else v)
                    for k, v in row.items()
                }
                holdings.append(decoded)
            if holdings and any("s" in h or "n" in h for h in holdings):
                return holdings
    return []


def _fetch_url(url: str) -> bytes:
    """Fetch URL, using curl subprocess as fallback when urllib SSL is blocked."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read()
    except Exception:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "20", "-A", _UA, url],
            capture_output=True,
            check=True,
        )
        return result.stdout


def get_holdings(etf_ticker: str, n: int = 10) -> list[dict]:
    """Return top-N holdings for an ETF as filter.py-compatible dicts.

    Each returned dict has:
      ticker  str   plain ticker symbol (normalized for TradingView)
      name    str   company name
      weight  float percentage weight (e.g. 11.99), or 0.0 if unavailable
      rank    int   1-based position in holdings list
    """
    url = f"https://stockanalysis.com/etf/{etf_ticker.lower()}/holdings/__data.json"
    payload = json.loads(_fetch_url(url))

    rows = _parse_sveltekit_holdings(payload, n)
    result = []
    for i, row in enumerate(rows):
        raw_ticker = row.get("s", "")
        name = row.get("n", "")
        raw_weight = row.get("as", "0")
        if isinstance(raw_weight, str):
            raw_weight = raw_weight.rstrip("%")
        try:
            weight = float(raw_weight)
        except (ValueError, TypeError):
            weight = 0.0

        if not raw_ticker or not name:
            continue

        result.append({
            "ticker": _decode_ticker(raw_ticker),
            "name": name,
            "weight": weight,
            "rank": i + 1,
        })
    return result


def get_holdings_batch(
    etf_tickers: list[str],
    n: int = 10,
    on_error: Optional[str] = "warn",
) -> dict[str, list[dict]]:
    """Fetch holdings for multiple ETFs. Returns {ticker: [holdings]} mapping.

    on_error: "warn" prints to stderr and continues, "raise" propagates, None silences.
    """
    import sys

    results = {}
    for ticker in etf_tickers:
        try:
            results[ticker] = get_holdings(ticker, n)
        except Exception as exc:
            if on_error == "raise":
                raise
            if on_error == "warn":
                print(f"[holdings] {ticker}: {exc}", file=sys.stderr)
            results[ticker] = []
    return results
