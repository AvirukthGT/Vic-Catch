import os
import json
import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import pydeck as pdk
from shapely import wkt
from google.cloud import bigquery
from google.oauth2 import service_account
from geopy.geocoders import Nominatim
import h3

# Auth: Point the SDK at my service account key (for local testing)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
local_secret_path = os.path.join(base_dir, "secrets", "root-anvil-474411-k5-fdd00fadc7e2.json")
if os.path.exists(local_secret_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_secret_path

# ---------------------------------------------------------------------------
# Set up my page config and apply some custom dark-mode CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Transit Catchment Opportunity Engine",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stMetric"] {
        background: rgba(28, 28, 40, 0.65);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 14px 18px;
    }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; }
    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
    section[data-testid="stSidebar"] > div { padding-top: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Data pull — cached so I only hit BQ once per session
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Pulling precinct data from BigQuery…")
def load_data():
    if "gcp_service_account" in st.secrets:
        credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        client = bigquery.Client(credentials=credentials, project=credentials.project_id)
    else:
        client = bigquery.Client()
    query = """
        SELECT
            hex_id,
            hex_geometry,
            archetype,
            precinct_population,
            transit_stop_count,
            precinct_daily_trips,
            total_poi_count,
            walkway_count,
            cycleway_count,
            retail_count,
            car_parking_count,
            predicted_daily_trips,
            opportunity_gap
        FROM `root-anvil-474411-k5.vic_catch_dev.mart_precinct_archetypes`
    """
    df = client.query(query).to_dataframe()

    # I need to parse the WKT strings into Shapely geometries here
    df["geometry"] = df["hex_geometry"].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

    return gdf


# ---------------------------------------------------------------------------
# Load data and build a dynamic color palette for my charts
# ---------------------------------------------------------------------------
gdf = load_data()

# Distinct hex colors for plotly — I want one per archetype, guaranteed unique
_PALETTE = [
    "#FF006E", "#FB5607", "#FFBE0B", "#8338EC",
    "#3A86FF", "#06D6A0", "#FF6464", "#28DCDC",
    "#C882FF", "#FFC878",
]
unique_archetypes = sorted(gdf["archetype"].dropna().unique().tolist())
ARCHETYPE_COLOURS = {
    name: _PALETTE[i % len(_PALETTE)]
    for i, name in enumerate(unique_archetypes)
}

def hex_to_rgb(hex_col):
    hex_col = hex_col.lstrip("#")
    return [int(hex_col[i:i+2], 16) for i in (0, 2, 4)]

ARCHETYPE_COLOURS_RGB = {k: hex_to_rgb(v) for k, v in ARCHETYPE_COLOURS.items()}

# ---------------------------------------------------------------------------
# Build out my sidebar filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("Vic-Catch")
    st.markdown(
        """
        **Transit Catchment Opportunity Engine**

        Interactive decision-support tool for urban planners
        and property developers. Each hexagon is an H3 Res-8
        precinct (~0.7 km²) across Greater Melbourne.

        Archetypes are classified via K-Means clustering on
        transit supply, population demand, and active-transport
        infrastructure from GTFS, ABS Census, and OpenStreetMap.

        **Opportunity Gap** is the ML-predicted transit demand
        minus current supply - higher means under-served.
        """
    )
    st.divider()

    selected_archetypes = st.multiselect(
        "Archetypes",
        options=unique_archetypes,
        default=unique_archetypes,
        help="Pick one or more archetypes to display.",
        key="archetype_filter",
    )

    st.divider()

    pop_max = int(gdf["precinct_population"].max())
    min_pop = st.slider("Minimum Population", 0, pop_max, 0, key="pop_slider")

    trips_max = int(gdf["precinct_daily_trips"].max())
    min_trips = st.slider("Minimum Daily Transit Trips", 0, trips_max, 0, key="trips_slider")

    poi_max = int(gdf["total_poi_count"].max())
    min_pois = st.slider("Minimum OpenStreetMap POIs", 0, poi_max, 0, key="poi_slider")


# ---------------------------------------------------------------------------
# Apply my selected filters to the dataframe
# ---------------------------------------------------------------------------
filtered = gdf[
    (gdf["archetype"].isin(selected_archetypes))
    & (gdf["precinct_population"] >= min_pop)
    & (gdf["precinct_daily_trips"] >= min_trips)
    & (gdf["total_poi_count"] >= min_pois)
].copy()

# ---------------------------------------------------------------------------
# Set up the main header
# ---------------------------------------------------------------------------
st.title("Transit Catchment Opportunity Engine")
st.caption("Greater Melbourne · H3 Res-8 Precincts · Powered by BigQuery + dbt + XGBoost")

# ---------------------------------------------------------------------------
# Top KPI row for quick stats
# ---------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Filtered Precincts", f"{len(filtered):,}")
k2.metric("Total Population", f"{int(filtered['precinct_population'].sum()):,}")
k3.metric("Transit Stops", f"{int(filtered['transit_stop_count'].sum()):,}")
k4.metric("Daily Trips", f"{int(filtered['precinct_daily_trips'].sum()):,}")

# ---------------------------------------------------------------------------
# Render my Precinct Map (toggle between 2D Plotly or 3D PyDeck)
# ---------------------------------------------------------------------------
map_col1, map_col2 = st.columns([3, 1])
with map_col1:
    st.subheader("Precinct Map")
with map_col2:
    st.write("") # Spacer
    map_view = st.radio("Map View", ["2D (Plotly)", "3D (PyDeck)"], horizontal=True, label_visibility="collapsed")

if len(filtered) > 0:
    if map_view == "2D (Plotly)":
        geojson = json.loads(filtered.to_json())
    
        fig_map = px.choropleth_map(
            filtered,
            geojson=geojson,
            locations=filtered.index,
            color="archetype",
            color_discrete_map=ARCHETYPE_COLOURS,
            map_style="carto-darkmatter",
            center={"lat": -37.8136, "lon": 144.9631},
            zoom=9.5,
            opacity=0.65,
            hover_data={
                "hex_id": True,
                "archetype": True,
                "precinct_population": ":,",
                "precinct_daily_trips": ":,",
                "opportunity_gap": ":.1f",
            },
            labels={
                "hex_id": "Hex ID",
                "archetype": "Archetype",
                "precinct_population": "Population",
                "precinct_daily_trips": "Daily Trips",
                "opportunity_gap": "Opportunity Gap",
            },
        )
    
        fig_map.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            height=620,
            legend=dict(
                title="Archetype",
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=12),
            ),
        )
    
        st.plotly_chart(fig_map, width="stretch")
    else:
        # Rendering the PyDeck 3D Map
        filtered_pdk = filtered.copy()
        
        # I need RGB colors for PyDeck instead of hex
        def get_color(archetype):
            return ARCHETYPE_COLOURS_RGB.get(archetype, [255, 255, 255])
            
        filtered_pdk["fill_color"] = filtered_pdk["archetype"].apply(get_color)
        
        # Set the elevation based on my opportunity gap (I'm scaling it for visibility)
        filtered_pdk["elevation"] = filtered_pdk["opportunity_gap"].clip(lower=0) * 0.4
        
        layer = pdk.Layer(
            "GeoJsonLayer",
            json.loads(filtered_pdk.to_json()),
            pickable=True,
            stroked=True,
            filled=True,
            extruded=True,
            wireframe=True,
            get_fill_color="properties.fill_color",
            get_elevation="properties.elevation",
            get_line_color=[255, 255, 255, 50],
            line_width_min_pixels=1,
        )

        view_state = pdk.ViewState(
            latitude=-37.8136,
            longitude=144.9631,
            zoom=9.5,
            pitch=45,
            bearing=0,
        )

        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style=pdk.map_styles.DARK,
            tooltip={
                "html": "<b>Hex ID:</b> {hex_id}<br/>"
                        "<b>Archetype:</b> {archetype}<br/>"
                        "<b>Population:</b> {precinct_population}<br/>"
                        "<b>Daily Trips:</b> {precinct_daily_trips}<br/>"
                        "<b>Opp Gap:</b> {opportunity_gap}",
                "style": {"backgroundColor": "#1C1C28", "color": "white", "fontFamily": "sans-serif"}
            }
        )

        st.pydeck_chart(r, use_container_width=True)
else:
    st.info("No precincts match the current filters.")

# ---------------------------------------------------------------------------
# Display the top 10 under-served precincts (using my AI-driven ranking)
# ---------------------------------------------------------------------------
st.subheader("Top 10 Under-Served Precincts (AI Identified)")
st.caption("Ranked by the LightGBM Opportunity Gap (Predicted Demand vs Actual Supply)")

# Set up a geocoder to translate my hex IDs into human-readable suburb names
geolocator = Nominatim(user_agent="transit_catchment_engine")

@st.cache_data(show_spinner=False)
def get_human_address(hex_id):
    try:
        lat, lon = h3.cell_to_latlng(hex_id)
        location = geolocator.reverse(f"{lat}, {lon}", timeout=3)
        address = location.raw.get("address", {})
        suburb = address.get("suburb", address.get("town", address.get("city", "Unknown")))
        road = address.get("road", "")
        if road and suburb:
            return f"Near {road}, {suburb}"
        return suburb
    except Exception:
        return "Location Lookup Failed"

if len(filtered) > 0:
    top_10 = filtered.sort_values("opportunity_gap", ascending=False).head(10).copy()

    with st.spinner("Translating Hex IDs to human-readable locations..."):
        top_10["Location"] = top_10["hex_id"].apply(get_human_address)

    display_columns = [
        "Location", "archetype", "precinct_population",
        "precinct_daily_trips", "predicted_daily_trips", "opportunity_gap",
    ]
    st.dataframe(top_10[display_columns], hide_index=True, use_container_width=True)
else:
    st.info("No precincts match the current filters.")

# ---------------------------------------------------------------------------
# Render my 2x2 Analytics Grid Command Center
# ---------------------------------------------------------------------------
st.subheader("Analytics Command Center")
st.caption("All charts react to the sidebar filters above.")

# Shared layout config: using a dark template, no gridlines, and tight margins
_BASE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=40, b=10, l=10, r=10),
    height=360,
    xaxis=dict(showgrid=False, tickformat=","),
    yaxis=dict(showgrid=False, tickformat=","),
)

if len(filtered) > 0:
    # ---- Row 1 ----
    col1, col2 = st.columns(2)

    # Chart 1: Infrastructure Profile — I'm using a single brand color and data labels
    with col1:
        feature_cols = ["walkway_count", "cycleway_count", "retail_count", "car_parking_count"]
        feature_labels = ["Walkways", "Cycleways", "Retail", "Car Parking"]
        avg_values = [filtered[c].mean() for c in feature_cols]

        fig1 = px.bar(
            x=feature_labels, y=avg_values,
            text_auto=".2s",
            title="Avg Infrastructure per Precinct",
        )
        fig1.update_traces(
            marker_color="#3A86FF",
            textposition="outside",
            textfont_size=13,
        )
        fig1.update_layout(**_BASE)
        fig1.update_layout(
            showlegend=False,
            yaxis=dict(visible=False, showgrid=False),
            xaxis_title=None,
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Demand vs Supply — a scatter plot with marker outlines
    with col2:
        fig2 = px.scatter(
            filtered,
            x="precinct_population", y="precinct_daily_trips",
            color="archetype",
            color_discrete_map=ARCHETYPE_COLOURS,
            title="Population vs. Transit Frequency",
            labels={
                "precinct_population": "Population",
                "precinct_daily_trips": "Daily Trips",
            },
            opacity=0.6,
            hover_data={
                "precinct_population": ":,",
                "precinct_daily_trips": ":,",
            },
        )
        fig2.update_traces(
            marker=dict(size=6, line=dict(width=0.5, color="white")),
        )
        fig2.update_layout(**_BASE)
        fig2.update_layout(
            legend=dict(
                title=None,
                orientation="h",
                yanchor="top", y=-0.2,
                xanchor="center", x=0.5,
                font=dict(size=10),
            ),
            margin=dict(t=40, b=80, l=10, r=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ---- Row 2 ----
    col3, col4 = st.columns(2)

    # Chart 3: Opportunity Gap — setting this up as a log-scale histogram
    with col3:
        fig3 = px.histogram(
            filtered,
            x="opportunity_gap",
            nbins=50,
            log_y=True,
            title="Opportunity Gap Distribution (log scale)",
            labels={"opportunity_gap": "Gap (Predicted − Actual)"},
            color_discrete_sequence=["#8338EC"],
        )
        fig3.update_layout(**_BASE)
        fig3.update_layout(
            bargap=0.04,
            yaxis_title=None,
            xaxis=dict(showgrid=False, tickformat=",.0f"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Chart 4: Archetype Composition — donut chart with outside labels
    with col4:
        arch_counts = filtered["archetype"].value_counts().reset_index()
        arch_counts.columns = ["archetype", "count"]

        fig4 = px.pie(
            arch_counts,
            names="archetype", values="count",
            hole=0.4,
            title="Archetype Breakdown",
            color="archetype",
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
        fig4.update_traces(
            textposition="outside",
            textinfo="percent+label",
            textfont_size=10,
        )
        fig4.update_layout(**_BASE)
        fig4.update_layout(
            showlegend=False,
            margin=dict(t=40, b=30, l=10, r=10),
        )
        st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No precincts match the current filters.")
