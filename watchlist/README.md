# Watchlist automation

Generates the public student-facing swing trading watchlist by combining a
weekly sector ranking with a nightly stock-qualification pass.

## Two cadences

| Cadence | Slash command              | Writes                          |
| ------- | -------------------------- | ------------------------------- |
| Weekly  | `/update-sectors-weekly`   | `watchlist/data/sectors.json`   |
| Daily   | `/update-watchlist-daily`  | `watchlist/data/watchlist.json` + `docs/watchlist.json` (commits + pushes) |

The weekly run freezes which **sectors** appear on the watchlist for the week.
The daily run only changes which **stocks** under each sector are currently
qualified — the sector list itself is not touched between weekly runs.

## How qualification works

Each candidate symbol (every sector ETF and its top-10 US-listed holdings) is
checked against three booleans surfaced by the **CB Swing Labels** indicator
on the daily timeframe:

| Plot           | Source in indicator       | Means                              |
| -------------- | ------------------------- | ---------------------------------- |
| `qualTrend`    | `trendState == 1`         | bullish trend                      |
| `qualAbove200` | `close > sma200`          | above 252-day SMA                  |
| `qualEarnings` | `earningsFar`             | no earnings within 2 weeks         |

A symbol is **qualified** iff all three plots equal `1`. A symbol that errors
or has no indicator data is silently dropped.

## Tier rules (weekly)

The weekly script picks 10 "core" sectors plus any number of "honorary" ones:

1. **Tier 1 — Absolute + Relative.** Up >0% AND beating SPY. Sorted by return desc.
2. **Tier 2 — Absolute.** Up >0% but ≤ SPY. Fills core slots until total = 10.
3. **Tier 3 — Honorary Mentions.** Non-core ETFs (MAGS, XMAG, BUZZ, FFTY,
   XLRE, IBB) that beat SPY. Any number — appears at the bottom of the page.

Negative-return sectors are never included. If Tier 1 + Tier 2 combined < 10
(bear tape), the page just shows fewer cards.

The set of "non-core" ETFs is configurable in `watchlist/config.json`.

## Data flow

```
                  Relative Sector Performance layout (TV)
                                  │
                /update-sectors-weekly  (Mon AM)
                                  │
                                  ▼
                       data/sectors.json   ← frozen list
                                  │
                                  ▼
       refresh/holdings.py + filter.py    (top-10 US-listed per sector)
                                  │
                                  ▼
                /update-watchlist-daily   (every evening)
                                  │
                  CB Swing Labels qualification via batch_run
                                  │
                                  ▼
                       data/watchlist.json
                                  │
                                  ▼
                       docs/watchlist.json   (page reads this)
                                  │
                                  ▼
                       git commit + push → GitHub Pages
```

## Files

```
watchlist/
  config.json                # non-core ETFs, lookback bars, target count, RSP layout name
  weekly_sectors.py          # pure-python: return calc + tiering
  daily_qualify.py           # pure-python: holdings fetch + symbol list builder
  test_weekly_sectors.py     # unit tests for tiering
  data/
    sectors.json             # frozen Mon, untouched all week
    watchlist.json           # rewritten nightly
docs/                        # GitHub Pages root
  index.html, style.css, app.js, watchlist.json
.claude/commands/
  update-sectors-weekly.md
  update-watchlist-daily.md
```

## First-time setup

1. **Indicator plots** — confirm the three hidden plots
   (`qualTrend`/`qualAbove200`/`qualEarnings`) are present on every chart's
   CB Swing Labels instance. They use `display=display.data_window` so they
   don't render visually but `data_get_study_values` can read them.

2. **GitHub Pages** — point Pages at `docs/` on the default branch:
   ```
   gh repo edit --enable-pages --pages-source docs
   ```
   (Or set it manually in repo Settings → Pages.)

3. **Run once manually** to make sure both commands work end-to-end, before
   wiring up the nightly cron.

## Nightly cron via launchd

Create `~/Library/LaunchAgents/com.tradesmart.watchlist-daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tradesmart.watchlist-daily</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-lc</string>
        <!-- Adjust path to your `claude` binary if it's not in /usr/local/bin -->
        <string>cd /Users/chris/dev/tradingview-integration && /usr/local/bin/claude -p "/update-watchlist-daily" >> /tmp/watchlist-daily.log 2>&1</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>    <integer>21</integer>
        <key>Minute</key>  <integer>30</integer>
    </dict>

    <key>StandardOutPath</key> <string>/tmp/watchlist-daily.out</string>
    <key>StandardErrorPath</key> <string>/tmp/watchlist-daily.err</string>
</dict>
</plist>
```

Load it:

```sh
launchctl load ~/Library/LaunchAgents/com.tradesmart.watchlist-daily.plist
```

For the weekly run, copy the plist to `…watchlist-weekly.plist`, change the
slash command to `/update-sectors-weekly`, and use `StartCalendarInterval` with
both `Weekday=1` (Mon) and your preferred hour. The weekly run must complete
before the same evening's daily run.

**Prerequisite for either cron:** TradingView Desktop must be open and
launched with the CDP debug flags
(`--remote-debugging-port=9222 --disable-gpu-sandbox --disable-gpu`) at the
scheduled time. If your laptop is closed/asleep, the run will fail silently —
check `/tmp/watchlist-daily.log`.

## Tests

```sh
cd /Users/chris/dev/tradingview-integration
python3 -m unittest watchlist.test_weekly_sectors -v
```
