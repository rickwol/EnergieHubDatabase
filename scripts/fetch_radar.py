#!/usr/bin/env python3
"""
fetch_radar.py — Haal alle initiatieven op van de energiehubs.nl Initiatievenradar.

De radar rendert client-side, maar de ?view=list weergave levert server-side HTML
met alle velden. We pagineren over ?view=list&page=N tot alle resultaten binnen zijn.

Output: data/radar_raw.json  (lijst van dicts, 1 per initiatief)
"""
from __future__ import annotations
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = "https://energiehubs.nl/initiatieven?view=list&page={page}"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "radar_data" / "radar_raw.json"

UA = "energiehubs-radar-bot/1.0 (+https://github.com; onderzoek HvA)"

# Eén initiatief-blok op de ?view=list pagina ziet er (als platte tekst) zo uit:
#   <naam>
#   <plaats>
#   <gemeente> (<PROV>)
#   Contact
#   [Bekijk case](...)            <- optioneel
#   N bedrijven aangesloten        (of "N bedrijf aangesloten")
#   <fase>: <subfase>
#   <netbeheerder>
#   <typering, komma-gescheiden>
#   <status>                       (Actief / Gestopt / On hold)
#   <energiedragers, komma-gescheiden>
#
# We parsen defensief op basis van ankerregels ("... aangesloten", provincie-code,
# bekende netbeheerders en statuswaarden) in plaats van op vaste posities.

NETBEHEERDERS = {"Enexis", "Liander", "Stedin", "Westland Infra", "RENDO", "Coteq", "Rendo"}
STATUSSEN = {"Actief", "Gestopt", "On hold"}
PROV_CODES = {"GR", "FR", "DR", "OV", "FL", "GE", "UT", "NH", "ZH", "ZE", "NB", "LI"}


def fetch_page(page: int, retries: int = 3) -> str:
    url = BASE.format(page=page)
    last = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except (URLError, HTTPError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Kon pagina {page} niet ophalen: {last}")


def html_to_lines(html: str) -> list[str]:
    """Strip tags, behoud tekst per regel, normaliseer whitespace."""
    # Verwijder scripts/styles
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Blok-elementen -> newline
    html = re.sub(r"</(p|div|li|h[1-6]|tr|td|section|article)>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    # Links: behoud tekst + markeer
    html = re.sub(r"<[^>]+>", "\n", html)
    # HTML-entities
    for a, b in [("&amp;", "&"), ("&quot;", '"'), ("&#x27;", "'"), ("&#39;", "'"),
                 ("&nbsp;", " "), ("&eacute;", "é"), ("&euml;", "ë"), ("&ouml;", "ö")]:
        html = html.replace(a, b)
    lines = [ln.strip() for ln in html.split("\n")]
    return [ln for ln in lines if ln]


def total_results(lines: list[str]) -> int | None:
    for ln in lines:
        m = re.search(r"Resultaten:\s*(\d+)", ln)
        if m:
            return int(m.group(1))
    return None


def parse_initiatieven(lines: list[str]) -> list[dict]:
    """Vind initiatief-blokken via de 'aangesloten'-ankerregel en lees eromheen."""
    out = []
    idx = [i for i, ln in enumerate(lines) if re.search(r"bedrij(f|ven) aangesloten", ln)]
    for i in idx:
        try:
            # bedrijven
            mb = re.search(r"(\d+)\s+bedrij", lines[i])
            bedrijven = mb.group(1) if mb else ""

            # Terugwerken: boven de "aangesloten"-regel staan Contact / Bekijk case,
            # en daarboven: naam, plaats, "gemeente (PROV)".
            # Zoek de gemeente+prov regel boven i.
            gem_line = None
            for j in range(i - 1, max(i - 8, -1), -1):
                if re.search(r"\(([A-Z]{2})\)\s*$", lines[j]) and \
                   re.search(r"\(([A-Z]{2})\)", lines[j]).group(1) in PROV_CODES:
                    gem_line = j
                    break
            if gem_line is None:
                continue
            mprov = re.search(r"^(.*?)\s*\(([A-Z]{2})\)\s*$", lines[gem_line])
            gemeente = mprov.group(1).strip()
            prov = mprov.group(2)

            # plaats = regel direct boven gemeente; naam = regel daarboven
            plaats = lines[gem_line - 1] if gem_line - 1 >= 0 else ""
            naam = lines[gem_line - 2] if gem_line - 2 >= 0 else ""
            # Als naam == "Initiatievenradar" o.i.d., sla over (header-bleed)
            if naam.lower() in ("initiatievenradar", "contact", "filters"):
                continue

            # Vooruit lezen vanaf i: fase, netbeheerder, status, energiedragers
            fase = netbeheerder = status = ""
            energiedragers = []
            for k in range(i + 1, min(i + 10, len(lines))):
                ln = lines[k]
                if not fase and re.match(r"^(Verkennen|Plannen & Ontwerpen|Realisatie|Exploiteren)", ln):
                    fase = ln
                elif not netbeheerder and ln in NETBEHEERDERS:
                    netbeheerder = ln
                elif not status and ln in STATUSSEN:
                    status = ln
                elif status and ln not in STATUSSEN and "legenda" not in ln.lower() \
                        and "betrokken" not in ln.lower() and "aanmelden" not in ln.lower():
                    # energiedragers staan na de status
                    energiedragers.append(ln)
                    break

            out.append({
                "naam": naam,
                "plaats": plaats,
                "gemeente": gemeente,
                "provincie_code": prov,
                "bedrijven": bedrijven,
                "fase": fase,
                "netbeheerder": netbeheerder,
                "status": status or "Actief",
                "energiedrager": "; ".join(energiedragers),
            })
        except Exception:
            continue
    return out


def main():
    html1 = fetch_page(1)
    lines1 = html_to_lines(html1)
    total = total_results(lines1) or 0
    per_page = 12
    pages = max(1, -(-total // per_page)) if total else 18  # ceil
    print(f"Totaal resultaten volgens radar: {total} → {pages} pagina's", file=sys.stderr)

    seen = {}
    all_items = parse_initiatieven(lines1)
    for page in range(2, pages + 1):
        html = fetch_page(page)
        items = parse_initiatieven(html_to_lines(html))
        all_items.extend(items)
        print(f"  pagina {page}: {len(items)} initiatieven", file=sys.stderr)
        time.sleep(1)  # vriendelijk pauzeren

    # Dedup binnen de radar op (naam, plaats)
    for it in all_items:
        key = (it["naam"].lower().strip(), it["plaats"].lower().strip())
        if key not in seen:
            seen[key] = it

    result = list(seen.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Opgehaald: {len(result)} unieke initiatieven → {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
