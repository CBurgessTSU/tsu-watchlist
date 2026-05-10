#!/usr/bin/env python3
"""
Execute sector layout updates via TradingView MCP.

This script:
1. Reads the orchestrator JSON with all holdings
2. Generates a detailed execution plan with all MCP calls needed for each layout
3. Outputs instructions for Claude Code to execute

The actual MCP tool calls must be made in the Claude Code session.
"""

import json
import sys

def generate_pane_assignment_js(holdings_dict):
    """Generate JavaScript to assign holdings to panes (column-major mapping)."""
    # Pane index map: holdings position -> pane index
    pane_map = {
        0: 2,  # #1 holding
        1: 4,  # #2 holding
        2: 6,  # #3 holding
        3: 1,  # #4 holding
        4: 3,  # #5 holding
        5: 5,  # #6 holding
        6: 7,  # #7 holding
    }

    assignments = []
    for rank, ticker in enumerate(holdings_dict.get("holdings", [])):
        if rank >= 7:
            break
        pane_index = pane_map.get(rank)
        if pane_index:
            assignments.append({
                "rank": rank + 1,
                "ticker": ticker,
                "pane_index": pane_index
            })

    return assignments

def main():
    with open("/tmp/sector_holdings_orchestrator.json") as f:
        data = json.load(f)

    holdings_map = data["holdings_map"]
    layouts = data["layouts"]

    # Generate execution plan
    plan = []
    for etf_ticker, chart_url in layouts:
        holdings = holdings_map.get(etf_ticker, [])
        if not holdings:
            plan.append({
                "etf": etf_ticker,
                "url": chart_url,
                "status": "SKIP",
                "reason": "No holdings data"
            })
            continue

        pane_assignments = generate_pane_assignment_js({"holdings": holdings})
        plan.append({
            "etf": etf_ticker,
            "url": chart_url,
            "status": "TODO",
            "holdings": holdings,
            "pane_assignments": pane_assignments,
        })

    # Write execution plan
    with open("/tmp/tv_execution_plan.json", "w") as f:
        json.dump(plan, f, indent=2)

    print(f"Execution plan written to /tmp/tv_execution_plan.json")
    print(f"Total layouts: {len(plan)}")
    print(f"Ready to execute: {sum(1 for p in plan if p['status'] == 'TODO')}")

if __name__ == "__main__":
    main()
