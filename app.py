import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os

st.set_page_config(
    page_title="Solar & BESS Market Dashboard",
    page_icon="☀️",
    layout="wide"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Monda:wght@700&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f4f6fb;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Monda', sans-serif !important;
        font-weight: 700 !important;
        color: #0058C2 !important;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 18px 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
        text-align: center;
        border-top: 3px solid #0058C2;
        margin-bottom: 8px;
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
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    /* Style the tab bar to match brand */
    div[data-testid="stTabs"] button {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        color: #0058C2 !important;
        background: white !important;
        border-radius: 6px 6px 0 0 !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: #FFC000 !important;
        color: white !important;
        border-bottom: 2px solid #FFC000 !important;
    }
    div[data-testid="stTabs"] button:hover {
        background: #fff3cc !important;
    }
</style>
""", unsafe_allow_html=True)

BLUE_DARK = "#0058C2"
BLUE_LIGHT = "#0074FF"
AMBER = "#FFC000"
CHART_COLORS = [BLUE_DARK, BLUE_LIGHT, AMBER, "#93c5fd", "#fde68a"]

TECHNOLOGIES = ["Solar Photovoltaic", "Batteries"]
CHP_SECTORS = {"IPP CHP", "Industrial CHP", "Commercial CHP"}

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


def styled_bar(df_plot, x, y, title, color=None, color_map=None, orientation="v"):
    kwargs = dict(title=title, text=y,
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


# ── Find data file ─────────────────────────────────────────────────────────────
def find_data_file():
    matches = glob.glob("*generator*.xlsx") + glob.glob("*Generator*.xlsx")
    if matches:
        # Pick the most recently modified if multiple
        return max(matches, key=os.path.getmtime)
    return None

data_file = find_data_file()

if data_file:
    with open(data_file, "rb") as f:
        df_raw = process_file(f.read())
    data_loaded = True
else:
    data_loaded = False

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Filters")

    if not data_loaded:
        uploaded = st.file_uploader("Upload EIA 860M Excel file", type=["xlsx"])
        if uploaded:
            df_raw = process_file(uploaded.read())
            data_loaded = True

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
    st.info("No EIA data file found. Upload the EIA Form 860M Excel file using the sidebar.")
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

# ── Navigation tabs ────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Market Overview",
    "☀️  Solar Projects",
    "🔋  BESS Projects",
    "🗺️  Project Map"
])

# ── Market Overview ────────────────────────────────────────────────────────────
with tab1:
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
        st.plotly_chart(styled_bar(yr, "Operating Year", "GWac", "GWac by Operating Year"),
                        use_container_width=True)

    with cr:
        seg = df.groupby(["Segment", "Status"])["Total MWac"].sum().reset_index()
        seg["GWac"] = (seg["Total MWac"] / 1000).round(1)
        st.plotly_chart(styled_bar(seg, "Segment", "GWac", "GWac by Segment and Status",
                                   color="Status",
                                   color_map={"Operating": BLUE_DARK, "Development": BLUE_LIGHT}),
                        use_container_width=True)

    cl2, cr2 = st.columns(2)

    with cl2:
        st8 = df.groupby("Plant State")["Total MWac"].sum().reset_index()
        st8["GWac"] = (st8["Total MWac"] / 1000).round(1)
        st8 = st8.nlargest(15, "GWac").sort_values("GWac")
        st.plotly_chart(styled_bar(st8, "GWac", "Plant State", "Top 15 States by GWac",
                                   orientation="h"),
                        use_container_width=True)

    with cr2:
        ts = df.groupby(["Technology", "Segment"])["Total MWac"].sum().reset_index()
        ts["GWac"] = (ts["Total MWac"] / 1000).round(1)
        st.plotly_chart(styled_bar(ts, "Technology", "GWac", "GWac by Technology and Segment",
                                   color="Segment",
                                   color_map={"Utility": BLUE_DARK, "DG": AMBER}),
                        use_container_width=True)

# ── Solar Projects ─────────────────────────────────────────────────────────────
with tab2:
    st.title("Solar Project List")
    d = df[df["Technology"] == "Solar Photovoltaic"].copy()
    cols = ["Plant Name", "Owner", "Plant State", "County", "Sector", "Segment",
            "Operating Year", "Status", "Total MWdc", "Total MWac"]
    cols = [c for c in cols if c in d.columns]
    d = d[cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=650)

# ── BESS Projects ──────────────────────────────────────────────────────────────
with tab3:
    st.title("BESS Project List")
    d = df[df["Technology"] == "Batteries"].copy()
    cols = ["Plant Name", "Owner", "Plant State", "County", "Sector", "Segment",
            "Operating Year", "Status", "Total MWh", "Total MWac"]
    cols = [c for c in cols if c in d.columns]
    d = d[cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=650)

# ── Project Map ────────────────────────────────────────────────────────────────
with tab4:
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
