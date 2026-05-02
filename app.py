import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Solar & BESS Market Dashboard",
    page_icon="☀️",
    layout="wide"
)

# ── Google Fonts + Global CSS ──────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Monda:wght@700&display=swap" rel="stylesheet">
<style>
    /* Base font */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f4f6fb;
    }

    /* All headers use Monda bold */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Monda', sans-serif !important;
        font-weight: 700 !important;
        color: #0058C2 !important;
    }

    /* Fixed top nav bar */
    .top-nav {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: #0058C2;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 24px;
        height: 52px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .top-nav .brand {
        font-family: 'Monda', sans-serif;
        font-weight: 700;
        font-size: 16px;
        color: white;
        margin-right: 24px;
        white-space: nowrap;
    }
    .top-nav a {
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        font-weight: 500;
        color: rgba(255,255,255,0.75);
        text-decoration: none;
        padding: 6px 14px;
        border-radius: 6px;
        transition: background 0.15s;
        cursor: pointer;
        border: none;
        background: none;
        white-space: nowrap;
    }
    .top-nav a.active, .top-nav a:hover {
        background: rgba(255,255,255,0.15);
        color: white;
    }

    /* Push content below fixed nav */
    .main .block-container {
        padding-top: 72px !important;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 18px 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
        text-align: center;
        border-top: 3px solid #0058C2;
    }
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .metric-value {
        font-family: 'Monda', sans-serif;
        font-size: 30px;
        font-weight: 700;
        color: #0058C2;
        margin-top: 4px;
    }
    .metric-sub {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        color: #9ca3af;
        margin-top: 2px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        font-family: 'Monda', sans-serif !important;
        font-size: 15px !important;
    }

    /* Hide default streamlit radio for page nav (we use query params) */
    div[data-testid="stRadio"] { display: none; }

    /* Plotly chart border */
    .js-plotly-plot {
        border-radius: 8px;
        background: white;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
</style>
""", unsafe_allow_html=True)

# ── Color palette ──────────────────────────────────────────────────────────────
BLUE_DARK = "#0058C2"
BLUE_LIGHT = "#0074FF"
AMBER = "#FFC000"
CHART_COLORS = [BLUE_DARK, BLUE_LIGHT, AMBER, "#93c5fd", "#fde68a"]

TECHNOLOGIES = ["Solar Photovoltaic", "Batteries"]

# CHP sectors to exclude
CHP_SECTORS = {"IPP CHP", "Industrial CHP", "Commercial CHP"}

# Sector name cleanup (remove " Non-CHP")
def clean_sector(s):
    if isinstance(s, str):
        return s.replace(" Non-CHP", "").replace(" CHP", "")
    return s

OPERATING_KEEP = [
    "Entity ID", "Entity Name", "Plant ID", "Plant Name",
    "Plant State", "County", "Sector", "Technology",
    "Nameplate Capacity (MW)", "DC Net Capacity (MW)", "Nameplate Energy Capacity (MWh)",
    "Operating Month", "Operating Year", "Status",
    "Latitude", "Longitude"
]

PLANNED_KEEP = [
    "Entity ID", "Entity Name", "Plant ID", "Plant Name",
    "Plant State", "County", "Sector", "Technology",
    "Nameplate Capacity (MW)", "Latitude", "Longitude",
    "Planned Operation Month", "Planned Operation Year", "Status"
]


@st.cache_data
def process_file(file_bytes):
    import io
    f = io.BytesIO(file_bytes)

    # Operating
    op = pd.read_excel(f, sheet_name="Operating", header=2)
    op = op[[c for c in OPERATING_KEEP if c in op.columns]].copy()
    op = op[op["Plant State"] != "PR"]
    op = op[op["Technology"].isin(TECHNOLOGIES)]
    op = op[~op["Sector"].isin(CHP_SECTORS)]
    op["Sector"] = op["Sector"].apply(clean_sector)
    op = op.rename(columns={
        "Nameplate Capacity (MW)": "MWac",
        "DC Net Capacity (MW)": "MWdc",
        "Nameplate Energy Capacity (MWh)": "MWh"
    })
    op["Status_Simple"] = "Operating"

    # Planned
    f.seek(0)
    pl = pd.read_excel(f, sheet_name="Planned", header=2)
    pl = pl[[c for c in PLANNED_KEEP if c in pl.columns]].copy()
    pl = pl[pl["Plant State"] != "PR"]
    pl = pl[pl["Technology"].isin(TECHNOLOGIES)]
    pl = pl[~pl["Sector"].isin(CHP_SECTORS)]
    pl["Sector"] = pl["Sector"].apply(clean_sector)
    pl = pl.rename(columns={
        "Nameplate Capacity (MW)": "MWac",
        "Planned Operation Month": "Operating Month",
        "Planned Operation Year": "Operating Year"
    })
    pl["MWdc"] = None
    pl["MWh"] = None
    pl["Status_Simple"] = "Development"

    combined = pd.concat([op, pl], ignore_index=True)

    for col in ["MWac", "MWdc", "MWh", "Latitude", "Longitude", "Operating Year"]:
        combined[col] = pd.to_numeric(combined[col], errors="coerce")

    # Plant-level aggregation
    agg = combined.groupby(["Plant ID", "Technology"], as_index=False).agg(
        Total_MWac=("MWac", "sum"),
        Total_MWdc=("MWdc", "sum"),
        Total_MWh=("MWh", "sum"),
    )

    meta_cols = ["Plant ID", "Technology", "Plant Name", "Entity Name", "Entity ID",
                 "Plant State", "County", "Sector", "Operating Year", "Operating Month",
                 "Status_Simple", "Latitude", "Longitude"]
    meta_cols = [c for c in meta_cols if c in combined.columns]
    meta = combined[meta_cols].drop_duplicates(subset=["Plant ID", "Technology"], keep="first")

    df = agg.merge(meta, on=["Plant ID", "Technology"], how="left")

    def segment(row):
        if row["Technology"] == "Solar Photovoltaic" and row["Total_MWac"] >= 75:
            return "Utility"
        elif row["Technology"] == "Batteries" and row["Total_MWac"] >= 10:
            return "Utility"
        return "DG"

    df["Segment"] = df.apply(segment, axis=1)
    df["Status"] = df["Status_Simple"]
    df["GWac"] = (df["Total_MWac"] / 1000).round(3)
    df["Operating Year"] = df["Operating Year"].astype("Int64")

    df = df.rename(columns={
        "Total_MWac": "Total MWac",
        "Total_MWdc": "Total MWdc",
        "Total_MWh": "Total MWh",
        "Entity Name": "Owner",
    })
    df = df.drop(columns=["Status_Simple"], errors="ignore")
    return df


def to_gw(series):
    return round(pd.to_numeric(series, errors="coerce").sum() / 1000, 1)


def styled_bar(df_plot, x, y, title, color=None, color_map=None, orientation="v", text_col=None):
    kwargs = dict(title=title, text=text_col or y,
                  color_discrete_sequence=CHART_COLORS if color is None else None)
    if color:
        kwargs["color"] = color
    if color_map:
        kwargs["color_discrete_map"] = color_map
    if orientation == "h":
        fig = px.bar(df_plot, x=x, y=y, orientation="h", **kwargs)
    else:
        fig = px.bar(df_plot, x=x, y=y, **kwargs)
    fig.update_traces(textposition="outside", texttemplate="%{text:.1f}")
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12),
        title_font=dict(family="Monda, sans-serif", size=14, color=BLUE_DARK),
        showlegend=color is not None,
        margin=dict(t=50, b=40, l=40, r=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    )
    return fig


# ── Page routing via query params ──────────────────────────────────────────────
PAGES = ["Market Overview", "Solar Projects", "BESS Projects", "Project Map"]
params = st.query_params
page = params.get("page", "Market Overview")
if page not in PAGES:
    page = "Market Overview"

nav_links = ""
for p in PAGES:
    active = "active" if p == page else ""
    safe = p.replace(" ", "+")
    nav_links += f'<a class="{active}" href="?page={safe}">{p}</a>'

st.markdown(f"""
<div class="top-nav">
    <span class="brand">☀️ Solar & BESS Market</span>
    {nav_links}
</div>
""", unsafe_allow_html=True)

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Filters")

    DATA_FILE = "march_generator2026__1_.xlsx"
    try:
        with open(DATA_FILE, "rb") as f:
            file_bytes = f.read()
        df_raw = process_file(file_bytes)
        data_loaded = True
    except FileNotFoundError:
        uploaded = st.file_uploader("Upload EIA 860M Excel file", type=["xlsx"])
        if uploaded:
            df_raw = process_file(uploaded.read())
            data_loaded = True
        else:
            data_loaded = False

    if data_loaded:
        tech_options = sorted(df_raw["Technology"].dropna().unique())
        selected_tech = st.multiselect("Technology", tech_options, default=list(tech_options))

        seg_options = sorted(df_raw["Segment"].dropna().unique())
        selected_seg = st.multiselect("Segment", seg_options, default=list(seg_options))

        status_options = sorted(df_raw["Status"].dropna().unique())
        selected_status = st.multiselect("Status", status_options, default=list(status_options))

        year_options = sorted(df_raw["Operating Year"].dropna().unique().tolist())
        selected_years = st.multiselect("Operating Year", year_options, default=year_options)

        state_options = ["All"] + sorted(df_raw["Plant State"].dropna().unique())
        selected_state = st.selectbox("Plant State", state_options)

        sector_options = ["All"] + sorted(df_raw["Sector"].dropna().unique())
        selected_sector = st.selectbox("Sector", sector_options)

# ── No data ────────────────────────────────────────────────────────────────────
if not data_loaded:
    st.title("Solar & BESS Market Dashboard")
    st.info("Upload the EIA Form 860M Excel file using the sidebar to get started.")
    st.stop()

# ── Apply filters ──────────────────────────────────────────────────────────────
df = df_raw.copy()
if selected_tech:
    df = df[df["Technology"].isin(selected_tech)]
if selected_seg:
    df = df[df["Segment"].isin(selected_seg)]
if selected_status:
    df = df[df["Status"].isin(selected_status)]
if selected_years:
    df = df[df["Operating Year"].isin(selected_years)]
if selected_state != "All":
    df = df[df["Plant State"] == selected_state]
if selected_sector != "All":
    df = df[df["Sector"] == selected_sector]

# ── Market Overview ────────────────────────────────────────────────────────────
if page == "Market Overview":
    st.title("Market Overview")

    solar = df[df["Technology"] == "Solar Photovoltaic"]
    bess = df[df["Technology"] == "Batteries"]
    operating = df[df["Status"] == "Operating"]
    development = df[df["Status"] == "Development"]

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val, sub in [
        (c1, "Total GWac", to_gw(df["Total MWac"]), f"{len(df):,} plants"),
        (c2, "Solar GWac", to_gw(solar["Total MWac"]), f"{len(solar):,} plants"),
        (c3, "BESS GWac", to_gw(bess["Total MWac"]), f"{len(bess):,} plants"),
        (c4, "Operating GWac", to_gw(operating["Total MWac"]), f"{len(operating):,} plants"),
        (c5, "Development GWac", to_gw(development["Total MWac"]), f"{len(development):,} plants"),
    ]:
        with col:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{val}</div>
                <div class="metric-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    cl, cr = st.columns(2)

    with cl:
        yr = df.groupby("Operating Year")["Total MWac"].sum().reset_index()
        yr["GWac"] = (yr["Total MWac"] / 1000).round(1)
        yr = yr[yr["Operating Year"].between(2015, 2035)]
        st.plotly_chart(styled_bar(yr, "Operating Year", "GWac", "GWac by Operating Year"), use_container_width=True)

    with cr:
        seg = df.groupby(["Segment", "Status"])["Total MWac"].sum().reset_index()
        seg["GWac"] = (seg["Total MWac"] / 1000).round(1)
        fig2 = styled_bar(seg, "Segment", "GWac", "GWac by Segment and Status",
                          color="Status",
                          color_map={"Operating": BLUE_DARK, "Development": BLUE_LIGHT})
        st.plotly_chart(fig2, use_container_width=True)

    cl2, cr2 = st.columns(2)

    with cl2:
        st8 = df.groupby("Plant State")["Total MWac"].sum().reset_index()
        st8["GWac"] = (st8["Total MWac"] / 1000).round(1)
        st8 = st8.nlargest(15, "GWac").sort_values("GWac")
        fig3 = styled_bar(st8, "GWac", "Plant State", "Top 15 States by GWac", orientation="h")
        st.plotly_chart(fig3, use_container_width=True)

    with cr2:
        ts = df.groupby(["Technology", "Segment"])["Total MWac"].sum().reset_index()
        ts["GWac"] = (ts["Total MWac"] / 1000).round(1)
        fig4 = styled_bar(ts, "Technology", "GWac", "GWac by Technology and Segment",
                          color="Segment",
                          color_map={"Utility": BLUE_DARK, "DG": AMBER})
        st.plotly_chart(fig4, use_container_width=True)

# ── Solar Projects ─────────────────────────────────────────────────────────────
elif page == "Solar Projects":
    st.title("Solar Project List")
    d = df[df["Technology"] == "Solar Photovoltaic"].copy()
    cols = ["Plant Name", "Owner", "Plant State", "County", "Sector", "Segment",
            "Operating Year", "Status", "Total MWdc", "Total MWac"]
    cols = [c for c in cols if c in d.columns]
    d = d[cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=650)

# ── BESS Projects ──────────────────────────────────────────────────────────────
elif page == "BESS Projects":
    st.title("BESS Project List")
    d = df[df["Technology"] == "Batteries"].copy()
    cols = ["Plant Name", "Owner", "Plant State", "County", "Sector", "Segment",
            "Operating Year", "Status", "Total MWh", "Total MWac"]
    cols = [c for c in cols if c in d.columns]
    d = d[cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=650)

# ── Project Map ────────────────────────────────────────────────────────────────
elif page == "Project Map":
    st.title("Project Map")
    m = df.dropna(subset=["Latitude", "Longitude", "Total MWac"]).copy()
    m = m[(m["Latitude"].between(24, 50)) & (m["Longitude"].between(-125, -66))]
    m["bubble_size"] = m["Total MWac"].clip(upper=2000) ** 0.5
    fig = px.scatter_mapbox(
        m, lat="Latitude", lon="Longitude",
        size="bubble_size", color="Technology",
        color_discrete_map={"Solar Photovoltaic": BLUE_DARK, "Batteries": AMBER},
        hover_name="Plant Name",
        hover_data={"Plant State": True, "Segment": True, "Status": True,
                    "Total MWac": True, "Operating Year": True,
                    "bubble_size": False, "Latitude": False, "Longitude": False},
        zoom=3.5, center={"lat": 38.5, "lon": -96},
        mapbox_style="open-street-map", height=680
    )
    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                    font=dict(family="Inter, sans-serif"))
    )
    st.plotly_chart(fig, use_container_width=True)
