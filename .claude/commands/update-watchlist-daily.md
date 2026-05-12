---
description: Re-qualify stocks for each frozen sector using CB Swing Labels and rewrite the public watchlist. Run nightly.
allowed-tools: Bash, Read, Write, Edit, Agent, mcp__tradingview__*
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
re-check.

**Hard abort if TV is still unreachable after the launch attempt.** Print
`ERROR: TradingView unreachable after launch attempt — aborting. No files
written.` to stderr and stop immediately. Do NOT fall back to reading the
existing watchlist.json or summarizing a previous run.

### 2. Build sector bundles
Run inline python (`Bash` with `python3 -c`):

```python
import sys, json
from dataclasses import asdict
sys.path.insert(0, 'watchlist')
from daily_qualify import load_sectors, build_sector_bundles, all_unique_symbols

payload = load_sectors('watchlist/data/sectors.json')
bundles  = build_sector_bundles(payload, n_holdings=10)
syms     = all_unique_symbols(bundles)

with open('/tmp/wl_bundles.json', 'w') as f:
    json.dump([asdict(b) for b in bundles], f)
with open('/tmp/wl_symbols.json', 'w') as f:
    json.dump(syms, f)
print(f'sectors: {len(bundles)}, unique symbols: {len(syms)}')
```

### 3. Qualify symbols — one agent per sector (sequential)

**Prerequisite — verify CB Swing Labels plots are visible:**
Call `data_get_study_values`. Confirm "CB Swing Labels" appears with
`qualTrend`, `qualAbove200`, `qualEarnings` fields. If it is missing, the
Pine Script source must be fixed: the three `display=display.data_window`
lines at the bottom of CB Swing Labels must be changed to `display=display.all`
and the indicator re-added to the chart (remove old instance, open the indicators
dialog, double-click CB Swing Labels from Favorites). Only proceed once the plots
are visible.

**Clear stale checkpoints:** `rm -f /tmp/wl_qual_*.json`

**For each bundle in order (one at a time, NOT parallel):**

1. Write the sector's candidate symbols to a temp file:
   ```bash
   echo '<json-array-of-symbols>' > /tmp/wl_qual_input_{ETF}.json
   ```

2. Spawn a subagent (Agent tool) with this brief — substitute the real ETF
   ticker and symbol list:

   > TradingView is open. CB Swing Labels is on the chart (Daily) and returns
   > qualTrend, qualAbove200, qualEarnings from data_get_study_values.
   >
   > Qualify these symbols for the {ETF} sector: [{sym1}, {sym2}, ...]
   >
   > For each symbol:
   > 1. chart_set_symbol(sym)
   > 2. data_get_study_values()
   > 3. Find "CB Swing Labels". qualified = (qualTrend==1 AND qualAbove200==1
   >    AND qualEarnings==1). Any field missing or not 1.0 → False.
   >    If "CB Swing Labels" absent from result: Bash `sleep 2`, retry once.
   >    Still absent → False.
   > 4. After EVERY symbol, read /tmp/wl_qual_{ETF}.json (or {} if absent),
   >    merge the new result, write it back. This saves progress mid-sector.
   >
   > When done, print: "{ETF}: N qualified / M total — [list of True symbols]"

3. Wait for the agent to complete before starting the next sector.

**After all sectors complete**, merge checkpoints and cross-check coverage:

```python
import json, glob
qualified = {}
for path in sorted(glob.glob('/tmp/wl_qual_*.json')):
    qualified.update(json.load(open(path)))

with open('/tmp/wl_symbols.json') as f:
    expected = json.load(f)

missing = [s for s in expected if s not in qualified]
if missing:
    print(f'WARNING: {len(missing)} symbols missing from qualification — marking False: {missing}')
for s in missing:
    qualified[s] = False

with open('/tmp/wl_qualified.json', 'w') as f:
    json.dump(qualified, f)
print(f'Total qualified: {sum(qualified.values())} / {len(qualified)}')
```

### 4. Check options liquidity for qualified symbols
Run inline python (`Bash` with `python3 -c`):

```python
import sys, json
sys.path.insert(0, 'watchlist')
import options_check

with open('/tmp/wl_qualified.json') as f:
    qualified = json.load(f)

qualified_syms = [s for s, v in qualified.items() if v]
print(f'[options] checking {len(qualified_syms)} qualified symbols...')
options_warnings = options_check.check_options_liquidity(qualified_syms)
warned = [s for s, w in options_warnings.items() if w]
print(f'[options] {len(warned)} flagged: {warned}')

with open('/tmp/wl_options.json', 'w') as f:
    json.dump(options_warnings, f)
```

If this step errors, write `{}` to `/tmp/wl_options.json` and continue — the
warning is informational, not a gate.

### 5. Assemble the watchlist payload
Run inline python (`Bash` with `python3 -c`):

```python
import sys, json
from datetime import datetime
from zoneinfo import ZoneInfo
from dataclasses import asdict

sys.path.insert(0, 'watchlist')
from daily_qualify import assemble_watchlist_payload, write_watchlist_json, SectorBundle, Candidate

with open('/tmp/wl_qualified.json') as f:
    qualified = json.load(f)
with open('/tmp/wl_options.json') as f:
    options_warnings = json.load(f)
with open('/tmp/wl_bundles.json') as f:
    bundles_raw = json.load(f)
with open('watchlist/data/sectors.json') as f:
    sectors = json.load(f)

bundles = [
    SectorBundle(
        etf=b['etf'], tier=b['tier'],
        return_pct=b['return_pct'], spy_return_pct=b['spy_return_pct'],
        bucket=b['bucket'],
        candidates=[Candidate(symbol=c['symbol'], name=c['name']) for c in b['candidates']]
    )
    for b in bundles_raw
]

sectors_frozen_at = sectors['generated_at']
generated_at = datetime.now(ZoneInfo('America/New_York')).isoformat()

payload = assemble_watchlist_payload(bundles, qualified, sectors_frozen_at, generated_at, options_warnings)
write_watchlist_json('watchlist/data/watchlist.json', payload)
print(f'Written: watchlist/data/watchlist.json, generated_at={generated_at}')
```

### 6. Copy to docs/
`cp watchlist/data/watchlist.json docs/watchlist.json`

### 6.5. Verify the written file is fresh
Read back `docs/watchlist.json` and confirm:
- `generated_at` parses as a valid ISO 8601 timestamp.
- `generated_at` is **today's date** (America/New_York) — not a date from a
  previous run.

If either check fails, print `ERROR: watchlist.json generated_at is stale or
missing — file was not updated. Aborting commit.` to stderr and stop. Do NOT
commit or push.

### 7. Commit + push
- `cd` into the repo (already there).
- `git add docs/watchlist.json watchlist/data/watchlist.json`
- `git commit -m "watchlist: refresh $(date -u +%Y-%m-%dT%H:%MZ)"` — if the
  commit produces no changes (qualification identical to last run), skip the
  push and report "no changes".
- `git push` — only if the commit succeeded. Capture the exit code. If push
  fails, print `ERROR: git push failed (exit <code>) — watchlist written
  locally but NOT published.` to stderr.

**Report "Pushed: yes" only if `git push` exited 0. Report "Pushed: no —
commit only" if commit succeeded but push failed. Never infer push success
from the absence of errors.**

If the repo is not a git repo or has no `origin` remote yet, skip step 7 and
print clear instructions for the user to set it up.

### 8. Report to the user
Print:
- The `generated_at` timestamp **read back from the written file** (not from memory).
- Total symbols probed, how many qualified.
- Per-sector qualified counts (e.g. "SMH: ETF + 6 stocks").
- Any symbols that received the ⚠️ options warning.
- Path to the written file and "Pushed: yes/no" based on actual git exit codes.

## Style

- Treat individual ticker failures as data, not as exceptions — log and move on.
- The user expects this to run unattended overnight. Output should be quiet on
  success and loud on real failures (TV down, sectors.json missing, etc.).
