"""Card page rendering — the prospect-facing surface.

Split out of app.py because this is the part that actually sells; it deserves to be read.
Every interactive element reports a distinct event kind so the heat score reflects
what the prospect DID, not just that they opened it.
"""
from __future__ import annotations

from html import escape


# ── inline SVG art ──────────────────────────────────────────────────────────
# Self-contained on purpose: no hotlinking, nothing to 404, no external host to
# trust. A real deployment swaps these for the tenant's uploaded assets.

def cover_svg(a: str, b: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 320" preserveAspectRatio="xMidYMid slice">'
            f'<defs><linearGradient id="c" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
            f'<linearGradient id="s" x1="0" y1="1" x2="0" y2="0">'
            f'<stop offset="0" stop-color="#0A0A12" stop-opacity=".85"/>'
            f'<stop offset="1" stop-color="#0A0A12" stop-opacity="0"/></linearGradient></defs>'
            f'<rect width="800" height="320" fill="url(#c)"/>'
            f'<g fill="#fff" opacity=".13">'
            f'<path d="M0 250 L150 150 L260 220 L400 110 L540 200 L680 120 L800 190 L800 320 L0 320Z"/></g>'
            f'<g fill="#fff" opacity=".07">'
            f'<path d="M0 285 L120 215 L250 270 L390 190 L520 255 L660 195 L800 245 L800 320 L0 320Z"/></g>'
            f'<g opacity=".22" fill="#fff"><circle cx="662" cy="72" r="30"/></g>'
            f'<rect width="800" height="320" fill="url(#s)"/></svg>')


def logo_svg(company: str, a: str, b: str) -> str:
    """Generated brand mark used when the tenant hasn't uploaded a logo yet.
    A real deployment replaces this with profile['logo_url']."""
    words = [w for w in company.split() if w]
    mono = "".join(w[0] for w in words[:2]).upper() or "R"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
            f'<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'
            f'<rect width="120" height="120" rx="28" fill="url(#lg)"/>'
            f'<path d="M28 84 L52 44 L70 74 L82 54 L96 84 Z" fill="#fff" opacity=".22"/>'
            f'<text x="60" y="74" font-family="system-ui,-apple-system,sans-serif" font-size="42" '
            f'font-weight="700" fill="#fff" text-anchor="middle" letter-spacing="-1">{mono}</text></svg>')


def shot_svg(a: str, b: str, label: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'
            f'<rect width="400" height="300" fill="url(#g)"/>'
            f'<g fill="#0A0A12" opacity=".30">'
            f'<path d="M0 214 L96 150 L170 196 L248 128 L330 182 L400 142 L400 300 L0 300Z"/></g>'
            f'<g fill="#fff" opacity=".18"><rect x="60" y="96" width="122" height="72" rx="6"/>'
            f'<rect x="196" y="118" width="104" height="50" rx="6"/></g>'
            f'<text x="200" y="272" font-family="system-ui,sans-serif" font-size="17" font-weight="600" '
            f'fill="#fff" opacity=".92" text-anchor="middle">{escape(label)}</text></svg>')


def stars(rating: float, size: int = 15) -> str:
    full = int(rating)
    half = (rating - full) >= 0.5
    out = []
    for i in range(5):
        fill = "#FFB84A" if i < full else ("url(#half)" if i == full and half else "rgba(255,255,255,.20)")
        out.append(f'<path fill="{fill}" d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 17.8 5.8 21.1 7 14.2 2 9.3l6.9-1z"/>')
    return (f'<svg width="{size*5+8}" height="{size}" viewBox="0 0 {24*5} 24" style="vertical-align:-2px">'
            f'<defs><linearGradient id="half"><stop offset="50%" stop-color="#FFB84A"/>'
            f'<stop offset="50%" stop-color="rgba(255,255,255,.20)"/></linearGradient></defs>'
            + "".join(f'<g transform="translate({i*24},0)">{s}</g>' for i, s in enumerate(out))
            + "</svg>")


# ── social glyphs (licensed-free simple paths, per PREMIUM-UI-LAW: no icon-font defaults) ──
GLYPH = {
    "website":  '<path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 2c1.7 0 3.4 3 3.4 8S13.7 20 12 20s-3.4-3-3.4-8S10.3 4 12 4zM4.3 9h3.2a22 22 0 000 6H4.3a8 8 0 010-6zm12.2 0h3.2a8 8 0 010 6h-3.2a22 22 0 000-6z"/>',
    "facebook": '<path d="M13.5 22v-8h2.7l.4-3.1h-3.1V8.9c0-.9.25-1.5 1.55-1.5h1.65V4.6c-.29-.04-1.27-.13-2.41-.13-2.39 0-4.03 1.46-4.03 4.14v2.29H7.5V14h2.76v8z"/>',
    "instagram":'<path d="M12 2.2c3.2 0 3.58.01 4.85.07 3.25.15 4.77 1.69 4.92 4.92.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.15 3.23-1.66 4.77-4.92 4.92-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-3.26-.15-4.77-1.7-4.92-4.92C2.21 15.58 2.2 15.2 2.2 12s.01-3.58.07-4.85C2.42 3.92 3.93 2.38 7.15 2.27 8.42 2.21 8.8 2.2 12 2.2zm0 5.13a4.67 4.67 0 100 9.34 4.67 4.67 0 000-9.34zm0 7.7a3.03 3.03 0 110-6.06 3.03 3.03 0 010 6.06zm4.85-7.88a1.09 1.09 0 100-2.18 1.09 1.09 0 000 2.18z"/>',
    "linkedin": '<path d="M6.94 5a2 2 0 11-4 0 2 2 0 014 0zM3.2 8.5h3.5V22H3.2zM9.5 8.5H13v1.85h.05c.49-.92 1.68-1.9 3.45-1.9 3.7 0 4.38 2.43 4.38 5.6V22h-3.5v-5.25c0-1.25-.02-2.86-1.75-2.86-1.75 0-2.02 1.36-2.02 2.77V22H9.5z"/>',
    "youtube":  '<path d="M21.6 7.2s-.2-1.4-.8-2c-.75-.8-1.6-.8-2-.85C16 4.2 12 4.2 12 4.2h-.01s-4 0-6.8.2c-.4.05-1.25.05-2 .85-.6.6-.8 2-.8 2S2.2 8.8 2.2 10.5v1.6c0 1.65.2 3.3.2 3.3s.2 1.4.8 2c.75.8 1.75.78 2.2.86 1.6.15 6.8.2 6.8.2s4 0 6.8-.21c.4-.05 1.25-.05 2-.85.6-.6.8-2 .8-2s.2-1.65.2-3.3v-1.6c0-1.65-.2-3.3-.2-3.3zM9.9 14.6V8.9l5.15 2.86z"/>',
    "google":   '<path d="M21.35 11.1H12v2.9h5.35c-.25 1.5-1.85 4.4-5.35 4.4a5.9 5.9 0 110-11.8c1.7 0 2.85.72 3.5 1.35l2.4-2.3C16.4 4.2 14.4 3.3 12 3.3a8.7 8.7 0 100 17.4c5.02 0 8.35-3.53 8.35-8.5 0-.57-.06-1-.15-1.4z"/>',
    "quote":    '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zm-1 7V3.5L18.5 9zM8 13h8v2H8zm0 4h8v2H8zm0-8h3v2H8z"/>',
    "phone":    '<path d="M6.6 10.8a15.1 15.1 0 006.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.2.4 2.4.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 013 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.4 0 .8-.2 1z"/>',
    "financing":'<path d="M12 1l9 4v6c0 5-3.8 9.7-9 11-5.2-1.3-9-6-9-11V5zm0 4.8L7 8v3.2c0 3.2 2.1 6.2 5 7.2 2.9-1 5-4 5-7.2V8z"/>',
}


def icon(name: str, size: int = 19, colour: str = "currentColor") -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="{colour}" '
            f'aria-hidden="true">{GLYPH.get(name, GLYPH["website"])}</svg>')


CARD_CSS = """
.cover{position:relative;margin:-24px -18px 0;height:168px;overflow:hidden}
.cover svg{width:100%;height:100%;display:block}
.logochip{position:absolute;top:14px;right:14px;display:flex;align-items:center;gap:8px;
padding:7px 12px;border-radius:999px;background:rgba(10,10,18,.55);border:1px solid rgba(255,255,255,.16);
backdrop-filter:blur(10px);font-size:12px;font-weight:600;letter-spacing:.02em}
.ident{margin-top:-46px;padding:0 4px;text-align:center;position:relative}
.avatar{width:96px;height:96px;border-radius:50%;display:grid;place-items:center;margin:0 auto 12px;
font-size:33px;font-weight:600;border:3px solid #0A0A12;box-shadow:0 8px 26px rgba(0,0,0,.5);object-fit:cover}
.badge{display:inline-flex;align-items:center;gap:5px;font-size:10.5px;font-weight:700;letter-spacing:.10em;
padding:4px 9px;border-radius:6px;background:rgba(74,158,255,.14);color:#78BBFF;
border:1px solid rgba(74,158,255,.30);margin-top:9px}
.sec{margin-top:20px}
.sec h2{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim);
margin-bottom:11px;font-weight:600}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.qa{display:flex;flex-direction:column;align-items:center;gap:6px;padding:13px 4px;border-radius:14px;
background:var(--panel);border:1px solid var(--line);color:var(--ink);text-decoration:none;
font-size:11.5px;font-weight:500}
.qa:active{background:rgba(255,255,255,.09)}
.linkrow{display:flex;align-items:center;gap:12px;padding:14px 15px;border-radius:14px;
background:var(--panel);border:1px solid var(--line);color:var(--ink);text-decoration:none;margin-bottom:8px}
.linkrow .chev{margin-left:auto;opacity:.4}
.socials{display:flex;gap:9px;flex-wrap:wrap}
.soc{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;
background:var(--panel);border:1px solid var(--line);color:var(--ink);text-decoration:none}
.gal{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.gal a{border-radius:13px;overflow:hidden;border:1px solid var(--line);display:block;line-height:0}
.gal a:first-child{grid-column:1/-1}
.gal svg{width:100%;height:100%;display:block}
.vid{position:relative;border-radius:15px;overflow:hidden;border:1px solid var(--line);line-height:0}
.vid video{width:100%;display:block;background:#000}
.rev{padding:15px;border-radius:14px;background:var(--panel);border:1px solid var(--line);margin-bottom:9px}
.chips{display:flex;flex-wrap:wrap;gap:7px}
.chip{font-size:12.5px;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.05);
border:1px solid var(--line);color:var(--dim)}
"""

CHEV = '<svg class="chev" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M9 6l6 6-6 6"/></svg>'


def render_card(token: str, rep: dict, base: str) -> tuple[str, str]:
    """-> (head_meta, body_html)"""
    p = rep.get("profile") or {}
    name = rep["name"]
    accent = rep.get("accent") or "#4A9EFF"
    accent2 = p.get("accent2", "#7B3FD4")
    company = rep.get("company") or ""
    photo = rep.get("photo_url")
    initials = "".join(x[0] for x in name.split()[:2]).upper()

    avatar = (f'<img class="avatar" src="{escape(photo)}" alt="{escape(name)}">' if photo else
              f'<div class="avatar" style="background:linear-gradient(135deg,{accent},{accent2})">{initials}</div>')

    rating = float(rep.get("rating") or 0)
    nrev = int(rep.get("reviews") or 0)
    rating_html = (f'<div style="margin-top:10px">{stars(rating)}'
                   f'<span class="muted" style="margin-left:8px">{rating} · {nrev} reviews</span></div>'
                   if nrev else "")

    def A(kind, href, cls, inner, target=False):
        t = ' target="_blank" rel="noopener"' if target else ""
        return f'<a class="{cls}" href="{escape(href)}"{t} onclick="hit(\'{kind}\')">{inner}</a>'

    # quick actions
    qa = []
    if rep.get("phone"):
        qa.append(A("tap_call", f'tel:{rep["phone"]}', "qa", f'{icon("phone")}<span>Call</span>'))
    if rep.get("phone"):
        qa.append(A("tap_text", f'sms:{rep["phone"]}', "qa", '<svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H4a2 2 0 00-2 2v18l4-4h14a2 2 0 002-2V4a2 2 0 00-2-2z"/></svg><span>Text</span>'))
    if rep.get("email"):
        qa.append(A("tap_email", f'mailto:{rep["email"]}', "qa", '<svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor"><path d="M20 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V6a2 2 0 00-2-2zm0 4l-8 5-8-5V6l8 5 8-5z"/></svg><span>Email</span>'))
    qa.append(A("tap_save", f'/c/{token}/vcf', "qa", '<svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor"><path d="M17 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V7zm-5 16a3 3 0 110-6 3 3 0 010 6zm3-10H6V5h9z"/></svg><span>Save</span>'))

    book = (f'<div class="sec">{A("tap_book", p["book_url"], "btn", "Book a time with " + escape(name.split()[0]), True)}</div>'
            if p.get("book_url") else "")

    video = ""
    if p.get("video"):
        video = f"""<div class="sec"><h2>Watch first — 40 seconds</h2>
<div class="vid"><video controls preload="metadata" playsinline poster="/card/img/poster/{token}"
 onplay="hit('tap_video')"><source src="{escape(p['video'])}" type="video/mp4"></video></div></div>"""

    services = ""
    if p.get("services"):
        services = ('<div class="sec"><h2>What I do</h2><div class="chips">'
                    + "".join(f'<span class="chip">{escape(s)}</span>' for s in p["services"])
                    + "</div></div>")

    gallery = ""
    if p.get("gallery"):
        cells = "".join(
            f'<a href="/card/img/shot/{token}/{i}" onclick="hit(\'tap_gallery\')" target="_blank" rel="noopener">'
            f'{shot_svg(g.get("a", accent), g.get("b", accent2), g.get("label", ""))}</a>'
            for i, g in enumerate(p["gallery"]))
        gallery = f'<div class="sec"><h2>Recent work</h2><div class="gal">{cells}</div></div>'

    reviews = ""
    if p.get("review_list"):
        items = "".join(
            f'<div class="rev">{stars(float(r.get("stars", 5)), 13)}'
            f'<p style="margin-top:9px;font-size:14px;line-height:1.55">{escape(r["text"])}</p>'
            f'<p class="muted" style="margin-top:8px;font-size:12px">— {escape(r["who"])}</p></div>'
            for r in p["review_list"])
        reviews = f'<div class="sec"><h2>What customers say</h2>{items}</div>'

    links = ""
    if p.get("links"):
        rows = "".join(
            A(l.get("kind", "tap_link"), l["url"], "linkrow",
              f'{icon(l.get("icon", "website"))}<span>{escape(l["label"])}</span>{CHEV}', True)
            for l in p["links"])
        links = f'<div class="sec"><h2>Links</h2>{rows}</div>'

    socials = ""
    if p.get("socials"):
        cells = "".join(
            A("tap_social", s["url"], "soc", icon(s["icon"], 20), True) for s in p["socials"])
        socials = f'<div class="sec"><h2>Follow</h2><div class="socials">{cells}</div></div>'

    referral = f"""<div class="sec">
  <div class="glass" style="padding:18px;text-align:center">
    <p style="font-size:15px;font-weight:600">Know someone who needs this?</p>
    <p class="muted" style="margin:7px 0 14px">Pass my card along — it takes one tap.</p>
    <button class="btn ghost" onclick="shareCard()">Share this card</button>
  </div></div>"""

    logo_url = p.get("logo_url")
    logo_mark = (f'<img src="{escape(logo_url)}" alt="{escape(company)} logo" '
                 f'style="width:22px;height:22px;border-radius:6px;object-fit:contain">'
                 if logo_url else
                 f'<span style="width:22px;height:22px;border-radius:6px;overflow:hidden;'
                 f'display:inline-block;line-height:0">'
                 f'<img src="/card/img/logo/{token}" alt="{escape(company)} logo" '
                 f'style="width:100%;height:100%;display:block"></span>')

    head = (f'<meta property="og:title" content="{escape(name)} — {escape(company)}">'
            f'<meta property="og:description" content="{escape(p.get("og_desc") or rep.get("title") or "Tap to save my card")}">'
            f'<meta property="og:type" content="profile">'
            f'<meta property="og:url" content="{base}/c/{token}">'
            f'<meta property="og:image" content="{base}/card/img/cover/{token}">'
            f'<meta name="twitter:card" content="summary_large_image">'
            f'<style>{CARD_CSS}</style>')

    body = f"""
<div class="wrap">
  <div class="cover">{cover_svg(accent, accent2)}
    <div class="logochip">{logo_mark}<span>{escape(company)}</span></div>
  </div>

  <div class="ident">
    {avatar}
    <h1>{escape(name)}</h1>
    <p class="muted" style="margin-top:5px">{escape(rep.get('title') or '')}{' · ' + escape(rep['location']) if rep.get('location') else ''}</p>
    {rating_html}
    {f'<div class="badge">{escape(p["badge"])}</div>' if p.get("badge") else ''}
  </div>

  {book}
  <div class="sec"><div class="grid4">{''.join(qa)}</div></div>
  {f'<div class="sec"><h2>About</h2><p class="muted" style="font-size:14.5px">{escape(rep.get("blurb") or "")}</p></div>' if rep.get("blurb") else ''}
  {video}{services}{gallery}{reviews}{links}{socials}{referral}

  <p class="muted" style="text-align:center;margin-top:24px;font-size:11px;opacity:.6;line-height:1.6">
    This card lets {escape(company or name)} see when it's opened so they know to follow up.<br>
    No account needed. Nothing is shared with anyone else.</p>
</div>
<script>
const T={token!r};
function beacon(k,m){{try{{navigator.sendBeacon('/card/e',
  new Blob([JSON.stringify({{t:T,kind:k,meta:m||''}})],{{type:'application/json'}}));}}catch(e){{}}}}
function hit(k){{beacon(k);}}
async function shareCard(){{
  hit('tap_share');
  const url=location.href, title={name!r}+" — {company}";
  if(navigator.share){{try{{await navigator.share({{title:title,url:url}});}}catch(e){{}}}}
  else{{try{{await navigator.clipboard.writeText(url);alert('Card link copied.');}}catch(e){{prompt('Copy this link:',url);}}}}
}}
let deep=false;
addEventListener('scroll',()=>{{if(!deep&&(scrollY+innerHeight)>document.body.scrollHeight-80)
  {{deep=true;beacon('scroll','bottom');}}}},{{passive:true}});
setTimeout(()=>beacon('dwell','15s'),15000);
setTimeout(()=>beacon('dwell','60s'),60000);
</script>"""
    return head, body
