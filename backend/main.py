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
        "nri_risk_score",
        "nri_resilience_score",
        "PollutionScore",
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
    }
    return jsonable_encoder({"aggregates": aggregates, "metadata": meta})


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
        "nri_risk_score",
        "nri_resilience_score",
        "PollutionScore",
        "personalized_score",
    ]
    return {"results": jsonable_encoder(recs[columns].to_dict(orient="records"))}
