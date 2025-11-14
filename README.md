# StatAtlas

StatAtlas is a California-focused environmental intelligence platform. It blends CalEnviroScreen 4.0 polygons, ACS commute behavior (walkability / car-dependency proxy), FEMA National Risk Index scores, CDC air-quality metrics, WHO context, and lightweight machine learning.

## Features
- **FastAPI backend (`backend/main.py`)** – exposes `/api/health`, `/api/tracts`, `/api/summary`, and `/api/recommendations`, suitable for any web/mobile client.
- **React + Vite front-end (`frontend/`)** – modern SPA consuming the FastAPI endpoints; styled stat cards, quick recommendation buttons, and summary tables.
- **Streamlit prototype (`src/app.py`)** – interactive map with FEMA/CDC overlays, personalized recommender sliders, and descriptive expanders.
- **Data pipeline** – reproducible script downloads authoritative sources, derives walkability + FEMA + CDC features, and writes both GeoJSON and Parquet artifacts.
- **Native acceleration** – the quality-of-life scorer runs via a small C helper (`src/c_extensions/qol_scores.c`) that compiles automatically.

## Quick start
```bash
# 1) Install dependencies (Python ≥ 3.10 recommended)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) Build datasets (downloads CalEnviroScreen + ACS/CDC/FEMA/WHO inputs)
python -m src.data_pipeline.build_dataset

# 3a) Launch the Streamlit prototype
streamlit run src/app.py

# 3b) Or launch the production API
uvicorn backend.main:app --reload

# 3c) Front-end (React + Vite)
cd frontend
npm install
npm run dev

# All-in-one dev stack (backend + frontend)
./scripts/run_stack.sh
```

> Tip: rerun `python -m src.data_pipeline.build_dataset --skip-download` to regenerate processed files from cached raw inputs in `data/raw/`.

### Docker (full stack)
```bash
docker compose up --build
# backend available at http://localhost:8000, React preview at http://localhost:4173
```

## Data sources
| Theme | Dataset |
| --- | --- | 
| Pollution, health burden | [CalEnviroScreen 4.0 Results](https://data.ca.gov/dataset/calenviroscreen-4-0-results) via ArcGIS REST API | 
| Historical comparison | [CalEnviroScreen 3.0 Results](https://data.ca.gov/dataset/calenviroscreen-3-0-results) CSV | 
| Walkability / car dependence | [ACS 2022 5-year (table B08301)](https://api.census.gov/data/2022/acs/acs5/groups/B08301.html) | 
| Hazard & resilience | [FEMA National Risk Index](https://hazards.fema.gov/nri/data-resources#csvDownload) | 
| Air quality exceedances | [CDC Tracking Network air quality measures (cjae-szjv)](https://data.cdc.gov/Environmental-Health-Toxicology/Air-Quality-Measures-on-the-National-Environmental-H/cjae-szjv) | 
| Global context | [WHO Air Quality Database 2022](https://www.who.int/data/gho/data/themes/air-pollution/who-air-quality-database/2022) |

### Walkability & quality-of-life scoring
1. **Walkability index** = 0.4·(walk + bike share) + 0.4·(public transit share) + 0.2·(work-from-home share).  
2. **Lack of car dependency** = 1 − drive-alone share.  
3. **Quality-of-life index** normalizes walkability, non-auto share, pollution score (inverted), traffic (inverted), FEMA risk/resilience, and CDC exceedances before computing a weighted blend.  
4. **Recommender sliders** reuse the normalized columns (`*_norm`) so users can tilt toward low poverty, low asthma, clean air, hazard resilience, etc.

## Project layout
```
├── requirements.txt
├── src
│   ├── app.py                         # Streamlit interface (map, analytics, recommender)
│   ├── c_extensions                   # Native helpers (quality-of-life scoring)
│   ├── data_pipeline
│   │   ├── __init__.py
│   │   └── build_dataset.py           # Downloads + enriches datasets
│   └── services
│       └── recommender.py             # Shared recommendation utilities (Streamlit + API)
├── backend
│   ├── __init__.py
│   └── main.py                        # FastAPI service serving tracts/recommendations
├── data
│   ├── raw                            # Cached API responses (GeoJSON/CSV)
│   └── processed
│       ├── statatlas.geojson          # Map-ready features
│       ├── statatlas_features.parquet # Full feature matrix with ML columns
│       ├── cluster_profiles.json      # Persisted cluster centroids
│       └── insight_metadata.json      # WHO/CDC context shared with the UI/API
└── assets                             # Placeholders for future diagrams/notebooks
```

## FastAPI backend
- `uvicorn backend.main:app --reload` launches a production-ready API with `/api/health`, `/api/tracts`, `/api/summary`, and `/api/recommendations`.
- The backend reuses the same recommendation engine as the Streamlit UI and powers the React SPA.

