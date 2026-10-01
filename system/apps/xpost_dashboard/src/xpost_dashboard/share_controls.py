"""Copy-link control and mesh-peer link rendering, shared by the mock and
the real page so both stay in sync.

The dashboard's own URL (`SHARE_LINK_HTML`'s script) is read from
`window.location.href` client-side -- genuinely real and correct on any
page it's dropped into, no mock needed, since the browser already knows
its own address.

Peer dashboard URLs are a different story: DESIGN.md section 9 in the
xpost-bridge project lists "how dashboards on different minds reach each
other" as not designed yet (repeated in section 12's open items) -- there
is no real discovery or connectivity mechanism to link to today. The mesh
links below demonstrate the intended interaction (click a peer, land on
their dashboard) using a `url` field that is `None` until something real
exists to put there; `render_peer_row` renders a peer with no url as
plain text instead of a broken/fake link.
"""

import html as _html


def render_peer_row(name: str, reachable: bool, instance_count: int | None, url: str | None) -> str:
    label = f"{instance_count} bridge{'s' if instance_count != 1 else ''} running" if reachable else "unreachable"
    css_class = "ok" if reachable else "bad"
    safe_name = _html.escape(name)
    name_html = f'<a href="{_html.escape(url)}" target="_blank" rel="noopener noreferrer">{safe_name}</a>' if url else safe_name
    return f"""
        <div class="peer">
          {name_html}
          <span class="pill {css_class}"><span class="dot"></span>{_html.escape(label)}</span>
        </div>"""


SHARE_CSS = """
  .share-link {
    display: flex; align-items: center; gap: 8px;
    font-size: 12px; color: var(--muted);
  }
  .share-link code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    background: var(--mute-bg); padding: 3px 8px; border-radius: 5px;
    max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .copy-link-btn {
    font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px;
    border: 1px solid var(--border); background: #fafafa; color: var(--text); cursor: pointer;
    flex-shrink: 0;
  }
  .copy-link-btn:hover { background: #f1f1f1; }
  .copy-link-btn.copied { color: var(--ok); border-color: var(--ok); }
  .mesh .peer a { color: var(--text); text-decoration: none; font-weight: 600; }
  .mesh .peer a:hover { text-decoration: underline; }
"""

SHARE_LINK_HTML = """
<div class="share-link">
  <code id="dashboard-url"></code>
  <button type="button" class="copy-link-btn" id="copy-link-btn">Copy link</button>
</div>
<script>
(function() {
  var urlEl = document.getElementById('dashboard-url');
  var btn = document.getElementById('copy-link-btn');
  urlEl.textContent = window.location.href;
  urlEl.title = window.location.href;
  btn.addEventListener('click', function() {
    navigator.clipboard.writeText(window.location.href).then(function() {
      var original = btn.textContent;
      btn.textContent = 'Copied';
      btn.classList.add('copied');
      setTimeout(function() { btn.textContent = original; btn.classList.remove('copied'); }, 1500);
    });
  });
})();
</script>
"""
