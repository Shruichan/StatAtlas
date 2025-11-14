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

## Data sources
| Theme | Dataset | Notes |
| --- | --- | --- |
| Pollution, health burden | [CalEnviroScreen 4.0 Results](https://data.ca.gov/dataset/calenviroscreen-4-0-results) via ArcGIS REST API | 
| Historical comparison | [CalEnviroScreen 3.0 Results](https://data.ca.gov/dataset/calenviroscreen-3-0-results) CSV | 
| Walkability / car dependence | [ACS 2022 5-year (table B08301)](https://api.census.gov/data/2022/acs/acs5/groups/B08301.html) | 
| Hazard & resilience | [FEMA National Risk Index (tract CSV)](https://hazards.fema.gov/nri/data-resources#csvDownload) | 
| Air quality exceedances | [CDC Tracking Network air quality measures (cjae-szjv)](https://data.cdc.gov/Environmental-Health-Toxicology/Air-Quality-Measures-on-the-National-Environmental-H/cjae-szjv) | 
| Global context | [WHO Air Quality Database 2022](https://www.who.int/data/gho/data/themes/air-pollution/who-air-quality-database/2022) | Supplies California-wide PM2.5/NO₂ averages so that tract-level data can be compared against WHO measurements. |


### Walkability & quality-of-life scoring
1. **Walkability index** = 0.4·(walk + bike share) + 0.4·(public transit share) + 0.2·(work-from-home share).  
2. **Lack of car dependency** = 1 − drive-alone share.  
3. **Quality-of-life index** normalizes walkability, non-auto share, pollution score (inverted), and traffic (inverted) to the 0–1 range and averages them with weights (0.35, 0.25, 0.20, 0.20).  
4. **Recommender sliders** reuse the normalized columns (`*_norm`) so users can tilt toward low poverty, low asthma, clean air, or high mobility options.
