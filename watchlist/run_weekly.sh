#!/bin/bash
# Invoked every 15 min (see plist StartInterval) while the Mac is awake, not on
# a fixed clock time. This guard makes each invocation a cheap no-op except for
# the first poll that lands on a Saturday/Sunday where the weekly run hasn't
# completed yet that week — so it fires shortly after the user starts using
# the computer over the weekend, instead of at a fixed hour that can be missed
# entirely if the Mac is asleep then.
MARKER_DIR="$HOME/Library/Application Support/tsu-watchlist"
MARKER_FILE="$MARKER_DIR/last_weekly_run"

weekday=$(date +%u)   # 1=Mon ... 6=Sat, 7=Sun
this_week=$(date +%G-W%V)

if [[ "$weekday" != "6" && "$weekday" != "7" ]]; then
    exit 0
fi

if [[ -f "$MARKER_FILE" ]] && [[ "$(cat "$MARKER_FILE")" == "$this_week" ]]; then
    exit 0
fi

set -e
cd /Users/chris/dev/tradingview-integration

/Users/chris/.local/bin/claude --model claude-sonnet-4-6 --dangerously-skip-permissions -p "/update-sectors-weekly"
/Users/chris/.local/bin/claude --model claude-sonnet-4-6 --dangerously-skip-permissions -p "/update-watchlist-daily"

mkdir -p "$MARKER_DIR"
echo "$this_week" > "$MARKER_FILE"
