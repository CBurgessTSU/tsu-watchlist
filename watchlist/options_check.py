"""Options liquidity checker using CBOE's free delayed-quotes API.

For each symbol, fetches all options in one request, filters to monthly
(3rd-Friday) call expirations within 50 days, and checks whether any strike
in the viable window (5 at/below price + 2 above price) has OI ≥ MIN_OI.

Returns {symbol: True} for symbols that LACK liquid calls — callers use this
to attach the ⚠️ warning flag. Symbols with sufficient liquidity are omitted.
Data gaps (network errors, no options listed) are treated as "no warning" to
avoid penalising tickers for infrastructure failures.
"""

from __future__ import annotations

import bisect
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional


_CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

MIN_OI = 500
STRIKES_ITM = 5   # strikes at or below current price (includes ATM)
STRIKES_OTM = 2   # strikes strictly above current price
DAYS_HORIZON = 50


def _is_third_friday(d: date) -> bool:
    """Monthly option expiration: the 3rd Friday falls on days 15–21."""
    return d.weekday() == 4 and 15 <= d.day <= 21


def _parse_occ(symbol: str) -> tuple[str, float, date] | tuple[None, None, None]:
    """Parse an OCC option symbol → (kind, strike, expiry_date).

    Format: <TICKER><YYMMDD><C|P><8-digit strike×1000>
    Example: AAPL260511C00200000 → ('C', 200.0, date(2026, 5, 11))
    """
    for i in range(1, len(symbol)):
        if symbol[i : i + 6].isdigit() and len(symbol) > i + 6 and symbol[i + 6] in "CP":
            try:
                yy = int(symbol[i : i + 2])
                mm = int(symbol[i + 2 : i + 4])
                dd = int(symbol[i + 4 : i + 6])
                kind = symbol[i + 6]
                strike = int(symbol[i + 7 :]) / 1000.0
                return kind, strike, date(2000 + yy, mm, dd)
            except (ValueError, OverflowError):
                pass
    return None, None, None


def _viable_strikes(sorted_strikes: list[float], price: float) -> list[float]:
    """Return the viable window: STRIKES_ITM at/below price + STRIKES_OTM above."""
    if not sorted_strikes:
        return []
    atm_idx = bisect.bisect_right(sorted_strikes, price) - 1
    if atm_idx < 0:
        # All strikes are above current price — take the first OTM strikes only
        return sorted_strikes[: STRIKES_OTM]
    itm_start = max(0, atm_idx - (STRIKES_ITM - 1))
    otm_end = min(len(sorted_strikes), atm_idx + 1 + STRIKES_OTM)
    return sorted_strikes[itm_start:otm_end]


def _strip_exchange_prefix(symbol: str) -> str:
    """'NYSE:HAL' → 'HAL', 'AAPL' → 'AAPL'."""
    return symbol.split(":")[-1] if ":" in symbol else symbol


_FETCH_RETRIES = 2
_RETRY_DELAY = 3.0


def _fetch_cboe(cboe_sym: str) -> dict | None:
    """Fetch CBOE delayed-quote data for a symbol. Retries on transient errors.

    Returns the parsed 'data' dict, or None if all attempts fail (fail open).
    """
    url = _CBOE_URL.format(symbol=cboe_sym)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    for attempt in range(_FETCH_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())["data"]
        except (urllib.error.URLError, KeyError, json.JSONDecodeError):
            if attempt < _FETCH_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
    return None


def check_symbol(symbol: str, today: Optional[date] = None) -> bool:
    """Return True if the symbol should show the ⚠️ warning (no liquid calls found).

    Fetches from CBOE with retries. All attempts failing → fail open (no warning),
    so transient CDN errors don't generate false warnings.
    """
    if today is None:
        today = date.today()
    cutoff = today + timedelta(days=DAYS_HORIZON)
    cboe_sym = _strip_exchange_prefix(symbol).replace(".", "-")  # BRK.B → BRK-B on CBOE

    data = _fetch_cboe(cboe_sym)
    if data is None:
        return False  # can't reach CBOE after retries → no warning

    price = data.get("current_price")
    if not price:
        return False

    options = data.get("options", [])
    if not options:
        return True  # listed but no options at all → warn

    # Build {exp → {strike → OI}} for monthly expirations within the horizon only.
    # Keying by expiration prevents out-of-window calls at the same strike from
    # masking a genuinely illiquid monthly.
    monthly: dict[date, dict[float, float]] = defaultdict(dict)
    for opt in options:
        kind, strike, exp = _parse_occ(opt.get("option", ""))
        if kind != "C" or exp is None:
            continue
        if today <= exp <= cutoff and _is_third_friday(exp):
            monthly[exp][strike] = opt.get("open_interest") or 0

    if not monthly:
        return True  # no monthly expirations in window → warn

    for strike_oi in monthly.values():
        viable = _viable_strikes(sorted(strike_oi.keys()), price)
        for s in viable:
            if strike_oi.get(s, 0) >= MIN_OI:
                return False  # found a liquid monthly call — no warning needed

    return True  # exhausted all monthly expirations, none had liquid calls


def check_options_liquidity(
    symbols: list[str],
    today: Optional[date] = None,
) -> dict[str, bool]:
    """Check options liquidity for a list of symbols.

    Returns {symbol: True} for symbols that should display the ⚠️ warning.
    Symbols with sufficient liquidity are not included in the result.
    """
    if today is None:
        today = date.today()

    result: dict[str, bool] = {}
    for i, sym in enumerate(symbols):
        if i > 0:
            time.sleep(0.4)  # stay well under CBOE's rate limit
        if check_symbol(sym, today):
            result[sym] = True
    return result
