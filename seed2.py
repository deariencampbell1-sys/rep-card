"""Seed contacts + appointments so every tab shows a real working example."""
import psycopg

DSN = "postgresql:///sales?host=/var/run/postgresql"

PEOPLE = [
    # first, last, phone, email, kind, notes, token(existing send), appt
    ("Ray", "Miller", "+14695550142", "ray.miller@gmail.com", "lead",
     "Asked about financing — wants 25-yr term", "demo-hot",
     ("Site survey — Miller house", "+1 day 15:00", "scheduled")),
    ("Alvarez", "Cruz", "+12145550188", "acruz@northtexroof.com", "customer",
     "Trade show booth 214 — roofing GC, wants a referral deal", "demo-warm",
     ("Partnership call", "+3 days 10:30", "scheduled")),
    ("Dana", "Whitfield", "+19725550133", None, "lead",
     "Door knock 4412 Cedar — spouse decides, come back evening", "demo-cool", None),
    ("Jenny", "Okafor", "+14695550177", "jenny@saguarodental.com", "other",
     "Referral source — sends us her patients", "demo-cold",
     ("Coffee — thank-you", "-2 days 09:00", "done")),
    ("Priya", "Raman", None, "priya.raman@outlook.com", "recruit",
     "Wants to join the install crew — 6 yrs experience", None, None),
]

with psycopg.connect(DSN, autocommit=True) as c:
    rid = c.execute("SELECT id FROM reps WHERE slug='marcus'").fetchone()[0]
    c.execute("DELETE FROM appointments")
    c.execute("DELETE FROM contacts")

    for first, last, phone, email, kind, notes, token, appt in PEOPLE:
        cid = c.execute("""INSERT INTO contacts (rep_id,first,last,phone,email,kind,notes)
                           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (rid, first, last, phone, email, kind, notes)).fetchone()[0]
        if token:
            c.execute("UPDATE sends SET contact_id=%s, label=%s WHERE token=%s",
                      (cid, f"{first} {last}", token))
        if appt:
            title, when, status = appt
            c.execute("INSERT INTO appointments (rep_id,contact_id,title,at,status) "
                      "VALUES (%s,%s,%s, now() + %s::interval, %s)",
                      (rid if status != "scheduled" or first != "Alvarez" else None,
                       cid, title, when, status))

    print("contacts:", c.execute("SELECT first,last,kind FROM contacts ORDER BY id").fetchall())
    print("appts:", c.execute("SELECT title,status FROM appointments ORDER BY at").fetchall())
    print("linked sends:", c.execute(
        "SELECT label,token,contact_id FROM sends WHERE contact_id IS NOT NULL").fetchall())
