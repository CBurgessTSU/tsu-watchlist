# tradingview-integration

Personal project wiring Claude Code to TradingView Desktop for analysis-only workflow automation (no trading, no scanning).

## Layout

```
.
├── .mcp.json              Project-scoped MCP config — points Claude Code at the vendored server
├── rules.json             Sector ETF list and project config (user-owned)
├── mcp-server/            Vendored upstream MCP (tradesdontlie/tradingview-mcp)
├── refresh/               Python scraper + filter for the weekly sector layout refresh
│   ├── filter.py          Stage 1: reject foreign/invalid holdings by ticker shape + name
│   └── test_filter.py     Unit tests (run: `cd refresh && python3 -m unittest test_filter -v`)
└── PROJECT.md             This file
```

## Upstream pin

- Repo: https://github.com/tradesdontlie/tradingview-mcp
- Pinned commit: `4795784` (2026-04-03)
- Update policy: manual. Review changes before bumping.

## Compat reference

Jackson fork (https://github.com/LewisWJackson/tradingview-mcp-jackson) kept as reference for TradingView Desktop v2.14+ launch compatibility fixes. Cherry-pick from there if upstream breaks on newer TV builds.

## Primary workflows

1. **Weekly sector layout rotation** — external research agent produces `{sector: [tickers]}`, this project pushes tickers into the corresponding TV layout's panes via `layout_switch` + `pane_set_symbol`.
2. **Pine Script development** — via `pine_*` tools.
3. **Ticker qualification** — `data_get_study_values` reads live indicator values to check against `rules.json` criteria.

## Explicit non-goals

- Placing trades (ever)
- Using TradingView's scanner

## Prerequisites

- TradingView Desktop launched with `--remote-debugging-port=9222 --disable-gpu-sandbox --disable-gpu` (double-click `/Applications/TradingView CDP.app` wrapper bundle, or use the `tv_launch` MCP tool)
- Claude Code restarted in this directory so `.mcp.json` loads

## Known compat patches (vs upstream `4795784`)

- **TV v2.14.0 CDP launch hang** — CDP launch hangs the chart renderer unless BOTH `--disable-gpu-sandbox` and `--disable-gpu` are passed. Patched in `mcp-server/scripts/launch_tv_debug_mac.sh` and `mcp-server/src/core/health.js` (spawn args); also baked into `/Applications/TradingView CDP.app` wrapper bundle. Re-apply if upstream is bumped.
