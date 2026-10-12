# Energiehubs dashboard — Railway

Statische site (HTML + d3 + JSON), geserveerd door een minimale Python-webserver in Docker.

## Deploy
1. Zet deze map in een GitHub-repo (of `railway init` + `railway up` vanuit deze map).
2. Railway: New Project → Deploy from GitHub repo. Railway pakt de `Dockerfile` op via `railway.json`.
3. Settings → Networking → Generate Domain. Railway zet zelf `PORT`.

## Data bijwerken
Vervang `public/energiehubs.json`. Provinciegrenzen staan in `public/provincies.json` (CBS/PDOK via cartomap, 2023).
`python clean.py Energiehubs_Uniform_Fases_RES_REGIO.xlsx` (vereist pandas + openpyxl).
Contactpersonen, e-mail en telefoon worden bewust niet meegenomen.

## Learning communities
`public/communities.json` en `public/community_links.json` komen uit `communities_hubs_brongestuurd.xlsx` (maart 2026).
Hubs zijn op naam en provincie gekoppeld aan de inventarisatie (`hub_id`); 8 hubs uit het overzicht staan niet in de inventarisatie en hebben geen `hub_id`.
