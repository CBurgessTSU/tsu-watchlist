"""Pure-python tiering logic for the weekly sector ranking.

Takes a dict of {etf: return_pct_over_lookback} (already computed elsewhere from
OHLCV via the MCP) plus SPY's return, and produces the tiered ranking written
to data/sectors.json. No I/O or MCP calls in this module — kept pure so it's
trivially unit-testable.

Tiering rules (as specified by the user):
  Tier 1 (Absolute + Relative): up absolutely (>0%) AND beats SPY
  Tier 2 (Absolute):             up absolutely (>0%) but ≤ SPY — fills core
                                 slots until len(core) == target
  Tier 3 (Honorary Mentions):    non-core ETFs beating SPY (any number)

Negative-return sectors are NEVER included (bear-tape behavior is deferred).
Within each tier, sectors are sorted by return descending.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class TieredEntry:
    etf: str
    return_pct: float
    spy_return_pct: float
    tier: str  # "absolute_relative" | "absolute" | "honorary"


@dataclass(frozen=True)
class TierResult:
    core: list[TieredEntry]
    honoraries: list[TieredEntry]


def compute_return_pct(close_now: float, close_then: float) -> float:
    """Simple total return over a window: (now / then - 1) * 100."""
    if close_then <= 0:
        raise ValueError(f"close_then must be positive, got {close_then}")
    return (close_now / close_then - 1.0) * 100.0


def tier_sectors(
    returns_by_etf: dict[str, float],
    spy_return: float,
    non_core: Iterable[str],
    target: int = 10,
) -> TierResult:
    """Apply the three-tier ranking rules.

    Args:
      returns_by_etf: {etf_ticker: return_pct} — must NOT include SPY itself.
      spy_return:     SPY's return over the same lookback, as a percent.
      non_core:       ETFs excluded from core tiers (Honorary Mentions only).
      target:         Desired core count (Tier 1 + Tier 2 combined).
    """
    non_core_set = {t.upper() for t in non_core}

    core_universe = {
        etf: r for etf, r in returns_by_etf.items() if etf.upper() not in non_core_set
    }
    honorary_universe = {
        etf: r for etf, r in returns_by_etf.items() if etf.upper() in non_core_set
    }

    tier1 = sorted(
        ((etf, r) for etf, r in core_universe.items() if r > 0 and r > spy_return),
        key=lambda x: -x[1],
    )
    tier2 = sorted(
        ((etf, r) for etf, r in core_universe.items() if r > 0 and r <= spy_return),
        key=lambda x: -x[1],
    )

    core: list[TieredEntry] = []
    for etf, r in tier1:
        if len(core) >= target:
            break
        core.append(TieredEntry(etf, r, spy_return, "absolute_relative"))

    for etf, r in tier2:
        if len(core) >= target:
            break
        core.append(TieredEntry(etf, r, spy_return, "absolute"))

    honoraries = [
        TieredEntry(etf, r, spy_return, "honorary")
        for etf, r in sorted(
            ((etf, r) for etf, r in honorary_universe.items() if r > spy_return),
            key=lambda x: -x[1],
        )
    ]

    return TierResult(core=core, honoraries=honoraries)


def serialize(result: TierResult, generated_at: str, lookback_bars: int) -> dict:
    """Render TierResult to the on-disk sectors.json structure."""
    return {
        "generated_at": generated_at,
        "lookback_bars": lookback_bars,
        "spy_return_pct": result.core[0].spy_return_pct if result.core
                          else (result.honoraries[0].spy_return_pct if result.honoraries else 0.0),
        "core": [asdict(e) for e in result.core],
        "honoraries": [asdict(e) for e in result.honoraries],
    }


def write_sectors_json(path: str, payload: dict) -> None:
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
