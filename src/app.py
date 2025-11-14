"""Streamlit prototype for the StatAtlas interactive explorer."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


st.set_page_config(page_title="StatAtlas", layout="wide")

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
GEOJSON_PATH = DATA_DIR / "statatlas.geojson"
FEATURES_PATH = DATA_DIR / "statatlas_features.parquet"
CLUSTER_PATH = DATA_DIR / "cluster_profiles.json"
METADATA_PATH = DATA_DIR / "insight_metadata.json"
CALIFORNIA_BOUNDS = [[32.0, -125.0], [42.5, -113.5]]

METRICS = {
    "quality_of_life_score": {
        "label": "Quality of Life Index",
        "color": "YlGn",
        "description": "Composite of walkability, clean air, and low congestion.",
    },
    "PollutionScore": {
        "label": "Pollution Burden Score",
        "color": "OrRd",
        "description": "Higher values indicate more cumulative pollution pressure.",
    },
    "walkability_index": {
        "label": "Walkability Index",
        "color": "PuBuGn",
        "description": "Blend of ACS walking, biking, transit, and remote work shares.",
    },
    "non_auto_share": {
        "label": "Lack of Car Dependency",
        "color": "BuPu",
        "description": "Share of commuters who do not drive alone.",
    },
    "drive_alone_share": {
        "label": "Drive-Alone Share",
        "color": "YlOrBr",
        "description": "Percent of commuters that rely solely on a personal vehicle.",
    },
    "asthma": {
        "label": "Asthma ED Visits (per 10k)",
        "color": "Reds",
        "description": "OEHHA asthma indicator per 10,000 residents.",
    },
    "nri_risk_score": {
        "label": "FEMA NRI Risk Score",
        "color": "YlOrRd",
        "description": "FEMA National Risk Index composite at the census-tract level (0-100).",
    },
    "nri_resilience_score": {
        "label": "FEMA NRI Resilience Score",
        "color": "PuBu",
        "description": "Higher values indicate stronger capacity to withstand disruptive events.",
    },
    "nri_wildfire_risk": {
        "label": "Wildfire Risk (FEMA)",
        "color": "YlOrBr",
        "description": "FEMA wildfire risk component as a percentile (0-100).",
    },
    "cdc_ozone_exceedance_days": {
        "label": "CDC Ozone Exceedance Days",
        "color": "PuRd",
        "description": "Latest CDC Tracking Network ozone exceedance days (county-level, monitor-only).",
    },
    "cdc_pm25_person_days": {
        "label": "CDC PM2.5 Exposure (person-days)",
        "color": "BuPu",
        "description": "Person-days exceeding PM2.5 standards (county-level, monitor-only).",
    },
    "ces_score_delta": {
        "label": "CalEnviroScreen Change (4.0-3.0)",
        "color": "PRGn",
        "description": "Positive values show higher CES 4.0 scores compared to 3.0 historical data.",
    },
    "pm25_gap_vs_who_ca": {
        "label": "PM2.5 Gap vs WHO CA Average",
        "color": "RdBu",
        "description": "Difference between tract PM2.5 (CalEnviroScreen) and WHO CA city average.",
    },
}

RECOMMENDATION_FEATURES = {
    "walkability_index_norm": "Prioritize walkability & transit access",
    "non_auto_share_norm": "Prefer communities with low car dependence",
    "PollutionScore_norm": "Avoid pollution burden",
    "traffic_norm": "Avoid high traffic volumes",
    "asthma_norm": "Seek lower asthma burdens",
    "pov_norm": "Prefer lower poverty rates",
    "nri_resilience_score_norm": "Value resilient infrastructure",
    "nri_risk_score_norm": "Minimize FEMA risk score",
    "cdc_ozone_exceedance_days_norm": "Reduce ozone exceedance days",
    "cdc_pm25_person_days_norm": "Reduce PM2.5 person-days",
    "ces_score_delta_norm": "Favor tracts improving since CES 3.0",
}


@st.cache_data(show_spinner=True)
def load_tabular_data() -> pd.DataFrame:
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"{FEATURES_PATH} is missing. Run `python -m src.data_pipeline.build_dataset` first."
        )
    df = pd.read_parquet(FEATURES_PATH)
    df["geoid"] = df["geoid"].astype(str).str.zfill(11)
    df["county_name"] = df["county_name"].fillna("Unknown County")
    return df


@st.cache_data(show_spinner=False)
def load_geojson() -> Dict:
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(
            f"{GEOJSON_PATH} is missing. Run `python -m src.data_pipeline.build_dataset` first."
        )
    return json.loads(GEOJSON_PATH.read_text())


@st.cache_data(show_spinner=False)
def load_cluster_profiles() -> pd.DataFrame:
    if CLUSTER_PATH.exists():
        data = json.loads(CLUSTER_PATH.read_text())["profiles"]
        return pd.DataFrame(data)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_metadata() -> Dict:
    if METADATA_PATH.exists():
        return json.loads(METADATA_PATH.read_text())
    return {}


def subset_geojson(geojson_doc: Dict, geoids: Iterable[str]) -> Dict:
    allowed = set(geoids)
    features = [
        feature
        for feature in geojson_doc.get("features", [])
        if feature.get("properties", {}).get("geoid") in allowed
    ]
    return {"type": "FeatureCollection", "features": features}


def render_map(df: pd.DataFrame, geojson_doc: Dict, metric: str) -> None:
    metric_info = METRICS[metric]
    df_metric = df.dropna(subset=[metric]).copy()
    if df_metric.empty:
        st.info("No features remain after filtering. Relax the filters to view the map.")
        return

    geojson_subset = subset_geojson(geojson_doc, df_metric["geoid"])

    m = folium.Map(
        location=[37.25, -119.5],
        zoom_start=5.8,
        tiles="cartodbpositron",
        max_bounds=True,
    )
    m.fit_bounds(CALIFORNIA_BOUNDS)
    folium.Choropleth(
        geo_data=geojson_subset,
        name=metric_info["label"],
        data=df_metric,
        columns=["geoid", metric],
        key_on="feature.properties.geoid",
        fill_color=metric_info["color"],
        bins=6,
        fill_opacity=0.75,
        line_opacity=0.2,
        nan_fill_color="lightgray",
        legend_name=metric_info["label"],
    ).add_to(m)

    tooltip_fields = [
        ("geoid", "Tract FIPS"),
        ("county_name", "County"),
        ("cluster_label", "Cluster"),
        ("quality_of_life_score", "Quality Index"),
        ("walkability_index", "Walkability"),
        ("non_auto_share", "Non-auto share"),
        ("drive_alone_share", "Drive-alone share"),
        ("PollutionScore", "Pollution score"),
        ("asthma", "Asthma rate"),
        ("nri_risk_score", "FEMA Risk Score"),
        ("nri_resilience_score", "FEMA Resilience Score"),
        ("nri_wildfire_risk", "Wildfire Risk"),
        ("cdc_ozone_exceedance_days", "CDC Ozone Days"),
        ("cdc_pm25_person_days", "CDC PM2.5 person-days"),
        ("ces_score_delta", "CES 4.0–3.0 Δ"),
        ("pm25_gap_vs_who_ca", "PM2.5 gap vs WHO CA"),
    ]

    folium.GeoJson(
        geojson_subset,
        name="Details",
        style_function=lambda _: {
            "fillOpacity": 0,
            "weight": 0.5,
            "color": "#222222",
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=[f[0] for f in tooltip_fields],
            aliases=[f[1] for f in tooltip_fields],
            localize=True,
        ),
    ).add_to(m)

    st_folium(m, height=600, width=None)


def summarize_key_metrics(df: pd.DataFrame) -> None:
    cols = st.columns(4)
    metrics = [
        (cols[0], "Avg Walkability Index", df["walkability_index"].mean(), "{:.3f}"),
        (cols[1], "Non-auto Commute Share", df["non_auto_share"].mean(), "{:.1%}"),
        (cols[2], "FEMA NRI Risk Score", df["nri_risk_score"].mean(), "{:.1f}"),
        (cols[3], "FEMA Resilience Score", df["nri_resilience_score"].mean(), "{:.1f}"),
    ]
    for slot, label, value, fmt in metrics:
        if pd.isna(value):
            slot.metric(label, "n/a")
        else:
            slot.metric(label, fmt.format(value))
    cols2 = st.columns(3)
    extra_metrics = [
        (cols2[0], "CDC Ozone Days", df["cdc_ozone_exceedance_days"].mean(), "{:.1f}"),
        (cols2[1], "CDC PM2.5 Person-days", df["cdc_pm25_person_days"].mean(), "{:.2e}"),
        (cols2[2], "PM2.5 Gap vs WHO CA Avg", df["pm25_gap_vs_who_ca"].mean(), "{:.2f}"),
    ]
    for slot, label, value, fmt in extra_metrics:
        if pd.isna(value):
            slot.metric(label, "n/a")
        else:
            slot.metric(label, fmt.format(value))
    with st.expander("How do these stats relate to quality of life?", expanded=False):
        st.markdown(
            """
            - **Walkability & non-auto share** show how easy it is to travel without a car; higher values typically
              mean better access to services and healthier commutes.
            - **FEMA risk/resilience** scores compare each tract's exposure to hazards (wildfire, drought, storms) and
              ability to bounce back after disasters.
            - **CDC ozone & PM2.5 metrics** indicate how often air quality exceeded federal standards in the latest
              monitor-only dataset.
            - **PM2.5 gap vs WHO** highlights where local particulate matter deviates from the statewide WHO city average;
              positive numbers mean dirtier air than the California benchmark.
            """
        )


def apply_range_filter(df: pd.DataFrame, column: str, value_range: Tuple[float, float]) -> pd.DataFrame:
    if column not in df.columns:
        return df
    low, high = value_range
    mask = df[column].between(low, high) | df[column].isna()
    return df[mask]


def run_recommender(df: pd.DataFrame, prefs: Dict[str, float], counties: List[str], top_n: int) -> pd.DataFrame:
    working_df = df.copy()
    if counties:
        working_df = working_df[working_df["county_name"].isin(counties)].copy()
    if working_df.empty:
        return working_df

    total_weight = sum(prefs.values()) or 1.0
    score = np.zeros(len(working_df))
    for idx, (col, weight) in enumerate(prefs.items()):
        normalized_col = working_df[col].fillna(working_df[col].median())
        score += (weight / total_weight) * normalized_col.to_numpy()
    working_df["personalized_score"] = score
    return (
        working_df.sort_values("personalized_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def county_options(df: pd.DataFrame) -> List[str]:
    counties = sorted(df["county_name"].dropna().unique().tolist())
    return [c for c in counties if c != "Unknown County"]


def cluster_overview(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("cluster_label")
        .agg(
            tracts=("geoid", "count"),
            avg_quality=("quality_of_life_score", "mean"),
            avg_pollution=("PollutionScore", "mean"),
            avg_walkability=("walkability_index", "mean"),
            avg_risk=("nri_risk_score", "mean"),
            avg_resilience=("nri_resilience_score", "mean"),
        )
        .sort_values("avg_quality", ascending=False)
    )
    return summary


def render_cluster_profiles(df: pd.DataFrame, profiles: pd.DataFrame) -> None:
    st.subheader("Machine Learning Cluster Profiles")
    summary = cluster_overview(df)
    st.dataframe(
        summary.style.format(
            {
                "avg_quality": "{:.3f}",
                "avg_pollution": "{:.2f}",
                "avg_walkability": "{:.3f}",
                "avg_risk": "{:.1f}",
                "avg_resilience": "{:.1f}",
            }
        ),
        width="stretch",
    )
    if not profiles.empty:
        pretty = profiles.rename(
            columns={
                "cluster_id": "Cluster",
                "PollutionScore": "Pollution",
                "walkability_index": "Walkability",
                "non_auto_share": "Non-auto share",
                "asthma": "Asthma",
                "pov": "Poverty",
                "CIscore": "CalEnviroScreen score",
                "nri_risk_score": "FEMA Risk",
                "nri_resilience_score": "FEMA Resilience",
                "cdc_ozone_exceedance_days": "CDC Ozone Days",
            }
        ).set_index("Cluster")
        formatting = {
            "Pollution": "{:.2f}",
            "Walkability": "{:.3f}",
            "Non-auto share": "{:.1%}",
            "Asthma": "{:.1f}",
            "Poverty": "{:.1f}",
            "CalEnviroScreen score": "{:.2f}",
            "FEMA Risk": "{:.1f}",
            "FEMA Resilience": "{:.1f}",
            "CDC Ozone Days": "{:.1f}",
        }
        st.dataframe(pretty.style.format(formatting), width="stretch")
        st.caption(
            "Cluster centroids derived from the K-Means model across pollution, walkability, asthma, poverty, and composite CalEnviroScreen scores."
        )


def main() -> None:
    try:
        df = load_tabular_data()
        geojson_doc = load_geojson()
        metadata = load_metadata()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    st.title("StatAtlas · Environmental & Health Intelligence for California")
    st.caption(
        "Blend CalEnviroScreen 4.0 with ACS commute behavior to surface pollution, walkability, and health signals through interactive maps."
    )

    sidebar = st.sidebar
    sidebar.title("Explore California")
    sidebar.caption("StatAtlas currently focuses on California census tracts; data layers outside CA are hidden.")

    with sidebar.expander("Geography filters", expanded=True):
        county_selection = st.multiselect(
            "Counties",
            options=county_options(df),
            default=[],
            help="Narrow the map to specific counties.",
        )
        cluster_choices = sorted(df["cluster_label"].dropna().unique().tolist())
        cluster_filter = st.multiselect(
            "Cluster labels",
            options=cluster_choices,
            default=[],
        )
    with sidebar.expander("Quality & risk thresholds", expanded=True):
        quality_range = st.slider(
            "Quality-of-life score",
            min_value=0.0,
            max_value=1.0,
            value=(0.0, 1.0),
            step=0.05,
        )
        risk_range = st.slider(
            "FEMA NRI risk score",
            min_value=0.0,
            max_value=100.0,
            value=(0.0, 100.0),
            step=1.0,
        )
        resilience_range = st.slider(
            "FEMA resilience score",
            min_value=0.0,
            max_value=100.0,
            value=(0.0, 100.0),
            step=1.0,
        )
    with sidebar.expander("Display options", expanded=True):
        metric_key = st.selectbox(
            "Map metric",
            options=list(METRICS.keys()),
            format_func=lambda key: METRICS[key]["label"],
        )
        st.write(METRICS[metric_key]["description"])

    filtered = df.copy()
    if county_selection:
        filtered = filtered[filtered["county_name"].isin(county_selection)]
    if cluster_filter:
        filtered = filtered[filtered["cluster_label"].isin(cluster_filter)]
    filtered = filtered[
        (filtered["quality_of_life_score"] >= quality_range[0])
        & (filtered["quality_of_life_score"] <= quality_range[1])
    ]
    filtered = apply_range_filter(filtered, "nri_risk_score", risk_range)
    filtered = apply_range_filter(filtered, "nri_resilience_score", resilience_range)

    st.markdown(
        f"**Showing {len(filtered):,} of {len(df):,} tracts** "
        f"({len(filtered['county_name'].unique())} counties)."
    )

    summarize_key_metrics(filtered)
    render_map(filtered, geojson_doc, metric_key)

    st.subheader("Walkability vs. Car Dependency Snapshot")
    chart_df = filtered[
        ["county_name", "walkability_index", "non_auto_share", "drive_alone_share"]
    ].groupby("county_name").mean().reset_index()
    if not chart_df.empty:
        st.bar_chart(
            chart_df.set_index("county_name")[["walkability_index", "non_auto_share"]],
            height=300,
        )
    else:
        st.info("No data available for the selected filters.")

    st.subheader("FEMA Hazard & CDC Air Quality Snapshot")
    hazard_df = (
        filtered[["county_name", "nri_risk_score", "nri_resilience_score"]]
        .groupby("county_name")
        .mean()
        .reset_index()
    )
    aq_df = (
        filtered[["county_name", "cdc_ozone_exceedance_days", "cdc_pm25_person_days"]]
        .groupby("county_name")
        .mean()
        .reset_index()
    )
    if not hazard_df.empty:
        st.bar_chart(
            hazard_df.set_index("county_name")[["nri_risk_score", "nri_resilience_score"]],
            height=300,
        )
    if not aq_df.empty:
        st.bar_chart(
            aq_df.set_index("county_name")[["cdc_ozone_exceedance_days"]],
            height=250,
        )
    elif hazard_df.empty:
        st.info("Hazard and CDC summaries unavailable for the selected filters.")

    if metadata:
        st.subheader("WHO & CDC Benchmarks")
        who_meta = metadata.get("who", {})
        cdc_meta = metadata.get("cdc", {})
        cols = st.columns(4)
        who_metrics = [
            (cols[0], "WHO global PM2.5 mean", who_meta.get("world_pm25_mean"), "{:.1f} μg/m³"),
            (cols[1], "WHO USA PM2.5 mean", who_meta.get("usa_pm25_mean"), "{:.1f} μg/m³"),
            (cols[2], "WHO California PM2.5 mean", who_meta.get("california_pm25_mean"), "{:.1f} μg/m³"),
            (cols[3], "WHO California NO₂ mean", who_meta.get("california_no2_mean"), "{:.1f} μg/m³"),
        ]
        for slot, label, value, fmt in who_metrics:
            if value is None or pd.isna(value):
                slot.metric(label, "n/a")
            else:
                slot.metric(label, fmt.format(value))
        latest_year = cdc_meta.get("cdc_latest_year")
        if latest_year:
            st.caption(f"CDC ozone and PM2.5 values are monitor-only data from {int(latest_year)}.")

    st.subheader("Quality of Life Recommender")
    st.write(
        "Adjust the sliders to emphasize what matters most. The recommender scores every tract "
        "with the same normalized features used by the clustering model."
    )

    with st.form("recommender_form"):
        pref_cols = st.columns(2)
        weights: Dict[str, float] = {}
        feature_items = list(RECOMMENDATION_FEATURES.items())
        midpoint = math.ceil(len(feature_items) / 2)
        for group_idx, feature_group in enumerate(
            [feature_items[:midpoint], feature_items[midpoint:]]
        ):
            for key, label in feature_group:
                base_value = 3.0 if any(token in key for token in ["walkability", "non_auto", "resilience", "ces"]) else 2.0
                weights[key] = pref_cols[group_idx].slider(
                    label,
                    min_value=0.0,
                    max_value=5.0,
                    value=base_value,
                    step=0.5,
                )
        preferred_counties = st.multiselect(
            "Boost these counties (optional)",
            options=county_options(df),
            default=county_selection,
        )
        top_n = st.number_input(
            "How many recommendations?",
            min_value=3,
            max_value=30,
            value=8,
            step=1,
        )
        submitted = st.form_submit_button("Recommend tracts")

    if submitted:
        recommendations = run_recommender(df, weights, preferred_counties, int(top_n))
        if recommendations.empty:
            st.warning("No tracts matched the current filters/preferences.")
        else:
            display_cols = [
                "geoid",
                "county_name",
                "cluster_label",
                "quality_of_life_score",
                "walkability_index",
                "non_auto_share",
                "drive_alone_share",
                "PollutionScore",
                "nri_risk_score",
                "nri_resilience_score",
                "cdc_ozone_exceedance_days",
                "personalized_score",
            ]
            st.dataframe(
                recommendations[display_cols].style.format(
                    {
                        "quality_of_life_score": "{:.3f}",
                        "walkability_index": "{:.3f}",
                        "non_auto_share": "{:.1%}",
                        "drive_alone_share": "{:.1%}",
                        "PollutionScore": "{:.2f}",
                        "nri_risk_score": "{:.1f}",
                        "nri_resilience_score": "{:.1f}",
                        "cdc_ozone_exceedance_days": "{:.1f}",
                        "personalized_score": "{:.3f}",
                    }
                ),
                use_container_width=True,
            )
            top_pick = recommendations.iloc[0]
            st.success(
                f"Top match: census tract {top_pick['geoid']} "
                f"in {top_pick['county_name']} — {top_pick['cluster_label']}. "
                f"Walkability index {top_pick['walkability_index']:.3f}, "
                f"non-auto share {top_pick['non_auto_share']:.1%}, "
                f"drive-alone share {top_pick['drive_alone_share']:.1%}, "
                f"pollution score {top_pick['PollutionScore']:.2f}, "
                f"FEMA risk {top_pick['nri_risk_score']:.1f}, resilience {top_pick['nri_resilience_score']:.1f}."
            )

    cluster_profiles = load_cluster_profiles()
    render_cluster_profiles(df, cluster_profiles)

    st.caption(
        "Data sources: CalEnviroScreen 4.0 (OEHHA), ACS 2022 5-year estimates (U.S. Census Bureau), "
        "plus derived walkability and car-dependency metrics."
    )


if __name__ == "__main__":
    main()
