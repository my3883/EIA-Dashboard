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
        gap: 4px;
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
        "Entity Name": "Owner",
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


# ── Find data file ─────────────────────────────────────────────────────────────
def find_data_file():
    matches = glob.glob("*generator*.xlsx") + glob.glob("*Generator*.xlsx")
    return max(matches, key=os.path.getmtime) if matches else None

data_file = find_data_file()
data_loaded = False

if data_file:
    with open(data_file, "rb") as f:
        df_raw = process_file(f.read())
    data_loaded = True

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Filters")

    if not data_loaded:
        uploaded = st.file_uploader("Upload EIA 860M Excel file", type=["xlsx"])
        if uploaded:
            df_raw = process_file(uploaded.read())
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Solar Market",
    "BESS Market",
    "Solar Projects",
    "BESS Projects",
    "Project Map",
    "Vegetation",
    "Search"
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
    d = solar_df[["Plant Name", "Owner", "State", "County", "Operating Year",
                  "Status", "Total MWdc", "Total MWac"]].copy()
    d = d[[c for c in d.columns if c in solar_df.columns]]
    d = d.sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=650)

# ── BESS Projects ──────────────────────────────────────────────────────────────
with tab4:
    st.title("BESS Project List")
    d = bess_df[["Plant Name", "Owner", "State", "County", "Operating Year",
                 "Status", "Total MWh", "Total MWac"]].copy()
    d = d[[c for c in d.columns if c in bess_df.columns]]
    d = d.sort_values("Total MWac", ascending=False).reset_index(drop=True)
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

    table_cols = ["Plant Name", "Owner", "State", "County",
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
    st.title("Plant Search")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        search_name = st.text_input("Search by plant name", placeholder="e.g. Desert Sunlight, Gemini...")
    with col_s2:
        search_owner = st.text_input("Search by owner", placeholder="e.g. NextEra, Invenergy...")

    show_detail = False

    if search_name or search_owner:
        mask = pd.Series([True] * len(df_raw), index=df_raw.index)
        if search_name:
            mask = mask & df_raw["Plant Name"].str.contains(search_name, case=False, na=False)
        if search_owner:
            mask = mask & df_raw["Owner"].str.contains(search_owner, case=False, na=False)
        results = df_raw[mask].copy()

        if len(results) == 0:
            st.warning("No plants found matching that search.")
        else:
            # Owner-only search: show a summary table first
            if search_owner and not search_name:
                st.markdown(f"**{len(results):,} plants found for owner matching '{search_owner}'**")
                owner_cols = ["Plant Name", "Owner", "State", "County", "Technology",
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
    else:
        st.markdown("Enter a plant name or owner above to search. Partial matches are supported.")
