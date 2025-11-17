import { useCallback, useEffect, useMemo, useState } from "react";
import {useNavigate } from "react-router-dom";
import type { GeoJsonObject } from "geojson";
import type {
  Tract,
  CountyStat,
  ClusterStat,
  SummaryResponse,
} from "../api";
import {
  fetchSummary,
  fetchTracts,
  fetchRecommendations,
  fetchGeojson,
} from "../api";
import { MapView } from "../MapView";
import type { FeatureProperties } from "../types";
import 'bootstrap/dist/css/bootstrap.css'


const defaultWeights: Record<string, number> = {
  walkability_index_norm: 3.5,
  non_auto_share_norm: 3.0,
  PollutionScore_norm: 2.5,
  traffic_norm: 2.0,
  nri_resilience_score_norm: 3.0,
  nri_risk_score_norm: 2.0,
};

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-card">
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
    </div>
  );
}

function formatValue(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return Number(value).toFixed(digits);
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}


export function HomePage() {
  const [tracts, setTracts] = useState<Tract[]>([]);
  const [summary, setSummary] = useState<SummaryResponse["aggregates"]>({});
  const [metadata, setMetadata] = useState<SummaryResponse["metadata"]>();
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<Tract[]>([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [activeCountyFilter, setActiveCountyFilter] = useState<string | null>(
    null,
  );
  const [geojson, setGeojson] = useState<GeoJsonObject | null>(null);
  const [countyStats, setCountyStats] = useState<CountyStat[]>([]);
  const [clusterStats, setClusterStats] = useState<ClusterStat[]>([]);
  const [selectedFeature, setSelectedFeature] = useState<FeatureProperties | null>(
    null,
  );

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

  const counties = useMemo(
    () =>
      countyStats
        .map((county) => county.county_name)
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b)),
    [countyStats],
  );

  const countyLookup = useMemo(() => {
    return countyStats.reduce<Record<string, CountyStat>>((acc, county) => {
      acc[county.county_name] = county;
      return acc;
    }, {});
  }, [countyStats]);

  const topCounties = useMemo(
    () =>
      [...countyStats]
        .filter((county) => Number.isFinite(county.avg_quality))
        .sort((a, b) => b.avg_quality - a.avg_quality)
        .slice(0, 6),
    [countyStats],
  );

  const featuredTracts = useMemo(
    () =>
      [...tracts]
        .sort(
          (a, b) => b.quality_of_life_score - a.quality_of_life_score,
        )
        .slice(0, 3),
    [tracts],
  );

  const selectedCounty = selectedFeature?.county_name ?? null;
  const selectedCountyStats = selectedCounty
    ? countyLookup[selectedCounty]
    : null;

  const guidance = useMemo(
    () => [
      {
        metric: "Walkability Index",
        good: "≥ 0.05 is excellent for pedestrians.",
        caution: "0.02 - 0.05 suggests moderate walkability.",
        concern: "< 0.02 indicates auto dependence.",
        value: toNumber(selectedFeature?.walkability_index),
      },
      {
        metric: "FEMA Risk Score",
        good: "< 25 (low hazard exposure).",
        caution: "25 - 60 monitor for localized hazards.",
        concern: "> 60 indicates elevated hazard vulnerability.",
        value: toNumber(selectedFeature?.nri_risk_score),
      },
      {
        metric: "FEMA Resilience",
        good: "> 60 strong recovery capacity.",
        caution: "30 - 60 improving infrastructure helps.",
        concern: "< 30 indicates challenges recovering from events.",
        value: toNumber(selectedFeature?.nri_resilience_score),
      },
      {
        metric: "Pollution Burden",
        good: "< 3 clean air and water context.",
        caution: "3 - 6 moderate impacts; monitor sensitive groups.",
        concern: "> 6 sustained exposure concerns.",
        value: toNumber(selectedFeature?.PollutionScore),
      },
      {
        metric: "Ozone Days (CDC)",
        good: "< 10 days above standard.",
        caution: "10 - 40 moderate, plan for alerts.",
        concern: "> 40 indicates frequent unhealthy ozone.",
        value: toNumber(selectedCountyStats?.avg_ozone),
      },
      {
        metric: "PM2.5 Person-Days",
        good: "< 1e7 (manageable exposure).",
        caution: "1e7 - 3e7 moderate concern.",
        concern: "> 3e7 indicates chronic particulate exposure.",
        value: toNumber(selectedCountyStats?.avg_pm25),
      },
    ],
    [selectedCountyStats, selectedFeature],
  );

  const whoContext = metadata?.who;
  const cdcContext = metadata?.cdc;

  const handleFeatureSelect = useCallback((featureProps: FeatureProperties) => {
    setSelectedFeature(featureProps ?? null);
  }, []);

  const handleRecommend = useCallback(
    async (countyFilter: string | null) => {
      setRecsLoading(true);
      setActiveCountyFilter(countyFilter);
      try {
        const result = await fetchRecommendations({
          weights: defaultWeights,
          counties: countyFilter ? [countyFilter] : [],
          top_n: 8,
        });
        setRecommendations(result);
      } catch (error) {
        console.error("Failed to fetch recommendations", error);
        setErrorMessage("Could not fetch recommendations. Please try again.");
      } finally {
        setRecsLoading(false);
      }
    },
    [],
  );
  const navigate = useNavigate();

  let items = ["Home", "About", "Contact"];
  return (
    <div className="container">
      <header>
        <h1>StatAtlas</h1>
        <p>
          FastAPI + React preview. Data courtesy of CalEnviroScreen, FEMA, CDC Tracking, WHO, and ACS.
        </p>
      </header>

      {errorMessage && (
        <div className="alert error" role="status">
          {errorMessage}
        </div>
      )}

      {loading && <p className="loading">Loading StatAtlas…</p>}

      <section>
        <h2>California Map</h2>
        <div className="map-layout">
          <MapView
            data={geojson}
            selectedGeoid={selectedFeature?.geoid ?? null}
            onSelectFeature={handleFeatureSelect}
          />
          <aside className={`map-sidebar ${selectedFeature ? "open" : ""}`}>
            {selectedFeature ? (
              <>
                <div className="sidebar-header">
                  <h3>{selectedCounty ?? "Unknown county"}</h3>
                  <button onClick={() => setSelectedFeature(null)}>Close</button>
                </div>
                <p>
                  Tract <strong>{selectedFeature.geoid}</strong> · Cluster{" "}
                  {selectedFeature.cluster_label ?? "n/a"}
                </p>
                <div className="mt-2">
                  <button
                    className="btn btn-outline-primary"
                    onClick={() => navigate(`/tract/${selectedFeature.geoid}/stats`, {
                      state: {tract: selectedFeature}
                    })}>
                      View Statistics
                    </button>
                </div>
                <div className="sidebar-metrics">
                  <p>
                    Quality of Life Score:{" "}
                    {formatValue(
                      toNumber(selectedFeature.quality_of_life_score),
                      3,
                    )}
                  </p>
                  {selectedCountyStats && (
                    <>
                      <p>
                        County avg QoL:{" "}
                        {formatValue(selectedCountyStats.avg_quality, 2)}
                      </p>
                      <p>
                        County population:{" "}
                        {selectedCountyStats.population
                          ? selectedCountyStats.population.toLocaleString()
                          : "n/a"}
                      </p>
                    </>
                  )}
                </div>
                <div className="guidance-list">
                  {guidance.map((item) => (
                    <div key={item.metric} className="guidance-item">
                      <h4>{item.metric}</h4>
                      <p className="metric-value">
                        Current value:{" "}
                        {item.value !== null ? item.value.toFixed(2) : "n/a"}
                      </p>
                      <p className="range good">{item.good}</p>
                      <p className="range caution">{item.caution}</p>
                      <p className="range concern">{item.concern}</p>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p>Click any tract to see county summaries and guidance.</p>
            )}
          </aside>
        </div>
      </section>

      <section>
        <h2>County Snapshots</h2>
        <div className="stats-grid">
          {topCounties.map((county) => (
            <StatCard
              key={county.county_name}
              label={`${county.county_name}: QoL ${formatValue(county.avg_quality, 2)}`}
              value={`Walk ${formatValue(county.avg_walkability, 2)} | Risk ${formatValue(county.avg_risk, 1)}`}
            />
          ))}
        </div>
      </section>

      {featuredTracts.length > 0 && (
        <section>
          <h2>Top Performing Tracts</h2>
          <div className="stats-grid">
            {featuredTracts.map((tract) => (
              <StatCard
                key={tract.geoid}
                label={`${tract.county_name} · ${tract.geoid}`}
                value={`QoL ${tract.quality_of_life_score.toFixed(3)} | Walk ${tract.walkability_index.toFixed(3)}`}
              />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2>Statewide Highlights</h2>
        <div className="stats-grid">
          <StatCard
            label="Avg Walkability"
            value={formatValue(summary.avg_walkability, 3)}
          />
          <StatCard
            label="Avg FEMA Risk"
            value={formatValue(summary.avg_nri_risk, 1)}
          />
          <StatCard
            label="Avg FEMA Resilience"
            value={formatValue(summary.avg_resilience, 1)}
          />
          <StatCard
            label="Avg Pollution"
            value={formatValue(summary.avg_pollution, 2)}
          />
          {summary.avg_quality !== undefined && (
            <StatCard
              label="Avg QoL"
              value={formatValue(summary.avg_quality, 3)}
            />
          )}
          {summary.avg_ozone_days !== undefined && (
            <StatCard
              label="Avg Ozone Days"
              value={formatValue(summary.avg_ozone_days, 1)}
            />
          )}
        </div>
        {cdcContext?.cdc_latest_year && (
          <p className="section-note">
            CDC exceedance data last updated {cdcContext.cdc_latest_year}.
          </p>
        )}
      </section>

      {whoContext && (
        <section>
          <h2>WHO Air-Quality Context</h2>
          <div className="stats-grid">
            <StatCard
              label="California PM2.5"
              value={`${formatValue(whoContext.california_pm25_mean, 1)} µg/m³`}
            />
            <StatCard
              label="USA PM2.5"
              value={`${formatValue(whoContext.usa_pm25_mean, 1)} µg/m³`}
            />
            <StatCard
              label="Global PM2.5"
              value={`${formatValue(whoContext.world_pm25_mean, 1)} µg/m³`}
            />
            <StatCard
              label="California NO₂"
              value={`${formatValue(whoContext.california_no2_mean, 1)} µg/m³`}
            />
          </div>
        </section>
      )}

      {clusterStats.length > 0 && (
        <section>
          <h2>Cluster Profiles</h2>
          <div className="cluster-grid">
            {clusterStats.slice(0, 4).map((cluster) => (
              <div key={cluster.cluster_label} className="cluster-card">
                <h3>{cluster.cluster_label}</h3>
                <p className="chip">{cluster.tracts.toLocaleString()} tracts</p>
                <div className="cluster-metrics">
                  <span>QoL {cluster.avg_quality.toFixed(2)}</span>
                  <span>Pollution {cluster.avg_pollution.toFixed(2)}</span>
                  <span>Walk {cluster.avg_walkability.toFixed(2)}</span>
                  <span>Risk {cluster.avg_risk.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2>Quick Recommendations</h2>
        <div className="actions">
          <button
            className={activeCountyFilter === null ? "active" : ""}
            onClick={() => handleRecommend(null)}
            disabled={recsLoading}
          >
            Statewide
          </button>
          {counties.slice(0, 5).map((county) => (
            <button
              key={county}
              className={activeCountyFilter === county ? "active" : ""}
              onClick={() => handleRecommend(county)}
              disabled={recsLoading}
            >
              {county}
            </button>
          ))}
        </div>
        {recsLoading && <p className="loading">Building personalized list…</p>}
        {recommendations.length > 0 && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Tract</th>
                  <th>County</th>
                  <th>Cluster</th>
                  <th>QoL</th>
                  <th>Walkability</th>
                  <th>Risk</th>
                  <th>Personalized</th>
                </tr>
              </thead>
              <tbody>
                {recommendations.map((tract) => (
                  <tr key={tract.geoid}>
                    <td>{tract.geoid}</td>
                    <td>{tract.county_name}</td>
                    <td>{tract.cluster_label}</td>
                    <td>{tract.quality_of_life_score.toFixed(3)}</td>
                    <td>{tract.walkability_index.toFixed(3)}</td>
                    <td>{tract.nri_risk_score.toFixed(1)}</td>
                    <td>
                      {tract.personalized_score !== undefined
                        ? tract.personalized_score.toFixed(3)
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}