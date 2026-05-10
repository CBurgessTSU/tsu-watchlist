#!/usr/bin/env python3
"""
Sector layout update resume helper.

Usage:
  python3 resume.py            → print status + next pending layouts as JSON
  python3 resume.py done XLB   → mark XLB as completed
  python3 resume.py fail XLB   → mark XLB as failed (with optional reason)
"""

import json
import sys
from datetime import datetime

ORCHESTRATOR_JSON = "/tmp/sector_holdings_orchestrator.json"
PROGRESS_JSON = "/tmp/sector_progress.json"
SKIP = {"MAGS"}  # always skip — manually curated


def load_progress():
    try:
        with open(PROGRESS_JSON) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"completed": [], "failed": []}


def save_progress(progress):
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_JSON, "w") as f:
        json.dump(progress, f, indent=2)


def main():
    with open(ORCHESTRATOR_JSON) as f:
        data = json.load(f)

    progress = load_progress()

    # Handle mark-done / mark-fail subcommands
    if len(sys.argv) >= 3:
        cmd, etf = sys.argv[1], sys.argv[2].upper()
        if cmd == "done":
            if etf not in progress["completed"]:
                progress["completed"].append(etf)
            progress["failed"] = [f for f in progress["failed"] if f != etf]
            save_progress(progress)
            print(f"Marked {etf} as completed.")
        elif cmd == "fail":
            reason = sys.argv[3] if len(sys.argv) > 3 else "unknown"
            if etf not in progress["failed"]:
                progress["failed"].append(etf)
            save_progress(progress)
            print(f"Marked {etf} as failed: {reason}")
        return

    # Status report
    completed = set(progress["completed"])
    failed = set(progress["failed"])
    holdings_map = data["holdings_map"]

    all_layouts = [(etf, url) for etf, url in data["layouts"] if etf not in SKIP]
    pending = [(etf, url) for etf, url in all_layouts if etf not in completed]

    if not pending:
        print(json.dumps({
            "status": "ALL_DONE",
            "completed": len(completed),
            "failed": list(failed),
        }, indent=2))
        return

    pane_map = {0: 2, 1: 4, 2: 6, 3: 1, 4: 3, 5: 5, 6: 7}

    next_layouts = []
    for etf, url in pending:
        holdings = holdings_map.get(etf, [])
        panes = [
            {"pane_index": pane_map[i], "symbol": h}
            for i, h in enumerate(holdings[:7])
        ]
        next_layouts.append({
            "etf": etf,
            "chart_url": url,
            "holdings": holdings,
            "pane_assignments": panes,
        })

    print(json.dumps({
        "status": "PENDING",
        "completed": len(completed),
        "remaining": len(pending),
        "failed": list(failed),
        "pending_layouts": next_layouts,
    }, indent=2))


if __name__ == "__main__":
    main()
