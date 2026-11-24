"""Bella Vista Preiswächter – Suche für den Server (GitHub Actions).

Sucht Pauschalreisen (CHECK24) und Flug + Hotel einzeln (Google Flüge + Google Hotels)
ab Graz, schreibt das Ergebnis nach docs/data.json und schickt bei Preisalarm eine
Nachricht über ntfy (Umgebungsvariable NTFY_TOPIC).
"""
import base64, datetime as dt, json, os, re, sys, time, urllib.parse, urllib.request
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

HIER = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HIER, "docs", "data.json")
CONFIG = os.path.join(HIER, "config.json")
WIEN = ZoneInfo("Europe/Vienna")
C24_HOTEL = 8541
GH_ENTITY = "ChcIkq6L_6eHjdASGgsvZy8xdGhqNzY1ZhAB"
GRUPPEN = [
    {"key": "woche", "titel": "1 Woche", "days": [7, 8]},   # 6 oder 7 Nächte
    {"key": "zehn", "titel": "10 Tage", "days": [9, 10]},   # 8 oder 9 Nächte
]
HOOK = r"""
(() => {
  if (window.__bvOffers) return;
  const store = (window.__bvOffers = []);
  function take(j) { try { for (const o of Object.values((j && j.items) || {})) {
    const ta = o.travelAttributes || {}, pr = o.price || {}, out = (o.flight && o.flight.outbound) || {}, acc = o.accommodationData || {};
    store.push({ preis: Number(pr.person ?? pr.total), abflug: String(ta.departureDate || "").slice(0, 10), rueckkehr: String(ta.returnDate || "").slice(0, 10),
      naechte: Number(ta.overnightStays), airport: out.airport && out.airport.code, stops: out.stops, airline: out.airline && out.airline.name,
      verpflegung: acc.mealType || acc.mealCategory || "", transfer: acc.transfer || "" }); } } catch (e) {} }
  const isOffer = (u) => String(u || "").includes("json/dynamic/offer");
  const f = window.fetch;
  window.fetch = async function (...a) { const r = await f.apply(this, a); try { if (isOffer(a[0] && (a[0].url || a[0]))) r.clone().json().then(take).catch(() => {}); } catch (e) {} return r; };
  const op = XMLHttpRequest.prototype.open; XMLHttpRequest.prototype.open = function (m, u, ...r) { this.__u = String(u); return op.call(this, m, u, ...r); };
  const sd = XMLHttpRequest.prototype.send; XMLHttpRequest.prototype.send = function (...a) { if (isOffer(this.__u)) this.addEventListener("load", () => { try { take(JSON.parse(this.responseText)); } catch (e) {} }); return sd.apply(this, a); };
})();
"""


def log(*a):
    print(*a, flush=True)


def add_days(s, n):
    return (dt.date.fromisoformat(s) + dt.timedelta(days=n)).isoformat()


def naechte(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def c24_url(a, b, days):
    return ("https://urlaub.check24.de/suche/angebot?airport=GRZ&transportType=flight&roomAllocation=A"
            f"&departureDate={a}&returnDate={b}&days={days}&page=1&pageArea=package&areaId=673"
            f"&hotelId={C24_HOTEL}&ds=h&offerSort=price&areaSort=topregion")


def flug_url(a, b):
    return ("https://www.google.com/travel/flights?q=" + urllib.parse.quote(f"Flights from GRZ to HRG on {a} through {b}")
            + "&hl=de&curr=EUR")


def _v(n):
    o = []
    while n > 127:
        o.append((n & 127) | 128); n >>= 7
    o.append(n); return o


def _d(tag, s):
    y, m, d = map(int, s.split("-")); b = [8, *_v(y), 16, m, 24, d]; return [tag, len(b), *b]


def hotel_url(a, b):
    inner = _d(10, a) + _d(18, b) + [24, naechte(a, b)]
    l2 = [18, len(inner), *inner, 50, 2, 16, 0]
    l1 = [10, 2, 26, 0, 18, len(l2), *l2]
    ad = [10, 2, 8, 3, 16, 0]
    al = [8, 1, 18, len(ad), *ad, 26, len(l1), *l1, 42, 9, 10, 5, 58, 3, 69, 85, 82, 26, 0]
    ts = base64.b64encode(bytes(al)).decode().rstrip("=")
    return (f"https://www.google.com/travel/hotels/entity/{GH_ENTITY}/prices?hl=de&gl=at&curr=EUR&ts="
            + urllib.parse.quote(ts, safe=""))


# ---------------- Quellen ----------------
def check24(ctx, von, bis, days):
    pg = ctx.new_page()
    try:
        pg.add_init_script(HOOK)
        pg.goto(c24_url(von, bis, days), wait_until="domcontentloaded", timeout=60000)
        last, stabil = -1, 0
        for _ in range(25):
            time.sleep(2)
            n = pg.evaluate("(window.__bvOffers||[]).length")
            if n and n == last:
                stabil += 1
                if stabil >= 2:
                    break
            else:
                stabil = 0
            last = n
        offs = pg.evaluate("window.__bvOffers||[]")
        if not offs:
            log("  CHECK24 lieferte nichts. Seitentitel:", pg.title())
        return [o for o in offs if o.get("preis") and o["abflug"] >= von and o.get("rueckkehr") and o["rueckkehr"] <= bis
                and (not o.get("airport") or o["airport"] == "GRZ")]
    finally:
        pg.close()


def notiz_paket(o):
    t = []
    if o.get("stops") == 0:
        t.append("Direktflug")
    elif (o.get("stops") or 0) > 0:
        t.append(f"Flug mit {o['stops']} Umstieg" + ("en" if o["stops"] > 1 else ""))
    if o.get("airline"):
        t.append(o["airline"])
    mv = {"AllInclusive": "All Inclusive", "HalfBoard": "Halbpension", "FullBoard": "Vollpension", "Breakfast": "Frühstück"}
    if o.get("verpflegung"):
        t.append(mv.get(o["verpflegung"], o["verpflegung"]))
    if re.search("transfer", o.get("transfer") or "", re.I) and not re.search("no|kein|ohne", o.get("transfer") or "", re.I):
        t.append("Transfer inklusive")
    return " · ".join(t)


def google_seite(ctx, url, warte, sek):
    pg = ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded", timeout=60000)
    if "consent.google" in pg.url:
        pg.evaluate("""()=>{const b=[...document.querySelectorAll('button')].find(x=>/Alle ablehnen|Reject all/i.test(x.innerText)); if(b) b.click();}""")
        time.sleep(3)
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
    txt = ""
    for _ in range(int(sek / 1.5)):
        time.sleep(1.5)
        txt = pg.inner_text("body")
        if re.search(warte, txt):
            time.sleep(1.5)
            txt = pg.inner_text("body")
            break
    if not re.search(warte, txt):
        log("  Google-Seite ohne Ergebnis. Titel:", pg.title(), "| URL:", pg.url[:100])
    pg.close()
    return txt


def flug(ctx, a, b):
    txt = google_seite(ctx, flug_url(a, b), r"Hin und zurück", 25)
    best = None
    for m in re.finditer(r"(\d{1,3}(?:\.\d{3})*)[\s ]*€[\s ]*\n[\s ]*Hin und zurück", txt):
        p = int(m.group(1).replace(".", ""))
        if best is None or p < best["preis"]:
            block = txt[max(0, m.start() - 400):m.start()]
            zeilen = [z.strip() for z in block.split("\n") if z.strip()]
            st = re.search(r"(\d) Stopp", block)
            gr = next((i for i, z in enumerate(zeilen) if z.startswith("GRZ")), -1)
            airline = zeilen[gr - 2] if gr > 1 else ""
            art = "Direktflug" if "Nonstop" in block else (f"{st.group(1)} Umstieg" + ("e" if st.group(1) != "1" else "") if st else "")
            best = {"preis": p, "notiz": art + (" · " + airline if airline else "")}
    return best


def hotel(ctx, a, b):
    n = naechte(a, b)
    txt = google_seite(ctx, hotel_url(a, b), r"Gesamtpreis|Zur Website", 20)
    m = re.search(r"€[\s ]?(\d[\d.]*)[\s ]*Gesamtpreis[\s ]*(\d+)[\s ]*Übernachtung", txt)
    if m and int(m.group(2)) == n:
        return {"preis": int(m.group(1).replace(".", "")), "notiz": "Hotel über Google Hotels"}
    i = min([x for x in (txt.find("Vorgestellte Optionen"), txt.find("Alle Optionen")) if x >= 0], default=-1)
    if i < 0:
        k = txt.find("Bella Vista")
        log("  Hotelseite ohne Preisliste:", repr(txt[max(0, k):max(0, k) + 700]))
        return None
    ende = txt.find("Ähnliche Hotels", i)
    teil = txt[i: ende if ende > 0 else i + 3000]
    best = None
    for stueck in teil.split("Zur Website")[:-1]:
        zeilen = [z.replace(" ", " ").strip() for z in stueck.split("\n") if z.strip()]
        pz = next((z for z in reversed(zeilen) if re.fullmatch(r"€ ?\d[\d.]*|\d[\d.]* ?€", z)), None)
        if not pz:
            continue
        p = int(re.sub(r"\D", "", pz))
        if not 15 <= p < 2000:
            continue
        idx = next((k for k, z in enumerate(zeilen) if re.search(r"€|Gäste|^,$", z) or z.startswith("Kostenlos")), len(zeilen))
        kand = [z for z in zeilen[:idx] if not re.search(r"·|Optionen|Gesponsert|^\*", z)]
        anbieter = kand[-1] if kand else "Google Hotels"
        verpfl = "nur Frühstück" if re.search(r"Frühstück", stueck) else ""
        if best is None or p < best[0]:
            best = (p, anbieter, verpfl)
    if not best:
        return None
    zusatz = ", " + best[2] if best[2] else ""
    return {"preis": best[0] * n, "notiz": f"Hotel über {best[1]} ({best[0]} € pro Nacht{zusatz})"}


# ---------------- Ablauf ----------------
def suche_alles(von, bis):
    heute = dt.datetime.now(WIEN).date().isoformat()
    if von <= heute:
        von = add_days(heute, 1)
    erg = {"zeit": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "von": von, "bis": bis, "gruppen": {}, "fehler": []}
    with sync_playwright() as p:
        # Lokal zum Testen: BROWSER_CHANNEL=chrome nutzt das installierte Chrome
        br = p.chromium.launch(headless=True, channel=os.environ.get("BROWSER_CHANNEL") or None)
        ctx = br.new_context(locale="de-AT", timezone_id="Europe/Vienna", viewport={"width": 1280, "height": 900},
                             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        for g in GRUPPEN:
            res = {"pauschal": None, "getrennt": None}
            alle = []
            for days in g["days"]:
                log(f"{g['titel']}: CHECK24 {days - 1} Nächte")
                try:
                    alle += check24(ctx, von, bis, days)
                except Exception as e:
                    erg["fehler"].append(f"CHECK24 {days - 1} Nächte: {e}")
            alle.sort(key=lambda o: o["preis"])
            pk = alle[0] if alle else None
            if pk:
                res["pauschal"] = {"preis": round(pk["preis"]), "abflug": pk["abflug"], "rueckkehr": pk["rueckkehr"],
                                   "naechte": naechte(pk["abflug"], pk["rueckkehr"]), "notiz": notiz_paket(pk),
                                   "url": c24_url(pk["abflug"], pk["rueckkehr"], naechte(pk["abflug"], pk["rueckkehr"]) + 1)}
            a = pk["abflug"] if pk else von
            b = pk["rueckkehr"] if pk else add_days(von, g["days"][1] - 1)
            fl = ho = None
            for versuch in (1, 2):  # Google liefert manchmal beim ersten Mal nichts
                if not fl:
                    log(f"{g['titel']}: Google Flüge {a} – {b} (Versuch {versuch})")
                    try:
                        fl = flug(ctx, a, b)
                    except Exception as e:
                        erg["fehler"].append(f"Google Flüge: {e}")
                if not ho:
                    log(f"{g['titel']}: Google Hotels {a} – {b} (Versuch {versuch})")
                    try:
                        ho = hotel(ctx, a, b)
                    except Exception as e:
                        erg["fehler"].append(f"Google Hotels: {e}")
                if fl and ho:
                    break
            if not fl:
                erg["fehler"].append(f"{g['titel']}: kein Flugpreis bei Google Flüge")
            if not ho:
                erg["fehler"].append(f"{g['titel']}: kein Hotelpreis bei Google Hotels")
            if fl and ho:
                res["getrennt"] = {"preis": fl["preis"] + ho["preis"], "flugPreis": fl["preis"], "hotelPreis": ho["preis"],
                                   "abflug": a, "rueckkehr": b, "naechte": naechte(a, b),
                                   "notiz": "Flug: " + fl["notiz"] + " · " + ho["notiz"], "flugUrl": flug_url(a, b), "hotelUrl": hotel_url(a, b)}
            log("  ->", json.dumps({k: (v and v["preis"]) for k, v in res.items()}))
            erg["gruppen"][g["key"]] = res
        br.close()
    return erg


def bester(r):
    c = [x for x in (r.get("pauschal"), r.get("getrennt")) if x]
    return min(c, key=lambda x: x["preis"]) if c else None


def datum(s):
    d = dt.date.fromisoformat(s)
    return ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][d.weekday()] + d.strftime(", %d.%m.%Y")


def eur(n):
    return f"{n:,.0f} €".replace(",", ".")


def ntfy(text, titel, link):
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        log("Kein NTFY_TOPIC gesetzt, keine Handy-Nachricht.")
        return
    req = urllib.request.Request("https://ntfy.sh/" + urllib.parse.quote(topic), data=text.encode("utf-8"), method="POST",
                                 headers={"Title": titel, "Priority": "high", "Tags": "palm_tree",
                                          **({"Click": link} if link else {})})
    urllib.request.urlopen(req, timeout=20)
    log("Handy-Nachricht gesendet.")


def alarm_pruefen(daten, cfg):
    gemeldet = daten.setdefault("gemeldet", {})
    treffer = []
    for g in GRUPPEN:
        grenze = (cfg.get("alarm") or {}).get(g["key"])
        b = bester(daten["ergebnis"]["gruppen"].get(g["key"], {}))
        if not grenze or not b or b["preis"] > grenze:
            gemeldet.pop(g["key"], None)
            continue
        if g["key"] in gemeldet and b["preis"] >= gemeldet[g["key"]]:
            continue
        gemeldet[g["key"]] = b["preis"]
        art = "Flug und Hotel einzeln" if b is daten["ergebnis"]["gruppen"][g["key"]].get("getrennt") else "Pauschalreise"
        treffer.append(f"{g['titel']}: {eur(b['preis'])} ({art}, {datum(b['abflug'])} bis {datum(b['rueckkehr'])}). Ihre Grenze: {eur(grenze)}.")
    if treffer:
        daten["alarmMeldung"] = {"zeit": daten["ergebnis"]["zeit"], "texte": treffer}
        try:
            ntfy("\n".join(treffer), "Preisalarm Bella Vista", os.environ.get("SEITE_URL", ""))
        except Exception as e:
            log("Handy-Nachricht fehlgeschlagen:", e)


def ist_suchzeit():
    """GitHub startet zu festen UTC-Zeiten; hier wird geprüft, ob es in Wien 7, 15 oder 20 Uhr ist (Sommer-/Winterzeit)."""
    plan = os.environ.get("CRON_PLAN", "")
    if not plan:
        return True  # manuell gestartet
    sommer = dt.datetime.now(WIEN).utcoffset() == dt.timedelta(hours=2)
    return ("5,13,18" in plan) == sommer


def main():
    if not ist_suchzeit():
        log("Andere Jahreszeit-Variante des Zeitplans, diese Ausführung wird übersprungen.")
        return
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    z = cfg.get("zeitraum") or {}
    heute = dt.datetime.now(WIEN).date().isoformat()
    von = z.get("von") or add_days(heute, 1)
    bis = z.get("bis") or add_days(heute, 212)
    daten = json.load(open(DATA, encoding="utf-8")) if os.path.exists(DATA) else {}
    erg = suche_alles(von, bis)
    daten["ergebnis"] = erg
    eintrag = {"zeit": erg["zeit"]}
    for g in GRUPPEN:
        r = erg["gruppen"].get(g["key"], {})
        eintrag[g["key"]] = {"p": r.get("pauschal") and r["pauschal"]["preis"], "e": r.get("getrennt") and r["getrennt"]["preis"]}
    daten["verlauf"] = (daten.get("verlauf") or [])[-1200:] + [eintrag]
    daten["alarm"] = cfg.get("alarm") or {}
    daten.pop("alarmMeldung", None)
    alarm_pruefen(daten, cfg)
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    json.dump(daten, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("Fertig.", "Fehler:" if erg["fehler"] else "", erg["fehler"] or "")
    gefunden = sum(1 for r in erg["gruppen"].values() for x in r.values() if x)
    if gefunden == 0:
        sys.exit("Keine Preise gefunden – vermutlich wurde die Abfrage blockiert.")


if __name__ == "__main__":
    main()
