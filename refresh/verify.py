"""Stage-2 TV ticker verification for ETF holdings.

Usage:
    python3 -m refresh.verify XLF
    python3 -m refresh.verify GDX --n 15

Outputs the post-filter ticker list so Claude can run symbol_search via MCP
to confirm each ticker resolves to a US exchange (NYSE/NASDAQ/AMEX/CBOE/BATS).
Any mismatches should be added to TICKER_REMAP in filter.py.
"""

import argparse
import sys
from refresh.holdings import get_holdings
from refresh.filter import filter_holdings, TICKER_REMAP

US_EXCHANGES = {"NYSE", "NASDAQ", "AMEX", "CBOE", "BATS", "NYSE ARCA", "NYSE AMERICAN"}


def get_candidates(etf_ticker: str, n: int = 15) -> list[dict]:
    rows = get_holdings(etf_ticker, n=n)
    result = filter_holdings(rows)
    return [{"ticker": h.ticker, "name": h.name} for h in result.kept]


def print_candidates(etf_ticker: str, n: int = 15) -> None:
    candidates = get_candidates(etf_ticker, n)
    remapped = {v: k for k, v in TICKER_REMAP.items()}

    print(f"\n{etf_ticker} — post-filter candidates (verify each via TV symbol_search):\n")
    for i, c in enumerate(candidates, 1):
        note = f"  ← remapped from {remapped[c['ticker']]}" if c["ticker"] in remapped else ""
        print(f"  {i:2}. {c['ticker']:<10} {c['name']}{note}")

    print(f"\nActive remaps applied: {TICKER_REMAP}")
    print("\nFor each ticker above, run symbol_search and confirm:")
    print("  - Exchange is one of:", ", ".join(sorted(US_EXCHANGES)))
    print("  - Company name matches expected holding")
    print("  - If wrong: add correction to TICKER_REMAP in filter.py\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("etf", help="ETF ticker to verify (e.g. GDX)")
    parser.add_argument("--n", type=int, default=15, help="Holdings depth to fetch")
    args = parser.parse_args()
    print_candidates(args.etf.upper(), args.n)
