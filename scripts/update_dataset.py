#!/usr/bin/env python3
"""
update_dataset.py — Vergelijk de opgehaalde radar met de bestaande Excel-dataset,
voeg nieuwe hubs toe, en schrijf een changelog.

Leest:   data/radar_raw.json        (van fetch_radar.py)
         data/dataset.xlsx          (de lopende dataset; blad 'Sheet1')
Schrijft:data/dataset.xlsx          (bijgewerkt in-place)
         data/changelog.md          (wat is nieuw / gestopt / van fase veranderd)
         data/radar_snapshot.csv     (volledige radar als platte CSV, voor diff/historie)

Geocoding is optioneel: zet env GEOCODE=1 om nieuwe hubs via Nominatim (OSM) van
GPS te voorzien. Zonder dat blijft GPS leeg en wordt het in de changelog gemarkeerd
als handmatig aan te vullen.
"""
from __future__ import annotations
import csv
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

ROOT = Path(__file__).resolve().parent.parent
# In de EnergieHubDatabase-repo staat de Excel in de root. Instelbaar via env.
XLSX = Path(os.environ.get("DATASET_PATH", ROOT / "Energiehubs_Uniform_Fases_RES_REGIO.xlsx"))
DATA_DIR = ROOT / "radar_data"          # werkmap voor radar-output (los van je app)
RAW = DATA_DIR / "radar_raw.json"
CHANGELOG = DATA_DIR / "changelog.md"
SNAPSHOT = DATA_DIR / "radar_snapshot.csv"

PROV_FULL = {
    "GR": "Groningen", "FR": "Friesland", "DR": "Drenthe", "OV": "Overijssel",
    "FL": "Flevoland", "GE": "Gelderland", "UT": "Utrecht", "NH": "Noord-Holland",
    "ZH": "Zuid-Holland", "ZE": "Zeeland", "NB": "Noord-Brabant", "LI": "Limburg",
}
PROV_EMAIL = {
    "ZH": "energie-infrastructuur@pzh.nl", "FL": "info@flevoland.nl", "ZE": "info@zeeland.nl",
    "UT": "energiehub@provincie-utrecht.nl", "FR": "energie@fryslan.frl", "GE": "energie@gelderland.nl",
    "GR": "info@provinciegroningen.nl", "LI": "info@liof.nl", "NH": "Ron.de.graaf@noord-holland.nl",
    "NB": "energiehubs@brabant.nl", "DR": "energiehubs@drenthe.nl", "OV": "secretariaatNEO@overijssel.nl",
}
FASE_MAP = {
    "verkennen": "Fase 1: Verkennen",
    "plannen & ontwerpen": "Fase 2: Plannen & Ontwerpen",
    "realisatie": "Fase 3: Realiseren",
    "exploiteren": "Fase 4: Exploiteren",
}

# Kleuren
BG_NIEUW = "FFD9A0"
BG_GESTOPT = "FFE0E0"
BG_ONHOLD = "E8E8E8"

STOPWORDS = {"energiehub", "energie", "hub", "energyhub", "ehub", "seh", "mceh",
             "energiehubs", "bedrijventerrein", "bt", "de", "het", "van", "bv"}


def norm(s: str) -> str:
    # Accent-ongevoelig: 'Siberië' en 'Siberie' moeten matchen, net als é/ë/ö/'.
    import unicodedata
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    words = [w for w in re.split(r"[^a-z0-9]+", s) if w and w not in STOPWORDS]
    return "".join(words)


def map_fase(radar_fase: str) -> str:
    low = (radar_fase or "").lower()
    for k, v in FASE_MAP.items():
        if low.startswith(k):
            return v
    return "Fase 1: Verkennen"


def geocode(adres: str, gemeente: str) -> str:
    """Optioneel: OSM Nominatim. Retourneert 'lat, lon' of ''. Respecteert rate-limit."""
    if os.environ.get("GEOCODE") != "1":
        return ""
    from urllib.request import Request, urlopen
    from urllib.parse import quote
    q = f"{adres}, {gemeente}, Nederland" if adres else f"{gemeente}, Nederland"
    url = f"https://nominatim.openstreetmap.org/search?q={quote(q)}&format=json&limit=1&countrycodes=nl"
    try:
        req = Request(url, headers={"User-Agent": "energiehubs-radar-bot/1.0 (onderzoek HvA)"})
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        time.sleep(1.1)  # Nominatim: max 1 req/sec
        if data:
            return f"{float(data[0]['lat']):.4f}, {float(data[0]['lon']):.4f}"
    except Exception:
        pass
    return ""


def load_existing(ws) -> dict:
    """Map genormaliseerde (naam|plaats) -> (rij, naam, fase, status)."""
    existing = {}
    for rij in range(2, ws.max_row + 1):
        naam = ws.cell(rij, 1).value or ""
        plaats = ws.cell(rij, 4).value or ""
        fase = ws.cell(rij, 6).value or ""
        if not naam:
            continue
        key = norm(naam) + "|" + norm(plaats)
        key_alt = norm(naam)
        existing[key] = {"rij": rij, "naam": naam, "fase": fase}
        existing.setdefault(key_alt, {"rij": rij, "naam": naam, "fase": fase})
    return existing


def style_cell(c, bg):
    s = Side(style="thin", color="CCCCCC")
    c.fill = PatternFill("solid", start_color=bg)
    c.font = Font(name="Arial", size=9)
    c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    c.border = Border(left=s, right=s, top=s, bottom=s)


def main():
    radar = json.loads(RAW.read_text(encoding="utf-8"))
    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Sheet1"]
    existing = load_existing(ws)

    nieuw, fase_changed, gestopt = [], [], []

    for it in radar:
        key = norm(it["naam"]) + "|" + norm(it["plaats"])
        key_alt = norm(it["naam"])
        match = existing.get(key) or existing.get(key_alt)
        uni_fase = map_fase(it["fase"])
        if match is None:
            nieuw.append(it)
        else:
            old_fase = match["fase"] or ""
            if old_fase and uni_fase and old_fase != uni_fase and old_fase.startswith("Fase"):
                fase_changed.append((match["naam"], old_fase, uni_fase))
            if it["status"].lower() == "gestopt" and "gestopt" not in old_fase.lower():
                gestopt.append(match["naam"])

    # Nieuwe hubs toevoegen
    start = ws.max_row + 1
    for i, it in enumerate(nieuw):
        rij = start + i
        pc = it["provincie_code"]
        st = it["status"].lower()
        bg = BG_GESTOPT if "gestopt" in st else (BG_ONHOLD if "hold" in st else BG_NIEUW)
        adres = f"{it['plaats']} ({it['gemeente']})"
        gps = geocode("", it["gemeente"])
        waarden = [
            it["naam"], "https://energiehubs.nl/initiatieven", PROV_FULL.get(pc, pc),
            it["plaats"], adres, map_fase(it["fase"]), gps, "Bedrijventerrein",
            f"Energiehubs.nl radar (auto {date.today()}) | {it['netbeheerder']} | "
            f"{it['bedrijven']} bedr | {it['fase']}",
            "", it["bedrijven"], it["energiedrager"], "",
            "", PROV_EMAIL.get(pc, ""), "",
            f"Provinciaal vangnet ({PROV_FULL.get(pc, pc)}) | automatisch toegevoegd via radar",
        ]
        for ci, val in enumerate(waarden, 1):
            style_cell(ws.cell(rij, ci, val), bg)
        ws.row_dimensions[rij].height = 16

    wb.save(XLSX)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Changelog
    lines = [f"# Radar-update {date.today()}", ""]
    lines.append(f"- Radar bevat **{len(radar)}** initiatieven")
    lines.append(f"- Dataset telt nu **{ws.max_row - 1}** hubs (+{len(nieuw)} nieuw)")
    lines.append("")
    if nieuw:
        lines.append(f"## {len(nieuw)} nieuwe hubs")
        for it in sorted(nieuw, key=lambda x: x["provincie_code"]):
            gps_flag = "" if os.environ.get("GEOCODE") == "1" else " _(GPS handmatig aanvullen)_"
            lines.append(f"- **{it['naam']}** — {it['plaats']} ({PROV_FULL.get(it['provincie_code'], it['provincie_code'])}) "
                         f"| {map_fase(it['fase'])} | {it['bedrijven']} bedr | {it['netbeheerder']} | {it['status']}{gps_flag}")
        lines.append("")
    if fase_changed:
        lines.append(f"## {len(fase_changed)} fasewijzigingen")
        for naam, oud, nieuw_f in fase_changed:
            lines.append(f"- **{naam}**: {oud} → {nieuw_f}")
        lines.append("")
    if gestopt:
        lines.append(f"## {len(gestopt)} nu gemarkeerd als gestopt")
        for naam in gestopt:
            lines.append(f"- {naam}")
        lines.append("")
    if not (nieuw or fase_changed or gestopt):
        lines.append("_Geen wijzigingen t.o.v. de huidige dataset._")
    CHANGELOG.write_text("\n".join(lines), encoding="utf-8")

    # Snapshot CSV (volledige radar, voor historie/diff in git)
    with SNAPSHOT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(radar[0].keys()) if radar else [])
        if radar:
            w.writeheader()
            w.writerows(sorted(radar, key=lambda x: (x["provincie_code"], x["naam"])))

    print(f"Nieuw: {len(nieuw)} | Faseverandering: {len(fase_changed)} | Gestopt: {len(gestopt)}",
          file=sys.stderr)
    print(f"Changelog → {CHANGELOG}", file=sys.stderr)


if __name__ == "__main__":
    main()
