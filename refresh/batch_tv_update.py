#!/usr/bin/env python3
"""Batch update all sector layouts via the `tv` CLI.

Reads /tmp/sector_holdings_orchestrator.json (produced by orchestrator.py) and
walks each (etf, chart_url) pair end-to-end: navigate, set panes, scroll to
realtime, screenshot, save with Ctrl+S. Designed to run as one shell command
so the whole batch finishes without per-turn tool-call limits.

Pre-reqs:
  1. TradingView Desktop running with CDP on port 9222 (tv launch).
  2. orchestrator.py has been run to produce the holdings JSON.

Usage:
  python3 batch_tv_update.py                  # run all layouts
  python3 batch_tv_update.py XLB XLC XLE      # run specific ETFs
  python3 batch_tv_update.py --dry-run        # print plan, no MCP calls
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ORCHESTRATOR_JSON = Path("/tmp/sector_holdings_orchestrator.json")
TV_CLI = Path(__file__).resolve().parent.parent / "mcp-server" / "src" / "cli" / "index.js"
LOG_FILE = Path(__file__).resolve().parent / f"batch_run_{datetime.now():%Y-%m-%d_%H%M}.md"

# Holding rank (0-indexed) → pane index. Column-major: top row panes 2/4/6, bottom row 1/3/5/7.
PANE_MAP = {0: 2, 1: 4, 2: 6, 3: 1, 4: 3, 5: 5, 6: 7}

NAV_WAIT_SECS = 4.0
POST_SAVE_WAIT_SECS = 1.0


def tv(*args: str) -> dict:
    """Run a `tv` CLI command and return parsed JSON. Raises on non-zero exit."""
    cmd = ["node", str(TV_CLI), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"tv {' '.join(args)} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def navigate(chart_url: str) -> None:
    tv("ui", "eval", "--expression",
       f'window.location.href = "https://www.tradingview.com/chart/{chart_url}/"')
    time.sleep(NAV_WAIT_SECS)


def set_pane(index: int, symbol: str) -> dict:
    return tv("pane", "symbol", "--index", str(index), "--symbol", symbol)


def scroll_realtime() -> dict:
    expr = (
        "(() => {"
        " const coll = window.TradingViewApi?._chartWidgetCollection;"
        " const all = coll?.getAll?.() || [];"
        " if (all.length === 0) return { scrolled: 0, total: 0 };"
        " for (const w of all) {"
        "   const ts = w.model?.()?.timeScale?.();"
        "   if (ts?.scrollToRealtime) ts.scrollToRealtime();"
        " }"
        " return { scrolled: all.length, total: all.length };"
        "})()"
    )
    return tv("ui", "eval", "--expression", expr)


def save_chart() -> None:
    tv("ui", "keyboard", "--key", "s", "--ctrl")
    time.sleep(POST_SAVE_WAIT_SECS)


def screenshot(name: str) -> dict:
    return tv("screenshot", "--region", "chart", "--output", f"{name}_verify")


def set_layout(layout_code: str) -> dict:
    return tv("pane", "layout", "--layout", layout_code)


def unload_unused_charts() -> dict:
    return tv("ui", "eval", "--expression",
              "window._exposed_chartWidgetCollection?.unloadUnusedCharts?.(); 'ok'")


def update_layout(etf: str, chart_url: str, holdings: list[str], log) -> dict:
    """Run the full update workflow for one sector layout."""
    log.write(f"\n### {etf}\n- URL: {chart_url}\n- Holdings: {', '.join(holdings)}\n")

    navigate(chart_url)

    # Blank-pane mechanic for <7 holdings: switch to 6-chart layout, then purge hidden defs.
    short = 5 <= len(holdings) < 7
    if short:
        set_layout("6")
        time.sleep(1.0)

    for rank, ticker in enumerate(holdings):
        if rank not in PANE_MAP:
            break
        set_pane(PANE_MAP[rank], ticker)

    if short:
        unload_unused_charts()

    panes = tv("pane", "list").get("panes", [])
    log.write("- Final panes: " + ", ".join(
        f"#{p['index']}={p['symbol'].split(':')[-1]}" for p in panes
    ) + "\n")

    scroll_realtime()
    screenshot(etf)
    save_chart()

    log.write(f"- Status: saved at {datetime.now():%H:%M:%S}\n")
    log.flush()
    return {"etf": etf, "ok": True, "panes": len(panes)}


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    selected = [a for a in argv[1:] if not a.startswith("--")]

    data = json.loads(ORCHESTRATOR_JSON.read_text())
    holdings_map: dict[str, list[str]] = data["holdings_map"]
    layouts: list[tuple[str, str]] = [tuple(x) for x in data["layouts"]]

    if selected:
        layouts = [(etf, url) for etf, url in layouts if etf in selected]
        if not layouts:
            print(f"No layouts matched: {selected}", file=sys.stderr)
            return 1

    print(f"Layouts to process: {len(layouts)}")
    print(f"Log file: {LOG_FILE}")

    if dry_run:
        for etf, url in layouts:
            print(f"  {etf:6s} {url}  ->  {holdings_map.get(etf, [])}")
        return 0

    tv("status")  # fail fast if CDP is down

    results = []
    with LOG_FILE.open("w") as log:
        log.write(f"# Batch TV update — {datetime.now():%Y-%m-%d %H:%M}\n")
        log.write(f"\nLayouts: {len(layouts)}\n")

        for i, (etf, url) in enumerate(layouts, 1):
            holdings = holdings_map.get(etf, [])
            print(f"[{i}/{len(layouts)}] {etf} ...", flush=True)
            if not holdings:
                log.write(f"\n### {etf}\n- SKIPPED: no holdings\n")
                results.append({"etf": etf, "ok": False, "reason": "no holdings"})
                continue
            try:
                results.append(update_layout(etf, url, holdings, log))
            except Exception as exc:
                log.write(f"- FAILED: {exc}\n")
                results.append({"etf": etf, "ok": False, "reason": str(exc)})
                print(f"   FAILED: {exc}", file=sys.stderr)

    ok = sum(1 for r in results if r.get("ok"))
    print(f"\nDone: {ok}/{len(results)} succeeded")
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
