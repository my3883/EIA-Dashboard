import streamlit as st
import pandas as pd
import numpy as np
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
    h1 {
        font-size: 2.4rem !important;
        margin-bottom: 0.5rem !important;
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
    .detail-card {
        background: white;
        border-radius: 10px;
        padding: 20px 24px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
        margin-bottom: 12px;
    }
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #f0f0f0;
        font-size: 14px;
    }
    .detail-label {
        color: #6c757d;
        font-weight: 600;
        min-width: 160px;
    }
    .detail-value {
        color: #1a1a2e;
        text-align: right;
    }
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    span[data-baseweb="tag"] {
        background-color: #0074FF !important;
    }
    span[data-baseweb="tag"] span {
        color: white !important;
    }
    div[data-baseweb="select"] > div {
        border-color: #0074FF !important;
    }
    div[data-testid="stTabs"] [role="tablist"] {
        gap: 28px;
        border-bottom: 2px solid #e5e7eb;
    }
    div[data-testid="stTabs"] button[role="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        color: #6c757d !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
        padding: 10px 20px !important;
        margin-bottom: -2px !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #0058C2 !important;
        border-bottom: 3px solid #FFC000 !important;
        background: transparent !important;
    }
    div[data-testid="stTabs"] button[role="tab"]:hover {
        color: #0058C2 !important;
        background: #f0f4ff !important;
    }
</style>
""", unsafe_allow_html=True)

BLUE_DARK = "#0058C2"
BLUE_LIGHT = "#0074FF"
AMBER = "#FFC000"
CHART_COLORS = [BLUE_DARK, BLUE_LIGHT, AMBER, "#93c5fd", "#fde68a"]

TECHNOLOGIES = ["Solar Photovoltaic", "Batteries"]
MIDWEST_STATES = ["IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"]

def clean_sector(s):
    if not isinstance(s, str):
        return s
    if s in ("Commercial Non-CHP", "Industrial Non-CHP", "Commercial CHP", "Industrial CHP", "IPP CHP"):
        return "IPP"
    s = s.replace(" Non-CHP", "").replace(" CHP", "")
    if s == "Electric Utility":
        return "Utility Owned"
    return s

OPERATING_KEEP = [
    "Entity ID", "Entity Name", "Plant ID", "Plant Name",
    "Plant State", "County", "Sector", "Technology",
    "Nameplate Capacity (MW)", "DC Net Capacity (MW)", "Nameplate Energy Capacity (MWh)",
    "Operating Month", "Operating Year", "Status", "Latitude", "Longitude"
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
                 "Status_Simple", "Status", "Latitude", "Longitude"]
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
    # Preserve original EIA status detail before overwriting with simplified version
    df = df.rename(columns={"Status": "EIA Status"})
    df["Status"] = df["Status_Simple"]
    df["GWac"] = (df["Total_MWac"] / 1000).round(3)
    df["Operating Year"] = df["Operating Year"].astype("Int64")

    def est_acres(row):
        mwdc = row["Total_MWdc"]
        mwac = row["Total_MWac"]
        if pd.notna(mwdc) and mwdc > 0:
            return round(5.5 * mwdc, 0)
        elif pd.notna(mwac) and mwac > 0:
            return round(5.5 * 1.3 * mwac, 0)
        return None

    df["Est. Acres"] = df.apply(est_acres, axis=1)

    df = df.rename(columns={
        "Total_MWac": "Total MWac",
        "Total_MWdc": "Total MWdc",
        "Total_MWh": "Total MWh",
        "Entity Name": "Project Entity",
        "Plant State": "State",
    })
    df = df.drop(columns=["Status_Simple"], errors="ignore")
    return df


def to_gw(series):
    return round(pd.to_numeric(series, errors="coerce").sum() / 1000, 1)


def metric_card(col, label, val, sub):
    with col:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{val}</div>
            <div class="metric-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)


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


def stacked_bar(df_in, group_col, stack_col, value_col, title, color_map=None):
    grp = df_in.dropna(subset=[group_col]).groupby([group_col, stack_col])[value_col].sum().reset_index()
    grp["GW"] = (grp[value_col] / 1000).round(2)
    fig = px.bar(
        grp, x=group_col, y="GW", color=stack_col, barmode="stack",
        title=title,
        color_discrete_map=color_map or {"Utility": BLUE_DARK, "DG": AMBER},
    )
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12),
        title_font=dict(family="Monda, sans-serif", size=14, color=BLUE_DARK),
        margin=dict(t=50, b=40, l=40, r=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis_title="GW",
    )
    return fig


def simple_bar(df_in, group_col, value_col, title, year_range=(2015, 2035)):
    grp = df_in.dropna(subset=[group_col]).copy()
    if year_range:
        grp = grp[grp[group_col].between(*year_range)]
    grp = grp.groupby(group_col)[value_col].sum().reset_index()
    grp["GW"] = (grp[value_col] / 1000).round(1)
    fig = px.bar(grp, x=group_col, y="GW", title=title, text="GW",
                 color_discrete_sequence=[BLUE_DARK])
    fig.update_traces(textposition="outside", texttemplate="%{text:.1f}")
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12),
        title_font=dict(family="Monda, sans-serif", size=14, color=BLUE_DARK),
        showlegend=False,
        margin=dict(t=50, b=40, l=40, r=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis_title="GW",
    )
    return fig


def make_map(df_map, height=680, center_lat=38.5, center_lon=-96, zoom=3.5):
    m = df_map.dropna(subset=["Latitude", "Longitude", "Total MWac"]).copy()
    m = m[(m["Latitude"].between(24, 50)) & (m["Longitude"].between(-125, -66))]
    m["bubble_size"] = m["Total MWac"].clip(upper=2000) ** 0.5
    fig = px.scatter_mapbox(
        m, lat="Latitude", lon="Longitude",
        size="bubble_size", color="Technology",
        color_discrete_map={"Solar Photovoltaic": BLUE_DARK, "Batteries": AMBER},
        hover_name="Plant Name",
        hover_data={"State": True, "Segment": True, "Status": True,
                    "Total MWac": True, "Operating Year": True,
                    "bubble_size": False, "Latitude": False, "Longitude": False},
        zoom=zoom, center={"lat": center_lat, "lon": center_lon},
        mapbox_style="open-street-map", height=height
    )
    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                    font=dict(family="Inter, sans-serif"))
    )
    return fig


# ── Wildfire data (NASA FIRMS) ──────────────────────────────────────────────────
FIRMS_BBOX = "-125,24,-66,50"  # CONUS: west,south,east,north

@st.cache_data(ttl=3600, show_spinner="Fetching active fire detections...")
def get_firms_data(map_key, source, day_range):
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{FIRMS_BBOX}/{day_range}"
    try:
        fires = pd.read_csv(url)
        if "latitude" not in fires.columns:
            # FIRMS returns an error message as a single-column CSV on bad key/params
            return pd.DataFrame(), "FIRMS returned no data. Check that your MAP_KEY is valid."
        return fires, None
    except Exception as e:
        return pd.DataFrame(), f"Could not reach FIRMS: {e}"


def filter_fire_confidence(fires_df, source, min_confidence):
    """Drop low-confidence detections (ag burns, industrial heat, glint) before risk scoring."""
    if fires_df is None or fires_df.empty or "confidence" not in fires_df.columns:
        return fires_df

    f = fires_df.copy()
    if source.startswith("VIIRS"):
        # VIIRS confidence is categorical: l (low), n (nominal), h (high)
        keep_map = {"High only": ["h"], "Nominal & High": ["n", "h"], "All (incl. low)": ["l", "n", "h"]}
        keep = keep_map.get(min_confidence, ["n", "h"])
        f = f[f["confidence"].isin(keep)]
    else:
        # MODIS confidence is numeric 0-100
        threshold_map = {"High only": 80, "Nominal & High": 50, "All (incl. low)": 0}
        threshold = threshold_map.get(min_confidence, 50)
        f = f[pd.to_numeric(f["confidence"], errors="coerce") >= threshold]
    return f


def compute_wildfire_risk(sites_df, fires_df, radius_miles):
    sites = sites_df.dropna(subset=["Latitude", "Longitude"]).copy()
    if fires_df is None or fires_df.empty or sites.empty:
        sites["Nearest Fire (mi)"] = None
        sites["At Risk"] = False
        return sites

    from scipy.spatial import cKDTree

    mean_lat = sites["Latitude"].mean()
    mi_per_deg_lat = 69.0
    mi_per_deg_lon = 69.0 * np.cos(np.radians(mean_lat))

    fire_xy = np.column_stack([
        fires_df["longitude"].values * mi_per_deg_lon,
        fires_df["latitude"].values * mi_per_deg_lat,
    ])
    site_xy = np.column_stack([
        sites["Longitude"].values * mi_per_deg_lon,
        sites["Latitude"].values * mi_per_deg_lat,
    ])

    tree = cKDTree(fire_xy)
    dist, _ = tree.query(site_xy, k=1)

    sites["Nearest Fire (mi)"] = dist.round(1)
    sites["At Risk"] = sites["Nearest Fire (mi)"] <= radius_miles
    return sites


# ── Find data file ─────────────────────────────────────────────────────────────
def find_data_file():
    matches = glob.glob("*generator*.xlsx") + glob.glob("*Generator*.xlsx")
    return max(matches, key=os.path.getmtime) if matches else None

@st.cache_data
def load_ownership():
    try:
        owners = pd.read_excel("EIA Asset Owners.xlsx")
        owners.columns = owners.columns.str.strip()
        if "Plant Name" in owners.columns and "Owner" in owners.columns:
            return owners[["Plant Name", "Owner"]].drop_duplicates(subset=["Plant Name"])
    except FileNotFoundError:
        pass
    return pd.DataFrame(columns=["Plant Name", "Owner"])

def apply_ownership(df, owners):
    if owners.empty:
        df["Owner"] = None
        return df
    # Strip whitespace from join key on both sides
    df["Plant Name"] = df["Plant Name"].str.strip()
    owners = owners.copy()
    owners["Plant Name"] = owners["Plant Name"].str.strip()
    df = df.merge(owners, on="Plant Name", how="left")
    if "Owner" not in df.columns:
        df["Owner"] = None
    return df

data_file = find_data_file()
data_loaded = False

if data_file:
    with open(data_file, "rb") as f:
        df_raw = process_file(f.read())
    owners_df = load_ownership()
    df_raw = apply_ownership(df_raw, owners_df)
    data_loaded = True

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Filters")

    if not data_loaded:
        uploaded = st.file_uploader("Upload EIA 860M Excel file", type=["xlsx"])
        if uploaded:
            df_raw = process_file(uploaded.read())
            owners_df = load_ownership()
            df_raw = apply_ownership(df_raw, owners_df)
            data_loaded = True

    if data_loaded:
        seg_options = sorted(df_raw["Segment"].dropna().unique())
        selected_seg = st.multiselect("Segment", seg_options, default=list(seg_options))

        status_options = sorted(df_raw["Status"].dropna().unique())
        selected_status = st.multiselect("Status", status_options, default=list(status_options))

        year_options = sorted(df_raw["Operating Year"].dropna().unique().tolist())
        selected_years = st.multiselect("Operating Year", year_options, default=year_options)

        state_options = sorted(df_raw["State"].dropna().unique())
        selected_states = st.multiselect("State", state_options, default=list(state_options))

        sector_options = sorted(df_raw["Sector"].dropna().unique())
        selected_sectors = st.multiselect("Sector", sector_options, default=list(sector_options))

if not data_loaded:
    st.title("Solar & BESS Market Dashboard")
    st.info("No EIA data file found. Upload the EIA Form 860M Excel file using the sidebar.")
    st.stop()

# ── Apply filters ──────────────────────────────────────────────────────────────
df = df_raw.copy()
if selected_seg:
    df = df[df["Segment"].isin(selected_seg)]
if selected_status:
    df = df[df["Status"].isin(selected_status)]
if selected_years:
    df = df[df["Operating Year"].isin(selected_years)]
if selected_states:
    df = df[df["State"].isin(selected_states)]
if selected_sectors:
    df = df[df["Sector"].isin(selected_sectors)]

solar_df = df[df["Technology"] == "Solar Photovoltaic"].copy()
bess_df = df[df["Technology"] == "Batteries"].copy()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab9, tab7, tab8 = st.tabs([
    "Solar Market",
    "BESS Market",
    "Solar Projects",
    "BESS Projects",
    "Project Map",
    "Vegetation",
    "Wildfire Risk",
    "Search by Project",
    "Search by Owner"
])

# ── Solar Market ───────────────────────────────────────────────────────────────
with tab1:
    st.title("Solar Market Overview")

    operating = solar_df[solar_df["Status"] == "Operating"]
    development = solar_df[solar_df["Status"] == "Development"]

    c1, c2, c3 = st.columns(3)
    metric_card(c1, "Total GWac", to_gw(solar_df["Total MWac"]), f"{len(solar_df):,} plants")
    metric_card(c2, "Operating GWac", to_gw(operating["Total MWac"]), f"{len(operating):,} plants")
    metric_card(c3, "Development GWac", to_gw(development["Total MWac"]), f"{len(development):,} plants")

    st.markdown("<br>", unsafe_allow_html=True)

    yr_solar = solar_df[solar_df["Operating Year"].between(2015, 2035)]
    fig_yr = stacked_bar(
        yr_solar, "Operating Year", "Segment", "Total MWac",
        "GWac by Operating Year",
        color_map={"Utility": BLUE_DARK, "DG": BLUE_LIGHT}
    )
    st.plotly_chart(fig_yr, use_container_width=True)

    st8 = solar_df.dropna(subset=["State"]).groupby("State")["Total MWac"].sum().reset_index()
    st8["GWac"] = (st8["Total MWac"] / 1000).round(1)
    st8 = st8.nlargest(15, "GWac").sort_values("GWac")
    st.plotly_chart(styled_bar(st8, "GWac", "State", "Top 15 States by GWac", orientation="h"),
                    use_container_width=True)

# ── BESS Market ────────────────────────────────────────────────────────────────
with tab2:
    st.title("BESS Market Overview")

    c1, c2 = st.columns(2)
    metric_card(c1, "Total GWac", to_gw(bess_df["Total MWac"]), f"{len(bess_df):,} plants")
    metric_card(c2, "Total GWh", to_gw(bess_df["Total MWh"]), "Energy capacity")

    st.markdown("<br>", unsafe_allow_html=True)

    cl, cr = st.columns(2)
    with cl:
        fig_bess_yr = simple_bar(bess_df, "Operating Year", "Total MWac", "GWac by Operating Year")
        st.plotly_chart(fig_bess_yr, use_container_width=True)

    with cr:
        fig_bess_gwh = simple_bar(bess_df.dropna(subset=["Total MWh"]),
                                  "Operating Year", "Total MWh", "GWh by Operating Year")
        st.plotly_chart(fig_bess_gwh, use_container_width=True)

    cl2, cr2 = st.columns(2)
    with cl2:
        st8_bess = bess_df.dropna(subset=["State"]).groupby("State")["Total MWac"].sum().reset_index()
        st8_bess["GWac"] = (st8_bess["Total MWac"] / 1000).round(1)
        st8_bess = st8_bess.nlargest(15, "GWac").sort_values("GWac")
        st.plotly_chart(styled_bar(st8_bess, "GWac", "State", "Top 15 States by GWac",
                                   orientation="h"), use_container_width=True)

    with cr2:
        st8_gwh = bess_df.dropna(subset=["State", "Total MWh"]).groupby("State")["Total MWh"].sum().reset_index()
        st8_gwh["GWh"] = (st8_gwh["Total MWh"] / 1000).round(1)
        st8_gwh = st8_gwh.nlargest(15, "GWh").sort_values("GWh")
        st.plotly_chart(styled_bar(st8_gwh, "GWh", "State", "Top 15 States by GWh",
                                   orientation="h"), use_container_width=True)

# ── Solar Projects ─────────────────────────────────────────────────────────────
with tab3:
    st.title("Solar Project List")
    cols = ["Plant Name", "Owner", "Project Entity", "State", "County", "Operating Year",
            "Status", "Total MWdc", "Total MWac"]
    cols = [c for c in cols if c in solar_df.columns]
    d = solar_df[cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=650)

# ── BESS Projects ──────────────────────────────────────────────────────────────
with tab4:
    st.title("BESS Project List")
    cols = ["Plant Name", "Owner", "Project Entity", "State", "County", "Operating Year",
            "Status", "Total MWh", "Total MWac"]
    cols = [c for c in cols if c in bess_df.columns]
    d = bess_df[cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=650)

# ── Project Map ────────────────────────────────────────────────────────────────
with tab5:
    st.title("Project Map")
    st.plotly_chart(make_map(df), use_container_width=True)

# ── Vegetation ─────────────────────────────────────────────────────────────────
with tab6:
    st.title("Vegetation Management")

    veg = df[
        (df["Technology"] == "Solar Photovoltaic") &
        (df["Segment"] == "Utility") &
        (df["State"].isin(MIDWEST_STATES)) &
        (df["Est. Acres"] > 1000)
    ].copy()

    st.markdown(f"**{len(veg):,} utility-scale solar sites** in the Midwest with Est. Acres > 1,000")
    st.markdown("<br>", unsafe_allow_html=True)

    table_cols = ["Plant Name", "Owner", "Project Entity", "State", "County",
                  "Est. Acres", "Total MWac", "Operating Year", "Status"]
    table_cols = [c for c in table_cols if c in veg.columns]
    veg_display = veg[table_cols].sort_values("Est. Acres", ascending=False).reset_index(drop=True)
    veg_display["Est. Acres"] = veg_display["Est. Acres"].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else ""
    )
    st.dataframe(veg_display, use_container_width=True, height=400)

    st.markdown("<br>", unsafe_allow_html=True)

    veg_map = veg.dropna(subset=["Latitude", "Longitude"]).copy()
    veg_map = veg_map[(veg_map["Latitude"].between(24, 50)) & (veg_map["Longitude"].between(-125, -66))]
    veg_map["bubble_size"] = veg_map["Est. Acres"].clip(upper=10000) ** 0.5

    if len(veg_map) > 0:
        fig_veg = px.scatter_mapbox(
            veg_map, lat="Latitude", lon="Longitude",
            size="bubble_size", color="Status",
            color_discrete_map={"Operating": BLUE_DARK, "Development": AMBER},
            hover_name="Plant Name",
            hover_data={"State": True, "County": True, "Status": True,
                        "Est. Acres": True, "Total MWac": True, "Operating Year": True,
                        "bubble_size": False, "Latitude": False, "Longitude": False},
            zoom=4, center={"lat": 42, "lon": -93},
            mapbox_style="open-street-map", height=500
        )
        fig_veg.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                        font=dict(family="Inter, sans-serif"))
        )
        st.plotly_chart(fig_veg, use_container_width=True)
    else:
        st.info("No sites with coordinates available for mapping.")

# ── Search ─────────────────────────────────────────────────────────────────────
with tab7:
    st.title("Search by Project")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        search_name = st.text_input("Search by project name", placeholder="e.g. Desert Sunlight, Gemini...")
    with col_s2:
        search_owner = st.text_input("Search by owner", placeholder="e.g. NextEra, Invenergy...")

    show_detail = False

    if search_name or search_owner:
        mask = pd.Series([True] * len(df_raw), index=df_raw.index)
        if search_name:
            mask = mask & df_raw["Plant Name"].str.contains(search_name, case=False, na=False)
        if search_owner:
            mask = mask & df_raw["Owner"].fillna("").str.contains(search_owner, case=False, na=False)
        results = df_raw[mask].copy()

        if len(results) == 0:
            st.warning("No plants found matching that search.")
        else:
            # Owner-only search: show a summary table first
            if search_owner and not search_name:
                st.markdown(f"**{len(results):,} plants found for owner matching '{search_owner}'**")
                owner_cols = ["Plant Name", "Owner", "Project Entity", "State", "County", "Technology",
                              "Segment", "Status", "Operating Year", "Total MWac", "Total MWh"]
                owner_cols = [c for c in owner_cols if c in results.columns]
                st.dataframe(
                    results[owner_cols].sort_values("Total MWac", ascending=False).reset_index(drop=True),
                    use_container_width=True, height=400
                )
                st.markdown("**Enter a plant name above to see full details and map for a specific plant.**")
            else:
                show_detail = True
                plant_names = sorted(results["Plant Name"].unique())
                if len(plant_names) > 1:
                    selected_plant = st.selectbox(f"{len(plant_names)} plants found -- select one", plant_names)
                else:
                    selected_plant = plant_names[0]

                plant_rows = results[results["Plant Name"] == selected_plant]
                row = plant_rows.iloc[0]

    if show_detail:
            st.markdown("<br>", unsafe_allow_html=True)

            # Detail cards
            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown("### Plant Details")

                def detail_row(label, value):
                    if pd.isna(value) or value == "" or value is None:
                        value = "—"
                    return f'<div class="detail-row"><span class="detail-label">{label}</span><span class="detail-value">{value}</span></div>'

                details_html = '<div class="detail-card">'
                details_html += detail_row("Plant Name", row.get("Plant Name", ""))
                details_html += detail_row("Owner", row.get("Owner", ""))
                details_html += detail_row("Project Entity", row.get("Project Entity", ""))
                details_html += detail_row("State", row.get("State", ""))
                details_html += detail_row("County", row.get("County", ""))
                details_html += detail_row("Technology", row.get("Technology", ""))
                details_html += detail_row("Sector", row.get("Sector", ""))
                details_html += detail_row("Segment", row.get("Segment", ""))
                details_html += detail_row("Status", row.get("Status", ""))
                details_html += detail_row("EIA Status", row.get("EIA Status", ""))
                details_html += detail_row("Operating Year", str(row.get("Operating Year", "")))
                details_html += detail_row("Total MWac", f"{row.get('Total MWac', 0):,.1f}")
                mwdc = row.get("Total MWdc", None)
                details_html += detail_row("Total MWdc", f"{mwdc:,.1f}" if pd.notna(mwdc) and mwdc else "—")
                mwh = row.get("Total MWh", None)
                details_html += detail_row("Total MWh", f"{mwh:,.1f}" if pd.notna(mwh) and mwh else "—")
                acres = row.get("Est. Acres", None)
                details_html += detail_row("Est. Acres", f"{int(acres):,}" if pd.notna(acres) and acres else "—")
                lat = row.get("Latitude", None)
                lon = row.get("Longitude", None)
                details_html += detail_row("Coordinates", f"{lat:.4f}, {lon:.4f}" if pd.notna(lat) and pd.notna(lon) else "—")
                details_html += '</div>'

                st.markdown(details_html, unsafe_allow_html=True)

                # If multiple technology rows (solar + BESS co-located) show them
                if len(plant_rows) > 1:
                    st.markdown("**Co-located assets at this plant:**")
                    sub = plant_rows[["Technology", "Total MWac", "Total MWh", "Segment"]].reset_index(drop=True)
                    st.dataframe(sub, use_container_width=True)

            with col_right:
                st.markdown("### Location")
                if pd.notna(lat) and pd.notna(lon):
                    zoom_level = 14
                    google_maps_url = f"https://maps.google.com/maps?q={lat},{lon}&z={zoom_level}&output=embed&t=k"
                    st.components.v1.iframe(google_maps_url, height=500)
                else:
                    st.info("No coordinates available for this plant.")

            # ── Nearby Projects ────────────────────────────────────────────────
            if pd.notna(lat) and pd.notna(lon):
                st.markdown("---")
                st.markdown("### Nearby Projects")

                radius_miles = st.number_input(
                    "Search radius (miles)", min_value=1, max_value=500,
                    value=50, step=5
                )

                # Haversine distance calculation
                import math

                def haversine(lat1, lon1, lat2, lon2):
                    R = 3958.8  # Earth radius in miles
                    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    return R * 2 * math.asin(math.sqrt(a))

                nearby = df.dropna(subset=["Latitude", "Longitude"]).copy()
                nearby["Distance (mi)"] = nearby.apply(
                    lambda r: haversine(lat, lon, r["Latitude"], r["Longitude"]), axis=1
                )
                nearby = nearby[nearby["Distance (mi)"] <= radius_miles]
                nearby = nearby[nearby["Plant Name"] != selected_plant]
                nearby = nearby.sort_values("Distance (mi)")

                st.markdown(f"**{len(nearby):,} projects within {radius_miles} miles**")

                if len(nearby) > 0:
                    # Table
                    nearby_cols = ["Plant Name", "Owner", "Project Entity", "State", "County", "Technology",
                                   "Segment", "Status", "Operating Year", "Total MWac", "Total MWdc",
                                   "Total MWh", "Distance (mi)"]
                    nearby_cols = [c for c in nearby_cols if c in nearby.columns]
                    nearby_display = nearby[nearby_cols].reset_index(drop=True)
                    nearby_display["Distance (mi)"] = nearby_display["Distance (mi)"].round(1)
                    st.dataframe(nearby_display, use_container_width=True, height=300)

                    # Map showing reference site + nearby projects
                    map_data = nearby[["Plant Name", "Latitude", "Longitude",
                                       "Technology", "Status", "Total MWac"]].copy()
                    map_data["Type"] = "Nearby"
                    map_data["bubble_size"] = map_data["Total MWac"].clip(upper=2000) ** 0.5

                    # Reference site marker
                    ref_mwac = row.get("Total MWac", 100)
                    ref_row = pd.DataFrame([{
                        "Plant Name": selected_plant + " (Reference)",
                        "Latitude": lat,
                        "Longitude": lon,
                        "Technology": row.get("Technology", "Solar Photovoltaic"),
                        "Status": row.get("Status", "Operating"),
                        "Total MWac": ref_mwac,
                        "Type": "Reference",
                        "bubble_size": max(float(ref_mwac if pd.notna(ref_mwac) else 100), 100) ** 0.5 * 1.5
                    }])

                    map_combined = pd.concat([ref_row, map_data], ignore_index=True)

                    fig_nearby = px.scatter_mapbox(
                        map_combined,
                        lat="Latitude", lon="Longitude",
                        size="bubble_size",
                        color="Type",
                        color_discrete_map={"Reference": AMBER, "Nearby": BLUE_DARK},
                        hover_name="Plant Name",
                        hover_data={"Technology": True, "Status": True,
                                    "Total MWac": True, "Type": False,
                                    "bubble_size": False, "Latitude": False, "Longitude": False},
                        zoom=7,
                        center={"lat": lat, "lon": lon},
                        mapbox_style="open-street-map",
                        height=500
                    )
                    fig_nearby.update_layout(
                        margin=dict(t=0, b=0, l=0, r=0),
                        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                                    xanchor="left", x=0,
                                    font=dict(family="Inter, sans-serif"))
                    )
                    st.plotly_chart(fig_nearby, use_container_width=True)
                else:
                    st.info(f"No other projects found within {radius_miles} miles.")
    else:
        st.markdown("Enter a plant name or owner above to search. Partial matches are supported.")

# ── Owner ──────────────────────────────────────────────────────────────────────
with tab8:
    st.title("Search by Owner")

    # Only useful if ownership data is populated
    if df["Owner"].isna().all():
        st.info("No ownership data loaded yet. Add owners to your EIA Asset Owners.xlsx file in GitHub.")
        st.stop()

    owner_query = st.text_input("Search owner name", placeholder="e.g. NextEra, Invenergy, AES...")

    if owner_query:
        owner_matches = df[df["Owner"].str.contains(owner_query, case=False, na=False)].copy()

        if len(owner_matches) == 0:
            st.warning("No owners found matching that search.")
        else:
            matched_owners = sorted(owner_matches["Owner"].dropna().unique())
            if len(matched_owners) > 1:
                selected_owner = st.selectbox(
                    f"{len(matched_owners)} owners found -- select one", ["-- Select --"] + matched_owners
                )
                if selected_owner == "-- Select --":
                    st.stop()
            else:
                selected_owner = matched_owners[0]

            owner_results = df[df["Owner"] == selected_owner].copy()

            st.markdown("<br>", unsafe_allow_html=True)

            # KPI row
            solar_own = owner_results[owner_results["Technology"] == "Solar Photovoltaic"]
            bess_own = owner_results[owner_results["Technology"] == "Batteries"]
            op_own = owner_results[owner_results["Status"] == "Operating"]
            dev_own = owner_results[owner_results["Status"] == "Development"]

            c1, c2, c3, c4, c5 = st.columns(5)
            metric_card(c1, "Total GWac", to_gw(owner_results["Total MWac"]), f"{len(owner_results):,} plants")
            metric_card(c2, "Solar GWac", to_gw(solar_own["Total MWac"]), f"{len(solar_own):,} plants")
            metric_card(c3, "BESS GWac", to_gw(bess_own["Total MWac"]), f"{len(bess_own):,} plants")
            metric_card(c4, "Operating GWac", to_gw(op_own["Total MWac"]), f"{len(op_own):,} plants")
            metric_card(c5, "Development GWac", to_gw(dev_own["Total MWac"]), f"{len(dev_own):,} plants")

            st.markdown("<br>", unsafe_allow_html=True)

            # Map
            map_own = owner_results.dropna(subset=["Latitude", "Longitude"]).copy()
            map_own = map_own[(map_own["Latitude"].between(24, 50)) & (map_own["Longitude"].between(-125, -66))]
            map_own["bubble_size"] = map_own["Total MWac"].clip(upper=2000) ** 0.5

            if len(map_own) > 0:
                fig_own = px.scatter_mapbox(
                    map_own,
                    lat="Latitude", lon="Longitude",
                    size="bubble_size",
                    color="Technology",
                    color_discrete_map={"Solar Photovoltaic": BLUE_DARK, "Batteries": AMBER},
                    hover_name="Plant Name",
                    hover_data={"State": True, "Status": True, "Total MWac": True,
                                "Operating Year": True, "bubble_size": False,
                                "Latitude": False, "Longitude": False},
                    zoom=3.5,
                    center={"lat": map_own["Latitude"].mean(), "lon": map_own["Longitude"].mean()},
                    mapbox_style="open-street-map",
                    height=450,
                    custom_data=["Plant Name", "Latitude", "Longitude"]
                )
                fig_own.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.01,
                                xanchor="left", x=0,
                                font=dict(family="Inter, sans-serif"))
                )
                st.plotly_chart(fig_own, use_container_width=True, key="owner_map")

            st.markdown("<br>", unsafe_allow_html=True)

            # Table
            table_cols = ["Plant Name", "Project Entity", "State", "County", "Technology",
                          "Segment", "Status", "EIA Status", "Operating Year",
                          "Total MWac", "Total MWdc", "Total MWh", "Est. Acres"]
            table_cols = [c for c in table_cols if c in owner_results.columns]
            owner_table = owner_results[table_cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
            st.dataframe(owner_table, use_container_width=True, height=400)

            # Site detail on selection
            st.markdown("---")
            st.markdown("### Site Detail")
            site_names = sorted(owner_results["Plant Name"].dropna().unique())
            selected_site = st.selectbox("Select a site to view satellite image", site_names)

            if selected_site:
                site_row = owner_results[owner_results["Plant Name"] == selected_site].iloc[0]
                site_lat = site_row.get("Latitude")
                site_lon = site_row.get("Longitude")

                detail_col, map_col = st.columns([1, 1])

                with detail_col:
                    def detail_row_own(label, value):
                        if pd.isna(value) or value == "" or value is None:
                            value = "—"
                        return f'<div class="detail-row"><span class="detail-label">{label}</span><span class="detail-value">{value}</span></div>'

                    d_html = '<div class="detail-card">'
                    d_html += detail_row_own("Plant Name", site_row.get("Plant Name", ""))
                    d_html += detail_row_own("Owner", site_row.get("Owner", ""))
                    d_html += detail_row_own("Project Entity", site_row.get("Project Entity", ""))
                    d_html += detail_row_own("State", site_row.get("State", ""))
                    d_html += detail_row_own("County", site_row.get("County", ""))
                    d_html += detail_row_own("Technology", site_row.get("Technology", ""))
                    d_html += detail_row_own("Segment", site_row.get("Segment", ""))
                    d_html += detail_row_own("Status", site_row.get("Status", ""))
                    d_html += detail_row_own("EIA Status", site_row.get("EIA Status", ""))
                    d_html += detail_row_own("Operating Year", str(site_row.get("Operating Year", "")))
                    mwac = site_row.get("Total MWac", 0)
                    d_html += detail_row_own("Total MWac", f"{mwac:,.1f}" if pd.notna(mwac) else "—")
                    mwdc = site_row.get("Total MWdc")
                    d_html += detail_row_own("Total MWdc", f"{mwdc:,.1f}" if pd.notna(mwdc) and mwdc else "—")
                    mwh = site_row.get("Total MWh")
                    d_html += detail_row_own("Total MWh", f"{mwh:,.1f}" if pd.notna(mwh) and mwh else "—")
                    acres = site_row.get("Est. Acres")
                    d_html += detail_row_own("Est. Acres", f"{int(acres):,}" if pd.notna(acres) and acres else "—")
                    d_html += '</div>'
                    st.markdown(d_html, unsafe_allow_html=True)

                with map_col:
                    if pd.notna(site_lat) and pd.notna(site_lon):
                        google_maps_url = f"https://maps.google.com/maps?q={site_lat},{site_lon}&z=14&output=embed&t=k"
                        st.components.v1.iframe(google_maps_url, height=460)
                    else:
                        st.info("No coordinates available for this site.")
    else:
        st.markdown("Enter an owner name above to search. Partial matches are supported.")

# ── Wildfire Risk ────────────────────────────────────────────────────────────
with tab9:
    st.title("Wildfire Risk")
    st.markdown(
        "Cross-references your operating sites against near-real-time active fire "
        "detections from NASA FIRMS (satellite thermal anomaly data)."
    )
    st.markdown("<br>", unsafe_allow_html=True)

    firms_key = st.secrets.get("FIRMS_MAP_KEY", "") if hasattr(st, "secrets") else ""
    if not firms_key:
        firms_key = st.text_input(
            "NASA FIRMS MAP_KEY", type="password",
            help="Free, instant key at https://firms.modaps.eosdis.nasa.gov/api/map_key/. "
                 "Add it to Streamlit secrets as FIRMS_MAP_KEY to skip this box."
        )

    if not firms_key:
        st.info("Enter a FIRMS MAP_KEY above to load fire data.")
        st.stop()

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        fire_source = st.selectbox(
            "Satellite source", ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "MODIS_NRT"],
            index=0, help="VIIRS detects smaller fires at 375m resolution; MODIS is coarser but has a longer track record."
        )
    with col_b:
        day_range = st.slider("Days of fire detections", 1, 7, 2)
    with col_c:
        radius_miles = st.slider("Risk radius (miles)", 5, 100, 25)
    with col_d:
        min_confidence = st.selectbox(
            "Minimum confidence", ["Nominal & High", "High only", "All (incl. low)"],
            index=0, help="Low-confidence detections often include agricultural burns, industrial heat, and other false positives rather than genuine wildfires."
        )

    fires, fire_err = get_firms_data(firms_key, fire_source, day_range)
    if fire_err:
        st.error(fire_err)
        st.stop()

    fires_raw_count = len(fires)
    fires = filter_fire_confidence(fires, fire_source, min_confidence)

    operating_sites = df[df["Status"] == "Operating"].copy()
    risk_sites = compute_wildfire_risk(operating_sites, fires, radius_miles)
    at_risk = risk_sites[risk_sites["At Risk"]]

    c1, c2, c3 = st.columns(3)
    metric_card(c1, "Sites at Risk", f"{len(at_risk):,}", f"within {radius_miles} mi of active fire")
    metric_card(c2, "GWac at Risk", to_gw(at_risk["Total MWac"]), f"{len(at_risk):,} operating sites")
    metric_card(c3, "Active Detections", f"{len(fires):,}", f"of {fires_raw_count:,} raw, last {day_range} day(s)")

    st.markdown("<br>", unsafe_allow_html=True)

    if len(at_risk) > 0:
        st.markdown("### Sites Within Risk Radius")
        table_cols = ["Plant Name", "Owner", "Project Entity", "State", "County",
                      "Technology", "Total MWac", "Nearest Fire (mi)"]
        table_cols = [c for c in table_cols if c in at_risk.columns]
        st.dataframe(
            at_risk[table_cols].sort_values("Nearest Fire (mi)").reset_index(drop=True),
            use_container_width=True, height=350
        )
    else:
        st.success(f"No operating sites within {radius_miles} miles of an active fire detection.")

    st.markdown("<br>", unsafe_allow_html=True)

    map_sites = risk_sites[risk_sites["At Risk"]].dropna(subset=["Latitude", "Longitude"]).copy()
    map_sites = map_sites[(map_sites["Latitude"].between(24, 50)) & (map_sites["Longitude"].between(-125, -66))]
    map_sites["bubble_size"] = map_sites["Total MWac"].clip(upper=2000) ** 0.5

    if map_sites.empty:
        st.info("No at-risk sites to show on the map at this radius and confidence level.")
    else:
        fig_wf = px.scatter_mapbox(
            map_sites, lat="Latitude", lon="Longitude",
            size="bubble_size", color_discrete_sequence=["#DC2626"],
            hover_name="Plant Name",
            hover_data={"State": True, "Total MWac": True, "Nearest Fire (mi)": True,
                        "bubble_size": False, "Latitude": False, "Longitude": False},
            zoom=3.5, center={"lat": 38.5, "lon": -96},
            mapbox_style="open-street-map", height=600
        )
        fig_wf.update_traces(name="At Risk Site", showlegend=True)
        if not fires.empty:
            fig_wf.add_scattermapbox(
                lat=fires["latitude"], lon=fires["longitude"],
                mode="markers",
                marker=dict(size=6, color="#FF8C00", opacity=0.6),
                name="Fire Detection",
                hoverinfo="skip"
            )
        fig_wf.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                        font=dict(family="Inter, sans-serif"))
        )
        st.plotly_chart(fig_wf, use_container_width=True)

    st.caption(
        "Fire detections are satellite thermal anomalies (NASA FIRMS, VIIRS/MODIS), filtered to "
        f"'{min_confidence}' confidence to reduce agricultural burns and other false positives. "
        "Cloud cover and small or slow-moving fires can still go undetected, so treat this as "
        "a screening layer, not a confirmed threat assessment."
    )

