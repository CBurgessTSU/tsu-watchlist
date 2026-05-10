"""Filter etfdb holdings to US-listed non-OTC equities.

Two-stage filter:
  Stage 1 (this module, pure): reject holdings that cannot be US-listed based
    on ticker shape or company-name signals. Emits pass-through candidates.
  Stage 2 (TV probe, elsewhere): resolve each candidate via chart_set_symbol
    and keep only those whose exchange is NYSE / Nasdaq / AMEX / etc.
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional

# Corrections for tickers where StockAnalysis uses the foreign-primary listing
# ticker instead of the US-listed equivalent. Updated as discrepancies are
# found during sector layout updates. Format: {sa_ticker: tv_ticker}
TICKER_REMAP: dict[str, str] = {
    "ABX": "B",        # Barrick Gold: TSX ABX → NYSE B (rebranded 2025)
    "K": "KGC",        # Kinross Gold: TSX K → NYSE KGC
    "EDG.DE": "GFI",   # Gold Fields: German EDG.DE → NYSE GFI (ADR)
    "HAL": "NYSE:HAL", # Halliburton: TV defaults to NSE:HAL (Hindustan Aeronautics) without prefix
    "DML": "DNN",      # Denison Mines: TSX DML → NYSE Arca DNN
    "CBRE": "NYSE:CBRE", # CBRE Group: TV defaults to IDX_DLY:CBRE without prefix
    "OR": "NYSE:OR",   # Osisko Gold Royalties: TV defaults to SET:PTT (Thai) without prefix
    "BHP": "NYSE:BHP", # BHP Group: TV defaults to ASX_DLY:BHP without prefix
    "HCC": "NYSE:HCC", # Warrior Met Coal: TV defaults to NSE_DLY:HCC (Indian) without prefix
    "IEX": "NYSE:IEX", # IDEX Corp: TV defaults to NSE_DLY:IEX (Indian) without prefix
}

# Tickers whose primary listing is on a foreign exchange with no direct US
# equivalent. StockAnalysis reports them verbatim because an ETF holds the
# foreign-primary shares; we drop them because TradingView can't resolve them
# to a clean US chart. If any of these ever get a US listing, remove from set.
FOREIGN_PRIMARY_TICKERS: set[str] = {
    "KAP",   # National Atomic Company Kazatomprom JSC — LSE GDR only (URA)
    "PDN",   # Paladin Energy Ltd — ASX primary (URA)
    "LUN",   # Lundin Mining Corporation — TSX primary, no US listing (COPX)
    "KGH",   # KGHM Polska Miedz — Warsaw primary (COPX)
    "FM",    # First Quantum Minerals Ltd — TSX primary (COPX)
    "NDA",   # Aurubis AG — German primary (COPX)
    "SFR",   # Sandfire Resources Limited — ASX primary (COPX)
    "IVN",   # Ivanhoe Mines Ltd — TSX primary (COPX)
    "CS",    # Capstone Copper Corp — TSX primary (COPX)
    "AC",    # Air Canada — TSX primary, no US listing (JETS)
    "DORL",  # Doral Group Renewable Energy Resources Ltd — TASE primary (TAN)
    "NOFR",  # O.Y. Nofar Energy Ltd — TASE primary (TAN)
    "ENRG",  # Energix - Renewable Energies Ltd — TASE primary (TAN)
}

# Dual-class share groups: only the first ticker in each tuple is kept;
# subsequent tickers are dropped as duplicates when the first is already present.
DUAL_CLASS_GROUPS: list[tuple[str, ...]] = [
    ("GOOGL", "GOOG"),   # Alphabet: keep GOOGL (Class A, voting), drop GOOG
    ("BRK.B", "BRK.A"),  # Berkshire: keep B shares (accessible), drop A
    ("MOG.A", "MOG.B"),  # Moog Inc
]


@dataclass(frozen=True)
class Holding:
    ticker: str
    name: str


@dataclass(frozen=True)
class SkippedHolding:
    ticker: str
    name: str
    reason: str


@dataclass(frozen=True)
class FilterResult:
    kept: List[Holding]
    skipped: List[SkippedHolding]


def _reject_by_shape(ticker: str) -> Optional[str]:
    if any(c.isdigit() for c in ticker):
        return "ticker contains a digit (foreign exchange code)"
    if "&" in ticker:
        return "ticker contains '&' (not permitted on US exchanges)"
    if "#" in ticker:
        return "ticker contains '#' (internal fund/instrument code)"
    if " " in ticker:
        return "ticker contains a space (not a valid equity symbol)"
    return None


def _reject_by_name(name: str) -> Optional[str]:
    norm = name.strip().rstrip(".").lower()
    foreign_suffixes = {
        " plc": "PLC (UK/Irish corporate suffix)",
        " asa": "ASA (Norwegian corporate suffix)",
        " aktiengesellschaft": "Aktiengesellschaft (German/Swiss corporate suffix)",
        " ab (publ)": "AB (publ) (Swedish corporate suffix)",
    }
    for suffix, label in foreign_suffixes.items():
        if norm.endswith(suffix):
            return f"name ends with '{label}'"
    lower = name.lower()
    for marker in ("sab de cv", "s.a.b."):
        if marker in lower:
            return f"name contains '{marker.upper()}' (foreign corporate form)"
    return None


def normalize_ticker(ticker: str) -> str:
    """Canonicalize dual-class share separators to the form TradingView uses."""
    return ticker.replace("/", ".")


def _build_dual_class_suppressed(kept_tickers: list[str]) -> set[str]:
    """Return the set of tickers that should be suppressed due to a preferred
    dual-class share already being present in kept_tickers."""
    suppressed: set[str] = set()
    for group in DUAL_CLASS_GROUPS:
        for i, ticker in enumerate(group):
            if ticker in kept_tickers:
                suppressed.update(group[i + 1:])
                break
    return suppressed


def filter_holdings(rows: Iterable[dict]) -> FilterResult:
    kept: List[Holding] = []
    skipped: List[SkippedHolding] = []
    rows = list(rows)

    # First pass: collect all remapped tickers to detect dual-class conflicts
    remapped = [TICKER_REMAP.get(r["ticker"].strip(), r["ticker"].strip()) for r in rows]
    suppressed = _build_dual_class_suppressed(remapped)

    for row in rows:
        raw_ticker = row["ticker"].strip()
        name = row["name"].strip()

        if raw_ticker in FOREIGN_PRIMARY_TICKERS:
            skipped.append(SkippedHolding(raw_ticker, name, "foreign-primary listing (no US equivalent)"))
            continue

        ticker = TICKER_REMAP.get(raw_ticker, raw_ticker)

        if ticker in suppressed:
            skipped.append(SkippedHolding(ticker, name, "dual-class duplicate (preferred share already included)"))
            continue

        reason = _reject_by_shape(ticker)
        if reason:
            skipped.append(SkippedHolding(ticker, name, reason))
            continue

        reason = _reject_by_name(name)
        if reason:
            skipped.append(SkippedHolding(ticker, name, reason))
            continue

        kept.append(Holding(ticker=normalize_ticker(ticker), name=name))

    return FilterResult(kept=kept, skipped=skipped)
