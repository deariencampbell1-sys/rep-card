"""The rep app shell — Home / Contacts / Send Card / Appts.

Four tabs, matching how field reps actually work. The send flow is lead-capture-first:
a card send is the LAST step of saving a contact, not a standalone action. Minimum to
send is a first name plus one reachable channel (phone or email).

The home screen is the real rep workspace: live card activity, contacts, and appointments.
It does not invent website-chat numbers or sell a separate product inside the app.
"""
from __future__ import annotations

from html import escape

SHELL_CSS = """
body{padding-bottom:80px}
.tabs{position:fixed;left:0;right:0;bottom:0;z-index:40;display:grid;grid-template-columns:repeat(4,1fr);
background:rgba(10,10,18,.88);border-top:1px solid var(--line);
backdrop-filter:blur(20px) saturate(160%);-webkit-backdrop-filter:blur(20px) saturate(160%);
padding-bottom:env(safe-area-inset-bottom)}
.tab{display:flex;flex-direction:column;align-items:center;gap:4px;padding:11px 0 10px;
color:var(--dim);text-decoration:none;font-size:10.5px;letter-spacing:.04em;font-weight:500}
.tab.on{color:var(--ink)}.tab.on svg{color:var(--accent)}
.stat{padding:15px 14px;border-radius:15px;background:var(--panel);border:1px solid var(--line)}
.stat .n{font-size:26px;font-weight:600;letter-spacing:-.02em;line-height:1.1}
.stat .k{font-size:11px;color:var(--dim);margin-top:4px;letter-spacing:.04em}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.bar{height:7px;border-radius:99px;background:rgba(255,255,255,.07);overflow:hidden;margin-top:7px}
.bar i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--violet))}
.panel{padding:15px;border-radius:15px;background:var(--panel);border:1px solid var(--line)}
.frow{display:flex;align-items:center;gap:11px;padding:9px 0}
.frow .lbl{font-size:13.5px;flex:1;min-width:0}
.frow .val{font-size:13.5px;font-weight:600;color:var(--dim)}
.locked{position:relative;border-radius:17px;overflow:hidden;border:1px solid var(--line);
background:var(--panel);margin-top:11px}
.locked .inner{padding:17px;filter:blur(2.6px);opacity:.40;pointer-events:none;user-select:none}
.lockover{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
justify-content:center;gap:9px;text-align:center;padding:20px;
background:linear-gradient(180deg,rgba(10,10,18,.32),rgba(10,10,18,.82))}
.spark{display:flex;align-items:flex-end;gap:4px;height:46px;margin-top:11px}
.spark i{flex:1;border-radius:3px 3px 0 0;background:linear-gradient(180deg,var(--accent),rgba(74,158,255,.25))}
.seg{display:flex;gap:7px;margin:16px 0 18px;overflow-x:auto;-webkit-overflow-scrolling:touch}
.seg a,.seg button{flex:none;padding:9px 15px;border-radius:999px;border:1px solid var(--line);
background:transparent;color:var(--dim);font-size:13px;font-family:inherit;text-decoration:none;cursor:pointer}
.seg .on{background:rgba(74,158,255,.14);border-color:rgba(74,158,255,.36);color:#78BBFF;font-weight:600}
.two{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.ava{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;flex:none;
font-size:15px;font-weight:600;background:linear-gradient(135deg,var(--accent),var(--violet))}
.cardstrip{display:flex;align-items:center;gap:12px;padding:13px;border-radius:15px;
background:var(--panel);border:1px solid var(--line);margin-bottom:20px}
.fab{position:fixed;right:18px;bottom:96px;width:56px;height:56px;border-radius:18px;z-index:35;
display:grid;place-items:center;border:0;cursor:pointer;text-decoration:none;
background:linear-gradient(135deg,var(--accent),var(--violet));box-shadow:0 10px 28px rgba(0,0,0,.5)}
.empty{text-align:center;padding:52px 20px}
.empty svg{opacity:.30;margin-bottom:16px}
.theme-toggle{position:fixed;top:14px;right:16px;z-index:50;border:1px solid var(--line);
background:var(--panel);color:var(--ink);border-radius:999px;padding:8px 11px;font:inherit;
font-size:12px;cursor:pointer;backdrop-filter:blur(14px)}
.theme-toggle:hover{border-color:var(--accent)}
html[data-theme="light"]{--bg:#F4F7F5;--panel:rgba(255,255,255,.86);--line:rgba(22,34,30,.14);
--ink:#16221E;--dim:rgba(22,34,30,.62);--accent:#2D6A4F;--violet:#1D5C73}
html[data-theme="light"] input,html[data-theme="light"] select,html[data-theme="light"] textarea{background:rgba(255,255,255,.78);color:var(--ink)}
"""

TAB_ICONS = {
    "home":  '<path d="M12 3l9 8h-2.5v9h-5v-6h-3v6h-5v-9H3z"/>',
    "cont":  '<path d="M4 3h16a1 1 0 011 1v16a1 1 0 01-1 1H4a1 1 0 01-1-1V4a1 1 0 011-1zm5 1v16h10V4zm-1.5 4h-2v2h2zm0 4h-2v2h2zm0 4h-2v2h2z"/>',
    "send":  '<path d="M3.4 20.4l17.45-7.48a1 1 0 000-1.84L3.4 3.6a.99.99 0 00-1.39.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .71.73 1.2 1.39.91z"/>',
    "appt":  '<path d="M19 3h-1V1h-2v2H8V1H6v2H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zm0 16H5V9h14zM7 11h5v5H7z"/>',
}
TABS = [("home", "/card/", "Home"), ("cont", "/card/contacts", "Contacts"),
        ("send", "/card/send", "Send Card"), ("appt", "/card/appts", "Appts")]


def tabs(active: str) -> str:
    out = []
    for key, href, label in TABS:
        on = " on" if key == active else ""
        out.append(f'<a class="tab{on}" href="{href}">'
                   f'<svg width="21" height="21" viewBox="0 0 24 24" fill="currentColor">{TAB_ICONS[key]}</svg>'
                   f'<span>{label}</span></a>')
    return f'''<button class="theme-toggle" id="theme-toggle" type="button" aria-label="Switch color mode">
  <span aria-hidden="true">◐</span> <span id="theme-label">Light</span>
</button>
<nav class="tabs">{"".join(out)}</nav>
<script>
(function () {{
  var root = document.documentElement;
  var saved = localStorage.getItem("frontman-theme") || "dark";
  root.setAttribute("data-theme", saved);
  var button = document.getElementById("theme-toggle");
  var label = document.getElementById("theme-label");
  function paint() {{ label.textContent = root.getAttribute("data-theme") === "light" ? "Dark" : "Light"; }}
  paint();
  button.addEventListener("click", function () {{
    var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
    root.setAttribute("data-theme", next);
    localStorage.setItem("frontman-theme", next);
    paint();
  }});
}}());
</script>'''


def card_strip(rep: dict, token_for_logo: str | None = None) -> str:
    """The 'this is your card' preview strip that sits above the send form."""
    initials = "".join(x[0] for x in rep["name"].split()[:2]).upper()
    logo = (f'<img src="{escape(rep["profile"]["logo_url"])}" alt="" '
            f'style="height:30px;max-width:96px;object-fit:contain">'
            if rep.get("profile", {}).get("logo_url") else
            (f'<img src="/card/img/logo/rep/{rep["id"]}" alt="" '
             f'style="height:34px;width:34px;border-radius:9px">'))
    photo = (f'<img class="ava" src="{escape(rep["photo_url"])}" alt="" style="object-fit:cover">'
             if rep.get("photo_url") else f'<div class="ava">{initials}</div>')
    return f"""<div class="cardstrip">
  {photo}
  <div style="flex:1;min-width:0">
    <div style="font-weight:600;font-size:15px">{escape(rep['name'])}</div>
    <div class="muted" style="font-size:12.5px">{escape(rep.get('title') or '')}</div>
  </div>{logo}</div>"""


def empty_state(icon_path: str, title: str, sub: str) -> str:
    return f"""<div class="empty">
  <svg width="72" height="72" viewBox="0 0 24 24" fill="var(--dim)">{icon_path}</svg>
  <p style="font-size:17px;font-weight:600">{escape(title)}</p>
  <p class="muted" style="margin-top:7px">{escape(sub)}</p></div>"""


# ── Home (the sales board) ──────────────────────────────────────────────────
def home_html(s: dict) -> str:
    def pct(n, d):
        return round(100 * n / d) if d else 0

    open_rate, eng_rate, act_rate = pct(s["opened"], s["sent"]), pct(s["engaged"], s["sent"]), pct(s["acted"], s["sent"])
    spark = "".join(f'<i style="height:{max(6, round(100*v/max(s["by_day_max"],1)))}%"></i>' for v in s["by_day"])

    hot_rows = "".join(f"""
<a href="/card/lead/{sid}" style="text-decoration:none;color:inherit">
<div class="frow" style="border-bottom:1px solid var(--line)">
  <div class="lbl">{escape(lbl)}</div>
  <div class="val" style="color:#FF5C39;font-weight:700">{sc}</div>
</div></a>""" for sid, lbl, sc in s["hot"]) or '<p class="muted">Nothing hot right now.</p>'

    leaders = "".join(f"""
<div class="frow">
  <div style="width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-size:11px;
    font-weight:700;background:linear-gradient(135deg,var(--accent),var(--violet))">{i+1}</div>
  <div class="lbl">{escape(nm)}</div><div class="val">{c} sent · {h} hot</div>
</div>""" for i, (nm, c, h) in enumerate(s["leaders"]))

    return f"""
<div class="wrap">
  <div class="eyebrow">RHOBEAR Frontman</div>
  <h1 style="margin:8px 0 5px">Frontman</h1>
  <p class="muted" style="margin-bottom:20px">Your card, contacts, and next appointments in one place.</p>

  <div class="grid2" style="margin-bottom:9px">
    <div class="stat"><div class="n">{s['sent']}</div><div class="k">Cards sent</div></div>
    <div class="stat"><div class="n">{open_rate}%</div><div class="k">Open rate</div></div>
  </div>
  <div class="grid2" style="margin-bottom:20px">
    <div class="stat"><div class="n">{s['contacts']}</div><div class="k">Contacts</div></div>
    <div class="stat"><div class="n" style="color:#FF5C39">{s['hot_count']}</div><div class="k">Hot right now</div></div>
  </div>

  <div class="sec"><h2>Last 7 days</h2>
    <div class="panel"><div class="spark">{spark}</div>
      <p class="muted" style="margin-top:10px;font-size:12px">{s['week_total']} touches this week</p></div></div>

  <div class="sec"><h2>Where they drop off</h2>
    <div class="panel">
      <div class="frow"><div class="lbl">Card sent</div><div class="val">{s['sent']}</div></div>
      <div class="bar"><i style="width:100%"></i></div>
      <div class="frow"><div class="lbl">Opened it</div><div class="val">{s['opened']} · {open_rate}%</div></div>
      <div class="bar"><i style="width:{open_rate}%"></i></div>
      <div class="frow"><div class="lbl">Read / watched</div><div class="val">{s['engaged']} · {eng_rate}%</div></div>
      <div class="bar"><i style="width:{eng_rate}%"></i></div>
      <div class="frow"><div class="lbl">Called, booked or saved</div><div class="val">{s['acted']} · {act_rate}%</div></div>
      <div class="bar"><i style="width:{act_rate}%"></i></div>
    </div></div>

  <div class="sec"><h2>Hot leads</h2><div class="panel">{hot_rows}</div></div>
  <div class="sec"><h2>Reps</h2><div class="panel">{leaders}</div></div>

</div>
{tabs('home')}"""
