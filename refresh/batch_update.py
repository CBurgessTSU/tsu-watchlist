#!/usr/bin/env python3
"""Batch sector layout refresh orchestrator.

This script:
1. Fetches holdings for each ETF via holdings.py
2. Filters via filter.py
3. Returns ready-to-use top-7 tickers for TradingView pane assignment
"""

import sys
from holdings import get_holdings
from filter import filter_holdings

SECTOR_LAYOUTS = {
    "XLB": "HvtVxkMY",
    "XLC": "HHWkk990",
    "XLE": "JWKa2afX",
    "XLI": "SSkPuTKa",
    "XLK": "qBkDx9RJ",
    "XLP": "JjKoyH0V",
    "XLRE": "l40nS2ol",
    "XLU": "SrisdiMk",
    "XLV": "wu8Hr6QK",
    "XLY": "Ni1PUFCp",
    "XLF": "sNI9obLU",
    "XLE": "JWKa2afX",
    "XLE": "JWKa2afX",
    "XOP": "9mHidhqQ",
    "XME": "od91pNpY",
    "XRT": "oeWhFxtT",
    "URA": "0C0XFnVK",
    "TAN": "wOamhhK7",
    "SMH": "FUejQwpB",
    "SIL": "hSIlThHE",
    "PHO": "Rq4CmExL",
    "PBW": "h6iYmMsz",
    "OIH": "JiQ1vYEQ",
    "MOO": "eOkWbbUy",
    "MARS": "RLxSh6cb",
    "KRE": "IZUpqXuE",
    "KIE": "XA33Awe0",
    "JETS": "Xt4bH37r",
    "IYZ": "PVEr9n6J",
    "IYT": "6Yl7xEtW",
    "ITB": "cnigsFuB",
    "ITA": "01Uljmtm",
    "FDN": "AVXKnZg2",
    "IGV": "9pejuP6p",
    "IBB": "DCLwCS5a",
    "GDX": "OPfjq59Q",
    "COPX": "i02YpLTo",
    "BUZZ": "Or2sPxhv",
    "FFTY": "wyIdu75V",
}

def get_top_7_us_listed(etf_ticker: str) -> list[str]:
    """Fetch top 7 US-listed holdings for an ETF.

    Returns list of tickers in weight order, or fewer if fewer than 7 are US-listed.
    """
    try:
        rows = get_holdings(etf_ticker, n=13)  # fetch 13 to filter down to 7
        result = filter_holdings(rows)

        # Take top 7 from kept list
        kept_tickers = [h.ticker for h in result.kept[:7]]
        return kept_tickers
    except Exception as e:
        print(f"ERROR fetching {etf_ticker}: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    # Test with first few
    for ticker in ["XLB", "XLC", "XLE"]:
        tickers = get_top_7_us_listed(ticker)
        print(f"{ticker}: {tickers}")
