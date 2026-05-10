/* TradeSmart Watchlist — fetch + render
 *
 * Reads watchlist.json (written by the daily slash command) and renders the
 * three tiers as a dense table layout. Pure DOM, no framework.
 */

const TIER_PILL_LABELS = {
  absolute_relative: 'Strong',
  absolute:          'Positive',
  honorary:          'Honorary',
};

async function loadWatchlist() {
  try {
    // Cache-bust so refreshes pick up new pushes immediately.
    const resp = await fetch(`watchlist.json?ts=${Date.now()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (err) {
    console.error('watchlist load failed', err);
    return null;
  }
}

function fmtPct(n, withSign = true) {
  if (n == null || Number.isNaN(n)) return '—';
  const sign = withSign && n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function fmtTimestamp(iso, mode = 'long') {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (mode === 'short') {
      return d.toLocaleString('en-US', {
        month: 'short', day: 'numeric',
        hour: 'numeric', minute: '2-digit',
        timeZone: 'America/New_York',
      });
    }
    return d.toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit',
      timeZone: 'America/New_York', timeZoneName: 'short',
    });
  } catch { return iso; }
}

function makeRow({ symbol, name, isEtf, optionsWarning }) {
  const li = document.createElement('li');
  li.className = 'row' + (isEtf ? ' is-etf' : '');

  const t = document.createElement('span');
  t.className = 'cell-ticker';
  t.textContent = symbol;

  const n = document.createElement('span');
  n.className = 'cell-name';
  n.textContent = name || (isEtf ? 'Sector ETF' : '—');

  const warn = document.createElement('span');
  warn.className = 'cell-warn';
  if (optionsWarning) {
    const icon = document.createElement('span');
    icon.className = 'warn-icon';
    icon.textContent = '!';
    icon.title = 'No liquid monthly calls within 50 days (OI < 500 in the 5-ITM/2-OTM strike window)';
    warn.appendChild(icon);
  }

  const tagWrap = document.createElement('span');
  tagWrap.className = 'cell-tag';
  if (isEtf) {
    const tag = document.createElement('span');
    tag.className = 'row-tag is-etf';
    tag.textContent = 'ETF';
    tagWrap.appendChild(tag);
  }

  li.append(t, n, warn, tagWrap);
  return li;
}

function makeSection(section) {
  const tpl = document.getElementById('tpl-section').content.cloneNode(true);
  const root = tpl.querySelector('.sector');
  root.dataset.tier = section.tier;

  root.querySelector('.sector-name').textContent = section.etf;

  const pill = root.querySelector('.tier-pill');
  pill.dataset.tier = section.tier;
  pill.textContent = TIER_PILL_LABELS[section.tier] ?? section.tier;

  const perf = root.querySelector('.perf-value');
  perf.textContent = fmtPct(section.return_pct);
  if (section.return_pct < 0) perf.classList.add('is-negative');

  const diff = section.return_pct - section.spy_return_pct;
  const sign = diff >= 0 ? '+' : '';
  root.querySelector('.perf-spy').textContent = `(SPY ${sign}${diff.toFixed(2)}%)`;

  const list = root.querySelector('.row-list');
  const rows = [];
  if (section.etf_qualified) {
    rows.push({ symbol: section.etf, name: '', isEtf: true, optionsWarning: !!section.etf_options_warning });
  }
  for (const s of (section.stocks || [])) {
    rows.push({ symbol: s.symbol, name: s.name || '', isEtf: false, optionsWarning: !!s.options_warning });
  }

  if (rows.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'row-empty';
    empty.textContent = 'No qualified stocks today';
    list.appendChild(empty);
  } else {
    for (const r of rows) list.appendChild(makeRow(r));
  }

  return root;
}

function computeStats(payload) {
  const sections = [
    ...(payload.core_sectors || []),
    ...(payload.honorable_mentions || []),
  ];
  let qualifiedSectorCount = 0;
  let qualifiedStockCount = 0;
  for (const s of sections) {
    const stockCount = (s.stocks || []).length + (s.etf_qualified ? 1 : 0);
    if (stockCount > 0) qualifiedSectorCount++;
    qualifiedStockCount += stockCount;
  }
  // Pull SPY return from any section (all share the same value).
  const spyRet = sections[0]?.spy_return_pct ?? null;
  return { qualifiedSectorCount, qualifiedStockCount, spyRet };
}

function renderStats(payload) {
  const stats = computeStats(payload);
  document.getElementById('stat-sectors').textContent = stats.qualifiedSectorCount;
  document.getElementById('stat-stocks').textContent = stats.qualifiedStockCount;

  const spyEl = document.getElementById('stat-spy');
  if (stats.spyRet == null) {
    spyEl.textContent = '—';
  } else {
    spyEl.textContent = fmtPct(stats.spyRet);
    spyEl.classList.toggle('is-positive', stats.spyRet > 0);
    spyEl.classList.toggle('is-negative', stats.spyRet < 0);
    spyEl.classList.toggle('is-neutral', stats.spyRet === 0);
  }

  if (payload.lookback_bars) {
    document.getElementById('stat-lookback').textContent = `${payload.lookback_bars} bars`;
  }
}

function render(payload) {
  document.getElementById('meta-generated').textContent = fmtTimestamp(payload.generated_at, 'short');
  document.getElementById('meta-frozen').textContent    = fmtTimestamp(payload.sectors_frozen_at, 'short');

  renderStats(payload);

  const main = document.getElementById('watchlist');
  main.innerHTML = '';

  const core = payload.core_sectors ?? [];
  const honoraries = payload.honorable_mentions ?? [];

  for (const s of core)       main.appendChild(makeSection(s));
  for (const s of honoraries) main.appendChild(makeSection(s));

  if (core.length === 0 && honoraries.length === 0) {
    const p = document.createElement('p');
    p.className = 'loading';
    p.textContent = 'No sectors qualified — check back next update.';
    main.appendChild(p);
  }
}

(async () => {
  const data = await loadWatchlist();
  if (!data) {
    document.getElementById('watchlist').innerHTML =
      '<p class="loading">Watchlist not yet generated. Run <code>/update-watchlist-daily</code> from Claude Code.</p>';
    return;
  }
  render(data);
})();
