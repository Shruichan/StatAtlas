"""FastAPI backend for StatAtlas."""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional
import json
from fastapi.encoders import jsonable_encoder

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    import reverse_geocoder as rg  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    rg = None

from src.services.recommender import (
    RECOMMENDATION_FEATURES,
    default_weight_for_feature,
    run_recommender,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "statatlas_features.parquet"
METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "insight_metadata.json"
GEOJSON_PATH = PROJECT_ROOT / "data" / "processed" / "statatlas.geojson"
CACHE_SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "cache" / "summary.json"

app = FastAPI(
    title="StatAtlas API",
    version="0.1.0",
    description="Programmatic access to StatAtlas environmental and health insights.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@lru_cache(maxsize=1)
def load_dataset() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            "Processed dataset missing. Run `python -m src.data_pipeline.build_dataset` first."
        )
    df = pd.read_parquet(DATA_PATH)
    df = ensure_pollution_derivatives(df)
    df = ensure_nearest_place(df)
    return apply_qol_penalties(df)


@lru_cache(maxsize=1)
def load_metadata() -> Dict:
    if not METADATA_PATH.exists():
        return {}
    return json.loads(METADATA_PATH.read_text())


@lru_cache(maxsize=1)
def load_geojson() -> Dict:
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError("statatlas.geojson missing; run the data pipeline first.")
    return json.loads(GEOJSON_PATH.read_text())


@lru_cache(maxsize=1)
def load_cached_summary() -> Dict:
    if CACHE_SUMMARY_PATH.exists():
        return json.loads(CACHE_SUMMARY_PATH.read_text())
    return {}


def ensure_pollution_derivatives(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived pollution metrics if a cached dataset lacks them."""
    if "pollution_percentile" not in df.columns and "PollutionP" in df.columns:
        df["pollution_percentile"] = df["PollutionP"]
    if "clean_air_index" not in df.columns and "PollutionScore_norm" in df.columns:
        df["clean_air_index"] = df["PollutionScore_norm"]
    if (
        "pollution_score_delta" not in df.columns
        and "PollutionScore" in df.columns
        and "ces3_pollution_score" in df.columns
    ):
        df["pollution_score_delta"] = df["PollutionScore"] - df["ces3_pollution_score"]
    if (
        "pollution_score_pct_change" not in df.columns
        and "pollution_score_delta" in df.columns
        and "ces3_pollution_score" in df.columns
    ):
        baseline = df["ces3_pollution_score"].replace({0: np.nan})
        df["pollution_score_pct_change"] = df["pollution_score_delta"] / baseline
    if "pollution_zscore" not in df.columns and "PollutionScore" in df.columns:
        std = float(df["PollutionScore"].std(ddof=0))
        mean = float(df["PollutionScore"].mean())
        if std and not np.isnan(std):
            df["pollution_zscore"] = (df["PollutionScore"] - mean) / std
        else:
            df["pollution_zscore"] = 0.0
    return df


def ensure_nearest_place(df: pd.DataFrame) -> pd.DataFrame:
    """Add nearest place label using tract centroid if missing."""
    if "nearest_place" in df.columns and df["nearest_place"].notna().any():
        df["nearest_place"] = df["nearest_place"].fillna(df.get("county_name"))
        return df
    if rg is None or "centroid_lat" not in df or "centroid_lon" not in df:
        df["nearest_place"] = df.get("county_name")
        return df
    mask = df[["centroid_lat", "centroid_lon"]].applymap(np.isfinite).all(axis=1)
    coords = list(zip(df.loc[mask, "centroid_lat"], df.loc[mask, "centroid_lon"]))
    if coords:
        results = rg.search(coords, mode=1)
        nearest_strings: Dict[int, str] = {}
        for idx, res in zip(df.loc[mask].index, results):
            city = res.get("name")
            admin2 = res.get("admin2")
            admin1 = res.get("admin1")
            parts = [p for p in (city, admin2, admin1) if p]
            nearest_strings[idx] = ", ".join(parts)
        df.loc[mask, "nearest_place"] = df.loc[mask].index.map(nearest_strings.get)
    df["nearest_place"] = df["nearest_place"].fillna(df.get("county_name"))
    return df


def apply_qol_penalties(df: pd.DataFrame) -> pd.DataFrame:
    """Apply hard penalties for low walkability / high car dependence."""
    if "quality_of_life_score" not in df:
        return df
    walk_penalty = np.ones(len(df))
    if "walkability_index" in df:
        walk_penalty = np.where(
            df["walkability_index"] < 0.02,
            0.4,
            np.where(df["walkability_index"] < 0.05, 0.7, 1.0),
        )
    car_penalty = np.ones(len(df))
    if "drive_alone_share" in df:
        car_penalty = np.where(
            df["drive_alone_share"] > 0.7,
            0.5,
            np.where(df["drive_alone_share"] > 0.6, 0.7, 1.0),
        )
    df["quality_of_life_score"] = (
        df["quality_of_life_score"] * walk_penalty * car_penalty
    ).clip(0, 1)
    if "walkability_index_norm" in df:
        df["quality_of_life_score"] = df[
            ["quality_of_life_score", "walkability_index_norm"]
        ].min(axis=1)
    return df


def safe_mean(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    return float(df[column].mean())


def compute_summary_tables(df: pd.DataFrame) -> tuple[Dict, List[Dict], List[Dict]]:
    aggregates = {
        "avg_walkability": safe_mean(df, "walkability_index"),
        "avg_nri_risk": safe_mean(df, "nri_risk_score"),
        "avg_resilience": safe_mean(df, "nri_resilience_score"),
        "avg_pollution": safe_mean(df, "PollutionScore"),
        "avg_pollution_percentile": safe_mean(df, "pollution_percentile"),
        "avg_clean_air_index": safe_mean(df, "clean_air_index"),
        "avg_pollution_delta": safe_mean(df, "pollution_score_delta"),
        "avg_pollution_pct_change": safe_mean(df, "pollution_score_pct_change"),
        "avg_quality": safe_mean(df, "quality_of_life_score"),
        "avg_ozone_days": safe_mean(df, "cdc_ozone_exceedance_days"),
        "avg_pm25_days": safe_mean(df, "cdc_pm25_person_days"),
        "avg_non_auto_share": safe_mean(df, "non_auto_share"),
        "avg_drive_alone_share": safe_mean(df, "drive_alone_share"),
        "avg_transit_share": safe_mean(df, "public_transit_share"),
        "avg_active_commute_share": safe_mean(df, "active_commute_share"),
        "avg_work_from_home_share": safe_mean(df, "work_from_home_share"),
    }

    county_aggs = {
        "tracts": ("geoid", "count"),
        "avg_quality": ("quality_of_life_score", "mean"),
        "avg_walkability": ("walkability_index", "mean"),
        "avg_risk": ("nri_risk_score", "mean"),
        "avg_resilience": ("nri_resilience_score", "mean"),
        "avg_pollution": ("PollutionScore", "mean"),
        "avg_ozone": ("cdc_ozone_exceedance_days", "mean"),
        "avg_pm25": ("cdc_pm25_person_days", "mean"),
        "population": ("ACS2019TotalPop", "sum"),
        "avg_non_auto_share": ("non_auto_share", "mean"),
        "avg_drive_alone_share": ("drive_alone_share", "mean"),
        "avg_transit_share": ("public_transit_share", "mean"),
        "avg_active_commute_share": ("active_commute_share", "mean"),
        "avg_work_from_home_share": ("work_from_home_share", "mean"),
    }
    if "pollution_percentile" in df.columns:
        county_aggs["avg_pollution_percentile"] = ("pollution_percentile", "mean")
    if "clean_air_index" in df.columns:
        county_aggs["avg_clean_air_index"] = ("clean_air_index", "mean")
    if "pollution_score_delta" in df.columns:
        county_aggs["avg_pollution_delta"] = ("pollution_score_delta", "mean")
    if "pollution_score_pct_change" in df.columns:
        county_aggs["avg_pollution_pct_change"] = ("pollution_score_pct_change", "mean")

    county_stats = (
        df.groupby("county_name")
        .agg(**county_aggs)
        .reset_index()
        .to_dict(orient="records")
    )

    cluster_aggs = {
        "tracts": ("geoid", "count"),
        "avg_quality": ("quality_of_life_score", "mean"),
        "avg_pollution": ("PollutionScore", "mean"),
        "avg_walkability": ("walkability_index", "mean"),
        "avg_risk": ("nri_risk_score", "mean"),
        "avg_resilience": ("nri_resilience_score", "mean"),
        "avg_non_auto_share": ("non_auto_share", "mean"),
        "avg_drive_alone_share": ("drive_alone_share", "mean"),
        "avg_transit_share": ("public_transit_share", "mean"),
        "avg_active_commute_share": ("active_commute_share", "mean"),
        "avg_work_from_home_share": ("work_from_home_share", "mean"),
    }
    if "pollution_percentile" in df.columns:
        cluster_aggs["avg_pollution_percentile"] = ("pollution_percentile", "mean")
    if "clean_air_index" in df.columns:
        cluster_aggs["avg_clean_air_index"] = ("clean_air_index", "mean")
    if "pollution_score_delta" in df.columns:
        cluster_aggs["avg_pollution_delta"] = ("pollution_score_delta", "mean")
    if "pollution_score_pct_change" in df.columns:
        cluster_aggs["avg_pollution_pct_change"] = ("pollution_score_pct_change", "mean")

    cluster_stats = (
        df.groupby("cluster_label")
        .agg(**cluster_aggs)
        .reset_index()
        .to_dict(orient="records")
    )
    return aggregates, county_stats, cluster_stats


def merge_records(cached: List[Dict], fresh: List[Dict], key: str) -> List[Dict]:
    cached_lookup = {row.get(key): row for row in cached if row.get(key) is not None}
    merged: List[Dict] = []
    for row in fresh:
        base = cached_lookup.get(row.get(key), {})
        merged.append({**base, **row})
    return merged


class RecommendationPayload(BaseModel):
    weights: Optional[Dict[str, float]] = None
    counties: List[str] = []
    top_n: int = 8


def default_weight_profile() -> Dict[str, float]:
    return {key: default_weight_for_feature(key) for key in RECOMMENDATION_FEATURES}


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "dataset_loaded": str(DATA_PATH.exists())}


@app.get("/api/tracts")
def tracts(limit: int = Query(100, ge=1, le=1000000), offset: int = Query(0, ge=0)) -> Dict:
    df = load_dataset()
    subset = df.iloc[offset : offset + limit]
    columns = [
        "geoid",
        "county_name",
        "nearest_place",
        "tract_label",
        "quality_of_life_score",
        "cluster_label",
        "walkability_index",
        "non_auto_share",
        "drive_alone_share",
        "public_transit_share",
        "active_commute_share",
        "work_from_home_share",
        "car_dependency_index",
        "nri_risk_score",
        "nri_resilience_score",
        "PollutionScore",
        "pollution_percentile",
        "clean_air_index",
        "pollution_score_delta",
        "pollution_score_pct_change",
        "pollution_zscore",
        "cdc_ozone_exceedance_days",
        "cdc_pm25_person_days",
        "cdc_pm25_annual_avg",
    ]
    subset = subset.replace([np.inf, -np.inf], np.nan)
    subset = subset.reindex(columns=columns).fillna(0)
    return {
        "total": int(len(df)),
        "results": jsonable_encoder(subset.to_dict(orient="records")),
    }


@app.get("/api/summary")
def summary() -> Dict:
    df = load_dataset()
    meta = load_metadata()
    cached = load_cached_summary()
    aggregates, county_stats, cluster_stats = compute_summary_tables(df)
    if cached:
        cached_aggs = cached.get("aggregates", {})
        aggregates = {**cached_aggs, **{k: v for k, v in aggregates.items() if v is not None}}
        county_stats = merge_records(cached.get("counties", []), county_stats, "county_name")
        cluster_stats = merge_records(cached.get("clusters", []), cluster_stats, "cluster_label")
    else:
        aggregates = {k: v for k, v in aggregates.items() if v is not None}
    return jsonable_encoder(
        {
            "aggregates": aggregates,
            "metadata": meta,
            "counties": county_stats,
            "clusters": cluster_stats,
        }
    )


@app.get("/api/geojson")
def geojson() -> JSONResponse:
    data = load_geojson()
    df = load_dataset()
    lookup = df.set_index("geoid")[["nearest_place", "tract_label", "county_name"]].to_dict("index")
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geoid = props.get("geoid")
        if geoid in lookup:
            extra = lookup[geoid]
            for key, value in extra.items():
                if props.get(key) in (None, "", 0):
                    props[key] = value
            feature["properties"] = props
    return JSONResponse(content=jsonable_encoder(data))


@app.post("/api/recommendations")
def recommendations(payload: RecommendationPayload) -> Dict:
    df = load_dataset()
    weights = payload.weights or default_weight_profile()
    recs = run_recommender(df, weights, payload.counties, payload.top_n)
    columns = [
        "geoid",
        "county_name",
        "nearest_place",
        "tract_label",
        "cluster_label",
        "quality_of_life_score",
        "walkability_index",
        "non_auto_share",
        "drive_alone_share",
        "public_transit_share",
        "active_commute_share",
        "work_from_home_share",
        "nri_risk_score",
        "nri_resilience_score",
        "PollutionScore",
        "pollution_percentile",
        "clean_air_index",
        "pollution_score_delta",
        "pollution_score_pct_change",
        "pollution_zscore",
        "cdc_ozone_exceedance_days",
        "cdc_pm25_person_days",
        "cdc_pm25_annual_avg",
        "personalized_score",
    ]
    recs = recs.reindex(columns=columns).fillna(0)
    return {"results": jsonable_encoder(recs.to_dict(orient="records"))}
