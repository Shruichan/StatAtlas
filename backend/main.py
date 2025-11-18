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
    return pd.read_parquet(DATA_PATH)


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
        "cdc_ozone_exceedance_days",
        "cdc_pm25_person_days",
        "cdc_pm25_annual_avg",
    ]
    subset = subset.replace([np.inf, -np.inf], np.nan).fillna(0)
    return {
        "total": int(len(df)),
        "results": jsonable_encoder(subset[columns].to_dict(orient="records")),
    }


@app.get("/api/summary")
def summary() -> Dict:
    df = load_dataset()
    meta = load_metadata()
    cached = load_cached_summary()
    if cached:
        return jsonable_encoder(
            {
                "aggregates": cached.get("aggregates", {}),
                "metadata": meta,
                "counties": cached.get("counties", []),
                "clusters": cached.get("clusters", []),
            }
        )
    aggregates = {
        "avg_walkability": float(df["walkability_index"].mean()),
        "avg_nri_risk": float(df["nri_risk_score"].mean()),
        "avg_resilience": float(df["nri_resilience_score"].mean()),
        "avg_pollution": float(df["PollutionScore"].mean()),
        "avg_quality": float(df["quality_of_life_score"].mean()),
        "avg_ozone_days": float(df["cdc_ozone_exceedance_days"].mean()),
        "avg_pm25_days": float(df["cdc_pm25_person_days"].mean()),
        "avg_non_auto_share": float(df["non_auto_share"].mean()),
        "avg_drive_alone_share": float(df["drive_alone_share"].mean()),
        "avg_transit_share": float(df["public_transit_share"].mean()),
        "avg_active_commute_share": float(df["active_commute_share"].mean()),
        "avg_work_from_home_share": float(df["work_from_home_share"].mean()),
    }
    county_stats = (
        df.groupby("county_name")
        .agg(
            tracts=("geoid", "count"),
            avg_quality=("quality_of_life_score", "mean"),
            avg_walkability=("walkability_index", "mean"),
            avg_risk=("nri_risk_score", "mean"),
            avg_resilience=("nri_resilience_score", "mean"),
            avg_pollution=("PollutionScore", "mean"),
            avg_ozone=("cdc_ozone_exceedance_days", "mean"),
            avg_pm25=("cdc_pm25_person_days", "mean"),
            population=("ACS2019TotalPop", "sum"),
            avg_non_auto_share=("non_auto_share", "mean"),
            avg_drive_alone_share=("drive_alone_share", "mean"),
            avg_transit_share=("public_transit_share", "mean"),
            avg_active_commute_share=("active_commute_share", "mean"),
            avg_work_from_home_share=("work_from_home_share", "mean"),
        )
        .reset_index()
        .to_dict(orient="records")
    )
    cluster_stats = (
        df.groupby("cluster_label")
        .agg(
            tracts=("geoid", "count"),
            avg_quality=("quality_of_life_score", "mean"),
            avg_pollution=("PollutionScore", "mean"),
            avg_walkability=("walkability_index", "mean"),
            avg_risk=("nri_risk_score", "mean"),
            avg_resilience=("nri_resilience_score", "mean"),
            avg_non_auto_share=("non_auto_share", "mean"),
            avg_drive_alone_share=("drive_alone_share", "mean"),
            avg_transit_share=("public_transit_share", "mean"),
            avg_active_commute_share=("active_commute_share", "mean"),
            avg_work_from_home_share=("work_from_home_share", "mean"),
        )
        .reset_index()
        .to_dict(orient="records")
    )
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
    return JSONResponse(content=jsonable_encoder(data))


@app.post("/api/recommendations")
def recommendations(payload: RecommendationPayload) -> Dict:
    df = load_dataset()
    weights = payload.weights or default_weight_profile()
    recs = run_recommender(df, weights, payload.counties, payload.top_n)
    columns = [
        "geoid",
        "county_name",
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
        "cdc_ozone_exceedance_days",
        "cdc_pm25_person_days",
        "cdc_pm25_annual_avg",
        "personalized_score",
    ]
    return {"results": jsonable_encoder(recs[columns].to_dict(orient="records"))}
