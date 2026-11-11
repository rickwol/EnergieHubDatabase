#!/usr/bin/env python3
"""
fetch_radar.py — Haal alle initiatieven op van de energiehubs.nl Initiatievenradar.

De radar is een Next.js-app die de lijst volledig client-side rendert; een platte
HTTP-fetch ziet de hubs niet. We gebruiken daarom Playwright (headless Chromium):
de browser rendert elke ?view=list&page=N, we wachten tot de hub-kaarten er staan
en lezen de tekst per kaart uit. De parser-logica werkt op dezelfde ankerregels
als voorheen ("... aangesloten", provincie-code, netbeheerder, status).

Output: radar_data/radar_raw.json  (lijst van dicts, 1 per initiatief)

Vereist: playwright  (pip install playwright && playwright install chromium)
"""
from __future__ import annotations
import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://energiehubs.nl/initiatieven?view=list&page={page}"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "radar_data" / "radar_raw.json"

NETBEHEERDERS = {"Enexis", "Liander", "Stedin", "Westland Infra", "RENDO", "Coteq", "Rendo"}
STATUSSEN = {"Actief", "Gestopt", "On hold"}
PROV_CODES = {"GR", "FR", "DR", "OV", "FL", "GE", "UT", "NH", "ZH", "ZE", "NB", "LI"}

# Teksten die geen hub-veld zijn en bij het parsen genegeerd worden.
NOISE = {
    "contact", "bekijk case", "ben jij betrokken bij dit initiatief?",
    "aanmelden als deelnemer", "initiatief aanmelden", "filters", "kaart",
}


def page_lines(page_text: str) -> list[str]:
    """Splits de innerText van <main> in schone regels."""
    lines = [ln.strip() for ln in page_text.split("\n")]
    return [ln for ln in lines if ln]


def parse_initiatieven(lines: list[str]) -> list[dict]:
    """Vind initiatief-blokken via de 'aangesloten'-ankerregel en lees eromheen."""
    out = []
    idx = [i for i, ln in enumerate(lines) if re.search(r"bedrij(f|ven) aangesloten", ln)]
    for i in idx:
        try:
            mb = re.search(r"(\d+)\s+bedrij", lines[i])
            bedrijven = mb.group(1) if mb else ""

            # Gemeente (PROV) staat boven de aangesloten-regel.
            gem_line = None
            for j in range(i - 1, max(i - 9, -1), -1):
                m = re.search(r"\(([A-Z]{2})\)\s*$", lines[j])
                if m and m.group(1) in PROV_CODES:
                    gem_line = j
                    break
            if gem_line is None:
                continue
            mprov = re.search(r"^(.*?)\s*\(([A-Z]{2})\)\s*$", lines[gem_line])
            gemeente = mprov.group(1).strip()
            prov = mprov.group(2)

            plaats = lines[gem_line - 1] if gem_line - 1 >= 0 else ""
            naam = lines[gem_line - 2] if gem_line - 2 >= 0 else ""
            if naam.lower() in NOISE or not naam:
                continue

            fase = netbeheerder = status = ""
            energiedragers = []
            for k in range(i + 1, min(i + 10, len(lines))):
                ln = lines[k]
                low = ln.lower()
                if not fase and re.match(r"^(Verkennen|Plannen & Ontwerpen|Realisatie|Exploiteren)", ln):
                    fase = ln
                elif not netbeheerder and ln in NETBEHEERDERS:
                    netbeheerder = ln
                elif not status and ln in STATUSSEN:
                    status = ln
                elif status and ln not in STATUSSEN and low not in NOISE:
                    energiedragers.append(ln)
                    break

            out.append({
                "naam": naam, "plaats": plaats, "gemeente": gemeente,
                "provincie_code": prov, "bedrijven": bedrijven, "fase": fase,
                "netbeheerder": netbeheerder, "status": status or "Actief",
                "energiedrager": "; ".join(energiedragers),
            })
        except Exception:
            continue
    return out


def total_and_pages(page) -> tuple[int, int]:
    """Bepaal het aantal lijstresultaten en daaruit het aantal pagina's.

    De pagina toont twee tellers: 'N energiehubs in Nederland' (breed totaal) en
    'Resultaten: M' (wat de lijst echt toont). We pagineren op M. Het aantal
    pagina's leiden we af uit M / paginagrootte, met het hoogste zichtbare
    paginanummer als ondergrens — robuuster dan alleen de pager uitlezen.
    """
    body = page.inner_text("main")
    results = 0
    m = re.search(r"Resultaten:\s*(\d+)", body)
    if m:
        results = int(m.group(1))
    else:
        m2 = re.search(r"(\d+)\s+energiehubs in Nederland", body)
        results = int(m2.group(1)) if m2 else 0

    per_page = len(parse_initiatieven(page_lines(body))) or 12
    pages_calc = -(-results // per_page) if results else 1  # ceil
    pager_nums = [int(n) for n in re.findall(r"\b(\d{1,3})\b",
                  body.split("Aanmelden als deelnemer")[-1])]
    pages_visible = max(pager_nums) if pager_nums else 1
    return results, max(pages_calc, pages_visible)


def main():
    all_items = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(user_agent="Mozilla/5.0 (energiehubs-radar-bot; onderzoek HvA)")
        page = ctx.new_page()

        # Pagina 1 + totaal/aantal pagina's bepalen
        page.goto(BASE.format(page=1), wait_until="networkidle", timeout=60000)
        page.wait_for_selector("text=aangesloten", timeout=30000)
        total, max_page = total_and_pages(page)
        print(f"Radar: {total} initiatieven, {max_page} pagina's", file=sys.stderr)
        all_items += parse_initiatieven(page_lines(page.inner_text("main")))

        for pg in range(2, max_page + 1):
            page.goto(BASE.format(page=pg), wait_until="networkidle", timeout=60000)
            try:
                page.wait_for_selector("text=aangesloten", timeout=30000)
            except Exception:
                print(f"  pagina {pg}: geen hubs geladen, overslaan", file=sys.stderr)
                continue
            items = parse_initiatieven(page_lines(page.inner_text("main")))
            all_items += items
            print(f"  pagina {pg}: {len(items)} initiatieven", file=sys.stderr)
            time.sleep(0.5)

        browser.close()

    # Dedup binnen de radar op (naam, plaats)
    seen = {}
    for it in all_items:
        key = (it["naam"].lower().strip(), it["plaats"].lower().strip())
        seen.setdefault(key, it)
    result = list(seen.values())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Opgehaald: {len(result)} unieke initiatieven → {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
