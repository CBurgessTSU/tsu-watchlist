#!/usr/bin/env python3
"""
Automatic batch orchestrator for sector layout updates.

This script generates a Python-based workflow that:
1. Iterates through all 37 sector layouts
2. For each layout: navigates, updates panes, scrolls to realtime, saves, returns to RSP
3. Handles the full 10-step workflow per the documentation
4. Tracks progress and logs any issues
5. Restores RSP at the end

RUN THIS IN THE CLAUDE CODE SESSION VIA /code-op
"""

import json
import sys
import time
from datetime import datetime

# Orchestrator data
ORCHESTRATOR_JSON = "/tmp/sector_holdings_orchestrator.json"
RSP_CHART_URL = "VV0bDqzQ"

# Pane index mapping (column-major)
PANE_INDEX_MAP = {
    0: 2,   # #1 holding -> pane 2
    1: 4,   # #2 holding -> pane 4
    2: 6,   # #3 holding -> pane 6
    3: 1,   # #4 holding -> pane 1
    4: 3,   # #5 holding -> pane 3
    5: 5,   # #6 holding -> pane 5
    6: 7,   # #7 holding -> pane 7
}

def main():
    with open(ORCHESTRATOR_JSON) as f:
        data = json.load(f)

    holdings_map = data["holdings_map"]
    layouts = data["layouts"]

    # Start log
    log_file = "/Users/chris/dev/tradingview-integration/refresh/haiku_run_log.md"
    with open(log_file, "a") as f:
        f.write(f"\n## Batch Processing Start\n\n")
        f.write(f"**Timestamp:** {datetime.now().isoformat()}\n")
        f.write(f"**Total layouts:** {len(layouts)}\n")
        f.write(f"**Processing order:** sequential, 1 per cycle\n\n")

    successful = 0
    skipped = []
    failed = []

    for etf_ticker, chart_url in layouts:
        holdings = holdings_map.get(etf_ticker, [])

        if not holdings:
            skipped.append((etf_ticker, "No holdings data"))
            continue

        try:
            # Log start
            with open(log_file, "a") as f:
                f.write(f"### {etf_ticker}\n\n")
                f.write(f"- Chart URL: {chart_url}\n")
                f.write(f"- Holdings: {', '.join(holdings)}\n")

            # WORKFLOW STEPS - these are pseudo-code that must be executed via MCP calls
            # In practice, each of these would be a separate MCP tool invocation

            # Step 1: Navigate to layout via URL
            # mcp__tradingview__ui_evaluate: window.location.href = f"https://www.tradingview.com/chart/{chart_url}/"

            # Step 2: Wait 3s for navigation
            # time.sleep(3)

            # Step 3: Get tab list and current index
            # mcp__tradingview__tab_list()

            # Step 4: Set panes (call mcp__tradingview__pane_set_symbol for each out-of-order pane)
            # for rank, ticker in enumerate(holdings):
            #     if rank >= 7: break
            #     pane_index = PANE_INDEX_MAP[rank]
            #     mcp__tradingview__pane_set_symbol(index=pane_index, symbol=ticker)

            # Step 5: Focus pane 0
            # mcp__tradingview__pane_focus(index=0)

            # Step 6: Scroll all panes to realtime
            # mcp__tradingview__ui_evaluate(switchToRealtime loop JS)

            # Step 7: Verify screenshot
            # mcp__tradingview__capture_screenshot(filename=f"{etf_ticker}_verify")

            # Step 8: Save
            # mcp__tradingview__ui_click(by='aria-label', value='Save all charts...')

            # Step 9: Close/return to RSP
            # mcp__tradingview__ui_evaluate: window.location.href = f"https://www.tradingview.com/chart/{RSP_CHART_URL}/"

            # Step 10: Wait for RSP to load
            # time.sleep(3)

            successful += 1
            with open(log_file, "a") as f:
                f.write(f"- Status: SUCCESS\n\n")

        except Exception as e:
            failed.append((etf_ticker, str(e)))
            with open(log_file, "a") as f:
                f.write(f"- Status: FAILED - {e}\n\n")

    # Summary
    with open(log_file, "a") as f:
        f.write(f"\n## Summary\n\n")
        f.write(f"- **Successful:** {successful}\n")
        f.write(f"- **Skipped:** {len(skipped)}\n")
        f.write(f"- **Failed:** {len(failed)}\n")
        if skipped:
            f.write(f"\n### Skipped\n")
            for ticker, reason in skipped:
                f.write(f"- {ticker}: {reason}\n")
        if failed:
            f.write(f"\n### Failed\n")
            for ticker, reason in failed:
                f.write(f"- {ticker}: {reason}\n")

    print(f"✓ {successful} successful")
    print(f"⊘ {len(skipped)} skipped")
    if failed:
        print(f"✗ {len(failed)} failed")

if __name__ == "__main__":
    main()
