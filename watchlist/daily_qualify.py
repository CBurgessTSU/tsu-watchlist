"""Helpers for the daily qualification pass.

Reads the frozen sectors.json, fetches each sector's top-10 holdings via the
existing refresh/holdings.py + refresh/filter.py modules (US-listed only,
foreign-primary dropped, dual-class deduped), and produces a flat symbol list
for the slash command to feed into batch_run.

The actual qualification (reading the three CB Swing Labels plots) happens via
MCP in the slash command itself — this module stays pure-python so it can be
tested and reused without an MCP context.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

# Reach the sibling refresh/ module without polluting sys.path globally.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "refresh"))
import holdings as _holdings  # noqa: E402
import filter as _filter      # noqa: E402
sys.path.pop(0)


@dataclass(frozen=True)
class Candidate:
    symbol: str
    name: str  # "" for the ETF itself (we don't fetch ETF names)


@dataclass(frozen=True)
class SectorBundle:
    etf: str
    tier: str
    return_pct: float
    spy_return_pct: float
    bucket: str        # "core" | "honorary"
    candidates: list[Candidate]  # ETF first, then top-10 US-listed holdings


def load_sectors(path: str | Path) -> dict:
    with open(path) as f:
        return json.load(f)


def build_sector_bundles(sectors_payload: dict, n_holdings: int = 10) -> list[SectorBundle]:
    """For each ranked sector, fetch + filter holdings and return a SectorBundle.

    Bundles are returned in the same order as the sectors.json (core first,
    then honoraries — both already sorted by return desc).
    """
    bundles: list[SectorBundle] = []

    for bucket_name in ("core", "honoraries"):
        bucket_label = "core" if bucket_name == "core" else "honorary"
        for entry in sectors_payload.get(bucket_name, []):
            etf = entry["etf"]
            try:
                raw = _holdings.get_holdings(etf, n=n_holdings)
            except Exception as exc:
                print(f"[daily_qualify] {etf} holdings fetch failed: {exc}", file=sys.stderr)
                raw = []

            filtered = _filter.filter_holdings(
                [{"ticker": h["ticker"], "name": h["name"]} for h in raw]
            )

            # ETF itself is the first candidate, then its US-listed top-N holdings.
            candidates: list[Candidate] = [Candidate(symbol=etf, name="")]
            for h in filtered.kept:
                candidates.append(Candidate(symbol=h.ticker, name=h.name))

            bundles.append(SectorBundle(
                etf=etf,
                tier=entry["tier"],
                return_pct=entry["return_pct"],
                spy_return_pct=entry["spy_return_pct"],
                bucket=bucket_label,
                candidates=candidates,
            ))

    return bundles


def all_unique_symbols(bundles: list[SectorBundle]) -> list[str]:
    """Flat de-duplicated symbol list — single batch_run call hits each ticker once."""
    seen: dict[str, None] = {}
    for b in bundles:
        for c in b.candidates:
            seen.setdefault(c.symbol, None)
    return list(seen.keys())


def assemble_watchlist_payload(
    bundles: list[SectorBundle],
    qualified: dict[str, bool],
    sectors_frozen_at: str,
    generated_at: str,
) -> dict:
    """Build the final watchlist.json payload.

    Args:
      bundles:           Output of build_sector_bundles.
      qualified:         {symbol: True/False} from MCP qualification step.
                         A symbol missing from the dict is treated as not qualified.
      sectors_frozen_at: Timestamp when sectors.json was generated.
      generated_at:      Timestamp for this watchlist run.
    """
    core: list[dict] = []
    honoraries: list[dict] = []

    for b in bundles:
        etf_qualified = qualified.get(b.etf, False)
        qualified_stocks = [
            {"symbol": c.symbol, "name": c.name}
            for c in b.candidates
            if c.symbol != b.etf and qualified.get(c.symbol, False)
        ]
        section = {
            "etf": b.etf,
            "tier": b.tier,
            "return_pct": b.return_pct,
            "spy_return_pct": b.spy_return_pct,
            "etf_qualified": etf_qualified,
            "stocks": qualified_stocks,
        }
        (core if b.bucket == "core" else honoraries).append(section)

    return {
        "generated_at": generated_at,
        "sectors_frozen_at": sectors_frozen_at,
        "core_sectors": core,
        "honorable_mentions": honoraries,
    }


def write_watchlist_json(path: str | Path, payload: dict) -> None:
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
