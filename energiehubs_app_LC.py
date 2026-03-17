import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re

st.set_page_config(
    page_title="Energiehubs Nederland",
    page_icon="⚡",
    layout="wide",
)

# ── SVG logo's ─────────────────────────────────────────────────────────────────
HVA_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 52" width="160" height="42">
  <rect x="0" y="0" width="48" height="52" fill="#E3000F"/>
  <text x="24" y="34" font-family="Arial,sans-serif" font-size="22" font-weight="900"
        fill="white" text-anchor="middle">H</text>
  <text x="58" y="18" font-family="Arial,sans-serif" font-size="9.5" font-weight="700"
        fill="#E3000F" letter-spacing="0.5">HOGESCHOOL</text>
  <text x="58" y="30" font-family="Arial,sans-serif" font-size="9.5" font-weight="700"
        fill="#E3000F" letter-spacing="0.5">VAN AMSTERDAM</text>
  <text x="58" y="44" font-family="Arial,sans-serif" font-size="8" fill="#555555"
        letter-spacing="0.3">Amsterdam University</text>
  <text x="58" y="54" font-family="Arial,sans-serif" font-size="8" fill="#555555"
        letter-spacing="0.3">of Applied Sciences</text>
</svg>
"""
CNZ_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 56" width="160" height="45">
  <circle cx="22" cy="28" r="22" fill="#00843D"/>
  <text x="22" y="35" font-family="Arial,sans-serif" font-size="20" font-weight="900"
        fill="white" text-anchor="middle">C</text>
  <text x="52" y="16" font-family="Arial,sans-serif" font-size="8.5" font-weight="700"
        fill="#00843D" letter-spacing="0.3">CENTRE OF EXPERTISE</text>
  <text x="52" y="28" font-family="Arial,sans-serif" font-size="10.5" font-weight="900"
        fill="#00843D" letter-spacing="0.5">CITY NET ZERO</text>
  <text x="52" y="40" font-family="Arial,sans-serif" font-size="7.5" fill="#555555">Hogeschool van Amsterdam</text>
</svg>
"""
LEVE_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 56" width="160" height="45">
  <rect x="0" y="4" width="44" height="44" rx="6" fill="#004B8D"/>
  <polygon points="22,10 34,28 26,28 26,42 18,42 18,28 10,28" fill="#F7A800"/>
  <text x="54" y="20" font-family="Arial,sans-serif" font-size="9" font-weight="700"
        fill="#004B8D" letter-spacing="0.5">LECTORENPLATFORM</text>
  <text x="54" y="34" font-family="Arial,sans-serif" font-size="13" font-weight="900"
        fill="#004B8D" letter-spacing="1">LEVE</text>
  <text x="54" y="46" font-family="Arial,sans-serif" font-size="7.5" fill="#555555">Energievoorziening in Evenwicht</text>
</svg>
"""

def logo_html(svg, link):
    inner = f'<a href="{link}" target="_blank" style="display:block">{svg}</a>' if link else svg
    return f"""<div style="background:white;border-radius:10px;padding:10px 12px;margin-bottom:10px;
        box-shadow:0 1px 4px rgba(0,0,0,0.15);display:flex;align-items:center;justify-content:center;">
        {inner}</div>"""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.02em; }

.main-title { font-family:'Syne',sans-serif; font-size:2.4rem; font-weight:800; color:#7feba1;
    letter-spacing:-0.03em; margin-bottom:0; line-height:1.1; }
.main-subtitle { font-family:'DM Sans',sans-serif; font-size:0.95rem; color:#6b7a8d;
    margin-top:4px; margin-bottom:0.8rem; }
.kpi-card { background:linear-gradient(135deg,#161b22 0%,#1c2333 100%); border:1px solid #2a3a2a;
    border-radius:12px; padding:12px 16px; text-align:center; }
.kpi-value { font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:700; color:#7feba1; line-height:1; }
.kpi-label { font-size:0.72rem; color:#6b7a8d; margin-top:3px; text-transform:uppercase; letter-spacing:0.06em; }
.section-title { font-family:'Syne',sans-serif; font-size:1.05rem; font-weight:700; color:#c8d8c0;
    text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem; margin-top:0.2rem; }

/* ── Hoofdtabs: groot en prominent ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0d1117;
    border-radius: 0;
    gap: 0;
    border-bottom: 2px solid #2a3a2a;
    margin-bottom: 1.4rem;
}
.stTabs [data-baseweb="tab"] {
    font-family:'Syne',sans-serif; font-size:1.35rem; font-weight:700;
    color:#6b7a8d; background:transparent;
    border-radius:0; padding:20px 40px; letter-spacing:0.04em;
    border-bottom: 4px solid transparent;
    margin-bottom: -2px;
}
.stTabs [data-baseweb="tab"]:hover { color:#c8d8c0; }
.stTabs [aria-selected="true"] {
    color:#7feba1 !important; background:transparent !important;
    border-bottom: 4px solid #7feba1 !important;
}

/* Subtabs (type-hubs tabs) krijgen kleinere stijl */
.subtabs .stTabs [data-baseweb="tab-list"] {
    background:#161b22; border-radius:8px 8px 0 0;
    gap:2px; border-bottom:2px solid #2a3a2a; margin-bottom:0;
}
.subtabs .stTabs [data-baseweb="tab"] {
    font-size:0.85rem; padding:8px 16px; font-weight:600;
}

.community-card { background:linear-gradient(135deg,#161b22 0%,#1c2333 100%); border:1px solid #2a3040;
    border-radius:12px; padding:18px 20px; margin-bottom:14px; }
.community-name { font-family:'Syne',sans-serif; font-size:1rem; font-weight:700; color:#7feba1; margin-bottom:6px; }
.community-meta { font-size:0.82rem; color:#8a9bb0; margin-bottom:8px; }
.community-body { font-size:0.85rem; color:#c8d8c0; line-height:1.6; }
.caveat { font-size:0.8rem; color:#6b7a8d; font-style:italic; margin-top:6px; }
.badge { display:inline-block; padding:2px 8px; border-radius:20px; font-size:0.75rem; font-weight:600; margin-right:4px; }
.divider { border:none; border-top:1px solid #2a3040; margin:1rem 0; }
.sidebar-label { font-family:'Syne',sans-serif; font-size:0.75rem; font-weight:700; text-transform:uppercase;
    letter-spacing:0.1em; color:#7feba1; margin:0.8rem 0 0.4rem 0; }
</style>
""", unsafe_allow_html=True)


# ── Data laden ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_hubs():
    base = Path(__file__).parent
    for path in [base / "Energiehubs_Uniform_Fases_RES_REGIO.xlsx", base / "Energiehubs_Uniform_Fases_RES_REGIO.xlsx"]:
        if path.exists():
            df = pd.read_excel(path)
            break
    else:
        st.error("❌ Zet 'Energiehubs_Uniform_Fases.xlsx' naast dit script.")
        st.stop()
    df.columns = ['Project naam', 'URL', 'Provincie', 'Plaats', 'Adres', 'Fase',
                  'GPS_Coordinate', 'Type Hub'] + list(df.columns[8:])
    def parse_gps(val):
        if pd.isna(val): return None, None
        m = re.match(r'^\s*([-\d.]+)\s*,\s*([-\d.]+)\s*$', str(val))
        return (float(m.group(1)), float(m.group(2))) if m else (None, None)
    df[['lat', 'lon']] = df['GPS_Coordinate'].apply(lambda x: pd.Series(parse_gps(x)))
    df['Type'] = df['Type Hub']
    return df

@st.cache_data
def load_communities():
    base = Path(__file__).parent
    path = base / "communities_hubs_brongestuurd.xlsx"
    if not path.exists():
        return None, None, None

    # ── Matrix: hubs × communities ─────────────────────────────────────────────
    raw = pd.read_excel(path, sheet_name='Communities x Hubs', header=None)

    # Rij 2 = kolomkoppen (robuust: zoek eerste rij waar col[1] == 'Provincie')
    header_row = next(
        i for i, row in raw.iterrows()
        if str(row[1]).strip().lower() == 'provincie'
    )
    headers = raw.iloc[header_row].tolist()

    # Datarijen: sla sectiekoppen (alle overige cellen NaN) en lege rijen over,
    # stop bij LEGENDA-blok (eerste kolom begint met 'LEGENDA' of '✅ =')
    data_indices = []
    for i, row in raw.iterrows():
        if i <= header_row:
            continue
        first = str(row[0]).strip()
        if first.upper().startswith('LEGENDA') or first == 'nan':
            continue
        # Sectiekop: alle kolommen vanaf index 1 zijn NaN
        rest_nan = all(str(row[j]) == 'nan' for j in range(1, len(row)))
        if rest_nan:
            continue
        data_indices.append(i)

    data_rows = raw.iloc[data_indices].copy()
    data_rows.columns = headers

    # Community-kolommen = alles tussen Provincie/Type (col 1-2) en Bron (laatste col)
    community_cols_raw = headers[3:-1]
    community_cols_clean = [str(c).replace('\n', ' ').strip() for c in community_cols_raw]
    data_rows = data_rows.rename(columns=dict(zip(community_cols_raw, community_cols_clean)))

    # Hernoem eerste en laatste kolom
    hub_col  = headers[0]
    bron_col = headers[-1]
    data_rows = data_rows.rename(columns={hub_col: 'Hub', bron_col: 'Bron'})
    data_rows = data_rows.reset_index(drop=True)

    # ── Community-profielen ────────────────────────────────────────────────────
    raw_prof = pd.read_excel(path, sheet_name='Community-profielen', header=None)

    # Zoek headerrij robuust (eerste cel == 'Community')
    prof_header_row = next(
        i for i, row in raw_prof.iterrows()
        if str(row[0]).strip() == 'Community'
    )
    headers_prof = raw_prof.iloc[prof_header_row].tolist()

    prof_indices = []
    for i, row in raw_prof.iterrows():
        if i <= prof_header_row:
            continue
        first = str(row[0]).strip()
        if first == 'nan':
            continue
        # Sectiekop: alle overige cellen NaN
        rest_nan = all(str(row[j]) == 'nan' for j in range(1, len(row)))
        if rest_nan:
            continue
        prof_indices.append(i)

    prof_rows = raw_prof.iloc[prof_indices].copy()
    prof_rows.columns = headers_prof
    prof_rows['Community'] = prof_rows['Community'].str.replace('\n', ' ').str.strip()

    # Normaliseer caveat-kolomnaam (verschilt per versie)
    caveat_col = next(
        (c for c in prof_rows.columns if 'caveat' in str(c).lower() or 'ontbreekt' in str(c).lower()),
        None
    )
    if caveat_col and caveat_col != 'Wat ontbreekt / caveat':
        prof_rows = prof_rows.rename(columns={caveat_col: 'Wat ontbreekt / caveat'})

    prof_rows = prof_rows.reset_index(drop=True)

    return data_rows, community_cols_clean, prof_rows

df = load_hubs()
matrix_df, community_cols, prof_df = load_communities()

FASE_ORDER  = ['Fase 1: Verkennen', 'Fase 2: Plannen & Ontwerpen', 'Fase 3: Realiseren', 'Fase 4: Exploiteren', 'Onbekend']
FASE_COLORS = {'Fase 1: Verkennen':'#38bdf8','Fase 2: Plannen & Ontwerpen':'#f59e0b',
               'Fase 3: Realiseren':'#a78bfa','Fase 4: Exploiteren':'#7feba1','Onbekend':'#4b5563'}
TYPE_COLOR  = {'Bedrijventerrein':'#f59e0b','Gebouwde Omgeving':'#38bdf8','Mobiliteit':'#7feba1','Cluster 6':'#a78bfa'}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-label">🔍 Filters</div>', unsafe_allow_html=True)
    sel_prov = st.multiselect("Provincie", sorted(df['Provincie'].dropna().unique()))
    sel_type = st.multiselect("Type Hub", sorted(df['Type'].dropna().unique()))
    sel_fase = st.multiselect("Fase", [f for f in FASE_ORDER if f in df['Fase'].unique()])
    st.markdown('<hr style="border:none;border-top:1px solid #2a3040;margin:1.2rem 0 0.8rem 0">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">Partners</div>', unsafe_allow_html=True)
    st.markdown(logo_html(HVA_SVG, "https://www.hva.nl"), unsafe_allow_html=True)
    st.markdown(logo_html(CNZ_SVG, "https://www.hva.nl/city-net-zero"), unsafe_allow_html=True)
    st.markdown(logo_html(LEVE_SVG, "https://www.hanze.nl/nld/onderzoek/speerpunten/energie/lectorenplatform-energievoorziening-evenwicht-leve"), unsafe_allow_html=True)

filtered = df.copy()
if sel_prov: filtered = filtered[filtered['Provincie'].isin(sel_prov)]
if sel_type: filtered = filtered[filtered['Type'].isin(sel_type)]
if sel_fase: filtered = filtered[filtered['Fase'].isin(sel_fase)]
filtered_map = filtered[filtered['lat'].notna()]

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">Energiehubs Nederland</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Overzicht van energiehub-projecten — filter via de zijbalk</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ── 3 HOOFDTABS ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
tab_hubs, tab_communities, tab_matrix = st.tabs([
    "⚡  Energiehubs",
    "🤝  Learning Communities",
    "🔗  Hubs × Communities",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ENERGIEHUBS
# ══════════════════════════════════════════════════════════════════════════════
with tab_hubs:

    # KPI's
    k1, k2, k3 = st.columns(3)
    for col, val, label in [(k1, len(filtered), "Hubs totaal"),
                             (k2, len(filtered[filtered["Fase"]=="Fase 4: Exploiteren"]), "Operationeel"),
                             (k3, len(data_rows), "Aangesloten bij Learning Community")]:
        col.markdown(f'<div class="kpi-card"><div class="kpi-value">{val}</div>'
                     f'<div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # Kaart + grafieken
    map_col, chart_col = st.columns([3, 2], gap="large")

    with map_col:
        st.markdown('<div class="section-title">📍 Locaties</div>', unsafe_allow_html=True)
        m = folium.Map(location=[52.3, 5.3], zoom_start=7, tiles='CartoDB dark_matter')
        for _, row in filtered_map.iterrows():
            color = TYPE_COLOR.get(row['Type'], '#ccc')
            url_link = f'<a href="{row["URL"]}" target="_blank" style="color:#7feba1">🔗 Website</a>' \
                       if pd.notna(row['URL']) else ''
            popup_html = f"""<div style='font-family:sans-serif;min-width:200px;font-size:13px'>
                <b style='font-size:14px'>{row['Project naam']}</b><br>
                📍 {row['Plaats'] if pd.notna(row['Plaats']) else ''}{', ' + str(row['Provincie']) if pd.notna(row['Provincie']) else ''}<br>
                🏷️ {row['Type']}<br>📋 {row['Fase'] if pd.notna(row['Fase']) else 'Onbekend'}<br>{url_link}</div>"""
            folium.CircleMarker(
                location=[row['lat'], row['lon']], radius=7, color=color,
                fill=True, fill_color=color, fill_opacity=0.9, weight=1.5,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=str(row['Project naam']),
            ).add_to(m)
        st_folium(m, height=450, use_container_width=True)

    with chart_col:
        st.markdown('<div class="section-title">📊 Hubs per Type</div>', unsafe_allow_html=True)
        type_counts = filtered['Type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Aantal']
        fig = px.bar(type_counts, x='Aantal', y='Type', orientation='h',
                     color='Type', color_discrete_map=TYPE_COLOR, text='Aantal')
        fig.update_traces(textposition='outside',
                          textfont=dict(color='#c8d8c0', size=13, family='Syne'),
                          marker_line_width=0)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font=dict(color='#8a9bb0'), showlegend=False,
                          margin=dict(l=0,r=50,t=10,b=10), height=200,
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''),
                          yaxis=dict(showgrid=False, title='', tickfont=dict(size=13, color='#c8d8c0')))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-title">📈 Hubs per Fase</div>', unsafe_allow_html=True)
        fase_counts = filtered['Fase'].value_counts().reindex(FASE_ORDER).dropna().reset_index()
        fase_counts.columns = ['Fase', 'Aantal']
        fig3 = px.bar(fase_counts, x='Aantal', y='Fase', orientation='h',
                      color='Fase', color_discrete_map=FASE_COLORS, text='Aantal')
        fig3.update_traces(textposition='outside',
                           textfont=dict(color='#c8d8c0', size=12), marker_line_width=0)
        fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                           font=dict(color='#8a9bb0'), showlegend=False,
                           margin=dict(l=0,r=50,t=10,b=10), height=220,
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''),
                           yaxis=dict(showgrid=False, title='', tickfont=dict(size=11, color='#c8d8c0')))
        st.plotly_chart(fig3, use_container_width=True)

    # Datasheets per type
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Datasheet per Type Hub</div>', unsafe_allow_html=True)

    TYPES = ['Bedrijventerrein', 'Gebouwde Omgeving', 'Mobiliteit', 'Cluster 6']
    ICONS = {'Bedrijventerrein': '🏭', 'Gebouwde Omgeving': '🏠', 'Mobiliteit': '🚗', 'Cluster 6': '⚡'}
    TAB_COLS = ['Project naam', 'URL', 'Provincie', 'Plaats', 'Adres', 'Fase', 'RES-Regio', 'Energiedrager']

    sub_tabs = st.tabs([f"{ICONS[t]}  {t}  ({len(filtered[filtered['Type'] == t])})" for t in TYPES])
    for sub_tab, hub_type in zip(sub_tabs, TYPES):
        with sub_tab:
            subset = filtered[filtered['Type'] == hub_type][TAB_COLS].reset_index(drop=True)
            if len(subset) == 0:
                st.info("Geen hubs gevonden voor dit type met de huidige filters.")
            else:
                st.dataframe(
                    subset, use_container_width=True,
                    height=min(35 * len(subset) + 38, 520),
                    column_config={
                        "URL": st.column_config.LinkColumn("URL", display_text="🔗 Open"),
                        "Project naam": st.column_config.TextColumn("Project naam", width="large"),
                        "Provincie": st.column_config.TextColumn("Provincie", width="medium"),
                        "Plaats": st.column_config.TextColumn("Plaats", width="medium"),
                        "Adres": st.column_config.TextColumn("Adres", width="large"),
                        "Fase": st.column_config.TextColumn("Fase", width="large"),
                        "RES-Regio": st.column_config.TextColumn("RES-Regio", width="medium"),
                        "Energiedrager": st.column_config.TextColumn("Energiedrager", width="medium"),
                    },
                    hide_index=True,
                )

    st.markdown(f"<div style='color:#3a4a3a;font-size:0.75rem;text-align:right;margin-top:1rem'>"
                f"Dataset: {len(df)} hubs · {len(df[df['lat'].notna()])} met GPS</div>",
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LEARNING COMMUNITIES
# ══════════════════════════════════════════════════════════════════════════════
with tab_communities:
    if prof_df is None:
        st.info("Bestand 'communities_hubs_brongestuurd.xlsx' niet gevonden naast dit script.")
    else:
        st.markdown('<div class="section-title">🤝 Learning Communities & CoP\'s</div>',
                    unsafe_allow_html=True)
        st.markdown("<p style='color:#6b7a8d;font-size:0.9rem;margin-bottom:1.2rem'>"
                    "Overzicht van communities of practice en learning communities rondom energiehubs "
                    "in Nederland. Brongestuurd — alleen aantoonbare deelnames.</p>",
                    unsafe_allow_html=True)

        deeln_bekend = prof_df['Deelnemers aantoonbaar?'].str.contains('JA', na=False).sum()
        ck1, ck2, ck3 = st.columns(3)
        for col, val, label in [
            (ck1, len(prof_df), "Communities"),
            (ck2, deeln_bekend, "Met aantoonbare deelnemers"),
            (ck3, len(prof_df) - deeln_bekend, "Deelnemers niet publiek"),
        ]:
            col.markdown(f'<div class="kpi-card"><div class="kpi-value">{val}</div>'
                         f'<div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        DEELN_COLOR = {'JA':'#7feba1','DEELS':'#f59e0b','NEE':'#ef4444','OPEN':'#38bdf8'}
        for _, row in prof_df.iterrows():
            deeln_str = str(row.get('Deelnemers aantoonbaar?', ''))
            badge_key = next((k for k in DEELN_COLOR if k in deeln_str.upper()), 'NEE')
            badge_color = DEELN_COLOR[badge_key]
            regio     = str(row.get('Regio', '')).replace('\n', ', ')
            type_hubs = str(row.get('Type hubs', '')).replace('\n', ', ')
            bewijs    = str(row.get('Bewijs / bron', ''))
            bewijs    = bewijs[:300] + ('...' if len(bewijs) > 300 else '')
            caveat    = str(row.get('Wat ontbreekt / caveat', ''))
            caveat    = caveat[:200] + ('...' if len(caveat) > 200 else '')
            st.markdown(f"""
            <div class="community-card">
                <div class="community-name">{row['Community']}</div>
                <div class="community-meta">
                    <span class="badge" style="background:{badge_color}22;color:{badge_color};
                        border:1px solid {badge_color}44">{deeln_str}</span>
                    &nbsp;📍 {regio} &nbsp;·&nbsp; 🏭 {type_hubs}
                </div>
                <div class="community-body">{bewijs}</div>
                <div class="caveat">⚠️ {caveat}</div>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — HUBS × COMMUNITIES MATRIX
# ══════════════════════════════════════════════════════════════════════════════
with tab_matrix:
    if matrix_df is None or community_cols is None:
        st.info("Bestand 'communities_hubs_brongestuurd.xlsx' niet gevonden naast dit script.")
    else:
        st.markdown('<div class="section-title">🔗 Overlap: Hubs × Communities</div>',
                    unsafe_allow_html=True)
        st.markdown("<p style='color:#6b7a8d;font-size:0.9rem;margin-bottom:1.2rem'>"
                    "Welke energiehubs nemen deel aan welke learning community? "
                    "Brongestuurd overzicht (maart 2026).</p>", unsafe_allow_html=True)

        # Legenda
        leg_cols = st.columns(4)
        for col, emoji, label, color in [
            (leg_cols[0], '✅', 'Aantoonbare deelname', '#7feba1'),
            (leg_cols[1], '❓', 'Niet bevestigd',       '#f59e0b'),
            (leg_cols[2], '🔓', 'Open platform',        '#38bdf8'),
            (leg_cols[3], '—',  'Niet van toepassing',  '#4b5563'),
        ]:
            col.markdown(
                f"<div style='background:{color}22;border:1px solid {color}44;"
                f"border-radius:8px;padding:8px 12px;font-size:0.82rem;color:{color}'>"
                f"{emoji} {label}</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # Filters
        fc1, fc2 = st.columns(2)
        with fc1:
            prov_filter = st.multiselect(
                "Filter op Provincie",
                sorted(matrix_df['Provincie'].dropna().unique()),
                key="matrix_prov")
        with fc2:
            show_only = st.checkbox("Toon alleen hubs met ≥1 aantoonbare deelname (✅)", value=False)

        mx = matrix_df.copy()
        if prov_filter:
            mx = mx[mx['Provincie'].isin(prov_filter)]
        if show_only:
            mx = mx[mx[community_cols].apply(lambda r: '✅' in r.values, axis=1)]

        st.markdown(f"<p style='color:#6b7a8d;font-size:0.82rem'>{len(mx)} hubs weergegeven</p>",
                    unsafe_allow_html=True)

        # Heatmap
        symbol_map = {'✅': 2, '❓': 1, '🔓': 0.5, '—': 0}
        def sym_to_num(val):
            for k, v in symbol_map.items():
                if str(val).strip() == k: return v
            return 0

        short_names = [c.split('(')[0].strip()[:30] for c in community_cols]

        if len(mx) > 0:
            hub_names  = mx['Hub'].tolist()
            prov_names = mx['Provincie'].tolist()
            hover_vals = mx[community_cols].values.tolist()
            z_vals     = mx[community_cols].applymap(sym_to_num).values.tolist()
            hover_text = [
                [f"<b>{hub_names[i]}</b><br>{prov_names[i]}<br>{community_cols[j]}<br>{hover_vals[i][j]}"
                 for j in range(len(community_cols))]
                for i in range(len(hub_names))
            ]
            fig_heat = go.Figure(data=go.Heatmap(
                z=z_vals, x=short_names, y=hub_names,
                text=[[str(v) for v in row] for row in hover_vals],
                texttemplate="%{text}",
                hovertext=hover_text, hovertemplate="%{hovertext}<extra></extra>",
                colorscale=[[0,'#1c2333'],[0.25,'#2a3a5a'],[0.5,'#1a4a3a'],[1,'#1a6a40']],
                showscale=False, xgap=3, ygap=2,
            ))
            fig_heat.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#c8d8c0', size=11),
                margin=dict(l=10, r=10, t=10, b=80),
                height=max(400, len(mx) * 26 + 100),
                xaxis=dict(tickangle=-35, tickfont=dict(size=10, color='#8a9bb0'), side='bottom'),
                yaxis=dict(tickfont=dict(size=10, color='#c8d8c0'), autorange='reversed'),
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        with st.expander("📋 Tabel weergave"):
            display_cols = ['Hub', 'Provincie', 'Type'] + community_cols
            available = [c for c in display_cols if c in mx.columns]
            st.dataframe(
                mx[available].reset_index(drop=True),
                use_container_width=True,
                height=min(35 * len(mx) + 38, 500),
                column_config={
                    "Hub":      st.column_config.TextColumn("Hub",      width="large"),
                    "Provincie":st.column_config.TextColumn("Provincie",width="medium"),
                    "Type":     st.column_config.TextColumn("Type",     width="medium"),
                },
                hide_index=True,
            )
        st.markdown("<div style='color:#3a4a3a;font-size:0.75rem;margin-top:0.5rem'>"
                    "Bron: communities_hubs_brongestuurd.xlsx · "
                    "Alleen aantoonbare deelnames op basis van publieke bronnen</div>",
                    unsafe_allow_html=True)