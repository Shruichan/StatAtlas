import { useCallback, useState, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import {
  fetchSummary,
  fetchTracts,
  fetchGeojson,
  Tract,
  CountyStat,
  ClusterStat,
  SummaryResponse,
} from "./api";
import type { GeoJsonObject } from "geojson";

import type { FeatureProperties } from "./types";
import { NavigationBar } from "./components/NavigationBar";
import 'bootstrap/dist/css/bootstrap.css'
import imagePath from './assets/logo-unsplash-olivier.jpg'
import StatsPage from "./pages/StatsPage.tsx"
import { HomePage } from "./pages/HomePage.tsx";

export default function App() {
  return (<BrowserRouter><MainContent></MainContent></BrowserRouter>)
}

function MainContent() {
  const [tracts, setTracts] = useState<Tract[]>([]);
  const [summary, setSummary] = useState<SummaryResponse["aggregates"]>({});
  const [metadata, setMetadata] = useState<SummaryResponse["metadata"]>();
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [geojson, setGeojson] = useState<GeoJsonObject | null>(null);
  const [countyStats, setCountyStats] = useState<CountyStat[]>([]);
  const [clusterStats, setClusterStats] = useState<ClusterStat[]>([]);
  const [selectedFeature, setSelectedFeature] = useState<FeatureProperties | null>(
    null,
  );

  const handleFeatureSelect = useCallback((featureProps: FeatureProperties) => {
    setSelectedFeature(featureProps ?? null);
  }, []);

  useEffect(() => {
    let mounted = true;
    async function bootstrap() {
      setLoading(true);
      try {
        const [tractList, summaryData, geojsonData] = await Promise.all([
          fetchTracts(10000, 0),
          fetchSummary(),
          fetchGeojson(),
        ]);

        if (!mounted) return;
        setTracts(tractList);
        setSummary(summaryData.aggregates ?? {});
        setMetadata(summaryData.metadata);
        setCountyStats(summaryData.counties ?? []);
        setClusterStats(summaryData.clusters ?? []);
        setGeojson(geojsonData);
        setErrorMessage(null);
      } catch (error) {
        console.error("Failed to load StatAtlas data", error);
        if (mounted) {
          setErrorMessage(
            "Unable to reach the StatAtlas API. Ensure `uvicorn backend.main:app` is running.",
          );
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }
    bootstrap();
    return () => {
      mounted = false;
    };
  }, []);

  const items = ["Home", "About", "Contact"];
  return (
    <div className="container">
      <header>
        <h1>StatAtlas</h1>
        <p>
          FastAPI + React preview. Data courtesy of CalEnviroScreen, FEMA, CDC Tracking, WHO, and ACS.
        </p>
      </header>

      <div>
        <NavigationBar
          brandName="StatAtlas"
          imageSrcPath={imagePath}
          navItems={items}
          tracts={tracts}
          onSelectTract={(tract) =>
            handleFeatureSelect({
              geoid: tract.geoid,
              county_name: tract.county_name,
              walkability_index: tract.walkability_index,
              non_auto_share: tract.non_auto_share,
              drive_alone_share: tract.drive_alone_share,
              public_transit_share: tract.public_transit_share,
              active_commute_share: tract.active_commute_share,
              work_from_home_share: tract.work_from_home_share,
              nri_risk_score: tract.nri_risk_score,
              nri_resilience_score: tract.nri_resilience_score,
              PollutionScore: tract.PollutionScore,
              quality_of_life_score: tract.quality_of_life_score,
              cluster_label: tract.cluster_label,
              cdc_ozone_exceedance_days: tract.cdc_ozone_exceedance_days,
              cdc_pm25_person_days: tract.cdc_pm25_person_days,
              cdc_pm25_annual_avg: tract.cdc_pm25_annual_avg,
            })
          }>
        </NavigationBar>
        <Routes>
          <Route
            path="/" element={<HomePage
            // Passing all necessary data/state as props
            tracts={tracts}
            loading={loading}
            geojson={geojson}
            summary={summary}
            metadata={metadata}
            countyStats={countyStats}
            clusterStats={clusterStats}
            // Also pass down the selector callback if HomePage needs it
            onSelectFeature={handleFeatureSelect} 
            selectedFeature={selectedFeature}
        />}   ></Route>
          <Route path="/about" element={<div>About StatAtlas...</div>} />
          <Route path="/contact" element={<div>Contact Creators...</div>} />
          <Route
            path="/tract/:geoid/stats"
            element={
              <StatsPage
                tracts={tracts}
                countyStats={countyStats}
                summary={summary}
                metadata={metadata}
              />
            }
          />

        </Routes>
      </div>

      {errorMessage && (
        <div className="alert error" role="status">
          {errorMessage}
        </div>
      )}

      {loading && <p className="loading">Loading StatAtlas…</p>}


    </div>
  );
}
