#!/bin/bash
set -e
cd /Users/chris/dev/tradingview-integration

/Users/chris/.local/bin/claude --model claude-sonnet-4-6 --dangerously-skip-permissions -p "/update-sectors-weekly"
/Users/chris/.local/bin/claude --model claude-sonnet-4-6 --dangerously-skip-permissions -p "/update-watchlist-daily"
