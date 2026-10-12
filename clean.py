import pandas as pd, json, re, sys
df=pd.read_excel(sys.argv[1])
df.columns=[c.strip().rstrip(':') for c in df.columns]
out=[]
fmap={'Fase 1: Verkennen':(1,'Verkennen'),'Fase 2: Plannen & Ontwerpen':(2,'Plannen & ontwerpen'),'Fase 3: Realiseren':(3,'Realiseren'),'Fase 4: Exploiteren':(4,'Exploiteren')}
def s(v): return None if pd.isna(v) else str(v).strip()
for i,r in df.iterrows():
    f=fmap.get(s(r['Fase']))
    lat=lon=None
    m=re.match(r'\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',str(r['GPS_Coordinate']))
    if m: lat,lon=float(m.group(1)),float(m.group(2))
    ed=s(r['Energiedrager']) or ''
    parts={p.strip() for p in ed.split(',') if p.strip() and p.strip()!='Nog niet bekend'}
    bron=s(r['Contact – bron / toelichting']) or ''
    bc='Direct hubcontact' if bron.startswith('Direct') else ('Provinciaal vangnet' if bron.startswith('Provinciaal vangnet') or bron.startswith('Radar') else 'Overig')
    typ=s(r['Verfijnde typering']) or ''
    nb=None
    for n in ['Enexis','Liander','Stedin']:
        if n in typ: nb=n
    radar='radar' in typ.lower()
    deeln=s(r['Deelnemers'])
    out.append(dict(id=i+1,naam=s(r['Project naam']),url=s(r['URL']),provincie=s(r['Provincie']),plaats=s(r['Plaats']),
        fase_nr=f[0] if f else 0,fase=f[1] if f else 'Onbekend',type_hub=s(r['Type Hub']),
        typering=None if radar else (typ or None),res_regio=s(r['RES-Regio']) or 'Onbekend',
        lat=lat,lon=lon,energiedrager=', '.join(sorted(parts)) or None,
        elektriciteit=int('Elektriciteit' in parts),warmte=int('Warmte' in parts),waterstof=int('Waterstof' in parts),
        groen_gas=int('Groen gas' in parts),koude=int('Koude' in parts),n_dragers=len(parts),
        deelnemers_bekend=int(deeln is not None),bron=bc,energiehubs_radar=int(radar),netbeheerder=nb))
o=pd.DataFrame(out)
print(o.lat.describe(),o.lon.describe())
print(o.fase.value_counts(), o.bron.value_counts(), o.netbeheerder.value_counts(dropna=False))
print(pd.crosstab(o.type_hub,o.fase))
print(o[o.naam.duplicated(keep=False)][['naam','plaats','fase']])
json.dump(out,open('energiehubs.json','w'),ensure_ascii=False)
import os;print(os.path.getsize('energiehubs.json'))
