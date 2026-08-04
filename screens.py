"""Send Card / Contacts / Appts screens.

Send is lead-capture-first: you are saving a CONTACT, and firing the card is the last
step of that save. Gate is deliberately loose — first name plus any one reachable
channel — because a rep at a door shouldn't be blocked by a missing field.
"""
from __future__ import annotations

from html import escape

from shell import tabs, card_strip, empty_state

KINDS = [("lead", "Lead"), ("customer", "Customer"), ("recruit", "Recruit"), ("other", "Other")]


def send_html(rep: dict, reps: list) -> str:
    opts = "".join(f'<option value="{r[0]}"{" selected" if r[0] == rep["id"] else ""}>'
                   f'{escape(r[1])}</option>' for r in reps)
    chips = "".join(
        f'<button type="button" class="kind{" on" if k == "lead" else ""}" data-k="{k}">{lbl}</button>'
        for k, lbl in KINDS)

    return f"""
<div class="wrap">
  <div class="eyebrow">Send Frontman card</div>
  <div style="display:flex;align-items:center;gap:8px;margin:6px 0 16px">
    <select id="rep" style="width:auto;padding:8px 12px;font-size:15px;font-weight:600">{opts}</select>
  </div>

  {card_strip(rep)}

  <div class="two" style="margin-bottom:14px">
    <div><label>First name *</label><input id="first" placeholder="Marcus" autocomplete="given-name"></div>
    <div><label>Last name</label><input id="last" placeholder="Miller" autocomplete="family-name"></div>
  </div>
  <div style="margin-bottom:14px"><label>Phone number</label>
    <input id="phone" type="tel" inputmode="tel" placeholder="(555) 123-4567" autocomplete="tel"></div>
  <div style="margin-bottom:16px"><label>Email</label>
    <input id="email" type="email" inputmode="email" placeholder="name@company.com" autocomplete="email"></div>

  <label>Contact type</label>
  <div class="seg" id="kinds" style="margin:7px 0 16px">{chips}</div>

  <div style="margin-bottom:14px"><label>Initial message</label>
    <textarea id="msg" rows="3">Great meeting you! Here's my card:</textarea></div>

  <div style="margin-bottom:14px"><label>Note to yourself <span style="opacity:.6">(optional)</span></label>
    <input id="notes" placeholder="Asked about financing — follow up Thursday"></div>

  <div class="panel" style="margin-bottom:16px">
    <div class="frow"><div class="lbl">Include social profiles</div>
      <input type="checkbox" id="socials" checked style="width:auto;transform:scale(1.25)"></div>
    <div class="frow" style="border-top:1px solid var(--line)"><div class="lbl">Attach intro video</div>
      <input type="checkbox" id="video" checked style="width:auto;transform:scale(1.25)"></div>
  </div>

  <label>Send via</label>
  <div class="seg" id="chans" style="margin:7px 0 18px">
    <button type="button" class="chan on" data-c="text">Text</button>
    <button type="button" class="chan" data-c="email">Email</button>
  </div>

  <button class="btn" id="go">Save lead &amp; send card</button>
  <p class="muted" id="hint" style="margin-top:12px;text-align:center;min-height:20px"></p>
  <p class="muted" style="margin-top:4px;text-align:center;font-size:11.5px;opacity:.7">
    The message opens in your own app and sends from your real number — no shared sending number.</p>
</div>
<style>.kind,.chan{{padding:9px 15px;border-radius:999px;border:1px solid var(--line);
background:transparent;color:var(--dim);font-size:13px;font-family:inherit;cursor:pointer}}
.kind.on,.chan.on{{background:rgba(74,158,255,.14);border-color:rgba(74,158,255,.36);
color:#78BBFF;font-weight:600}}</style>
<script>
const $=id=>document.getElementById(id);
let KIND='lead', CHAN='text';
document.querySelectorAll('.kind').forEach(b=>b.onclick=()=>{{
  document.querySelectorAll('.kind').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); KIND=b.dataset.k;}});
document.querySelectorAll('.chan').forEach(b=>b.onclick=()=>{{
  document.querySelectorAll('.chan').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); CHAN=b.dataset.c;}});

$('go').onclick=async()=>{{
  const first=$('first').value.trim(), phone=$('phone').value.trim(), email=$('email').value.trim();
  if(!first){{$('hint').textContent='First name is required.';return;}}
  if(!phone && !email){{$('hint').textContent='Add a phone number or an email so you can reach them.';return;}}
  if(CHAN==='text' && !phone){{$('hint').textContent='Texting needs a phone number.';return;}}
  if(CHAN==='email' && !email){{$('hint').textContent='Emailing needs an email address.';return;}}
  $('go').textContent='Saving…';
  const r=await fetch('/card/api/lead',{{method:'POST',headers:{{'content-type':'application/json'}},
    body:JSON.stringify({{rep_id:+$('rep').value,first:first,last:$('last').value.trim(),
      phone:phone,email:email,kind:KIND,notes:$('notes').value.trim(),
      channel:CHAN,message:$('msg').value.trim(),
      socials:$('socials').checked,video:$('video').checked}})}});
  const d=await r.json();
  if(d.error){{$('hint').textContent=d.error;$('go').textContent='Save lead & send card';return;}}
  const body=encodeURIComponent($('msg').value.trim()+' '+d.url);
  if(CHAN==='text'){{
    // `?&body=` is the one form that works on BOTH iOS and Android. Do not "simplify".
    location.href='sms:'+d.to+'?&body='+body;
  }}else{{
    location.href='mailto:'+d.to+'?subject='+encodeURIComponent(d.subject)+'&body='+body;
  }}
  $('go').textContent='Save lead & send card';
  $('hint').innerHTML='Saved to Contacts. <a href="/card/contact/'+d.contact_id+'">See '+d.first+'</a>';
}};
</script>
""" + tabs('send')


def contacts_html(rows: list, active: str) -> str:
    segs = "".join(
        f'<a class="{"on" if active == k else ""}" href="/card/contacts?k={k}">{lbl}</a>'
        for k, lbl in [("all", "All")] + KINDS)

    if not rows:
        body = empty_state(
            '<path d="M4 3h16a1 1 0 011 1v16a1 1 0 01-1 1H4a1 1 0 01-1-1V4a1 1 0 011-1zm5 1v16h10V4z"/>',
            "No contacts yet", "Save your first lead from the Send Card tab.")
    else:
        items = []
        for cid, first, last, phone, email, kind, sc, when in rows:
            nm = f"{first} {last or ''}".strip()
            initials = "".join(x[0] for x in nm.split()[:2]).upper()
            colour = "#FF5C39" if sc >= 70 else "#FFB84A" if sc >= 35 else "#4A9EFF" if sc > 0 else "#5A6070"
            items.append(f"""
<a href="/card/contact/{cid}" style="text-decoration:none;color:inherit">
<div class="panel" style="margin-bottom:9px;display:flex;gap:13px;align-items:center">
  <div class="ava">{initials}</div>
  <div style="flex:1;min-width:0">
    <div style="font-weight:600;font-size:15px">{escape(nm)}</div>
    <div class="muted" style="font-size:12.5px;margin-top:2px">
      {escape(phone or email or '')} · {escape(kind)}</div>
  </div>
  <div style="width:9px;height:9px;border-radius:50%;background:{colour};flex:none"></div>
</div></a>""")
        body = "".join(items)

    return f"""
<div class="wrap">
  <div class="eyebrow">RHOBEAR Frontman</div>
  <h1 style="margin:8px 0 4px">Contacts</h1>
  <p class="muted">Everyone you've saved, warmest first.</p>
  <div class="seg">{segs}</div>
  {body}
</div>
<a class="fab" href="/card/send" aria-label="Send a card">
  <svg width="24" height="24" viewBox="0 0 24 24" fill="#fff">
    <path d="M3.4 20.4l17.45-7.48a1 1 0 000-1.84L3.4 3.6a.99.99 0 00-1.39.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .71.73 1.2 1.39.91z"/></svg>
</a>""" + tabs('cont')


def appts_html(rows: list, active: str, month: str) -> str:
    segs = "".join(
        f'<a class="{"on" if active == k else ""}" href="/card/appts?f={k}">{lbl}</a>'
        for k, lbl in [("all", "All appts"), ("mine", "My appts"), ("un", "Unassigned")])

    if not rows:
        body = empty_state(
            '<path d="M19 3h-1V1h-2v2H8V1H6v2H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zm0 16H5V9h14z"/>',
            "No appointments yet", "Book one from a contact, or tap + to add.")
    else:
        items = []
        for aid, title, at, status, nm, cid, rep in rows:
            colour = {"scheduled": "#4A9EFF", "done": "#3FCF8E",
                      "no_show": "#FF5C39", "cancelled": "#5A6070"}.get(status, "#4A9EFF")
            items.append(f"""
<a href="/card/contact/{cid}" style="text-decoration:none;color:inherit">
<div class="panel" style="margin-bottom:9px;display:flex;gap:13px;align-items:center">
  <div style="text-align:center;flex:none;width:46px">
    <div style="font-size:19px;font-weight:600;line-height:1">{at.strftime('%d')}</div>
    <div class="muted" style="font-size:10.5px;letter-spacing:.08em">{at.strftime('%b').upper()}</div>
  </div>
  <div style="flex:1;min-width:0;border-left:1px solid var(--line);padding-left:13px">
    <div style="font-weight:600;font-size:14.5px">{escape(title)}</div>
    <div class="muted" style="font-size:12.5px;margin-top:2px">
      {at.strftime('%-I:%M %p')} · {escape(nm)}{' · ' + escape(rep) if rep else ' · unassigned'}</div>
  </div>
  <span class="pill" style="background:{colour}1F;color:{colour};border:1px solid {colour}44">
    {escape(status.replace('_', ' ').upper())}</span>
</div></a>""")
        body = "".join(items)

    return f"""
<div class="wrap">
  <div class="eyebrow">RHOBEAR Frontman</div>
  <h1 style="margin:8px 0 4px">{escape(month)}</h1>
  <p class="muted">Appointments your cards created.</p>
  <div class="seg">{segs}</div>
  {body}
</div>""" + tabs('appt')
