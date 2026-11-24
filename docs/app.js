// Bella Vista Preiswächter – Anzeige der Ergebnisse (liest data.json)
"use strict";
const GRUPPEN = [
  { key: "woche", titel: "1 Woche", untertitel: "6 oder 7 Nächte" },
  { key: "zehn", titel: "10 Tage", untertitel: "8 oder 9 Nächte" }
];
const $ = (id) => document.getElementById(id);
const WT = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];
function de(s) { if (!s) return "–"; const d = new Date(s + "T12:00:00"); return WT[d.getDay()] + ", " + String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0") + "." + d.getFullYear(); }
const eur = (n) => new Intl.NumberFormat("de-AT", { maximumFractionDigits: 0 }).format(n) + " €";
function el(tag, cls, txt) { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
function knopf(txt, url, alt) { if (!url || !url.startsWith("https://")) return null; const a = el("a", "btn" + (alt ? " alt" : ""), txt); a.href = url; a.target = "_blank"; a.rel = "noopener"; return a; }

function zeigeGruppe(g, res) {
  const box = $("erg-" + g.key); box.textContent = "";
  const kopf = el("div", "res-head"); kopf.append(el("h2", null, g.titel), el("span", "when", g.untertitel)); box.append(kopf);
  const p = res && res.pauschal, e = res && res.getrennt;
  const best = [p, e].filter(Boolean).sort((x, y) => x.preis - y.preis)[0];
  if (!best) { box.append(el("p", "none", "Bei der letzten Suche wurde kein Preis gefunden.")); return; }
  const b = el("div", "best");
  b.append(el("div", "lbl", "Bester Preis"), el("div", "price", eur(best.preis)),
    el("div", "what", (best === e ? "Flug und Hotel einzeln gebucht" : "Pauschalreise") + " · " + de(best.abflug) + " bis " + de(best.rueckkehr) + " (" + best.naechte + " Nächte)"));
  box.append(b);

  const o1 = el("div", "opt"); const t1 = el("div", "opt-top");
  t1.append(el("span", "opt-name", "Pauschalreise (alles in einem)"), el("span", "opt-price", p ? eur(p.preis) : "–")); o1.append(t1);
  if (p) {
    o1.append(el("div", "opt-info", de(p.abflug) + " bis " + de(p.rueckkehr) + " (" + p.naechte + " Nächte)" + (p.notiz ? " · " + p.notiz : "")));
    const purl = p.url;
    const bt = el("div", "btns"); const k = knopf("Pauschalreise ansehen und buchen", purl); if (k) bt.append(k); o1.append(bt);
  } else o1.append(el("div", "opt-info", "Kein Angebot gefunden."));
  box.append(o1);

  const o2 = el("div", "opt"); const t2 = el("div", "opt-top");
  t2.append(el("span", "opt-name", "Flug und Hotel einzeln"), el("span", "opt-price", e ? eur(e.preis) : "–")); o2.append(t2);
  if (e) {
    o2.append(el("div", "opt-info", "Flug " + eur(e.flugPreis) + " + Hotel " + eur(e.hotelPreis) + " · " + de(e.abflug) + " bis " + de(e.rueckkehr) + (e.notiz ? " · " + e.notiz : "")));
    const bt = el("div", "btns"); const k1 = knopf("Flug ansehen und buchen", e.flugUrl); const k2 = knopf("Hotel ansehen und buchen", e.hotelUrl, true);
    if (k1) bt.append(k1); if (k2) bt.append(k2); o2.append(bt);
  } else o2.append(el("div", "opt-info", "Kein Angebot gefunden."));
  box.append(o2);
}

// ---------- Preisverlauf-Diagramm ----------
const SVGNS = "http://www.w3.org/2000/svg";
function s(tag, attrs, txt) { const e = document.createElementNS(SVGNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (txt != null) e.textContent = txt; return e; }
const kurz = (z) => { const d = new Date(z); return String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0") + "."; };

function verlaufBox(g, verlauf, grenze) {
  const box = el("div", "chart-box");
  box.append(el("div", "chart-title", "Preisverlauf " + g.titel));
  const pts = verlauf.map((v) => ({ zeit: v.zeit, p: v[g.key] && v[g.key].p, e: v[g.key] && v[g.key].e })).filter((v) => v.p != null || v.e != null);
  if (!pts.length) { box.append(el("div", "chart-empty", "Der Verlauf füllt sich mit jeder Suche.")); return box; }

  const leg = el("div", "legend");
  const li = (cls, txt, col) => { const sp = el("span"); const i = el("i", cls); if (col) i.style.background = col; sp.append(i, document.createTextNode(txt)); return sp; };
  leg.append(li("", "Pauschalreise", "var(--s1)"), li("", "Flug + Hotel einzeln", "var(--s2)"));
  if (grenze) leg.append(li("dash", "Ihr Preisalarm (" + eur(grenze) + ")"));
  box.append(leg);

  // Breite an den Bildschirm anpassen, damit die Schrift auf dem Handy lesbar bleibt
  const W = Math.min(720, Math.max(340, Math.round(window.innerWidth) - 70)), H = W < 500 ? 240 : 280, L = 70, R = W < 500 ? 125 : 150, T = 18, B = 40;
  const werte = pts.flatMap((v) => [v.p, v.e]).filter((x) => x != null);
  if (grenze) werte.push(grenze);
  let lo = Math.min(...werte), hi = Math.max(...werte);
  const pad = Math.max(30, (hi - lo) * 0.15); lo = Math.floor((lo - pad) / 50) * 50; hi = Math.ceil((hi + pad) / 50) * 50;
  const t0 = new Date(pts[0].zeit).getTime(), t1 = new Date(pts[pts.length - 1].zeit).getTime();
  const x = (z) => pts.length === 1 || t1 === t0 ? L + (W - L - R) / 2 : L + ((new Date(z).getTime() - t0) / (t1 - t0)) * (W - L - R);
  const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);

  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Preisverlauf " + g.titel });
  const schritt = Math.max(50, Math.ceil((hi - lo) / 4 / 50) * 50);
  for (let v = lo; v <= hi; v += schritt) {
    svg.append(s("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid" }));
    svg.append(s("text", { x: L - 10, y: y(v) + 5, "text-anchor": "end", class: "axis" }, eur(v)));
  }
  const xt = pts.length === 1 ? [pts[0]] : [pts[0], pts[pts.length - 1]];
  xt.forEach((v, i) => svg.append(s("text", { x: x(v.zeit), y: H - 10, "text-anchor": pts.length === 1 ? "middle" : i === 0 ? "start" : "end", class: "axis" }, kurz(v.zeit))));
  if (grenze) svg.append(s("line", { x1: L, x2: W - R, y1: y(grenze), y2: y(grenze), class: "limit" }));

  const endLabels = [];
  for (const [k, cls] of [["p", "p"], ["e", "e"]]) {
    const ser = pts.filter((v) => v[k] != null);
    if (!ser.length) continue;
    if (ser.length > 1) svg.append(s("path", { d: ser.map((v, i) => (i ? "L" : "M") + x(v.zeit) + " " + y(v[k])).join(" "), class: "ser-" + cls, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    ser.forEach((v) => svg.append(s("circle", { cx: x(v.zeit), cy: y(v[k]), r: 5, class: "dot-" + cls })));
    const last = ser[ser.length - 1];
    endLabels.push({ y: y(last[k]), x: x(last.zeit), txt: (k === "p" ? "Pauschal " : "Einzeln ") + eur(last[k]) });
  }
  endLabels.sort((a, b) => a.y - b.y);
  if (endLabels.length === 2 && endLabels[1].y - endLabels[0].y < 22) { const m = (endLabels[0].y + endLabels[1].y) / 2; endLabels[0].y = m - 11; endLabels[1].y = m + 11; }
  endLabels.forEach((l) => svg.append(s("text", { x: l.x + 12, y: l.y + 5, class: "lbl" }, l.txt)));

  // Hover: Fadenkreuz + Info
  const cross = s("line", { y1: T, y2: H - B, class: "cross", visibility: "hidden" });
  svg.append(cross);
  const hit = s("rect", { x: L - 20, y: 0, width: W - L - R + 40, height: H, fill: "transparent" });
  svg.append(hit);
  const wrap = el("div", "chart"); wrap.append(svg);
  const tip = el("div", "tip"); tip.hidden = true; wrap.append(tip);
  const zeige = (clientX) => {
    const r = svg.getBoundingClientRect(); const sx = ((clientX - r.left) / r.width) * W;
    let best = pts[0]; for (const v of pts) if (Math.abs(x(v.zeit) - sx) < Math.abs(x(best.zeit) - sx)) best = v;
    const cx = x(best.zeit); cross.setAttribute("x1", cx); cross.setAttribute("x2", cx); cross.setAttribute("visibility", "visible");
    tip.textContent = "";
    tip.append(el("b", null, new Date(best.zeit).toLocaleString("de-AT", { weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) + " Uhr"));
    for (const [k, txt, col] of [["p", "Pauschal", "var(--s1)"], ["e", "Einzeln", "var(--s2)"]]) {
      const d = el("div"); const i = el("i"); i.style.background = col; d.append(i, document.createTextNode(txt + ": " + (best[k] != null ? eur(best[k]) : "–"))); tip.append(d);
    }
    tip.hidden = false;
    const px = (cx / W) * r.width; tip.style.top = "0px";
    tip.style.left = Math.min(Math.max(0, px + 14), r.width - tip.offsetWidth) + "px";
  };
  hit.addEventListener("pointermove", (ev) => zeige(ev.clientX));
  hit.addEventListener("pointerdown", (ev) => zeige(ev.clientX));
  hit.addEventListener("pointerleave", () => { tip.hidden = true; cross.setAttribute("visibility", "hidden"); });
  box.append(wrap);
  if (pts.length === 1) box.append(el("div", "chart-empty", "Bisher eine Messung. Mit jeder weiteren Suche entsteht eine Linie."));
  return box;
}


async function laden() {
  let d;
  try {
    const r = await fetch("data.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    d = await r.json();
  } catch (e) {
    $("status").textContent = "Die Preise konnten gerade nicht geladen werden. Bitte später „Seite neu laden“ drücken.";
    return;
  }
  const erg = d.ergebnis || {}, alarm = d.alarm || {};
  $("status").textContent = erg.zeit ? "Zuletzt geprüft: " + new Date(erg.zeit).toLocaleString("de-AT", { dateStyle: "full", timeStyle: "short" }) + " Uhr" : "Noch keine Suche gelaufen.";
  $("zeitraum").textContent = erg.von ? "Gesuchter Reisezeitraum: " + de(erg.von) + " bis " + de(erg.bis) : "";
  for (const g of GRUPPEN) {
    zeigeGruppe(g, erg.gruppen && erg.gruppen[g.key]);
    $("erg-" + g.key).append(verlaufBox(g, d.verlauf || [], alarm[g.key]));
  }
  const teile = GRUPPEN.filter((g) => alarm[g.key]).map((g) => g.titel + " unter " + eur(alarm[g.key]));
  $("alarmText").textContent = teile.length
    ? "Eine Nachricht kommt aufs Handy, sobald ein Preis gefunden wird für: " + teile.join(" und ") + "."
    : "Derzeit ist kein Preisalarm eingestellt.";
  const b = $("alarmBanner"); b.textContent = "";
  const m = d.alarmMeldung;
  if (m && m.texte && m.texte.length) {
    b.append(el("b", null, "Preisalarm!"));
    for (const t of m.texte) b.append(el("div", null, t));
    b.hidden = false;
  } else b.hidden = true;
}
$("neu").addEventListener("click", () => { $("status").textContent = "Wird geladen …"; laden(); });
laden();
