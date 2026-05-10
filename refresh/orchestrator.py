#!/usr/bin/env python3
"""Orchestrate all 38 sector layout updates via TradingView MCP.

This script coordinates the full workflow:
1. Fetch holdings for all ETFs
2. For each layout: navigate, set panes, screenshot, save, return to RSP
3. At the end: restore RSP to 1-month/Daily/2-bar-right view

Designed to be run WITHIN the Claude Code session (via /code-op calls to MCP tools).
"""

import json
import sys
import time

# Layout list with chart URLs
SECTOR_LAYOUTS = [
    ("XLB", "HvtVxkMY"),
    ("XLC", "HHWkk990"),
    ("XLE", "JWKa2afX"),
    ("XLI", "SSkPuTKa"),
    ("XLK", "qBkDx9RJ"),
    ("XLP", "JjKoyH0V"),
    ("XLRE", "l40nS2ol"),
    ("XLU", "SrisdiMk"),
    ("XLV", "wu8Hr6QK"),
    ("XLY", "Ni1PUFCp"),
    ("XLF", "sNI9obLU"),
    ("XOP", "9mHidhqQ"),
    ("XME", "od91pNpY"),
    ("XRT", "oeWhFxtT"),
    ("URA", "0C0XFnVK"),
    ("TAN", "wOamhhK7"),
    ("SMH", "FUejQwpB"),
    ("SIL", "hSIlThHE"),
    ("PHO", "Rq4CmExL"),
    ("PBW", "h6iYmMsz"),
    ("OIH", "JiQ1vYEQ"),
    ("MOO", "eOkWbbUy"),
    ("MARS", "RLxSh6cb"),
    ("KRE", "IZUpqXuE"),
    ("KIE", "XA33Awe0"),
    ("JETS", "Xt4bH37r"),
    ("IYZ", "PVEr9n6J"),
    ("IYT", "6Yl7xEtW"),
    ("ITB", "cnigsFuB"),
    ("ITA", "01Uljmtm"),
    ("FDN", "AVXKnZg2"),
    ("IGV", "9pejuP6p"),
    ("IBB", "DCLwCS5a"),
    ("GDX", "OPfjq59Q"),
    ("COPX", "i02YpLTo"),
    ("BUZZ", "Or2sPxhv"),
    ("FFTY", "wyIdu75V"),
    ("MAGS", "cXz6c6hd"),
    ("XPH", "ITAu5U1a"),
]

# MCP pane index mapping (column-major)
PANE_INDEX_MAP = {
    1: 2,   # #1 holding -> pane 2 (top row, col 2)
    2: 4,   # #2 holding -> pane 4 (top row, col 3)
    3: 6,   # #3 holding -> pane 6 (top row, col 4)
    4: 1,   # #4 holding -> pane 1 (bottom row, col 1)
    5: 3,   # #5 holding -> pane 3 (bottom row, col 2)
    6: 5,   # #6 holding -> pane 5 (bottom row, col 3)
    7: 7,   # #7 holding -> pane 7 (bottom row, col 4)
}

def main():
    """Print the holdings map and orchestration instructions."""
    from holdings import get_holdings
    from filter import filter_holdings

    holdings_map = {}
    for etf_ticker, chart_url in SECTOR_LAYOUTS:
        try:
            rows = get_holdings(etf_ticker, n=20)
            result = filter_holdings(rows)
            kept_tickers = [h.ticker for h in result.kept[:7]]
            holdings_map[etf_ticker] = kept_tickers
        except Exception as e:
            print(f"ERROR {etf_ticker}: {e}", file=sys.stderr)
            holdings_map[etf_ticker] = []

    # Write to JSON for downstream use
    with open("/tmp/sector_holdings_orchestrator.json", "w") as f:
        json.dump({
            "holdings_map": holdings_map,
            "layouts": SECTOR_LAYOUTS,
            "pane_map": PANE_INDEX_MAP,
        }, f, indent=2)

    print("Orchestrator data written to /tmp/sector_holdings_orchestrator.json", file=sys.stderr)
    print(json.dumps(holdings_map, indent=2))

if __name__ == "__main__":
    main()
