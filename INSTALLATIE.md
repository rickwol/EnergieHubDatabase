# Automatische radar-sync voor EnergieHubDatabase (Railway)

Deze bestanden voegen een **wekelijkse automatische update** toe aan je bestaande
`rickwol/EnergieHubDatabase`-repo. De keten:

```
GitHub Action (ma 07:00)
  → haalt de energiehubs.nl initiatievenradar op
  → werkt Energiehubs_Uniform_Fases_RES_REGIO.xlsx bij (nieuwe hubs, gestopt, fasewijziging)
  → draait clean.py → regenereert public/energiehubs.json
  → commit beide bestanden terug naar de repo
Railway ziet de push → herdeployt → je dashboard toont de nieuwe hubs
```

Je hoeft dus **niets** aan je Dockerfile, railway.json of app te veranderen. Alleen
deze bestanden toevoegen aan de repo.

## Wat je toevoegt aan de repo

Leg deze bestanden op exact deze plekken in `EnergieHubDatabase`:

```
.github/workflows/update-energiehubs.yml      (nieuw)
scripts/fetch_radar.py                         (nieuw)
scripts/update_dataset.py                      (nieuw)
scripts/enrich_hubs.py                         (nieuw)
```

Je bestaande `clean.py`, `Dockerfile`, `railway.json` en `public/` blijven
ongewijzigd. De Action roept je eigen `clean.py` aan.

## Stappenplan

### 1. Bestanden toevoegen
Upload de vier bestanden hierboven naar je repo (via de GitHub-website:
*Add file → Upload files*, of met `git`). Let op dat `.github` een map met een punt
is — zet verborgen bestanden aan zodat je de workflow zeker meeneemt.

### 2. Workflow-rechten
Repo → **Settings → Actions → General → Workflow permissions** →
**Read and write permissions** → **Save**. Zonder dit kan de bot niet terugpushen.

### 3. Eerste testrun
Tabblad **Actions → Update energiehubs-data → Run workflow**. Na ~2 min zie je een
groen vinkje. Controleer dat er (als er nieuwe hubs waren) een commit is gemaakt en
dat Railway daarna herdeployt. Was er niets nieuw, dan commit de Action niets — dat
is correct gedrag, geen fout.

### 4. (optioneel) Agentische verrijking
Alleen nodig als je ook contact + GPS automatisch wilt laten opzoeken. Let op: je
`clean.py` zet contactgegevens **bewust niet** in de publieke JSON, dus verrijking
verbetert je Excel maar verschijnt niet op de site.
- Voeg een repo-secret toe: **Settings → Secrets and variables → Actions →
  New repository secret**, naam `ANTHROPIC_API_KEY`, waarde je key van
  console.anthropic.com (los pay-as-you-go-tegoed, staat los van je Claude-abonnement).
- Start dan **Run workflow** met **enrich = true**.

## Belangrijk om te weten

- **Accenten.** De dedup is accent-ongevoelig gemaakt ("Siberië" = "Siberie"),
  omdat de radar accenten soms anders schrijft dan jouw dataset. Zonder die fix
  zou je dubbele hubs krijgen. **Zet dezelfde fix ook in je `clean.py`** als je
  daar ooit op naam dedupliceert (nu niet het geval).
- **Nieuwe hubs zonder GPS.** Een vers radar-initiatief heeft geen coördinaten;
  die hub staat wél in de JSON maar verschijnt (nog) niet op de kaart tot je GPS
  invult — handmatig of via de verrijkingsstap.
- **[skip ci].** De commit-message bevat `[skip ci]` zodat de Action zichzelf niet
  opnieuw triggert. Railway negeert dit en deployt gewoon; het voorkomt alleen een
  lus in GitHub Actions.
- **Geen dubbele deploys.** De Action commit alleen als er echt iets veranderd is,
  dus Railway herdeployt niet onnodig.

## Lokaal draaien (handmatig testen)

```bash
export DATASET_PATH=Energiehubs_Uniform_Fases_RES_REGIO.xlsx
python scripts/fetch_radar.py
python scripts/update_dataset.py
python clean.py "$DATASET_PATH" && mv energiehubs.json public/energiehubs.json
```
