import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from pathlib import Path
import re

st.set_page_config(
    page_title="Energiehubs Nederland",
    page_icon="⚡",
    layout="wide",
)

# ── SVG logo's als inline strings ─────────────────────────────────────────────
# Hogeschool van Amsterdam – rode blok + tekst
HVA_SVG = """
<svg xmlns="https://zakelijkschrijven.nl/hva-logo/" viewBox="0 0 200 52" width="160" height="42">
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

# City Net Zero – groen blad/cirkel icoon + tekst
CNZ_SVG = """
<svg xmlns="https://media.licdn.com/dms/image/v2/C4E0BAQHDOWaE9cxiiA/company-logo_200_200/company-logo_200_200/0/1679308588602/city_net_zero_logo?e=2147483647&v=beta&t=IkQsjO5KE7qmqVSHg5obO8jh1M84DDHNhr3xKkXJUUA" viewBox="0 0 200 56" width="160" height="45">
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

# LEVE – blauw/groen energiepijl icoon + tekst
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

def logo_html(svg: str, link: str) -> str:
    """Wrap SVG in a white pill card with optional hyperlink."""
    inner = f'<a href="{link}" target="_blank" style="display:block">{svg}</a>' if link else svg
    return f"""
    <div style="
        background: white;
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        justify-content: center;
    ">{inner}</div>
    """

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.02em; }

.main-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem; font-weight: 800;
    color: #7feba1; letter-spacing: -0.03em;
    margin-bottom: 0; line-height: 1.1;
}
.main-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem; color: #6b7a8d;
    margin-top: 4px; margin-bottom: 1.2rem;
}
.kpi-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
    border: 1px solid #2a3a2a; border-radius: 12px;
    padding: 16px 20px; text-align: center;
}
.kpi-value { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 700; color: #7feba1; line-height: 1; }
.kpi-label { font-size: 0.78rem; color: #6b7a8d; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
.section-title {
    font-family: 'Syne', sans-serif; font-size: 1.05rem; font-weight: 700;
    color: #c8d8c0; text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 0.5rem; margin-top: 0.2rem;
}
.stTabs [data-baseweb="tab-list"] { background: #161b22; border-radius: 8px 8px 0 0; gap: 2px; border-bottom: 2px solid #2a3a2a; }
.stTabs [data-baseweb="tab"] { font-family: 'Syne', sans-serif; font-size: 0.85rem; font-weight: 600; color: #6b7a8d; background: transparent; border-radius: 6px 6px 0 0; padding: 10px 18px; letter-spacing: 0.03em; }
.stTabs [aria-selected="true"] { color: #7feba1 !important; background: #1c2a1c !important; border-bottom: 2px solid #7feba1; }
.divider { border: none; border-top: 1px solid #2a3040; margin: 1rem 0; }
.sidebar-label { font-family: 'Syne', sans-serif; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #7feba1; margin: 0.8rem 0 0.4rem 0; }
</style>
""", unsafe_allow_html=True)


# ── Data laden ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    candidates = [
        Path(__file__).parent / "Energiehubs_Uniform_Fases.xlsx",
        Path("Energiehubs_Uniform_Fases.xlsx"),
    ]
    for path in candidates:
        if path.exists():
            df = pd.read_excel(path)
            break
    else:
        st.error("❌ Zet 'Energiehubs_Verfijnd_GPS.xlsx' naast dit script.")
        st.stop()

    df.columns = ['Project naam', 'URL', 'Provincie', 'Plaats', 'Adres', 'Fase', 'GPS_Coordinate', 'Type Hub', 'Verfijnde typering',	'RES-Regio' ,	'Deelnemers',	'Energiedrager', 'Type Contract'
]

    def parse_gps(val):
        if pd.isna(val):
            return None, None
        m = re.match(r'^\s*([-\d.]+)\s*,\s*([-\d.]+)\s*$', str(val))
        return (float(m.group(1)), float(m.group(2))) if m else (None, None)

    df[['lat', 'lon']] = df['GPS_Coordinate'].apply(lambda x: pd.Series(parse_gps(x)))
    df['Type'] = df['Type Hub'].apply(lambda t: t if t in ['Bedrijventerrein', 'Gebouwde Omgeving', 'Mobiliteit'] else 'Cluster 6')
    return df

df = load_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-label">🔍 Filters</div>', unsafe_allow_html=True)

    sel_prov = st.multiselect("Provincie", sorted(df['Provincie'].dropna().unique()))
    sel_type = st.multiselect("Type Hub", sorted(df['Type'].unique()))
    sel_fase = st.multiselect("Fase", sorted(df['Fase'].dropna().unique()))

    st.markdown('<hr style="border:none;border-top:1px solid #e0e0e0;margin:1.2rem 0 0.8rem 0">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">Partners</div>', unsafe_allow_html=True)
    st.markdown(logo_html(<img src="https://zakelijkschrijven.nl/wp-content/uploads/2021/01/HvA-logo-300x150.png", width="500", height="600">, "https://www.hva.nl"), unsafe_allow_html=True)
    st.markdown(logo_html(<img src="https://media.licdn.com/dms/image/v2/C4E0BAQHDOWaE9cxiiA/company-logo_200_200/company-logo_200_200/0/1679308588602/city_net_zero_logo?e=2147483647&v=beta&t=IkQsjO5KE7qmqVSHg5obO8jh1M84DDHNhr3xKkXJUUA", width="500", height="600">, "https://www.hva.nl/city-net-zero"), unsafe_allow_html=True)
    st.markdown(logo_html(<img src="https://lectorenplatformleve.nl/wp-content/uploads/2021/11/image.png-4.png", width="500", height="600">, "https://lectorenplatformleve.nl/"), unsafe_allow_html=True)

filtered = df.copy()
if sel_prov: filtered = filtered[filtered['Provincie'].isin(sel_prov)]
if sel_type: filtered = filtered[filtered['Type'].isin(sel_type)]
if sel_fase: filtered = filtered[filtered['Fase'].isin(sel_fase)]
filtered_map = filtered[filtered['lat'].notna()]

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">Energiehubs Nederland</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Overzicht van energiehub-projecten — filter via de zijbalk</div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
for col, val, label in [(k1, len(filtered), "Hubs totaal"), (k2, len(filtered_map), "Met locatie"), (k3, filtered['Provincie'].nunique(), "Provincies"), (k4, filtered['Type'].nunique(), "Types")]:
    col.markdown(f'<div class="kpi-card"><div class="kpi-value">{val}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ── Kaart + Grafiek ────────────────────────────────────────────────────────────
TYPE_COLOR = {'Bedrijventerrein': '#f59e0b', 'Gebouwde Omgeving': '#38bdf8', 'Mobiliteit': '#7feba1', 'Cluster 6': '#a78bfa'}

map_col, chart_col = st.columns([3, 2], gap="large")

with map_col:
    st.markdown('<div class="section-title">📍 Locaties</div>', unsafe_allow_html=True)
    m = folium.Map(location=[52.3, 5.3], zoom_start=7, tiles='CartoDB dark_matter')

    for _, row in filtered_map.iterrows():
        color = TYPE_COLOR.get(row['Type'], '#ccc')
        url_link = f'<a href="{row["URL"]}" target="_blank" style="color:#7feba1">🔗 Website</a>' if pd.notna(row['URL']) else ''
        popup_html = f"""
        <div style='font-family:sans-serif;min-width:200px;font-size:13px'>
            <b style='font-size:14px'>{row['Project naam']}</b><br>
            📍 {row['Plaats'] if pd.notna(row['Plaats']) else ''}{', ' + str(row['Provincie']) if pd.notna(row['Provincie']) else ''}<br>
            🏷️ {row['Type']}<br>
            📋 {row['Fase'] if pd.notna(row['Fase']) else 'Onbekend'}<br>
            {url_link}
        </div>"""
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=7, color=color, fill=True, fill_color=color,
            fill_opacity=0.9, weight=1.5,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=str(row['Project naam']),
        ).add_to(m)

    st_folium(m, height=430, use_container_width=True)

with chart_col:
    st.markdown('<div class="section-title">📊 Hubs per Type</div>', unsafe_allow_html=True)
    type_counts = filtered['Type'].value_counts().reset_index()
    type_counts.columns = ['Type', 'Aantal']

    fig = px.bar(type_counts, x='Aantal', y='Type', orientation='h', color='Type',
                 color_discrete_map=TYPE_COLOR, text='Aantal')
    fig.update_traces(textposition='outside', textfont=dict(color='#c8d8c0', size=13, family='Syne'), marker_line_width=0)
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#8a9bb0'),
                      showlegend=False, margin=dict(l=0, r=50, t=10, b=10), height=200,
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''),
                      yaxis=dict(showgrid=False, title='', tickfont=dict(size=13, color='#c8d8c0')))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">🗺️ Top 10 Provincies</div>', unsafe_allow_html=True)
    prov_counts = filtered['Provincie'].value_counts().head(10).reset_index()
    prov_counts.columns = ['Provincie', 'Aantal']

    fig2 = px.bar(prov_counts, x='Provincie', y='Aantal', color='Aantal',
                  color_continuous_scale=['#1c2a1c', '#7feba1'], text='Aantal')
    fig2.update_traces(textposition='outside', textfont=dict(color='#c8d8c0', size=11), marker_line_width=0)
    fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#8a9bb0'),
                       showlegend=False, coloraxis_showscale=False, margin=dict(l=0, r=10, t=10, b=60), height=195,
                       xaxis=dict(showgrid=False, title='', tickfont=dict(size=10, color='#8a9bb0'), tickangle=-35),
                       yaxis=dict(showgrid=False, showticklabels=False, title=''))
    st.plotly_chart(fig2, use_container_width=True)

# ── Tabs datasheet ─────────────────────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📋 Datasheet per Type Hub</div>', unsafe_allow_html=True)

TYPES = ['Bedrijventerrein', 'Gebouwde Omgeving', 'Mobiliteit', 'Cluster 6']
ICONS = {'Bedrijventerrein': '🏭', 'Gebouwde Omgeving': '🏠', 'Mobiliteit': '🚗', 'Cluster 6': '⚡'}
TAB_COLS = ['Project naam', 'URL', 'Provincie', 'Plaats', 'Adres', 'Fase', 'Verfijnde typering', 'RES-Regio' , 'Deelnemers', 'Energiedrager']

tabs = st.tabs([f"{ICONS[t]}  {t}  ({len(filtered[filtered['Type'] == t])})" for t in TYPES])

for tab, hub_type in zip(tabs, TYPES):
    with tab:
        subset = filtered[filtered['Type'] == hub_type][TAB_COLS].reset_index(drop=True)
        if len(subset) == 0:
            st.info("Geen hubs gevonden voor dit type met de huidige filters.")
        else:
            st.dataframe(
                subset,
                use_container_width=True,
                height=min(35 * len(subset) + 38, 520),
                column_config={
                    "URL": st.column_config.LinkColumn("URL", display_text="🔗 Open"),
                    "Project naam": st.column_config.TextColumn("Project naam", width="large"),
                    "Provincie": st.column_config.TextColumn("Provincie", width="medium"),
                    "Plaats": st.column_config.TextColumn("Plaats", width="medium"),
                    "Adres": st.column_config.TextColumn("Adres", width="large"),
                    "Fase": st.column_config.TextColumn("Fase", width="large"),
                },
                hide_index=True,
            )

st.markdown(f"<div style='color:#3a4a3a;font-size:0.75rem;text-align:right;margin-top:1rem'>Dataset: {len(df)} hubs · {len(df[df['lat'].notna()])} met GPS</div>", unsafe_allow_html=True)
