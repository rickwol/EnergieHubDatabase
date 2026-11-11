#!/usr/bin/env python3
"""
geocode_missing.py — Vul GPS-coördinaten aan voor hubs die ze nog missen.

Gebruikt OpenStreetMap/Nominatim (gratis, geen API-key). Zoekt per hub op
"<plaats>, <gemeente>, Nederland" en valt terug op alleen de gemeente. Respecteert
Nominatim's limiet van 1 verzoek/seconde. Schrijft de coördinaten terug in de
GPS_Coordinate-kolom van de Excel, en laat bestaande waarden ongemoeid.

Let op: dit geeft GPS op plaats/gemeenteniveau — goed genoeg om een hub op de kaart
te zetten, maar niet het exacte middelpunt van het bedrijventerrein. Een nieuwe
hub verschijnt zo wél meteen op de kaart in plaats van onzichtbaar te blijven.

Gebruik:
  python scripts/geocode_missing.py            # alle rijen zonder GPS
  python scripts/geocode_missing.py --limit 20 # eerste 20 (testen)
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
XLSX = Path(os.environ.get("DATASET_PATH", ROOT / "Energiehubs_Uniform_Fases_RES_REGIO.xlsx"))

COL_NAAM, COL_PLAATS, COL_GPS = 1, 4, 7
UA = "energiehubs-geocode/1.0 (onderzoek HvA; r.wolbertus)"


def geocode(query: str) -> str | None:
    url = (f"https://nominatim.openstreetmap.org/search?q={quote(query)}"
           f"&format=json&limit=1&countrycodes=nl")
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        if data:
            return f"{float(data[0]['lat']):.4f}, {float(data[0]['lon']):.4f}"
    except Exception as e:
        print(f"    ! {e}", file=sys.stderr)
    return None


def gemeente_van(plaats_cell: str) -> str:
    # In deze dataset staat 'Adres' als '<plaats> (<gemeente>)'; plaats zelf is kolom 4.
    return plaats_cell


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Sheet1"]

    todo = [r for r in range(2, ws.max_row + 1)
            if not str(ws.cell(r, COL_GPS).value or "").strip()
            and ws.cell(r, COL_NAAM).value]
    if args.limit:
        todo = todo[: args.limit]

    print(f"Te geocoderen: {len(todo)} hubs", file=sys.stderr)
    gelukt = 0
    for r in todo:
        naam = ws.cell(r, COL_NAAM).value
        plaats = str(ws.cell(r, COL_PLAATS).value or "").strip()
        coord = None
        if plaats:
            coord = geocode(f"{plaats}, Nederland")
            time.sleep(1.1)
        if not coord and plaats:
            # tweede poging met 'bedrijventerrein'
            coord = geocode(f"bedrijventerrein {plaats}, Nederland")
            time.sleep(1.1)
        if coord:
            ws.cell(r, COL_GPS).value = coord
            gelukt += 1
            print(f"  ✓ {naam} ({plaats}) → {coord}", file=sys.stderr)
        else:
            print(f"  – {naam} ({plaats}): niets gevonden", file=sys.stderr)
        if gelukt and gelukt % 25 == 0:
            wb.save(XLSX)   # tussentijds opslaan

    wb.save(XLSX)
    print(f"GPS ingevuld voor {gelukt}/{len(todo)} hubs", file=sys.stderr)


if __name__ == "__main__":
    main()
