#!/usr/bin/env python3
"""
relink_communities.py — Herbereken hub_id in de community-koppelingen.

De `id` in public/energiehubs.json is het rijnummer uit de Excel (clean.py doet
id = i+1). Dat nummer verschuift zodra de dataset van volgorde verandert — wat bij
een radar-update gebeurt. De koppelingen in public/community_links.json verwijzen
naar die id's en raken dan stilletjes verkeerd.

Dit script zet elke link opnieuw op de juiste hub, door `naam_in_inventarisatie`
(de hubnaam zoals die in de inventarisatie staat) op te zoeken in de actuele
energiehubs.json — accent-ongevoelig en met provincie als tiebreaker. Het laat de
inhoudelijke koppeling (welke hub bij welke community) volledig intact; het
corrigeert alleen de hub_id-verwijzing.

Uitvoer: public/community_links.json wordt in-place bijgewerkt.
         Een kort rapport van niet-herkoppelbare links gaat naar stderr.
"""
from __future__ import annotations
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HUBS = ROOT / "public" / "energiehubs.json"
LINKS = ROOT / "public" / "community_links.json"


def norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s)


def main():
    hubs = json.loads(HUBS.read_text(encoding="utf-8"))
    links = json.loads(LINKS.read_text(encoding="utf-8"))

    # Indexeer hubs op genormaliseerde naam (+ provincie als tiebreaker).
    by_name: dict[str, list] = {}
    for h in hubs:
        by_name.setdefault(norm(h.get("naam", "")), []).append(h)

    hersteld = behouden = niet_gevonden = 0
    ontbrekend = []

    for link in links:
        inv = link.get("naam_in_inventarisatie") or link.get("hub") or ""
        prov = (link.get("provincie") or "").strip().lower()
        kandidaten = by_name.get(norm(inv), [])

        gekozen = None
        if len(kandidaten) == 1:
            gekozen = kandidaten[0]
        elif len(kandidaten) > 1:
            # meerdere hubs met dezelfde naam: kies op provincie
            prov_match = [h for h in kandidaten if (h.get("provincie") or "").strip().lower() == prov]
            gekozen = prov_match[0] if prov_match else kandidaten[0]

        if gekozen is None:
            # Geen match op naam_in_inventarisatie: dit blijft handwerk (8 bekende gevallen).
            niet_gevonden += 1
            ontbrekend.append(f"{link.get('hub')} ({link.get('provincie')}) – community {link.get('community')}")
            link["hub_id"] = None
            continue

        oud = link.get("hub_id")
        link["hub_id"] = gekozen["id"]
        if oud == gekozen["id"]:
            behouden += 1
        else:
            hersteld += 1

    LINKS.write_text(json.dumps(links, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Links: {len(links)} | id ongewijzigd: {behouden} | "
          f"id gecorrigeerd: {hersteld} | geen hub-match: {niet_gevonden}", file=sys.stderr)
    if ontbrekend:
        print("Niet gekoppeld (handmatig te controleren):", file=sys.stderr)
        for o in ontbrekend:
            print(f"  – {o}", file=sys.stderr)


if __name__ == "__main__":
    main()
