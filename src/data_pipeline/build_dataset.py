"""Build the enriched StatAtlas dataset."""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple
from zipfile import ZipFile

import numpy as np
import pandas as pd
import requests
from shapely.geometry import shape
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
BUILD_DIR = PROJECT_ROOT / "build"
C_EXTENSION_DIR = PROJECT_ROOT / "src" / "c_extensions"
QOL_SRC = C_EXTENSION_DIR / "qol_scores.c"
CACHE_DIR = PROCESSED_DIR / "cache"

CALENVIROSCREEN_URL = (
    "https://services1.arcgis.com/PCHfdHz4GlDNAhBb/arcgis/rest/services/"
    "CalEnviroScreen_4_0_Results_/FeatureServer/0/query"
)
ACS_API = "https://api.census.gov/data/2022/acs/acs5"
FEMA_NRI_ZIP_URL = (
    "https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload//"
    "NRI_Table_CensusTracts/NRI_Table_CensusTracts_California.zip"
)
CDC_AIR_QUALITY_URL = "https://data.cdc.gov/api/views/cjae-szjv/rows.csv?accessType=DOWNLOAD"
WHO_AIR_QUALITY_URL = (
    "https://cdn.who.int/media/docs/default-source/air-pollution-documents/"
    "air-quality-and-health/who_aap_2021_v9_11august2022.xlsx"
)
CES3_RESULTS_URL = (
    "https://data.ca.gov/dataset/0bd5f40b-c59b-4183-be22-d057eae8383c/resource/"
    "89b3f4e9-0bf8-4690-8c6f-715a717f3fae/download/calenviroscreen-3.0-results-"
    "june-2018-update.csv"
)

CALENVIROSCREEN_FIELDS = [
    "tract",
    "TractTXT",
    "ACS2019TotalPop",
    "CIscore",
    "CIscoreP",
    "CIdecile",
    "CIvigintile",
    "ozone",
    "ozoneP",
    "pm",
    "pmP",
    "diesel",
    "dieselP",
    "traffic",
    "trafficP",
    "Pollution",
    "PollutionScore",
    "PollutionP",
    "asthma",
    "asthmaP",
    "pov",
    "povP",
    "unemp",
    "unempP",
    "PopChar",
    "PopCharScore",
    "PopCharP",
    "housingB",
    "housingBP",
    "Children_under10_pct",
    "Elderly_65over_pct",
    "Hispanic_pct",
    "White_pct",
    "African_American_pct",
    "Asian_American_pct",
]

ACS_FIELDS = [
    "NAME",
    "B08301_001E",
    "B08301_003E",
    "B08301_010E",
    "B08301_018E",
    "B08301_019E",
    "B08301_020E",
    "B08301_021E",
]

COMMUTE_KEEP_COLUMNS = [
    "geoid",
    "county_name",
    "county_fips",
    "drive_alone_share",
    "public_transit_share",
    "bike_share",
    "walk_share",
    "work_from_home_share",
    "active_commute_share",
    "non_auto_share",
    "walkability_index",
    "car_dependency_index",
]

CDC_MEASURE_MAP = {
    "83": "cdc_ozone_exceedance_days",
    "86": "cdc_pm25_person_days",
    "87": "cdc_pm25_annual_avg",
}

_QOL_LIB = None


def _shared_lib_suffix() -> str:
    system = platform.system().lower()
    if "darwin" in system:
        return "dylib"
    if "windows" in system:
        return "dll"
    return "so"


def ensure_qol_shared_lib() -> Path:
    """Compile the quality-of-life helper C library if needed."""
    if not QOL_SRC.exists():
        raise FileNotFoundError(f"C extension source missing at {QOL_SRC}")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = _shared_lib_suffix()
    lib_path = BUILD_DIR / f"libqol_scores.{suffix}"
    if lib_path.exists() and lib_path.stat().st_mtime >= QOL_SRC.stat().st_mtime:
        return lib_path
    compiler = shutil.which("gcc")
    if compiler is None:
        raise RuntimeError("gcc compiler not available on PATH")
    cmd = [
        compiler,
        "-shared",
        "-O3",
        "-std=c99",
        "-fPIC",
        "-o",
        str(lib_path),
        str(QOL_SRC),
    ]
    if suffix == "dll":
        cmd = [compiler, "-shared", "-O3", "-o", str(lib_path), str(QOL_SRC)]
    subprocess.run(cmd, check=True)
    return lib_path


def get_qol_lib() -> ctypes.CDLL | None:
    """Load (or compile then load) the native scoring helper."""
    global _QOL_LIB
    if _QOL_LIB is not None:
        return _QOL_LIB
    try:
        lib_path = ensure_qol_shared_lib()
    except Exception:
        return None
    lib = ctypes.CDLL(str(lib_path))
    lib.compute_quality_scores.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_double),
    ]
    _QOL_LIB = lib
    return _QOL_LIB


def accelerated_quality_scores(
    matrix: np.ndarray, weights: np.ndarray
) -> np.ndarray | None:
    """Use the native helper to compute weighted sums if possible."""
    lib = get_qol_lib()
    if lib is None:
        return None
    n_samples, n_features = matrix.shape
    out = np.empty(n_samples, dtype=np.float64)
    lib.compute_quality_scores(
        matrix.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        weights.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.c_size_t(n_samples),
        ctypes.c_size_t(n_features),
        out.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    return out


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def clean_json_ready(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: clean_json_ready(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_json_ready(v) for v in obj]
    if isinstance(obj, float):
        if not np.isfinite(obj):
            return None
        return float(obj)
    return obj


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    with dest.open("wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 64):
            if chunk:
                f.write(chunk)


def ensure_local_file(path: Path, url: str, skip_download: bool) -> Path:
    if path.exists():
        return path
    if skip_download:
        raise FileNotFoundError(f"Missing required file {path}, rerun without --skip-download.")
    download_file(url, path)
    return path


def fetch_calenviroscreen() -> List[Dict]:
    features: List[Dict] = []
    chunk = 2000
    offset = 0
    params = {
        "where": "1=1",
        "outFields": ",".join(CALENVIROSCREEN_FIELDS),
        "outSR": 4326,
        "f": "geojson",
        "returnGeometry": "true",
    }

    with tqdm(desc="CalEnviroScreen", unit="records") as bar:
        while True:
            paged_params = {**params, "resultOffset": offset, "resultRecordCount": chunk}
            response = requests.get(CALENVIROSCREEN_URL, params=paged_params, timeout=60)
            response.raise_for_status()
            data = response.json()
            batch = data.get("features", [])
            if not batch:
                break
            features.extend(batch)
            bar.update(len(batch))
            if len(batch) < chunk:
                break
            offset += chunk

    raw_path = RAW_DIR / "calenviroscreen_raw.geojson"
    raw_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return features


def fetch_acs_commute() -> pd.DataFrame:
    params = {
        "get": ",".join(ACS_FIELDS),
        "for": "tract:*",
        "in": "state:06",
    }
    response = requests.get(ACS_API, params=params, timeout=60)
    response.raise_for_status()
    rows = response.json()
    header, data = rows[0], rows[1:]
    df = pd.DataFrame(data, columns=header)

    numeric_cols = [col for col in df.columns if col not in {"NAME", "state", "county", "tract"}]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df["geoid"] = df["state"] + df["county"] + df["tract"]
    df["county_name"] = df["NAME"].str.split(";").str[1].str.strip()
    df["county_fips"] = df["geoid"].astype(str).str[:5]

    total = df["B08301_001E"].replace({0: np.nan})
    df["drive_alone_share"] = df["B08301_003E"] / total
    df["public_transit_share"] = df["B08301_010E"] / total
    df["bike_share"] = df["B08301_018E"] / total
    df["walk_share"] = df["B08301_019E"] / total
    df["other_share"] = df["B08301_020E"] / total
    df["work_from_home_share"] = df["B08301_021E"] / total

    share_cols = [
        "drive_alone_share",
        "public_transit_share",
        "bike_share",
        "walk_share",
        "other_share",
        "work_from_home_share",
    ]
    df[share_cols] = df[share_cols].fillna(0.0)

    df["active_commute_share"] = df["walk_share"] + df["bike_share"]
    df["non_auto_share"] = 1 - df["drive_alone_share"]
    df["walkability_index"] = (
        0.4 * df["active_commute_share"]
        + 0.4 * df["public_transit_share"]
        + 0.2 * df["work_from_home_share"]
    )
    df["car_dependency_index"] = df["drive_alone_share"]

    raw_path = RAW_DIR / "acs_commute_ca.csv"
    df.to_csv(raw_path, index=False)
    return df[COMMUTE_KEEP_COLUMNS]


def load_fema_nri(skip_download: bool) -> pd.DataFrame:
    zip_path = ensure_local_file(RAW_DIR / "fema_nri_ca_tracts.zip", FEMA_NRI_ZIP_URL, skip_download)
    usecols = [
        "TRACTFIPS",
        "RISK_SCORE",
        "RESL_SCORE",
        "SOVI_SCORE",
        "EAL_SCORE",
        "WFIR_RISKS",
        "CWAV_RISKS",
        "DRGT_RISKS",
        "ERQK_RISKS",
        "SWND_RISKS",
    ]
    with ZipFile(zip_path) as zf:
        with zf.open("NRI_Table_CensusTracts_California.csv") as f:
            df = pd.read_csv(f, usecols=usecols)
    rename_map = {
        "TRACTFIPS": "geoid",
        "RISK_SCORE": "nri_risk_score",
        "RESL_SCORE": "nri_resilience_score",
        "SOVI_SCORE": "nri_sovi_score",
        "EAL_SCORE": "nri_eal_score",
        "WFIR_RISKS": "nri_wildfire_risk",
        "CWAV_RISKS": "nri_coastal_wave_risk",
        "DRGT_RISKS": "nri_drought_risk",
        "ERQK_RISKS": "nri_earthquake_risk",
        "SWND_RISKS": "nri_strong_wind_risk",
    }
    df = df.rename(columns=rename_map)
    df["geoid"] = df["geoid"].astype(str).str.zfill(11)
    return df


def load_cdc_air_quality(skip_download: bool) -> Tuple[pd.DataFrame, Dict[str, float]]:
    csv_path = ensure_local_file(RAW_DIR / "cdc_tracking_air_quality.csv", CDC_AIR_QUALITY_URL, skip_download)
    usecols = [
        "MeasureId",
        "StateFips",
        "CountyFips",
        "CountyName",
        "ReportYear",
        "Value",
        "DataOrigin",
    ]
    df = pd.read_csv(csv_path, usecols=usecols, dtype=str)
    df = df[df["StateFips"] == "6"].copy()
    df["ReportYear"] = pd.to_numeric(df["ReportYear"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["CountyFips"] = df["CountyFips"].astype(str).str.zfill(5)
    df = df[df["MeasureId"].isin(CDC_MEASURE_MAP.keys())]
    df["DataOrigin"] = df["DataOrigin"].fillna("").str.lower()
    df = df[df["DataOrigin"] == "monitor only"]
    latest_year = int(df["ReportYear"].max()) if not df.empty else None
    if latest_year is not None:
        df = df[df["ReportYear"] == latest_year]
    pivot = df.pivot_table(
        index="CountyFips",
        columns="MeasureId",
        values="Value",
        aggfunc="mean",
    )
    pivot = pivot.rename(columns=CDC_MEASURE_MAP).reset_index().rename(columns={"CountyFips": "county_fips"})
    metadata = {
        "cdc_latest_year": latest_year,
        "measures": CDC_MEASURE_MAP,
    }
    return pivot, metadata


def load_ces3_results(skip_download: bool) -> pd.DataFrame:
    csv_path = ensure_local_file(RAW_DIR / "calenviroscreen_3_0_results.csv", CES3_RESULTS_URL, skip_download)
    df = pd.read_csv(csv_path)
    df.columns = [col.strip() for col in df.columns]
    rename_map = {
        "Census Tract": "geoid",
        "CES 3.0 Score": "ces3_score",
        "Pollution Burden Score": "ces3_pollution_score",
        "Pop. Char. Score": "ces3_pop_score",
    }
    df = df.rename(columns=rename_map)
    df["geoid"] = df["geoid"].astype(str).str.zfill(11)
    keep = ["geoid", "ces3_score", "ces3_pollution_score", "ces3_pop_score"]
    return df[keep]


def load_who_context(skip_download: bool) -> Dict[str, float]:
    xlsx_path = ensure_local_file(RAW_DIR / "who_air_quality_2022.xlsx", WHO_AIR_QUALITY_URL, skip_download)
    df = pd.read_excel(xlsx_path, sheet_name="AAP_2022_city_v9")
    usa = df[df["ISO3"] == "USA"].copy()
    usa["City or Locality"] = usa["City or Locality"].astype(str)
    is_ca = usa["City or Locality"].str.contains("(Ca", case=False, na=False, regex=False)
    ca_df = usa[is_ca]

    def safe_mean(series: pd.Series) -> float:
        if series.dropna().empty:
            return float("nan")
        return float(series.dropna().mean())

    metrics = {
        "world_pm25_mean": safe_mean(df["PM2.5 (μg/m3)"] if "PM2.5 (μg/m3)" in df else pd.Series(dtype=float)),
        "usa_pm25_mean": safe_mean(usa["PM2.5 (μg/m3)"] if "PM2.5 (μg/m3)" in usa else pd.Series(dtype=float)),
        "california_pm25_mean": safe_mean(ca_df["PM2.5 (μg/m3)"] if "PM2.5 (μg/m3)" in ca_df else pd.Series(dtype=float)),
        "california_no2_mean": safe_mean(ca_df["NO2 (μg/m3)"] if "NO2 (μg/m3)" in ca_df else pd.Series(dtype=float)),
    }
    return metrics


def normalize(series: pd.Series) -> pd.Series:
    scaler = MinMaxScaler()
    reshaped = series.values.reshape(-1, 1)
    scaled = scaler.fit_transform(reshaped)
    return pd.Series(scaled[:, 0], index=series.index)


def build_features(
    ces_features: List[Dict],
    commute_df: pd.DataFrame,
    fema_df: pd.DataFrame,
    cdc_df: pd.DataFrame,
    ces3_df: pd.DataFrame,
    who_metrics: Dict[str, float],
) -> pd.DataFrame:
    records: List[Dict] = []
    for feature in ces_features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry")
        tract_val = props.get("tract")
        if tract_val is None or geom is None:
            continue
        geoid = f"{int(tract_val):011d}"
        record = {**props}
        record["geoid"] = geoid
        record["geometry"] = geom
        try:
            centroid = shape(geom).centroid
            record["centroid_lon"] = centroid.x
            record["centroid_lat"] = centroid.y
        except Exception:
            record["centroid_lon"] = np.nan
            record["centroid_lat"] = np.nan
        records.append(record)

    ces_df = pd.DataFrame(records)
    merged = ces_df.merge(commute_df, on="geoid", how="left")
    merged = merged.merge(fema_df, on="geoid", how="left")
    merged = merged.merge(ces3_df, on="geoid", how="left")

    if "county_fips" not in merged.columns:
        merged["county_fips"] = merged["geoid"].astype(str).str[:5]
    county_lookup = (
        commute_df.drop_duplicates("county_fips")
        .set_index("county_fips")["county_name"]
        .to_dict()
    )
    merged["county_name"] = merged["county_name"].fillna(
        merged["county_fips"].map(county_lookup)
    )
    merged["county_name"] = merged["county_name"].fillna("Unknown County")
    if not cdc_df.empty:
        merged = merged.merge(cdc_df, on="county_fips", how="left")
    merged["ces_score_delta"] = merged["CIscore"] - merged["ces3_score"]
    merged["who_pm25_state_avg"] = who_metrics.get("california_pm25_mean")
    merged["pm25_gap_vs_who_ca"] = merged["pm"] - merged["who_pm25_state_avg"]

    positive_cols = [
        "walkability_index",
        "non_auto_share",
        "nri_resilience_score",
        "ces_score_delta",
    ]
    negative_cols = [
        "PollutionScore",
        "traffic",
        "asthma",
        "pov",
        "nri_risk_score",
        "cdc_ozone_exceedance_days",
        "cdc_pm25_person_days",
    ]

    for col in positive_cols:
        if col in merged:
            merged[f"{col}_norm"] = normalize(merged[col].fillna(merged[col].median()))

    for col in negative_cols:
        if col in merged:
            merged[f"{col}_norm"] = 1 - normalize(merged[col].fillna(merged[col].median()))

    weights = {
        "walkability_index_norm": 0.18,
        "non_auto_share_norm": 0.12,
        "nri_resilience_score_norm": 0.13,
        "ces_score_delta_norm": 0.07,
        "PollutionScore_norm": 0.18,
        "traffic_norm": 0.1,
        "cdc_ozone_exceedance_days_norm": 0.07,
        "cdc_pm25_person_days_norm": 0.07,
        "asthma_norm": 0.04,
        "pov_norm": 0.04,
    }
    for col in weights:
        if col not in merged:
            merged[col] = 0.0
    qol_cols = list(weights.keys())
    qol_matrix = merged[qol_cols].fillna(0.0).to_numpy(dtype=np.float64, copy=True)
    weight_vector = np.array([weights[col] for col in qol_cols], dtype=np.float64)
    native_scores = accelerated_quality_scores(qol_matrix, weight_vector)
    if native_scores is not None:
        merged["quality_of_life_score"] = native_scores
    else:
        merged["quality_of_life_score"] = qol_matrix.dot(weight_vector)

    feature_cols = [
        "PollutionScore",
        "walkability_index",
        "non_auto_share",
        "asthma",
        "pov",
        "CIscore",
        "nri_risk_score",
        "nri_resilience_score",
        "cdc_ozone_exceedance_days",
    ]
    ml_data = merged[feature_cols]
    pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("cluster", KMeans(n_clusters=5, random_state=42, n_init="auto")),
        ]
    )
    merged["cluster_id"] = pipeline.fit_predict(ml_data)

    cluster_stats = (
        merged.groupby("cluster_id")[feature_cols]
        .mean()
        .rename_axis("cluster_id")
        .reset_index()
    )

    def label_clusters() -> Dict[int, str]:
        ranked = cluster_stats.copy()
        ranked["pollution_rank"] = ranked["PollutionScore"].rank()
        ranked["walk_rank"] = ranked["walkability_index"].rank(ascending=False)
        ranked["composite"] = ranked["pollution_rank"] + ranked["walk_rank"]
        ranked = ranked.sort_values("composite")
        names = [
            "Low Pollution / High Walkability",
            "Low Pollution / Emerging Walkability",
            "Moderate Risk / Balanced Mobility",
            "Elevated Pollution / Auto Dependent",
            "Critical Hotspots",
        ]
        label_map: Dict[int, str] = {}
        for idx, (_, row) in enumerate(ranked.iterrows()):
            label_map[int(row["cluster_id"])] = names[min(idx, len(names) - 1)]
        return label_map

    merged["cluster_label"] = merged["cluster_id"].map(label_clusters())

    profiles_path = PROCESSED_DIR / "cluster_profiles.json"
    cluster_profiles = cluster_stats.to_dict(orient="records")
    profiles_path.write_text(json.dumps({"profiles": cluster_profiles}))

    return merged


def export_outputs(df: pd.DataFrame) -> None:
    geojson_features: List[Dict] = []
    keep_columns = [
        "geoid",
        "TractTXT",
        "county_name",
        "ACS2019TotalPop",
        "CIscore",
        "CIscoreP",
        "PollutionScore",
        "PollutionP",
        "traffic",
        "trafficP",
        "asthma",
        "asthmaP",
        "pov",
        "povP",
        "walkability_index",
        "non_auto_share",
        "quality_of_life_score",
        "cluster_id",
        "cluster_label",
        "centroid_lat",
        "centroid_lon",
        "nri_risk_score",
        "nri_resilience_score",
        "nri_wildfire_risk",
        "cdc_ozone_exceedance_days",
        "cdc_pm25_person_days",
        "cdc_pm25_annual_avg",
        "ces3_score",
        "ces_score_delta",
        "pm25_gap_vs_who_ca",
    ]

    for _, row in df.iterrows():
        properties = {key: row.get(key) for key in keep_columns if key in df.columns}
        properties.update(
            {
                "active_commute_share": row.get("active_commute_share"),
                "drive_alone_share": row.get("drive_alone_share"),
                "public_transit_share": row.get("public_transit_share"),
            }
        )
        geometry = row.get("geometry")
        if geometry:
            geojson_features.append(
                {"type": "Feature", "geometry": geometry, "properties": properties}
            )

    geojson_doc = {"type": "FeatureCollection", "features": geojson_features}
    geojson_path = PROCESSED_DIR / "statatlas.geojson"
    geojson_path.write_text(json.dumps(clean_json_ready(geojson_doc)))

    table_path = PROCESSED_DIR / "statatlas_features.parquet"
    df.drop(columns=["geometry"], errors="ignore").to_parquet(table_path, index=False)

    cached_stats = {
        "aggregates": {
            "avg_walkability": float(df["walkability_index"].mean()),
            "avg_nri_risk": float(df["nri_risk_score"].mean()),
            "avg_resilience": float(df["nri_resilience_score"].mean()),
            "avg_pollution": float(df["PollutionScore"].mean()),
            "avg_quality": float(df["quality_of_life_score"].mean()),
            "avg_ozone_days": float(df["cdc_ozone_exceedance_days"].mean()),
            "avg_pm25_days": float(df["cdc_pm25_person_days"].mean()),
        },
        "counties": (
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
            )
            .reset_index()
            .to_dict(orient="records")
        ),
        "clusters": (
            df.groupby("cluster_label")
            .agg(
                tracts=("geoid", "count"),
                avg_quality=("quality_of_life_score", "mean"),
                avg_pollution=("PollutionScore", "mean"),
                avg_walkability=("walkability_index", "mean"),
                avg_risk=("nri_risk_score", "mean"),
                avg_resilience=("nri_resilience_score", "mean"),
            )
            .reset_index()
            .to_dict(orient="records")
        ),
    }
    (CACHE_DIR / "summary.json").write_text(json.dumps(clean_json_ready(cached_stats), indent=2))


def export_metadata(context: Dict[str, Dict[str, float]]) -> None:
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        if isinstance(obj, float) and np.isnan(obj):
            return None
        return obj

    meta_path = PROCESSED_DIR / "insight_metadata.json"
    meta_path.write_text(json.dumps(clean(context), indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the StatAtlas dataset.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse cached raw files if they exist.",
    )
    return parser.parse_args()


def main() -> None:
    ensure_dirs()
    args = parse_args()

    ces_features = fetch_calenviroscreen()
    commute_df = fetch_acs_commute()
    commute_df["geoid"] = commute_df["geoid"].astype(str).str.zfill(11)

    fema_df = load_fema_nri(args.skip_download)
    cdc_df, cdc_meta = load_cdc_air_quality(args.skip_download)
    ces3_df = load_ces3_results(args.skip_download)
    who_metrics = load_who_context(args.skip_download)

    feature_df = build_features(ces_features, commute_df, fema_df, cdc_df, ces3_df, who_metrics)
    export_outputs(feature_df)
    export_metadata({"who": who_metrics, "cdc": cdc_meta})
    print(f"Wrote {len(feature_df)} tracts to {PROCESSED_DIR / 'statatlas.geojson'}")


if __name__ == "__main__":
    main()
