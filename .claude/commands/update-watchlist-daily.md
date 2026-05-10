---
description: Re-qualify stocks for each frozen sector using CB Swing Labels and rewrite the public watchlist. Run nightly.
allowed-tools: Bash, Read, Write, Edit, mcp__tradingview__*
---

# Daily watchlist qualification

Reads the frozen weekly sector ranking from `watchlist/data/sectors.json`,
fetches each sector's top-10 US-listed holdings, and qualifies each holding
(plus the sector ETF itself) against the three CB Swing Labels booleans.
Writes the qualified watchlist to `watchlist/data/watchlist.json`, copies it
into `docs/`, then commits + pushes to publish via GitHub Pages.

## Inputs

- `watchlist/data/sectors.json` — must exist (run `/update-sectors-weekly` first).
- CB Swing Labels indicator must expose three hidden plots:
  - `qualTrend`     (1 if `trendState == 1`, else 0)
  - `qualAbove200`  (1 if `close > sma200`, else 0)
  - `qualEarnings`  (1 if `earningsFar`, else 0)

## Output

- `watchlist/data/watchlist.json` (canonical)
- `docs/watchlist.json` (copy — GitHub Pages reads this)
- A new commit on the current branch + push to origin.

## Procedure

### 1. Verify TradingView is up (and launch if not)
Call `mcp__tradingview__tv_health_check`. If it fails with "CDP connection
failed", call `mcp__tradingview__tv_launch` with `kill_existing=false`, then
re-check. Only abort if TV refuses to come up after the launch attempt —
nightly cron requires self-healing.

### 2. Build sector bundles
Run a small inline python (`Bash` with `python3 -c`) that:
- Imports `watchlist.daily_qualify`
- Calls `load_sectors("watchlist/data/sectors.json")`
- Calls `build_sector_bundles(payload, n_holdings=10)`
- Calls `all_unique_symbols(bundles)`
- Pickles or json-dumps the bundles + symbol list to a temp file the next steps read.

(Alternatively: run python once to JSON-dump the bundles and the unique-symbol
list, then read the JSON back from the next steps.)

The unique-symbol list is what gets passed to MCP. Bundles preserve the
sector → candidates mapping for the assembly step.

### 3. Qualify all symbols in one batch
For the unique-symbol list, fetch the three plots from CB Swing Labels.

Preferred: `mcp__tradingview__batch_run` configured to call
`mcp__tradingview__data_get_study_values` across all symbols on the daily
timeframe, requesting the `qualTrend`, `qualAbove200`, `qualEarnings` plot
values from the CB Swing Labels indicator.

Fallback (if batch_run can't take that exact shape): loop sequentially —
`chart_set_symbol(sym)` → `data_get_study_values(...)` per symbol. Slower but
deterministic.

For each symbol, build `qualified[symbol] = (qualTrend == 1 AND qualAbove200
== 1 AND qualEarnings == 1)`. Missing values, missing indicator, or any error
→ `qualified[symbol] = False` (do NOT raise; just skip the symbol — keeps a
broken ticker from torpedoing the whole run).

### 4. Check options liquidity for qualified symbols
Collect every symbol that passed qualification (i.e. `qualified[s] == True`,
both ETFs and individual stocks) into a flat list.  Run inline python using
`python3.12`:

```python
import sys
sys.path.insert(0, "watchlist")
import options_check, json
from datetime import date

qualified_syms = [s for s, v in qualified.items() if v]
print(f"[options] checking {len(qualified_syms)} qualified symbols…")
options_warnings = options_check.check_options_liquidity(qualified_syms)
warned = [s for s, w in options_warnings.items() if w]
print(f"[options] {len(warned)} symbols flagged (no liquid monthly calls): {warned}")
```

Pass `options_warnings` to the assembly step below.  If this step errors or
takes too long, set `options_warnings = {}` and continue — the warning is
informational, not a gate.

### 5. Assemble the watchlist payload
Inline python again:
- Reload bundles
- `assemble_watchlist_payload(bundles, qualified, sectors_frozen_at, generated_at, options_warnings)`
- `write_watchlist_json("watchlist/data/watchlist.json", payload)`

`sectors_frozen_at` = `generated_at` from `sectors.json`.
`generated_at` = current ISO 8601 timestamp in America/New_York.

### 6. Copy to docs/
`cp watchlist/data/watchlist.json docs/watchlist.json`

### 7. Commit + push
- `cd` into the repo (already there).
- `git add docs/watchlist.json watchlist/data/watchlist.json`
- `git commit -m "watchlist: refresh $(date -u +%Y-%m-%dT%H:%MZ)"` — if the
  commit produces no changes (qualification identical to last run), skip the
  push and report "no changes".
- `git push` — only if the commit succeeded.

If the repo is not a git repo or has no `origin` remote yet, skip step 7 and
print clear instructions for the user to set it up.

### 8. Report to the user
Print:
- Total symbols probed, how many qualified.
- Per-sector qualified counts (e.g. "SMH: ETF + 6 stocks").
- Any symbols that received the ⚠️ options warning.
- Path to the written file and "Pushed: yes/no".

## Style

- Treat individual ticker failures as data, not as exceptions — log and move on.
- The user expects this to run unattended overnight. Output should be quiet on
  success and loud on real failures (TV down, sectors.json missing, etc.).
