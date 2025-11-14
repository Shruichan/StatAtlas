"""Reusable recommendation utilities for StatAtlas."""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

RECOMMENDATION_FEATURES: Dict[str, str] = {
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

DEFAULT_WEIGHT_HINTS: Dict[str, float] = {
    "walkability_index_norm": 3.5,
    "non_auto_share_norm": 3.0,
    "nri_resilience_score_norm": 3.0,
    "ces_score_delta_norm": 3.0,
}


def default_weight_for_feature(key: str) -> float:
    """Return a slider default weight for a recommendation feature."""
    return DEFAULT_WEIGHT_HINTS.get(key, 2.0)


def run_recommender(
    df: pd.DataFrame,
    prefs: Dict[str, float],
    counties: List[str],
    top_n: int,
) -> pd.DataFrame:
    """Return personalized tract recommendations given preference weights."""
    working_df = df.copy()
    if counties:
        working_df = working_df[working_df["county_name"].isin(counties)].copy()
    if working_df.empty:
        return working_df

    valid_prefs = {k: v for k, v in prefs.items() if k in working_df.columns}
    if not valid_prefs:
        return working_df.head(top_n)

    total_weight = sum(valid_prefs.values()) or 1.0
    score = np.zeros(len(working_df))
    for idx, (col, weight) in enumerate(valid_prefs.items()):
        normalized_col = working_df[col].fillna(working_df[col].median())
        score += (weight / total_weight) * normalized_col.to_numpy()
    working_df["personalized_score"] = score
    return (
        working_df.sort_values("personalized_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
