"""Renders the "Recent actions" feed as a sortable, filterable grid.

Uses SlickGrid (https://github.com/6pac/SlickGrid) from a version-pinned
CDN -- no bundler in this app, so this is the vanilla/no-build integration
path the project documents (dist/browser IIFE build + SortableJS, its one
hard dependency as of v5). The exact script/CSS paths and the
DataView + header-row-filter + onSort wiring below are taken from
SlickGrid's own maintained examples (example-header-row.html,
example-multi-column-sort.html), not guessed, and were checked live
(HTTP 200) against jsdelivr before use.

`render_dashboard` (render.py) calls `render_actions_grid` with rows built
by `_action_to_grid_row`, which fixes the row shape this module expects.

Column groups, left to right: the three timestamps; classification (event
type, bridged/not-bridged outcome, detailed state); direction; the message
and its platform links (two separate columns -- a long message must not be
able to push the links off the edge of a single truncated cell, which is
exactly the bug the first version of this grid had); IDs, internal and
platform-native, last since they're the columns glanced at least often.
"""

import json
from typing import Any

from xpost_dashboard.action_states import CATEGORY_LABEL, EVENT_TYPE_LABEL, STATE_STYLE

_SLICKGRID_VERSION = "5.20.2"
_CDN_BASE = f"https://cdn.jsdelivr.net/npm/slickgrid@{_SLICKGRID_VERSION}"

GRID_HEAD = f"""
<link rel="stylesheet" href="{_CDN_BASE}/dist/styles/css/slick-alpine-theme.css">
<script src="https://cdn.jsdelivr.net/npm/sortablejs/Sortable.min.js"></script>
<script src="{_CDN_BASE}/dist/browser/slick.core.js"></script>
<script src="{_CDN_BASE}/dist/browser/slick.interactions.js"></script>
<script src="{_CDN_BASE}/dist/browser/slick.grid.js"></script>
<script src="{_CDN_BASE}/dist/browser/slick.dataview.js"></script>
"""

GRID_CSS = """
  .grid-wrap { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
  .slick-cell {
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .slick-header-column { font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em; }
  .slick-headerrow-column input, .slick-headerrow-column select {
    width: 100%; height: 100%; box-sizing: border-box;
    border: 1px solid #dadada; border-radius: 3px; font-size: 12px; padding: 0 4px;
  }
  .grid-pill {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 999px;
    white-space: nowrap;
  }
  .grid-pill.ok { color: var(--ok); background: var(--ok-bg); }
  .grid-pill.warn { color: var(--warn); background: var(--warn-bg); }
  .grid-pill.bad { color: var(--bad); background: var(--bad-bg); }
  .grid-pill.neutral { color: var(--neutral); background: var(--neutral-bg); }
  .grid-pill.muted { color: var(--muted); background: var(--mute-bg); }
  .grid-platform-tag {
    font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 4px;
  }
  .grid-platform-tag.slack { background: #ece9fc; color: #4a3aa8; }
  .grid-platform-tag.discord { background: #e8ecff; color: #3f4bc9; }
  .grid-arrow { color: var(--muted); padding: 0 3px; }
  .grid-links a { color: var(--accent); text-decoration: none; font-size: 12px; margin-right: 8px; }
  .grid-links a:hover { text-decoration: underline; }
  .grid-edited-flag { color: var(--muted); font-style: italic; }
  .grid-id { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11px; color: var(--muted); }

  .grid-toolbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 10px; background: var(--panel); border-bottom: 1px solid var(--border);
    font-size: 12px; color: var(--muted); position: relative;
  }
  .grid-columns-btn {
    font-size: 12px; font-weight: 600; padding: 5px 10px; border-radius: 6px;
    border: 1px solid var(--border); background: #fafafa; color: var(--text); cursor: pointer;
  }
  .grid-columns-btn:hover { background: #f1f1f1; }
  .grid-columns-panel {
    position: absolute; top: 36px; right: 10px; z-index: 20;
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12); padding: 8px 0; min-width: 190px;
    max-height: 320px; overflow-y: auto;
  }
  .grid-columns-panel label {
    display: flex; align-items: center; gap: 8px;
    padding: 5px 14px; font-size: 13px; color: var(--text); cursor: pointer; white-space: nowrap;
  }
  .grid-columns-panel label:hover { background: var(--bg); }
  .grid-columns-panel .grid-columns-reset {
    display: block; width: 100%; text-align: left; padding: 6px 14px; margin-top: 4px;
    border: none; border-top: 1px solid var(--border); background: none;
    font-size: 12px; color: var(--accent); cursor: pointer;
  }
"""

def _rows_to_json(rows: list[dict[str, Any]]) -> str:
    # Guard against a stray "</script>" in any field value, which would
    # otherwise terminate the script block early.
    return json.dumps(rows).replace("</", "<\\/")


def _state_style_json() -> str:
    return json.dumps({k: {"cssClass": v[0], "label": v[1]} for k, v in STATE_STYLE.items()})


def render_actions_grid(container_id: str, rows: list[dict[str, Any]]) -> str:
    """`rows` items (see render.py's `_action_to_grid_row` for how these
    are built):

    state, stateLabel, category (acted|no_action|pending), eventType
    (posted|edited|deleted), sourcePlatform, destPlatform, directionText,
    sourceUrl, destUrl, originId, sourceMessageId, sourceChannelId,
    destMessageId, destChannelId, postedAtMs, editedAtMs, seenAtMs,
    bridgedAtMs (timestamps: epoch milliseconds or null)."""
    rows_json = _rows_to_json(rows)
    state_style_json = _state_style_json()
    category_labels_json = json.dumps(CATEGORY_LABEL)
    event_type_labels_json = json.dumps(EVENT_TYPE_LABEL)
    return f"""
<div class="grid-wrap">
  <div class="grid-toolbar">
    <span>Drag a column header to reorder it.</span>
    <button type="button" class="grid-columns-btn" id="{container_id}-columns-btn">Columns &#9662;</button>
    <div class="grid-columns-panel" id="{container_id}-columns-panel" style="display:none;"></div>
  </div>
  <div id="{container_id}" style="width:100%; height:420px;"></div>
</div>
<script>
(function() {{
  const STATE_STYLE = {state_style_json};
  const CATEGORY_LABELS = {category_labels_json};
  const EVENT_TYPE_LABELS = {event_type_labels_json};
  const ROWS = {rows_json}.map(function(r, i) {{ r.id = i; return r; }});

  function escapeHtml(s) {{
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c) {{
      return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];
    }});
  }}

  function formatRelative(ms) {{
    if (ms == null) return '—';
    const seconds = Math.round((Date.now() - ms) / 1000);
    if (seconds < 0) return 'just now';
    if (seconds < 60) return seconds + 's ago';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
  }}

  function platformTag(p) {{
    if (!p) return '';
    return '<span class="grid-platform-tag ' + escapeHtml(p) + '">' + escapeHtml(p.charAt(0).toUpperCase() + p.slice(1)) + '</span>';
  }}

  function timeFormatter(row, cell, value) {{
    return '<span title="' + (value ? new Date(value).toISOString() : '') + '">' + formatRelative(value) + '</span>';
  }}

  function postedFormatter(row, cell, value, columnDef, dataContext) {{
    let html = formatRelative(value);
    if (dataContext.editedAtMs != null) {{
      html += ' <span class="grid-edited-flag" title="Edited ' + new Date(dataContext.editedAtMs).toISOString() + '">(edited ' + formatRelative(dataContext.editedAtMs) + ')</span>';
    }}
    return '<span title="' + (value ? new Date(value).toISOString() : '') + '">' + html + '</span>';
  }}

  function stateFormatter(row, cell, value, columnDef, dataContext) {{
    // field is 'stateLabel' (for readable sort/filter); look the pill style
    // up from the raw state key on the row instead of the label.
    const style = STATE_STYLE[dataContext.state] || {{cssClass: 'warn', label: value}};
    return '<span class="grid-pill ' + style.cssClass + '">' + escapeHtml(style.label) + '</span>';
  }}

  const CATEGORY_PILL_CLASS = {{acted: 'ok', no_action: 'muted', pending: 'neutral'}};
  function categoryFormatter(row, cell, value, columnDef, dataContext) {{
    // field is 'categoryLabel' (for the filter dropdown's exact-match
    // against a readable value); style comes from the raw 'category' key.
    const cls = CATEGORY_PILL_CLASS[dataContext.category] || 'warn';
    return '<span class="grid-pill ' + cls + '">' + escapeHtml(value) + '</span>';
  }}

  function eventTypeFormatter(row, cell, value) {{
    // field is 'eventTypeLabel', same reasoning as categoryLabel above.
    return escapeHtml(value || '');
  }}

  function directionFormatter(row, cell, value, columnDef, dataContext) {{
    const src = platformTag(dataContext.sourcePlatform);
    const dst = dataContext.destPlatform ? platformTag(dataContext.destPlatform) : '';
    return dst ? src + '<span class="grid-arrow">&rarr;</span>' + dst : src;
  }}

  function linksFormatter(row, cell, value, columnDef, dataContext) {{
    // Links only, deliberately -- no message text lives in this contract
    // (the bridge itself keeps user message content out of anything it
    // writes to disk or logs at info level; the dashboard matches that).
    const links = [];
    if (dataContext.sourceUrl) {{
      links.push('<a href="' + escapeHtml(dataContext.sourceUrl) + '">' + escapeHtml((dataContext.sourcePlatform || '').replace(/^./, c => c.toUpperCase())) + ' &rarr;</a>');
    }}
    if (dataContext.destUrl) {{
      links.push('<a href="' + escapeHtml(dataContext.destUrl) + '">' + escapeHtml((dataContext.destPlatform || '').replace(/^./, c => c.toUpperCase())) + ' &rarr;</a>');
    }}
    return links.length ? '<span class="grid-links">' + links.join(' ') + '</span>' : '';
  }}

  function idFormatter(row, cell, value) {{
    if (!value) return '';
    return '<span class="grid-id" title="' + escapeHtml(value) + '">' + escapeHtml(value) + '</span>';
  }}

  const ALL_COLUMNS = [
    {{ id: 'seenAtMs', name: 'Seen', field: 'seenAtMs', width: 80, sortable: true, formatter: timeFormatter, filterable: false }},
    {{ id: 'postedAtMs', name: 'Posted', field: 'postedAtMs', width: 140, sortable: true, formatter: postedFormatter, filterable: false }},
    {{ id: 'bridgedAtMs', name: 'Bridged', field: 'bridgedAtMs', width: 80, sortable: true, formatter: timeFormatter, filterable: false }},
    {{ id: 'eventTypeLabel', name: 'Type', field: 'eventTypeLabel', width: 80, sortable: true, formatter: eventTypeFormatter,
       filterType: 'select', filterOptions: Object.values(EVENT_TYPE_LABELS) }},
    {{ id: 'categoryLabel', name: 'Action taken', field: 'categoryLabel', width: 110, sortable: true, formatter: categoryFormatter,
       filterType: 'select', filterOptions: Object.values(CATEGORY_LABELS) }},
    {{ id: 'stateLabel', name: 'State', field: 'stateLabel', width: 170, sortable: true, formatter: stateFormatter,
       filterType: 'select', filterOptions: Object.values(STATE_STYLE).map(function(s) {{ return s.label; }}) }},
    {{ id: 'directionText', name: 'Direction', field: 'directionText', width: 130, sortable: true, formatter: directionFormatter }},
    {{ id: 'links', name: 'Links', field: 'links', width: 220, sortable: false, formatter: linksFormatter, filterable: false }},
    {{ id: 'originId', name: 'Origin ID', field: 'originId', width: 200, sortable: true, formatter: idFormatter }},
    {{ id: 'sourceMessageId', name: 'Source msg ID', field: 'sourceMessageId', width: 140, sortable: true, formatter: idFormatter }},
    {{ id: 'destMessageId', name: 'Dest msg ID', field: 'destMessageId', width: 140, sortable: true, formatter: idFormatter }},
  ];
  const ALL_COLUMN_IDS = ALL_COLUMNS.map(function(c) {{ return c.id; }});
  const COLUMN_BY_ID = {{}};
  ALL_COLUMNS.forEach(function(c) {{ COLUMN_BY_ID[c.id] = c; }});

  // Column order + which are hidden persist per-grid (mock vs. real page
  // have separate keys via container_id) across reloads, since re-doing
  // this setup every visit is exactly the busywork a saved layout avoids.
  const STORAGE_KEY = 'xpost-dashboard-grid-columns-{container_id}';
  function loadColumnState() {{
    try {{
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (!parsed || !Array.isArray(parsed.order) || !Array.isArray(parsed.hidden)) return null;
      return parsed;
    }} catch (e) {{ return null; }}
  }}
  function saveColumnState() {{
    try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify({{order: columnOrder, hidden: Array.from(hiddenIds)}})); }} catch (e) {{}}
  }}

  const saved = loadColumnState();
  let columnOrder = (saved ? saved.order.filter(function(id) {{ return ALL_COLUMN_IDS.indexOf(id) !== -1; }}) : ALL_COLUMN_IDS.slice());
  ALL_COLUMN_IDS.forEach(function(id) {{ if (columnOrder.indexOf(id) === -1) columnOrder.push(id); }});
  let hiddenIds = new Set(saved ? saved.hidden.filter(function(id) {{ return ALL_COLUMN_IDS.indexOf(id) !== -1; }}) : []);

  function currentColumns() {{
    return columnOrder.filter(function(id) {{ return !hiddenIds.has(id); }}).map(function(id) {{ return COLUMN_BY_ID[id]; }});
  }}

  const options = {{
    enableCellNavigation: true,
    enableColumnReorder: true,
    showHeaderRow: true,
    headerRowHeight: 28,
    multiColumnSort: false,
    explicitInitialization: true,
    // Off, not on: with up to twelve columns, squeezing them all into the
    // viewport (what forceFitColumns does) makes every one unreadably
    // narrow. Fixed widths plus horizontal scroll keeps each column
    // legible -- the standard tradeoff for a wide data grid.
    forceFitColumns: false,
  }};

  const dataView = new Slick.Data.DataView();
  const grid = new Slick.Grid('#{container_id}', dataView, currentColumns(), options);

  const columnFilters = {{}};
  function passesFilter(item) {{
    for (const columnId in columnFilters) {{
      const needle = columnFilters[columnId];
      if (!needle) continue;
      const col = grid.getColumns()[grid.getColumnIndex(columnId)];
      if (!col) continue;
      const value = item[col.field] == null ? '' : String(item[col.field]);
      if (col.filterType === 'select') {{
        if (value !== needle) return false;
      }} else if (value.toLowerCase().indexOf(needle.toLowerCase()) === -1) {{
        return false;
      }}
    }}
    return true;
  }}

  dataView.onRowCountChanged.subscribe(function() {{ grid.updateRowCount(); grid.render(); }});
  dataView.onRowsChanged.subscribe(function(e, args) {{ grid.invalidateRows(args.rows); grid.render(); }});

  grid.onSort.subscribe(function(e, args) {{
    const field = args.sortCol.field;
    const sign = args.sortAsc ? 1 : -1;
    dataView.sort(function(a, b) {{
      const x = a[field], y = b[field];
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x > y ? 1 : x < y ? -1 : 0) * sign;
    }}, args.sortAsc);
  }});

  grid.onHeaderRowCellRendered.subscribe(function(e, args) {{
    if (args.column.filterable === false) return;
    args.node.innerHTML = '';
    if (args.column.filterType === 'select') {{
      const select = document.createElement('select');
      const optAll = document.createElement('option');
      optAll.value = '';
      optAll.textContent = 'All';
      select.appendChild(optAll);
      (args.column.filterOptions || []).forEach(function(label) {{
        const opt = document.createElement('option');
        opt.value = label;
        opt.textContent = label;
        select.appendChild(opt);
      }});
      select.value = columnFilters[args.column.id] || '';
      select.dataset.columnid = args.column.id;
      args.node.appendChild(select);
    }} else {{
      const input = document.createElement('input');
      input.placeholder = 'filter';
      input.dataset.columnid = args.column.id;
      input.value = columnFilters[args.column.id] || '';
      args.node.appendChild(input);
    }}
  }});

  grid.init();
  const headerRowElm = grid.getHeaderRow();
  function onFilterChange(e) {{
    const columnId = e.target.dataset.columnid;
    if (columnId != null) {{
      columnFilters[columnId] = e.target.tagName === 'SELECT' ? e.target.value : (e.target.value || '').trim();
      dataView.refresh();
    }}
  }}
  headerRowElm.addEventListener('input', onFilterChange);
  headerRowElm.addEventListener('change', onFilterChange);

  grid.onColumnsReordered.subscribe(function() {{
    // grid.getColumns() only reflects the currently-visible subset in
    // their new order; keep hidden ids appended after them, in whatever
    // relative order they already had, rather than dropping them.
    const newVisibleOrder = grid.getColumns().map(function(c) {{ return c.id; }});
    columnOrder = newVisibleOrder.concat(columnOrder.filter(function(id) {{ return hiddenIds.has(id); }}));
    saveColumnState();
  }});

  // "Columns" picker: a plain checkbox panel (not SlickGrid's own
  // ColumnPicker control) so it matches this app's own look instead of
  // SlickGrid's default styling, and so hiding the last visible column is
  // easy to refuse outright rather than leaving an empty grid.
  const columnsBtn = document.getElementById('{container_id}-columns-btn');
  const columnsPanel = document.getElementById('{container_id}-columns-panel');

  function renderColumnsPanel() {{
    columnsPanel.innerHTML = '';
    columnOrder.forEach(function(id) {{
      const col = COLUMN_BY_ID[id];
      const label = document.createElement('label');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = !hiddenIds.has(id);
      checkbox.addEventListener('change', function() {{
        if (!checkbox.checked && hiddenIds.size >= ALL_COLUMN_IDS.length - 1) {{
          checkbox.checked = true; // refuse hiding the last visible column
          return;
        }}
        if (checkbox.checked) {{
          hiddenIds.delete(id);
        }} else {{
          hiddenIds.add(id);
          delete columnFilters[id]; // a hidden column's filter can't be seen or cleared, so drop it
        }}
        grid.setColumns(currentColumns());
        saveColumnState();
        dataView.refresh();
      }});
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(col.name));
      columnsPanel.appendChild(label);
    }});
    const reset = document.createElement('button');
    reset.type = 'button';
    reset.className = 'grid-columns-reset';
    reset.textContent = 'Show all columns, default order';
    reset.addEventListener('click', function() {{
      columnOrder = ALL_COLUMN_IDS.slice();
      hiddenIds = new Set();
      for (const id in columnFilters) delete columnFilters[id];
      grid.setColumns(currentColumns());
      saveColumnState();
      dataView.refresh();
      renderColumnsPanel();
    }});
    columnsPanel.appendChild(reset);
  }}
  renderColumnsPanel();

  columnsBtn.addEventListener('click', function(e) {{
    e.stopPropagation();
    columnsPanel.style.display = columnsPanel.style.display === 'none' ? 'block' : 'none';
  }});
  document.addEventListener('click', function(e) {{
    if (columnsPanel.style.display !== 'none' && !columnsPanel.contains(e.target) && e.target !== columnsBtn) {{
      columnsPanel.style.display = 'none';
    }}
  }});

  dataView.beginUpdate();
  dataView.setItems(ROWS);
  dataView.setFilter(passesFilter);
  // Default view order: most recently seen first.
  dataView.sort(function(a, b) {{ return (a.seenAtMs || 0) - (b.seenAtMs || 0); }}, false);
  dataView.endUpdate();
}})();
</script>
"""
