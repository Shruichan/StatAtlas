# StatAtlas

StatAtlas is a California-focused prototype for contextualizing environmental and public-health data on an interactive map. It blends CalEnviroScreen 4.0 polygons, ACS commute behavior (walkability / car-dependency proxy), and lightweight machine learning to surface actionable insights for residents, researchers, and policy makers.

## Features
- **Interactive choropleth map** – pan/zoom across California, choose metrics (pollution, walkability, car dependency, asthma, composite quality index) and hover for tract-level details.
- **Walkability & car-dependency analytics** – ACS *B08301* commuting shares are transformed into a walkability index, non-auto share, and quality-of-life scorecard.
- **ML clustering** – a K-Means model groups tracts into interpretable resilience profiles (e.g., “Low Pollution / High Walkability”, “Critical Hotspots”). Cluster summaries update live with map filters.
- **Quality-of-life recommender** – slider-driven weights let a user emphasize low pollution, low congestion, high walkability, etc., and receive tract recommendations plus a human-readable rationale.
- **Data pipeline** – reproducible script downloads authoritative sources (ArcGIS OEHHA + U.S. Census ACS) and exports both GeoJSON and Parquet artifacts for the UI.

## Quick start
```bash
# 1) Install dependencies (Python ≥ 3.10 recommended)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) Build datasets (downloads CalEnviroScreen + ACS commute metrics)
python -m src.data_pipeline.build_dataset

# 3) Launch the Streamlit app
streamlit run src/app.py
```

> Tip: rerun `python -m src.data_pipeline.build_dataset --skip-download` to regenerate processed files from the cached raw downloads in `data/raw/`.

## Data sources & methodology
| Theme | Dataset | Notes |
| --- | --- | --- |
| Pollution, health burden | [CalEnviroScreen 4.0 Results](https://data.ca.gov/dataset/calenviroscreen-4-0-results) via ArcGIS REST API | Provides 8,000+ census-tract polygons with pollution burden, asthma, socioeconomic, and percentile ranks. |
| Historical comparison | [CalEnviroScreen 3.0 Results](https://data.ca.gov/dataset/calenviroscreen-3-0-results) CSV | Lets us compute CES 4.0 − CES 3.0 score deltas to highlight tracts with worsening/improving conditions. |
| Walkability / car dependence | [ACS 2022 5-year (table B08301)](https://api.census.gov/data/2022/acs/acs5/groups/B08301.html) | Pulls commuting modes (drive-alone, public transit, walk, bike, work-from-home) for every CA tract. |
| Hazard & resilience | [FEMA National Risk Index (tract CSV)](https://hazards.fema.gov/nri/data-resources#csvDownload) | Adds FEMA risk + resilience composites plus wildfire risk to each census tract. |
| Air quality exceedances | [CDC Tracking Network air quality measures (cjae-szjv)](https://data.cdc.gov/Environmental-Health-Toxicology/Air-Quality-Measures-on-the-National-Environmental-H/cjae-szjv) | Monitor-only ozone exceedance days, PM2.5 person-days, and annual PM2.5 averages at the county level. |
| Global context | [WHO Air Quality Database 2022](https://www.who.int/data/gho/data/themes/air-pollution/who-air-quality-database/2022) | Supplies California-wide PM2.5/NO₂ averages so that tract-level data can be compared against WHO measurements. |
| Clustering features | Derived | K-Means on pollution score, walkability index, non-auto share, asthma rate, poverty %, FEMA risk/resilience, and CDC ozone indicators. |
| Future integrations | FEMA National Risk Index (other hazards), WHO Air Quality DB daily feeds, EPA EnviroAtlas, NOAA climate indicators | Additional CSV/GeoDatabase feeds can be hooked into the same pipeline for wildfire, heat, PFAS, water quality, etc. |

### Walkability & quality-of-life scoring
1. **Walkability index** = 0.4·(walk + bike share) + 0.4·(public transit share) + 0.2·(work-from-home share).  
2. **Lack of car dependency** = 1 − drive-alone share.  
3. **Quality-of-life index** normalizes walkability, non-auto share, pollution score (inverted), and traffic (inverted) to the 0–1 range and averages them with weights (0.35, 0.25, 0.20, 0.20).  
4. **Recommender sliders** reuse the normalized columns (`*_norm`) so users can tilt toward low poverty, low asthma, clean air, or high mobility options.

## Project layout
```
├── requirements.txt
├── src
│   ├── app.py                         # Streamlit interface (map, analytics, recommender)
│   └── data_pipeline
│       ├── __init__.py
│       └── build_dataset.py           # Downloads + enriches datasets
├── data
│   ├── raw                            # Cached API responses (GeoJSON/CSV)
│   └── processed
│       ├── statatlas.geojson          # Map-ready features
│       ├── statatlas_features.parquet # Full feature matrix with ML columns
│       └── cluster_profiles.json      # Persisted cluster centroids
└── assets                             # Placeholders for future diagrams/notebooks
```

## Operational notes
- `build_dataset.py` is idempotent and paginates the ArcGIS FeatureServer (2,000 records per request) so the full CalEnviroScreen layer is downloaded in seconds.
- `statatlas.geojson` contains only the fields the UI needs; heavy columns remain in the Parquet file for analytics.
- The Streamlit app gracefully warns if processed files are missing, guiding contributors to run the pipeline first.
- `py_compile` is used for quick sanity checks: `python -m py_compile src/data_pipeline/build_dataset.py src/app.py`.

## Roadmap ideas
1. **Climate + hazard layers** – merge FEMA NRI, NOAA flood/heat indices, Cal Fire wildfire perimeters, and NASA imagery into extra map toggles.
2. **Quality-of-life narratives** – use HuggingFace summarization models to auto-generate localized context (landmarks, historical incidents) per tract.
3. **Time-aware metrics** – support year-over-year comparisons (CalEnviroScreen 3.0 vs 4.0, AQ trends from WHO, EPA AirNow, etc.).
4. **Citizen science hooks** – add a data intake form/API so residents can submit localized observations or uploads (photos, annotations).
5. **Global expansion** – replicate the same pipeline for other states/countries by swapping the ACS step with international commute/walkability proxies.

## Troubleshooting
- Missing modules? Re-run `python -m pip install -r requirements.txt` inside your virtual environment (Python 3.10+).
- Pipeline errors? Use `--skip-download` if you want to regenerate outputs from existing raw files or delete `data/raw` to force a clean pull.
- Streamlit map looks empty? Verify the sidebar filters (especially county + cluster filters) and ensure `quality_of_life_score` slider spans the 0–1 range.

---
Built with ❤️ by the StatAtlas team (San José State University · Department of Computer Science).
