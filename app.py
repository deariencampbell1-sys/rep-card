"""RHOBEAR Frontman — the live card workspace.

The workspace uses the real rep, contact, send, event, and appointment records from Postgres.
It does not render sample lead or appointment rows.

Surfaces
  GET  /card/                 rep PWA: pick rep, type a number, Send Card -> opens the phone's SMS app
  GET  /card/manifest.webmanifest
  GET  /card/sw.js
  GET  /card/dash             heat list (who's warm right now)
  GET  /c/{token}             the public card the prospect opens (SSR + OG tags)
  GET  /c/{token}/vcf         save-to-contacts
  POST /card/e                event beacon
  GET  /card/health

Runs on 127.0.0.1:8002 behind the Frontman Caddy block.
"""
from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timezone, timedelta
from html import escape
from pathlib import Path

import json
import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from card_render import render_card, cover_svg, shot_svg, logo_svg
from shell import tabs, home_html, SHELL_CSS, card_strip
from screens import send_html, contacts_html, appts_html

DSN = os.environ.get("REPCARD_DSN", "postgresql:///sales?host=/var/run/postgresql")
BASE = os.environ.get("REPCARD_BASE", "https://frontman.rhobear.ai")

app = FastAPI(title="RHOBEAR Frontman")


def db():
    return psycopg.connect(DSN, autocommit=True)


# ── heat scoring ────────────────────────────────────────────────────────────
# Deliberately simple and legible: a prototype should let you argue with the weights.
WEIGHTS = {
    "view": 10, "dwell": 8, "scroll": 4,
    "tap_call": 40, "tap_text": 30, "tap_book": 45, "tap_save": 25,
    "tap_email": 22, "tap_video": 28, "tap_gallery": 12,
    "tap_link": 14, "tap_social": 8, "tap_share": 35,
}

LABELS = {
    "view": "opened the card", "dwell": "stayed on the card", "scroll": "read to the bottom",
    "tap_call": "tapped CALL", "tap_text": "tapped TEXT", "tap_email": "tapped EMAIL",
    "tap_book": "tapped BOOK A TIME", "tap_save": "saved you to contacts",
    "tap_video": "played your video", "tap_gallery": "opened a work photo",
    "tap_link": "opened a link", "tap_social": "opened a social profile",
    "tap_share": "SHARED your card",
}


def heat(rows) -> int:
    """rows = [(kind, at)] -> 0..100. Recent touches count more; repeat visits compound."""
    now = datetime.now(timezone.utc)
    score = 0.0
    for kind, at in rows:
        w = WEIGHTS.get(kind, 2)
        age_h = max((now - at).total_seconds() / 3600.0, 0.0)
        decay = 0.5 ** (age_h / 48.0)          # half-life 48h
        score += w * decay
    return max(0, min(100, round(score)))


def band(score: int) -> tuple[str, str]:
    if score >= 70:
        return "HOT", "#FF5C39"
    if score >= 35:
        return "WARM", "#FFB84A"
    if score > 0:
        return "COOL", "#4A9EFF"
    return "COLD", "#5A6070"


def norm_phone(raw: str) -> str:
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 10:
        d = "1" + d
    return "+" + d if d else ""


# ── shared chrome ───────────────────────────────────────────────────────────
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0A0A12;--panel:rgba(255,255,255,.045);--line:rgba(255,255,255,.10);
--ink:#F2F4F8;--dim:#9AA3B2;--accent:#4A9EFF;--violet:#7B3FD4}
html,body{background:var(--bg);color:var(--ink);
font-family:ui-sans-serif,-apple-system,"Segoe UI",Inter,system-ui,sans-serif;
-webkit-font-smoothing:antialiased;min-height:100%}
body{background-image:radial-gradient(900px 500px at 18% -8%,rgba(74,158,255,.16),transparent 60%),
radial-gradient(800px 480px at 88% 4%,rgba(123,63,212,.14),transparent 62%)}
.wrap{max-width:520px;margin:0 auto;padding:24px 18px 56px}
.glass{background:var(--panel);border:1px solid var(--line);border-radius:18px;
backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%)}
.eyebrow{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}
h1{font-size:26px;font-weight:600;letter-spacing:-.02em;line-height:1.15}
label{display:block;font-size:12px;color:var(--dim);margin:0 0 7px;letter-spacing:.04em}
input,select,textarea{width:100%;background:rgba(0,0,0,.30);border:1px solid var(--line);
color:var(--ink);border-radius:12px;padding:14px 15px;font-size:16px;font-family:inherit;outline:none}
input:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(74,158,255,.14)}
.btn{display:flex;align-items:center;justify-content:center;gap:9px;width:100%;
background:linear-gradient(135deg,var(--accent),var(--violet));color:#fff;border:0;
border-radius:13px;padding:16px;font-size:16px;font-weight:600;font-family:inherit;
cursor:pointer;text-decoration:none;letter-spacing:.01em}
.btn:active{transform:translateY(1px)}
.btn.ghost{background:transparent;border:1px solid var(--line);color:var(--ink)}
.row{display:flex;gap:10px}
.muted{color:var(--dim);font-size:13px;line-height:1.55}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:700;
letter-spacing:.10em;padding:5px 10px;border-radius:999px}
a{color:var(--accent)}
"""


def page(title: str, body: str, head: str = "") -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0A0A12"><title>{escape(title)}</title>
<style>{CSS}{SHELL_CSS}</style>{head}</head><body>{body}</body></html>""")


# ── app surfaces ─────────────────────────────────────
def _reps():
    with db() as c:
        return c.execute("SELECT id,name,title FROM reps ORDER BY id").fetchall()


def _rep_by_id(rid: int):
    with db() as c:
        cols = ",".join(REP_COLS.split(","))
        row = c.execute(f"SELECT {cols} FROM reps WHERE id=%s", (rid,)).fetchone()
    return _rep_dict(row) if row else None


@app.get("/card/send", response_class=HTMLResponse)
def send_screen(rep_id: int | None = None):
    reps = _reps()
    rep = _rep_by_id(rep_id or reps[0][0])
    return page("Send card · RHOBEAR", send_html(rep, [(r[0], r[1]) for r in reps]))


@app.post("/card/api/lead")
async def api_lead(request: Request):
    """Save the CONTACT, then mint the card. The send is the last step of the save."""
    j = await request.json()
    first = (j.get("first") or "").strip()
    if not first:
        return JSONResponse({"error": "First name is required."})
    phone = norm_phone(j.get("phone", ""))
    email = (j.get("email") or "").strip()
    if not phone and not email:
        return JSONResponse({"error": "Add a phone number or an email."})
    chan = j.get("channel") or "text"
    if chan == "text" and not phone:
        return JSONResponse({"error": "Texting needs a phone number."})
    if chan == "email" and not email:
        return JSONResponse({"error": "Emailing needs an email address."})

    tok = secrets.token_urlsafe(7)
    with db() as c:
        rid = j.get("rep_id") or c.execute("SELECT id FROM reps ORDER BY id LIMIT 1").fetchone()[0]
        cid = c.execute("""INSERT INTO contacts (rep_id,first,last,phone,email,kind,notes)
                           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (rid, first, (j.get("last") or "").strip() or None, phone or None,
                         email or None, j.get("kind") or "lead",
                         (j.get("notes") or "").strip() or None)).fetchone()[0]
        label = (first + " " + (j.get("last") or "").strip()).strip()
        c.execute("""INSERT INTO sends (rep_id,contact_id,to_phone,label,token,channel,message)
                     VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                  (rid, cid, phone or None, label, tok, chan,
                   (j.get("message") or "").strip() or None))
        rep_name = c.execute("SELECT name FROM reps WHERE id=%s", (rid,)).fetchone()[0]

    return {"url": BASE + "/c/" + tok, "to": phone if chan == "text" else email,
            "contact_id": cid, "first": first, "subject": rep_name + " — my card"}


@app.get("/card/contacts", response_class=HTMLResponse)
def contacts(k: str = "all"):
    with db() as c:
        where = "WHERE ct.kind=%s" if k != "all" else ""
        rows = c.execute(
            "SELECT ct.id,ct.first,ct.last,ct.phone,ct.email,ct.kind,ct.created_at "
            "FROM contacts ct " + where + " ORDER BY ct.created_at DESC LIMIT 200",
            (k,) if k != "all" else ()).fetchall()
        evs = c.execute("SELECT s.contact_id,e.kind,e.at FROM events e "
                        "JOIN sends s ON s.id=e.send_id WHERE s.contact_id IS NOT NULL").fetchall()
    by = {}
    for cid, kind, at in evs:
        by.setdefault(cid, []).append((kind, at))
    out = [(r[0], r[1], r[2], r[3], r[4], r[5], heat(by.get(r[0], [])), r[6]) for r in rows]
    out.sort(key=lambda x: -x[6])
    return page("Contacts · RHOBEAR", contacts_html(out, k))


@app.get("/card/contact/{cid}", response_class=HTMLResponse)
def contact(cid: int):
    with db() as c:
        ct = c.execute("SELECT first FROM contacts WHERE id=%s", (cid,)).fetchone()
        if not ct:
            return page("Not found", '<div class="wrap"><p class="muted">No such contact.</p></div>')
        sids = c.execute("SELECT id FROM sends WHERE contact_id=%s ORDER BY sent_at DESC",
                         (cid,)).fetchall()
    if sids:
        return lead(sids[0][0])
    return page("Contact", '<div class="wrap"><h1>' + escape(ct[0]) +
                '</h1><p class="muted">No card sent yet.</p></div>' + tabs("cont"))


@app.get("/card/appts", response_class=HTMLResponse)
def appts(f: str = "all"):
    with db() as c:
        # The workspace must never present stale/past seed rows as current appointments.
        where = {"mine": "WHERE a.rep_id IS NOT NULL AND a.at >= now()",
                 "un": "WHERE a.rep_id IS NULL AND a.at >= now()"}.get(f, "WHERE a.at >= now()")
        rows = c.execute(
            "SELECT a.id,a.title,a.at,a.status,"
            "coalesce(ct.first||' '||coalesce(ct.last,''),'—'),a.contact_id,r.name "
            "FROM appointments a LEFT JOIN contacts ct ON ct.id=a.contact_id "
            "LEFT JOIN reps r ON r.id=a.rep_id " + where + " ORDER BY a.at").fetchall()
    month = datetime.now(timezone.utc).strftime("%b %Y")
    return page("Appointments · RHOBEAR", appts_html(rows, f, month))


@app.get("/card/", response_class=HTMLResponse)
@app.get("/card", response_class=HTMLResponse)
def home():
    with db() as c:
        sends = c.execute("SELECT s.id,s.label,s.to_phone,r.name FROM sends s "
                          "JOIN reps r ON r.id=s.rep_id "
                          "WHERE s.label IS DISTINCT FROM 'preview'").fetchall()
        evs = c.execute("SELECT send_id,kind,at FROM events").fetchall()
        week = c.execute("SELECT date_trunc('day',at) d,count(*) FROM events "
                         "WHERE at > now()-interval '7 days' GROUP BY d ORDER BY d").fetchall()
        ncontacts = c.execute("SELECT count(*) FROM contacts").fetchone()[0]

    by = {}
    for sid, kind, at in evs:
        by.setdefault(sid, []).append((kind, at))
    ENGAGE = {"scroll", "dwell", "tap_video", "tap_gallery"}
    ACT = {"tap_call", "tap_book", "tap_save", "tap_text", "tap_email", "tap_share"}
    opened = engaged = acted = 0
    hot, per_rep = [], {}
    for sid, label, phone, rep in sends:
        e = by.get(sid, [])
        kinds = {k for k, _ in e}
        if e:
            opened += 1
        if kinds & ENGAGE:
            engaged += 1
        if kinds & ACT:
            acted += 1
        sc = heat(e)
        if sc >= 70:
            hot.append((sid, label or phone or "lead", sc))
        cnt, h = per_rep.get(rep, (0, 0))
        per_rep[rep] = (cnt + 1, h + (1 if sc >= 70 else 0))
    hot.sort(key=lambda x: -x[2])
    counts = [int(n) for _, n in week] or [0]
    padded = ([0] * (7 - len(counts)) + counts)[-7:]

    return page("Frontman · RHOBEAR", home_html({
        "sent": len(sends), "opened": opened, "engaged": engaged, "acted": acted,
        "contacts": ncontacts, "hot_count": len(hot), "hot": hot[:5],
        "leaders": sorted(((n, c_, h) for n, (c_, h) in per_rep.items()), key=lambda x: -x[1])[:5],
        "by_day": padded, "by_day_max": max(padded), "week_total": sum(padded),
    }))


@app.post("/card/mint")
async def mint(request: Request):
    j = await request.json()
    to = norm_phone(j.get("phone", ""))
    if not to:
        return JSONResponse({"error": "That doesn't look like a phone number."})
    tok = secrets.token_urlsafe(7)
    with db() as c:
        rid = j.get("rep_id") or c.execute("SELECT id FROM reps ORDER BY id LIMIT 1").fetchone()[0]
        c.execute("INSERT INTO sends (rep_id,to_phone,label,token) VALUES (%s,%s,%s,%s)",
                  (rid, to, (j.get("label") or "").strip()[:120], tok))
    return {"url": f"{BASE}/c/{tok}", "to": to}


@app.get("/card/manifest.webmanifest")
def manifest():
    return JSONResponse({
        "name": "RHOBEAR Frontman", "short_name": "Frontman",
        "start_url": "/card/", "scope": "/card/", "display": "standalone",
        "background_color": "#0A0A12", "theme_color": "#0A0A12",
        "icons": [{"src": "/card/icon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }, media_type="application/manifest+json")


@app.get("/card/icon.svg")
def icon():
    return Response("""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#4A9EFF"/><stop offset="1" stop-color="#7B3FD4"/></linearGradient></defs>
<rect width="192" height="192" rx="42" fill="#0A0A12"/>
<rect x="34" y="56" width="124" height="80" rx="12" fill="none" stroke="url(#g)" stroke-width="7"/>
<circle cx="68" cy="88" r="13" fill="url(#g)"/>
<rect x="92" y="80" width="46" height="7" rx="3.5" fill="url(#g)"/>
<rect x="92" y="97" width="34" height="7" rx="3.5" fill="url(#g)" opacity=".6"/>
<rect x="54" y="110" width="84" height="7" rx="3.5" fill="url(#g)" opacity=".35"/></svg>""",
                    media_type="image/svg+xml")


@app.get("/card/sw.js")
def sw():
    return Response(
        "self.addEventListener('install',e=>self.skipWaiting());\n"
        "self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));\n",
        media_type="application/javascript")


# ── the public card ─────────────────────────────────────────────────────────
REP_COLS = ("id,slug,name,title,company,phone,email,photo_url,accent,book_url,blurb,"
            "profile,location,rating,reviews")


def _rep_dict(row) -> dict:
    keys = REP_COLS.split(",")
    d = dict(zip(keys, row))
    if isinstance(d.get("profile"), str):
        d["profile"] = json.loads(d["profile"])
    d["profile"] = d.get("profile") or {}
    if d.get("book_url") and "book_url" not in d["profile"]:
        d["profile"]["book_url"] = d["book_url"]
    if d.get("rating") is not None:
        d["rating"] = float(d["rating"])
    _merge_sales_chat_brand(d)
    return d


def _merge_sales_chat_brand(rep: dict) -> None:
    """Bring the real Frontman brand asset into the legacy card workspace.

    The card workspace and the old dashboard used to store the same rep twice. That is why
    the app could show the right name but a generated R mark instead of the owner's uploaded
    logo. Read only the existing branding record; never invent or copy an asset.
    """
    slug = str(rep.get("slug") or "").strip()
    if not slug:
        return
    path = Path(os.environ.get(
        "FRONTMAN_BRANDING_DIR", "/opt/rhobear/sales-chat/data/branding",
    )) / f"{slug}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    profile = rep["profile"]
    if data.get("logo") and not profile.get("logo_url"):
        profile["logo_url"] = str(data["logo"])
    if data.get("portrait") and not rep.get("photo_url"):
        rep["photo_url"] = str(data["portrait"])
    if str(profile.get("badge") or "").strip().upper() == "RHOBEAR SALES":
        profile["badge"] = "RHOBEAR FRONTMAN"


def _load(token: str):
    with db() as c:
        row = c.execute(f"""SELECT s.id, {REP_COLS.replace('id,', 'r.id,').replace(',', ',r.').replace('r.r.', 'r.')}
                            FROM sends s JOIN reps r ON r.id=s.rep_id WHERE s.token=%s""",
                        (token,)).fetchone()
    return row


@app.get("/c/{token}", response_class=HTMLResponse)
def card(token: str, request: Request):
    with db() as c:
        cols = ",".join("r." + x for x in REP_COLS.split(","))
        row = c.execute(f"SELECT s.id,{cols} FROM sends s JOIN reps r ON r.id=s.rep_id WHERE s.token=%s",
                        (token,)).fetchone()
        if not row:
            return page("Not found",
                        '<div class="wrap"><p class="muted">This card link has expired.</p></div>')
        sid = row[0]
        rep = _rep_dict(row[1:])
        c.execute("INSERT INTO events (send_id,rep_id,kind,ua) VALUES (%s,%s,'view',%s)",
                  (sid, rep["id"], (request.headers.get("user-agent") or "")[:300]))
    head, body = render_card(token, rep, BASE)
    return page(f"{rep['name']} — {rep.get('company') or 'card'}", body, head)


def _rep_for(token: str) -> dict | None:
    with db() as c:
        cols = ",".join("r." + x for x in REP_COLS.split(","))
        row = c.execute(f"SELECT {cols} FROM sends s JOIN reps r ON r.id=s.rep_id WHERE s.token=%s",
                        (token,)).fetchone()
    return _rep_dict(row) if row else None


@app.get("/card/img/cover/{token}")
def img_cover(token: str):
    rep = _rep_for(token)
    if not rep:
        return Response(status_code=404)
    p = rep["profile"]
    return Response(cover_svg(rep.get("accent") or "#4A9EFF", p.get("accent2", "#7B3FD4")),
                    media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/card/img/poster/{token}")
def img_poster(token: str):
    rep = _rep_for(token)
    if not rep:
        return Response(status_code=404)
    p = rep["profile"]
    return Response(shot_svg(rep.get("accent") or "#4A9EFF", p.get("accent2", "#7B3FD4"),
                             p.get("video_label", "Play")),
                    media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/card/img/shot/{token}/{i}")
def img_shot(token: str, i: int):
    rep = _rep_for(token)
    if not rep:
        return Response(status_code=404)
    g = (rep["profile"].get("gallery") or [])
    if i >= len(g):
        return Response(status_code=404)
    cell = g[i]
    return Response(shot_svg(cell.get("a", "#4A9EFF"), cell.get("b", "#7B3FD4"), cell.get("label", "")),
                    media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/card/static/intro.mp4")
def intro_video():
    from fastapi.responses import FileResponse
    return FileResponse("/opt/rhobear/rep-card/static/intro.mp4", media_type="video/mp4")


@app.get("/c/{token}/vcf")
def vcf(token: str):
    with db() as c:
        r = c.execute("""SELECT s.id,r.id,r.name,r.title,r.company,r.phone,r.email
                         FROM sends s JOIN reps r ON r.id=s.rep_id WHERE s.token=%s""",
                      (token,)).fetchone()
        if not r:
            return PlainTextResponse("not found", status_code=404)
        sid, rid, name, title, company, phone, email = r
        c.execute("INSERT INTO events (send_id,rep_id,kind) VALUES (%s,%s,'tap_save')", (sid, rid))
    last, _, first = name.partition(" ")
    card = ("BEGIN:VCARD\r\nVERSION:3.0\r\n"
            f"N:{first};{last};;;\r\nFN:{name}\r\n"
            + (f"ORG:{company}\r\n" if company else "")
            + (f"TITLE:{title}\r\n" if title else "")
            + (f"TEL;TYPE=CELL:{phone}\r\n" if phone else "")
            + (f"EMAIL:{email}\r\n" if email else "")
            + f"URL:{BASE}/c/{token}\r\nEND:VCARD\r\n")
    return Response(card, media_type="text/vcard",
                    headers={"Content-Disposition": f'attachment; filename="{name.replace(" ", "-")}.vcf"'})


@app.post("/card/e")
async def event(request: Request):
    try:
        j = await request.json()
    except Exception:
        return Response(status_code=204)
    kind = str(j.get("kind", ""))[:32]
    if kind not in WEIGHTS:
        return Response(status_code=204)
    with db() as c:
        r = c.execute("SELECT id,rep_id FROM sends WHERE token=%s", (j.get("t"),)).fetchone()
        if r:
            c.execute("INSERT INTO events (send_id,rep_id,kind,meta) VALUES (%s,%s,%s,%s)",
                      (r[0], r[1], kind, str(j.get("meta", ""))[:120]))
    return Response(status_code=204)


# ── heat list ───────────────────────────────────────────────────────────────
@app.get("/card/dash", response_class=HTMLResponse)
def dash():
    with db() as c:
        sends = c.execute("""SELECT s.id,s.to_phone,s.label,s.token,s.sent_at,r.name
                             FROM sends s JOIN reps r ON r.id=s.rep_id
                             WHERE s.label IS DISTINCT FROM 'preview'
                             ORDER BY s.sent_at DESC LIMIT 60""").fetchall()
        evs = c.execute("SELECT send_id,kind,at FROM events").fetchall()
    by = {}
    for sid, kind, at in evs:
        by.setdefault(sid, []).append((kind, at))

    rows = []
    for sid, to, label, tok, sent, rep in sends:
        e = by.get(sid, [])
        sc = heat(e)
        name, colour = band(sc)
        last = max((a for _, a in e), default=None)
        ago = "no opens yet"
        if last:
            m = (datetime.now(timezone.utc) - last).total_seconds() / 60
            ago = f"{int(m)}m ago" if m < 60 else (f"{int(m//60)}h ago" if m < 1440 else f"{int(m//1440)}d ago")
        taps = sum(1 for k, _ in e if k.startswith("tap_"))
        views = sum(1 for k, _ in e if k == "view")
        rows.append(f"""
<a href="/card/lead/{sid}" style="text-decoration:none;color:inherit;display:block">
<div class="glass" style="padding:15px 16px;margin-bottom:10px;display:flex;gap:14px;align-items:center">
  <div style="flex:1;min-width:0">
    <div style="font-weight:600;font-size:15px">{escape(label or to)}</div>
    <div class="muted" style="margin-top:3px">{escape(to)} · {escape(rep)} · {ago}</div>
    <div class="muted" style="margin-top:4px;font-size:12px;opacity:.8">
      {views} open{'s' if views != 1 else ''} · {taps} tap{'s' if taps != 1 else ''}</div>
  </div>
  <div style="text-align:right">
    <span class="pill" style="background:{colour}1F;color:{colour};border:1px solid {colour}44">{name}</span>
    <div style="font-size:22px;font-weight:600;margin-top:7px">{sc}</div>
  </div>
</div></a>""")

    empty = '<p class="muted">No cards sent yet. Send one, then open it on another device.</p>'
    return page("Frontman logbook · RHOBEAR", f"""
<div class="wrap">
  <div class="eyebrow">RHOBEAR Frontman</div>
  <h1 style="margin:8px 0 6px">Logbook</h1>
  <p class="muted" style="margin-bottom:22px">Ranked by what they actually did — recent taps beat old opens.</p>
  {''.join(rows) if rows else empty}
</div>
""" + tabs('cont'))


@app.get("/card/lead/{sid}", response_class=HTMLResponse)
def lead(sid: int):
    """The drill-down: exactly what this prospect did, newest first.

    This is the screen that makes the product obvious — a rep opens it and knows
    whether to call now or leave it alone."""
    with db() as c:
        s_row = c.execute("""SELECT s.to_phone,s.label,s.token,s.sent_at,r.name,r.company
                             FROM sends s JOIN reps r ON r.id=s.rep_id WHERE s.id=%s""",
                          (sid,)).fetchone()
        if not s_row:
            return page("Not found", '<div class="wrap"><p class="muted">No such lead.</p></div>')
        evs = c.execute("SELECT kind,meta,at FROM events WHERE send_id=%s ORDER BY at DESC",
                        (sid,)).fetchall()
    to, label, token, sent, rep, company = s_row
    sc = heat([(k, a) for k, _, a in evs])
    name, colour = band(sc)

    def ago(t):
        m = (datetime.now(timezone.utc) - t).total_seconds() / 60
        if m < 1:
            return "just now"
        if m < 60:
            return f"{int(m)} min ago"
        if m < 1440:
            return f"{int(m//60)} hr ago"
        return f"{int(m//1440)} d ago"

    timeline = "".join(f"""
<div style="display:flex;gap:13px;padding:13px 0;border-bottom:1px solid var(--line)">
  <div style="width:8px;height:8px;border-radius:50%;margin-top:6px;flex:none;
    background:{'#FF5C39' if k.startswith('tap_') else 'rgba(255,255,255,.28)'}"></div>
  <div style="flex:1">
    <div style="font-size:14.5px;font-weight:{600 if k.startswith('tap_') else 400}">
      {escape(LABELS.get(k, k))}</div>
    <div class="muted" style="font-size:12px;margin-top:2px">{ago(a)}{' · ' + escape(m) if m else ''}</div>
  </div></div>""" for k, m, a in evs) or '<p class="muted">Nothing yet &mdash; the card has not been opened.</p>'

    taps = sum(1 for k, _, _ in evs if k.startswith("tap_"))
    nudge = ("Call them now — they just tapped." if sc >= 70 else
             "Worth a follow-up today." if sc >= 35 else
             "Cooling off. A short text might revive it." if sc > 0 else
             "Never opened. Try resending, or a different number.")

    return page(f"{label or to} · lead", f"""
<div class="wrap">
  <a href="/card/contacts" class="muted" style="text-decoration:none">&larr; Contacts</a>
  <h1 style="margin:14px 0 5px">{escape(label or to)}</h1>
  <p class="muted">{escape(to)} · card sent by {escape(rep)} · {ago(sent)}</p>

  <div class="glass" style="padding:18px;margin-top:18px;display:flex;align-items:center;gap:16px">
    <div>
      <span class="pill" style="background:{colour}1F;color:{colour};border:1px solid {colour}44">{name}</span>
      <div style="font-size:34px;font-weight:600;margin-top:8px;line-height:1">{sc}</div>
      <div class="muted" style="font-size:11px;margin-top:3px">heat score</div>
    </div>
    <div style="flex:1;border-left:1px solid var(--line);padding-left:16px">
      <p style="font-size:14.5px;font-weight:600">{nudge}</p>
      <p class="muted" style="margin-top:6px">{len(evs)} touches · {taps} taps</p>
    </div>
  </div>

  <div class="sec" style="margin-top:22px">
    <h2 style="font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim);
      margin-bottom:6px;font-weight:600">Activity</h2>
    {timeline}
  </div>

  <div class="row" style="margin-top:20px">
    <a class="btn" href="tel:{escape(to)}">Call them</a>
    <a class="btn ghost" href="/c/{escape(token)}" target="_blank" rel="noopener">See their card</a>
  </div>
</div>""")


@app.get("/card/img/logo/{token}")
def img_logo(token: str):
    rep = _rep_for(token)
    if not rep:
        return Response(status_code=404)
    p = rep["profile"]
    return Response(logo_svg(rep.get("company") or "", rep.get("accent") or "#4A9EFF",
                             p.get("accent2", "#7B3FD4")),
                    media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/card/img/logo/rep/{rid}")
def img_logo_rep(rid: int):
    rep = _rep_by_id(rid)
    if not rep:
        return Response(status_code=404)
    return Response(logo_svg(rep.get("company") or "", rep.get("accent") or "#4A9EFF",
                             rep["profile"].get("accent2", "#7B3FD4")),
                    media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/card/board", response_class=HTMLResponse)
def board():
    return home()


@app.get("/card/health")
def health():
    with db() as c:
        c.execute("SELECT 1")
    return {"ok": True, "surface": "frontman"}
