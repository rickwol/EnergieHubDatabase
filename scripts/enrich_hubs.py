#!/usr/bin/env python3
"""
enrich_hubs.py — Agentische verrijking van nieuwe energiehubs.

Voor elke hub die nog geen direct contact of GPS heeft, laat dit script Claude
(met de ingebouwde web_search-tool) zoeken naar:
  - een direct contact (organisatie/coöperatie/parkmanagement, persoon, e-mail, telefoon)
  - GPS-coördinaten van het bedrijventerrein
  - een specifieke bron-URL

Elk veld krijgt een betrouwbaarheid mee (high/medium/low) plus een bron, zodat je
weet wat je kunt vertrouwen en wat je moet nachecken. Niets wordt klakkeloos
overschreven: bestaande handmatige waarden blijven staan tenzij --overwrite.

Vereist:  ANTHROPIC_API_KEY in de omgeving.
Kosten:   ~enkele centen per hub (web search + een paar duizend tokens).

Gebruik:
  python scripts/enrich_hubs.py                 # alle rijen zonder direct contact
  python scripts/enrich_hubs.py --only-new      # alleen rijen van de laatste radar-run
  python scripts/enrich_hubs.py --limit 10      # eerste 10 kandidaten (testen)
  python scripts/enrich_hubs.py --min-companies 5   # alleen hubs met >=5 bedrijven
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill

try:
    import anthropic
except ImportError:
    sys.exit("Installeer eerst de SDK:  pip install anthropic")

ROOT = Path(__file__).resolve().parent.parent
XLSX = Path(os.environ.get("DATASET_PATH", ROOT / "Energiehubs_Uniform_Fases_RES_REGIO.xlsx"))
REPORT = ROOT / "radar_data" / "enrichment_report.md"

MODEL = os.environ.get("ENRICH_MODEL", "claude-opus-4-8")

# Kolomindexen (1-based) in blad 'Sheet1'
COL = {
    "naam": 1, "url": 2, "provincie": 3, "plaats": 4, "adres": 5, "fase": 6,
    "gps": 7, "deelnemers": 11, "contactpersoon": 14, "email": 15,
    "telefoon": 16, "bron": 17,
}

# Betrouwbaarheid -> celkleur voor de contact/gps-cellen
CONF_FILL = {"high": "D4EDDA", "medium": "FFF3CD", "low": "FFE0E0"}

SYSTEM = """Je bent een onderzoeksassistent die contactgegevens en locaties opzoekt \
voor Nederlandse energiehubs op bedrijventerreinen. Je zoekt uitsluitend op het \
openbare web. Je verzint NOOIT gegevens: als je iets niet betrouwbaar kunt vinden, \
geef je het veld leeg terug met confidence "low". Je geeft e-mailadressen van \
organisaties/parkmanagement/coöperaties/gemeenten, nooit privé-adressen van \
individuen. Antwoord ALLEEN met geldige JSON volgens het gevraagde schema."""

PROMPT = """Zoek openbare gegevens voor deze energiehub:

Naam: {naam}
Plaats: {plaats}
Provincie: {provincie}
Netbeheerder/typering: {typering}

Zoek naar:
1. De organisatie die de hub trekt (coöperatie, parkmanagement/BIZ, of gemeente) \
   met een algemeen e-mailadres en eventueel een contactpersoon + telefoon.
2. GPS-coördinaten (lat, lon in decimale graden) van het betreffende \
   bedrijventerrein — het middelpunt volstaat.
3. De meest specifieke bron-URL (eigen website van de hub/coöperatie als die \
   bestaat; anders een gemeente- of nieuwspagina die specifiek over deze hub gaat).

Geef JSON terug met exact deze structuur:
{{
  "contactpersoon": "",
  "email": "",
  "telefoon": "",
  "gps": "lat, lon",
  "bron_url": "",
  "toelichting": "1 zin: welke organisatie en waarom dit het juiste contact is",
  "confidence": {{"contact": "high|medium|low", "gps": "high|medium|low"}}
}}

Laat velden leeg ("") als je ze niet betrouwbaar vindt. Verzin niets."""


def build_client() -> "anthropic.Anthropic":
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY ontbreekt in de omgeving.")
    return anthropic.Anthropic(api_key=key)


def enrich_one(client, hub: dict) -> dict | None:
    """Vraag Claude (met web search) om verrijking; retourneer parsed JSON of None."""
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            messages=[{"role": "user", "content": PROMPT.format(**hub)}],
        )
    except Exception as e:
        print(f"    ! API-fout voor {hub['naam']}: {e}", file=sys.stderr)
        return None

    # Pak de laatste tekstblok en haal er JSON uit
    text = ""
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text = block.text
    if not text:
        return None
    # JSON kan in ```json ... ``` staan
    import re
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-new", action="store_true",
                    help="alleen rijen die als 'automatisch toegevoegd via radar' zijn gemarkeerd")
    ap.add_argument("--limit", type=int, default=0, help="max aantal hubs (0 = alle)")
    ap.add_argument("--min-companies", type=int, default=0,
                    help="sla hubs over met minder dan N aangesloten bedrijven")
    ap.add_argument("--overwrite", action="store_true",
                    help="overschrijf ook cellen die al een waarde hebben")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Sheet1"]
    client = build_client()

    # Kies kandidaten: rijen zonder direct contact (of zonder GPS)
    kandidaten = []
    for rij in range(2, ws.max_row + 1):
        naam = ws.cell(rij, COL["naam"]).value
        if not naam:
            continue
        bron = (ws.cell(rij, COL["bron"]).value or "")
        heeft_direct = ("vangnet" not in bron.lower()) and bool(ws.cell(rij, COL["contactpersoon"]).value)
        heeft_gps = bool(ws.cell(rij, COL["gps"]).value)
        if args.only_new and "automatisch toegevoegd via radar" not in bron:
            continue
        if heeft_direct and heeft_gps and not args.overwrite:
            continue
        try:
            n_bedr = int(str(ws.cell(rij, COL["deelnemers"]).value or "0").split()[0])
        except (ValueError, IndexError):
            n_bedr = 0
        if n_bedr < args.min_companies:
            continue
        kandidaten.append((rij, n_bedr))

    # Meest gevorderde/grootste eerst
    kandidaten.sort(key=lambda x: -x[1])
    if args.limit:
        kandidaten = kandidaten[: args.limit]

    print(f"Kandidaten voor verrijking: {len(kandidaten)}", file=sys.stderr)
    report = [f"# Verrijkingsrapport ({len(kandidaten)} hubs)", ""]
    verrijkt = 0

    for rij, n_bedr in kandidaten:
        hub = {
            "naam": ws.cell(rij, COL["naam"]).value,
            "plaats": ws.cell(rij, COL["plaats"]).value or "",
            "provincie": ws.cell(rij, COL["provincie"]).value or "",
            "typering": ws.cell(rij, COL["url"]).value or "",
        }
        print(f"  [{rij}] {hub['naam']} ({hub['plaats']})…", file=sys.stderr)
        data = enrich_one(client, hub)
        if not data:
            report.append(f"- **{hub['naam']}** ({hub['plaats']}): geen bruikbaar resultaat")
            continue

        conf = data.get("confidence", {})
        conf_contact = conf.get("contact", "low")
        conf_gps = conf.get("gps", "low")

        def set_cell(col, value, confidence):
            if not value:
                return
            cell = ws.cell(rij, COL[col])
            if cell.value and not args.overwrite:
                return
            cell.value = value
            fill = CONF_FILL.get(confidence)
            if fill:
                cell.fill = PatternFill("solid", start_color=fill)
                cell.font = Font(name="Arial", size=9)

        set_cell("contactpersoon", data.get("contactpersoon"), conf_contact)
        set_cell("email", data.get("email"), conf_contact)
        set_cell("telefoon", data.get("telefoon"), conf_contact)
        set_cell("gps", data.get("gps"), conf_gps)

        # Bron-kolom bijwerken met toelichting + betrouwbaarheid
        toel = data.get("toelichting", "")
        url = data.get("bron_url", "")
        bron_cell = ws.cell(rij, COL["bron"])
        suffix = f" | [auto-verrijkt: contact={conf_contact}, gps={conf_gps}]"
        if toel or url:
            bron_cell.value = (f"{toel} {url}".strip() + suffix)

        report.append(
            f"- **{hub['naam']}** ({hub['plaats']}) — contact: {conf_contact}, gps: {conf_gps}"
            + (f" | {data.get('email')}" if data.get("email") else "")
        )
        verrijkt += 1
        wb.save(XLSX)       # tussentijds opslaan: veilig bij onderbreking
        time.sleep(1)

    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Verrijkt: {verrijkt}/{len(kandidaten)} | Rapport → {REPORT}", file=sys.stderr)


if __name__ == "__main__":
    main()
