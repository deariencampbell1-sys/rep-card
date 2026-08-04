"""Seed a FULLY populated demo card — what a customer's card looks like set up.

Fictional rep on purpose: SELLABLE-BY-DEFAULT says no founder identity in shippable
artifacts, and a field-sales persona shows the product better than ours does.
"""
import json
import psycopg

DSN = "postgresql:///sales?host=/var/run/postgresql"

MARCUS = {
    "slug": "marcus", "name": "Marcus Vale", "title": "Senior Energy Consultant",
    "company": "Sunline Solar", "phone": "+12145550188", "email": "marcus@sunlinesolar.com",
    "accent": "#FF8A3D", "location": "Dallas–Fort Worth, TX", "rating": 4.9, "reviews": 127,
    "blurb": ("Fifteen years on roofs across North Texas. I'll tell you straight whether solar "
              "makes sense for your house — and if it doesn't, I'll say so. No pressure, no "
              "24-hour-only pricing games."),
    "profile": {
        "accent2": "#C2410C",
        "badge": "TX LICENSED · NABCEP CERTIFIED",
        "og_desc": "Senior Energy Consultant at Sunline Solar · 4.9★ from 127 homeowners",
        "book_url": "https://cal.com/",
        "video": "/card/static/intro.mp4",
        "video_label": "Meet Marcus — 40 sec",
        "services": ["Residential solar", "Battery backup", "Roof + solar bundles",
                     "EV charger install", "Free shade analysis", "Financing to 25 yrs"],
        "gallery": [
            {"a": "#FF8A3D", "b": "#C2410C", "label": "Frisco — 14.2 kW + Powerwall"},
            {"a": "#F59E0B", "b": "#B45309", "label": "Plano — 9.8 kW"},
            {"a": "#FB923C", "b": "#9A3412", "label": "Arlington — roof + solar"},
        ],
        "review_list": [
            {"stars": 5, "who": "Denise R., Frisco",
             "text": "Marcus walked my roof, ran the numbers, and told me my shade was too heavy on "
                     "the west side. Sold me a smaller system than I asked for. Who does that?"},
            {"stars": 5, "who": "Anthony P., Plano",
             "text": "Third quote I got and the only one that showed me the actual production model "
                     "instead of a monthly payment. Install crew was clean and early."},
            {"stars": 4, "who": "Carmen L., Arlington",
             "text": "Permitting took longer than promised, but Marcus texted me every week until it "
                     "cleared. Panels have been flawless since March."},
        ],
        "links": [
            {"label": "sunlinesolar.com", "url": "https://example.com", "icon": "website", "kind": "tap_link"},
            {"label": "Get a free quote", "url": "https://example.com/quote", "icon": "quote", "kind": "tap_link"},
            {"label": "Financing options", "url": "https://example.com/financing", "icon": "financing", "kind": "tap_link"},
        ],
        "socials": [
            {"icon": "facebook", "url": "https://facebook.com"},
            {"icon": "instagram", "url": "https://instagram.com"},
            {"icon": "linkedin", "url": "https://linkedin.com"},
            {"icon": "youtube", "url": "https://youtube.com"},
            {"icon": "google", "url": "https://google.com/maps"},
        ],
    },
}

RHO = {
    "profile": {
        "accent2": "#7B3FD4",
        "badge": "RHOBEAR SALES",
        "book_url": "https://rhobear.ai",
        "video": "/card/static/intro.mp4",
        "video_label": "What RHOBEAR does",
        "services": ["AI sales chatbot", "Rep cards", "Lead heat scoring", "One dashboard"],
        "gallery": [{"a": "#4A9EFF", "b": "#7B3FD4", "label": "The dashboard"},
                    {"a": "#7B3FD4", "b": "#3D1FA8", "label": "Lead heat"}],
        "review_list": [{"stars": 5, "who": "Saguaro Dental",
                         "text": "The bot books consults while we're chairside. It paid for itself the first week."}],
        "links": [{"label": "rhobear.ai", "url": "https://rhobear.ai", "icon": "website", "kind": "tap_link"},
                  {"label": "See the sales page", "url": "https://rhobear.ai/sales.html", "icon": "quote", "kind": "tap_link"}],
        "socials": [{"icon": "website", "url": "https://rhobear.ai"}],
    },
}

with psycopg.connect(DSN, autocommit=True) as c:
    c.execute("""INSERT INTO reps (slug,name,title,company,phone,email,accent,book_url,blurb,
                                   profile,location,rating,reviews)
                 VALUES (%(slug)s,%(name)s,%(title)s,%(company)s,%(phone)s,%(email)s,%(accent)s,
                         %(book)s,%(blurb)s,%(profile)s,%(location)s,%(rating)s,%(reviews)s)
                 ON CONFLICT (slug) DO UPDATE SET
                   name=EXCLUDED.name,title=EXCLUDED.title,company=EXCLUDED.company,
                   phone=EXCLUDED.phone,email=EXCLUDED.email,accent=EXCLUDED.accent,
                   book_url=EXCLUDED.book_url,blurb=EXCLUDED.blurb,profile=EXCLUDED.profile,
                   location=EXCLUDED.location,rating=EXCLUDED.rating,reviews=EXCLUDED.reviews""",
              {**MARCUS, "book": MARCUS["profile"]["book_url"],
               "profile": json.dumps(MARCUS["profile"])})

    c.execute("UPDATE reps SET profile=%s, location=%s, rating=%s, reviews=%s, accent=%s "
              "WHERE slug='dearien'",
              (json.dumps(RHO["profile"]), "Dallas, TX", 5.0, 12, "#4A9EFF"))

    mid = c.execute("SELECT id FROM reps WHERE slug='marcus'").fetchone()[0]

    # rebuild the demo board against Marcus so every card in it is the rich one
    c.execute("DELETE FROM events"); c.execute("DELETE FROM sends")
    c.execute("""INSERT INTO sends (rep_id,to_phone,label,token,sent_at) VALUES
      (%s,'+14695550142','Miller house — asked about financing','demo-hot',  now()-interval '3 hours'),
      (%s,'+12145550188','Trade show — Alvarez, roofing','demo-warm', now()-interval '1 day'),
      (%s,'+19725550133','Door knock — 4412 Cedar','demo-cool', now()-interval '2 days'),
      (%s,'+14695550177','Referral from Jenny','demo-cold', now()-interval '4 days')""",
              (mid, mid, mid, mid))

    # HOT — read it all, watched the video, tapped call + book
    c.execute("""INSERT INTO events (send_id,rep_id,kind,at)
      SELECT id,%s,k,now()-(i||' minutes')::interval FROM sends,
      (VALUES ('view',182),('view',49),('view',11),('scroll',9),('tap_video',9),('dwell',8),
              ('tap_gallery',7),('tap_link',6),('tap_book',5),('tap_call',4)) AS t(k,i)
      WHERE token='demo-hot'""", (mid,))
    # WARM — opened twice, saved contact, shared it
    c.execute("""INSERT INTO events (send_id,rep_id,kind,at)
      SELECT id,%s,k,now()-(i||' hours')::interval FROM sends,
      (VALUES ('view',26),('view',20),('scroll',20),('tap_save',19),('tap_social',19)) AS t(k,i)
      WHERE token='demo-warm'""", (mid,))
    # COOL — one look, bounced
    c.execute("""INSERT INTO events (send_id,rep_id,kind,at)
      SELECT id,%s,'view',now()-interval '2 days' FROM sends WHERE token='demo-cool'""", (mid,))
    # COLD — never opened

    print("reps:", c.execute("SELECT slug,name,company FROM reps ORDER BY id").fetchall())
    print("board:", c.execute("""SELECT s.label,count(e.id) FROM sends s
                                 LEFT JOIN events e ON e.send_id=s.id
                                 GROUP BY s.id,s.label ORDER BY s.id""").fetchall())
