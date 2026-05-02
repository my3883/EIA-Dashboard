import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Solar & BESS Market Dashboard",
    page_icon="☀️",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        text-align: center;
    }
    .metric-label { font-size: 12px; color: #6c757d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 28px; font-weight: 700; color: #1a1a2e; margin-top: 4px; }
    .metric-sub { font-size: 12px; color: #6c757d; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

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

TECHNOLOGIES = ["Solar Photovoltaic", "Batteries"]


@st.cache_data
def process_file(file_bytes):
    import io
    f = io.BytesIO(file_bytes)

    # Operating tab
    op = pd.read_excel(f, sheet_name="Operating", header=2)
    op = op[[c for c in OPERATING_KEEP if c in op.columns]].copy()
    op = op[op["Plant State"] != "PR"]
    op = op[op["Technology"].isin(TECHNOLOGIES)]
    op = op.rename(columns={
        "Nameplate Capacity (MW)": "MWac",
        "DC Net Capacity (MW)": "MWdc",
        "Nameplate Energy Capacity (MWh)": "MWh"
    })
    op["Status_Simple"] = "Operating"

    # Planned tab
    f.seek(0)
    pl = pd.read_excel(f, sheet_name="Planned", header=2)
    pl = pl[[c for c in PLANNED_KEEP if c in pl.columns]].copy()
    pl = pl[pl["Plant State"] != "PR"]
    pl = pl[pl["Technology"].isin(TECHNOLOGIES)]
    pl = pl.rename(columns={
        "Nameplate Capacity (MW)": "MWac",
        "Planned Operation Month": "Operating Month",
        "Planned Operation Year": "Operating Year"
    })
    pl["MWdc"] = None
    pl["MWh"] = None
    pl["Status_Simple"] = "Development"

    # Append
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

    # Segment flag
    def segment(row):
        if row["Technology"] == "Solar Photovoltaic" and row["Total_MWac"] >= 75:
            return "Utility"
        elif row["Technology"] == "Batteries" and row["Total_MWac"] >= 10:
            return "Utility"
        return "DG"

    df["Segment"] = df.apply(segment, axis=1)
    df["Status"] = df["Status_Simple"]
    df["GWac"] = (df["Total_MWac"] / 1000).round(3)

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


# Sidebar
with st.sidebar:
    st.markdown("## ☀️ Solar & BESS Market")
    st.markdown("---")

    uploaded_file = st.file_uploader("Upload EIA 860M Excel file", type=["xlsx"])

    if uploaded_file:
        with st.spinner("Processing EIA data..."):
            df_raw = process_file(uploaded_file.read())

        st.success(f"{len(df_raw):,} plants loaded")
        st.markdown("### Filters")

        tech_options = sorted(df_raw["Technology"].dropna().unique())
        selected_tech = st.multiselect("Technology", tech_options, default=list(tech_options))

        seg_options = sorted(df_raw["Segment"].dropna().unique())
        selected_seg = st.multiselect("Segment", seg_options, default=list(seg_options))

        status_options = sorted(df_raw["Status"].dropna().unique())
        selected_status = st.multiselect("Status", status_options, default=list(status_options))

        state_options = ["All"] + sorted(df_raw["Plant State"].dropna().unique())
        selected_state = st.selectbox("Plant State", state_options)

        sector_options = ["All"] + sorted(df_raw["Sector"].dropna().unique())
        selected_sector = st.selectbox("Sector", sector_options)

        st.markdown("---")
        page = st.radio("Page", ["Market Overview", "Solar Project List", "BESS Project List", "Project Map"])

if not uploaded_file:
    st.title("Solar & BESS Market Dashboard")
    st.info("Upload the EIA Form 860M Excel file using the sidebar to get started.")
    st.markdown("""
    **Supported file:** EIA Form 860M monthly generator file (e.g. `march_generator2026.xlsx`)

    The app will automatically:
    - Read Operating and Planned tabs
    - Filter to Solar Photovoltaic and Batteries
    - Exclude Puerto Rico
    - Aggregate to plant level
    - Apply Utility / DG segment flags (75 MWac solar, 10 MWac BESS)
    - Combine Operating and Development status
    """)
    st.stop()

# Apply filters
df = df_raw.copy()
if selected_tech:
    df = df[df["Technology"].isin(selected_tech)]
if selected_seg:
    df = df[df["Segment"].isin(selected_seg)]
if selected_status:
    df = df[df["Status"].isin(selected_status)]
if selected_state != "All":
    df = df[df["Plant State"] == selected_state]
if selected_sector != "All":
    df = df[df["Sector"] == selected_sector]

# Market Overview
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
        fig = px.bar(yr, x="Operating Year", y="GWac", title="GWac by Operating Year",
                     text="GWac", color_discrete_sequence=["#2563eb"])
        fig.update_traces(textposition="outside", texttemplate="%{text:.0f}")
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                          showlegend=False, margin=dict(t=50, b=40))
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        seg = df.groupby(["Segment", "Status"])["Total MWac"].sum().reset_index()
        seg["GWac"] = (seg["Total MWac"] / 1000).round(1)
        fig2 = px.bar(seg, x="Segment", y="GWac", color="Status",
                      title="GWac by Segment and Status", text="GWac",
                      color_discrete_map={"Operating": "#2563eb", "Development": "#93c5fd"})
        fig2.update_traces(textposition="outside", texttemplate="%{text:.0f}")
        fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(t=50, b=40))
        st.plotly_chart(fig2, use_container_width=True)

    cl2, cr2 = st.columns(2)

    with cl2:
        st8 = df.groupby("Plant State")["Total MWac"].sum().reset_index()
        st8["GWac"] = (st8["Total MWac"] / 1000).round(1)
        st8 = st8.nlargest(15, "GWac").sort_values("GWac")
        fig3 = px.bar(st8, x="GWac", y="Plant State", orientation="h",
                      title="Top 15 States by GWac", text="GWac",
                      color_discrete_sequence=["#2563eb"])
        fig3.update_traces(textposition="outside", texttemplate="%{text:.1f}")
        fig3.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                           showlegend=False, margin=dict(t=50, b=40))
        st.plotly_chart(fig3, use_container_width=True)

    with cr2:
        ts = df.groupby(["Technology", "Segment"])["Total MWac"].sum().reset_index()
        ts["GWac"] = (ts["Total MWac"] / 1000).round(1)
        fig4 = px.bar(ts, x="Technology", y="GWac", color="Segment",
                      title="GWac by Technology and Segment", text="GWac",
                      color_discrete_map={"Utility": "#2563eb", "DG": "#93c5fd"})
        fig4.update_traces(textposition="outside", texttemplate="%{text:.0f}")
        fig4.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(t=50, b=40))
        st.plotly_chart(fig4, use_container_width=True)

# Solar Project List
elif page == "Solar Project List":
    st.title("Solar Project List")
    d = df[df["Technology"] == "Solar Photovoltaic"].copy()
    cols = ["Plant Name", "Owner", "Plant State", "County", "Sector", "Segment",
            "Operating Year", "Status", "Total MWdc", "Total MWac"]
    cols = [c for c in cols if c in d.columns]
    d = d[cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=600)

# BESS Project List
elif page == "BESS Project List":
    st.title("BESS Project List")
    d = df[df["Technology"] == "Batteries"].copy()
    cols = ["Plant Name", "Owner", "Plant State", "County", "Sector", "Segment",
            "Operating Year", "Status", "Total MWh", "Total MWac"]
    cols = [c for c in cols if c in d.columns]
    d = d[cols].sort_values("Total MWac", ascending=False).reset_index(drop=True)
    st.markdown(f"**{len(d):,} projects** | **{to_gw(d['Total MWac'])} GWac**")
    st.dataframe(d, use_container_width=True, height=600)

# Project Map
elif page == "Project Map":
    st.title("Project Map")
    m = df.dropna(subset=["Latitude", "Longitude", "Total MWac"]).copy()
    m = m[(m["Latitude"].between(-90, 90)) & (m["Longitude"].between(-180, 180))]
    m["bubble_size"] = m["Total MWac"].clip(upper=2000) ** 0.5
    fig = px.scatter_mapbox(
        m, lat="Latitude", lon="Longitude",
        size="bubble_size", color="Technology",
        color_discrete_map={"Solar Photovoltaic": "#2563eb", "Batteries": "#f59e0b"},
        hover_name="Plant Name",
        hover_data={"Plant State": True, "Segment": True, "Status": True,
                    "Total MWac": True, "Operating Year": True,
                    "bubble_size": False, "Latitude": False, "Longitude": False},
        zoom=3.5, center={"lat": 38.5, "lon": -96},
        mapbox_style="open-street-map", height=650
    )
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0),
                      legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0))
    st.plotly_chart(fig, use_container_width=True)
