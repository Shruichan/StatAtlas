import { useMemo } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import type { Tract, CountyStat, SummaryResponse } from "../api";
import { StatisticsCarousel } from "../components/StatisticsCarousel";
import type { Statistic } from "../components/StatisticsCarousel";

type FeatureLike = Pick<
  Tract,
  | "geoid"
  | "county_name"
  | "quality_of_life_score"
  | "walkability_index"
  | "non_auto_share"
  | "drive_alone_share"
  | "public_transit_share"
  | "active_commute_share"
  | "work_from_home_share"
  | "nri_risk_score"
  | "nri_resilience_score"
  | "PollutionScore"
  | "cdc_ozone_exceedance_days"
  | "cdc_pm25_person_days"
  | "cdc_pm25_annual_avg"
  | "cluster_label"
>;

interface TractStatsPageProps {
  tracts: Tract[];
  countyStats: CountyStat[];
  summary: SummaryResponse["aggregates"];
  metadata?: SummaryResponse["metadata"];
}

function safeNumber(value: unknown): number | null {
  if (typeof value !== "number") return null;
  return Number.isFinite(value) ? value : null;
}

function formatNumber(
  value: number | null | undefined,
  digits = 2,
  fallback = "n/a",
) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return fallback;
  }
  return Number(value).toFixed(digits);
}

function formatPercent(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export default function TractStatsPage({
  tracts,
  countyStats,
  summary,
  metadata,
}: TractStatsPageProps) {
  const { geoid } = useParams();
  const { state } = useLocation() as { state?: { tract?: FeatureLike } };

  const tract = useMemo<FeatureLike | undefined>(() => {
    if (state?.tract) return state.tract;
    if (!geoid) return undefined;
    return tracts.find((t) => t.geoid === geoid);
  }, [state, geoid, tracts]);

  const countyLookup = useMemo(() => {
    return countyStats.reduce<Record<string, CountyStat>>((acc, county) => {
      if (county.county_name) {
        acc[county.county_name] = county;
      }
      return acc;
    }, {});
  }, [countyStats]);

  if (!tract) {
    return (
      <div className="stats-page container">
        <h2>Tract {geoid}</h2>
        <p>Tract data isn’t loaded yet. Return to the map and open again.</p>
        <Link to="/">← Back to Explorer</Link>
      </div>
    );
  }

  const selectedCountyStats = tract.county_name
    ? countyLookup[tract.county_name]
    : undefined;
  const statewideQuality = safeNumber(summary?.avg_quality);

  const stats: Statistic[] = [
    {
      label: "Quality of Life Score",
      value: safeNumber(tract.quality_of_life_score),
      format: (val: number) => val.toFixed(3),
      description: "Composite score across walkability, pollution, FEMA risk, and resilience.",
      getColor: (val: number) => {
        if (val >= 0.7) return "good";
        if (val >= 0.4) return "caution";
        return "concern";
      },
    },
    {
      label: "Walkability Index",
      value: safeNumber(tract.walkability_index),
      format: (val: number) => val.toFixed(3),
      description: "≥ 0.05 pedestrian friendly · 0.02–0.05 moderate · < 0.02 auto dependent.",
      getColor: (val: number) => {
        if (val >= 0.05) return "good";
        if (val >= 0.02) return "caution";
        return "concern";
      },
    },
    {
      label: "Non-Auto Share",
      value: safeNumber(tract.non_auto_share),
      format: (val: number) => formatPercent(val),
      description: "Share of commuters who avoid driving alone (transit, walking, biking, WFH).",
      getColor: (val: number) => {
        if (val >= 0.7) return "good";
        if (val >= 0.5) return "caution";
        return "concern";
      },
    },
    {
      label: "Drive-Alone Share",
      value: safeNumber(tract.drive_alone_share),
      format: (val: number) => formatPercent(val),
      description: "Percentage of residents commuting solo by car (lower is better).",
      getColor: (val: number) => {
        if (val <= 0.5) return "good";
        if (val <= 0.7) return "caution";
        return "concern";
      },
    },
    {
      label: "Transit Share",
      value: safeNumber(tract.public_transit_share),
      format: (val: number) => formatPercent(val),
      description: "Residents using buses, light rail, or trains to commute.",
    },
    {
      label: "Active Commute Share",
      value: safeNumber(tract.active_commute_share),
      format: (val: number) => formatPercent(val),
      description: "Walking + biking share of total commutes.",
    },
    {
      label: "Work-From-Home",
      value: safeNumber(tract.work_from_home_share),
      format: (val: number) => formatPercent(val),
      description: "Remote work offers resilience when hazards disrupt mobility.",
    },
    {
      label: "FEMA Risk Score",
      value: safeNumber(tract.nri_risk_score),
      format: (val: number) => val.toFixed(1),
      description: "< 25 low hazard · 25–60 monitor hotspots · > 60 elevated vulnerability.",
      getColor: (val: number) => {
        if (val < 25) return "good";
        if (val <= 60) return "caution";
        return "concern";
      },
    },
    {
      label: "FEMA Resilience Score",
      value: safeNumber(tract.nri_resilience_score),
      format: (val: number) => val.toFixed(1),
      description: "> 60 strong recovery · 30–60 strengthening · < 30 fragile systems.",
      getColor: (val: number) => {
        if (val > 60) return "good";
        if (val >= 30) return "caution";
        return "concern";
      },
    },
    {
      label: "Pollution Burden",
      value: safeNumber(tract.PollutionScore),
      format: (val: number) => val.toFixed(2),
      description: "< 3 clean air/water · 3–6 monitor sensitive groups · > 6 sustained exposure concerns.",
      getColor: (val: number) => {
        if (val < 3) return "good";
        if (val <= 6) return "caution";
        return "concern";
      },
    },
    {
      label: "Cluster Context",
      value: tract.cluster_label ?? "Unclustered",
      description: "Assigned statewide profile highlighting similar tract characteristics.",
    },
  ];

  const quickCards = [
    {
      label: "Walkability",
      value: formatNumber(safeNumber(tract.walkability_index), 3),
      detail: "Normalized index",
    },
    {
      label: "FEMA Risk",
      value: formatNumber(safeNumber(tract.nri_risk_score), 1),
      detail: "0 (low) – 100 (high)",
    },
    {
      label: "FEMA Resilience",
      value: formatNumber(safeNumber(tract.nri_resilience_score), 1),
      detail: "Ability to rebound",
    },
    {
      label: "Pollution Burden",
      value: formatNumber(safeNumber(tract.PollutionScore), 2),
      detail: "CalEnviroScreen scale",
    },
    {
      label: "Non-Auto Share",
      value: formatPercent(safeNumber(tract.non_auto_share)),
      detail: "Transit + walking + biking + WFH",
    },
    {
      label: "Transit Share",
      value: formatPercent(safeNumber(tract.public_transit_share)),
      detail: "Residents commuting via transit",
    },
    {
      label: "Work-From-Home",
      value: formatPercent(safeNumber(tract.work_from_home_share)),
      detail: "Remote-friendly workforce",
    },
  ];

  const airQualityCards = [
    {
      label: "Tract Ozone Days",
      value: formatNumber(safeNumber(tract.cdc_ozone_exceedance_days), 1),
      detail: "CDC exceedance days",
    },
    {
      label: "Tract PM2.5 Person-Days",
      value: formatNumber(safeNumber(tract.cdc_pm25_person_days), 0),
      detail: "Exposure-weighted days",
    },
    {
      label: "County Avg Ozone",
      value: formatNumber(safeNumber(selectedCountyStats?.avg_ozone), 1),
      detail: "County context",
    },
    {
      label: "County Avg PM2.5",
      value: formatNumber(safeNumber(selectedCountyStats?.avg_pm25), 0),
      detail: "County context",
    },
  ];

  const guidance = [
    {
      metric: "Walkability Index",
      good: "≥ 0.05",
      caution: "0.02 – 0.05",
      concern: "< 0.02",
      value: safeNumber(tract.walkability_index),
    },
    {
      metric: "FEMA Risk Score",
      good: "< 25",
      caution: "25 – 60",
      concern: "> 60",
      value: safeNumber(tract.nri_risk_score),
    },
    {
      metric: "FEMA Resilience",
      good: "> 60",
      caution: "30 – 60",
      concern: "< 30",
      value: safeNumber(tract.nri_resilience_score),
    },
    {
      metric: "Pollution Burden",
      good: "< 3",
      caution: "3 – 6",
      concern: "> 6",
      value: safeNumber(tract.PollutionScore),
    },
    {
      metric: "Ozone Days (CDC)",
      good: "< 10",
      caution: "10 – 40",
      concern: "> 40",
      value: safeNumber(selectedCountyStats?.avg_ozone),
    },
    {
      metric: "PM2.5 Person-Days",
      good: "< 1e7",
      caution: "1e7 – 3e7",
      concern: "> 3e7",
      value: safeNumber(selectedCountyStats?.avg_pm25),
    },
  ];

  return (
    <div className="stats-page container">
      <Link className="back-link" to="/">
        ← Back to Explorer
      </Link>
      <div className="stats-header">
        <div>
          <p className="eyebrow">Census tract {tract.geoid}</p>
          <h1>{tract.county_name ?? "Unknown county"}</h1>
          <p className="subhead">
            Cluster: {tract.cluster_label ?? "Unclustered"} · Quality of Life{" "}
            {formatNumber(safeNumber(tract.quality_of_life_score), 3)}
          </p>
          {statewideQuality !== null && (
            <p className="section-note">
              Statewide avg QoL {formatNumber(statewideQuality, 3)}
            </p>
          )}
        </div>
        <div className="stats-header-badges">
          <span className="chip">Walk {formatNumber(safeNumber(tract.walkability_index), 3)}</span>
          <span className="chip">Risk {formatNumber(safeNumber(tract.nri_risk_score), 1)}</span>
          <span className="chip">Resilience {formatNumber(safeNumber(tract.nri_resilience_score), 1)}</span>
        </div>
      </div>

      <section className="stats-card-grid">
        {quickCards.map((card) => (
          <div key={card.label} className="stats-card">
            <p className="stat-label">{card.label}</p>
            <p className="stat-value">{card.value}</p>
            <p className="stat-detail">{card.detail}</p>
          </div>
        ))}
      </section>

      <section className="stats-section">
        <StatisticsCarousel stats={stats} />
      </section>

      <section className="stats-section">
        <h3>Air quality snapshot</h3>
        <div className="stats-card-grid compact">
          {airQualityCards.map((card) => (
            <div key={card.label} className="stats-card">
              <p className="stat-label">{card.label}</p>
              <p className="stat-value">{card.value}</p>
              <p className="stat-detail">{card.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {selectedCountyStats && (
        <section className="stats-section">
          <h3>County context</h3>
          <div className="stats-card-grid compact">
            <div className="stats-card">
              <p className="stat-label">County Avg QoL</p>
              <p className="stat-value">
                {formatNumber(safeNumber(selectedCountyStats.avg_quality), 2)}
              </p>
            </div>
            <div className="stats-card">
              <p className="stat-label">Population</p>
              <p className="stat-value">
                {selectedCountyStats.population
                  ? selectedCountyStats.population.toLocaleString()
                  : "n/a"}
              </p>
            </div>
            <div className="stats-card">
              <p className="stat-label">Avg Walkability</p>
              <p className="stat-value">
                {formatNumber(safeNumber(selectedCountyStats.avg_walkability), 3)}
              </p>
            </div>
            <div className="stats-card">
              <p className="stat-label">Avg FEMA Risk</p>
              <p className="stat-value">
                {formatNumber(safeNumber(selectedCountyStats.avg_risk), 1)}
              </p>
            </div>
            <div className="stats-card">
              <p className="stat-label">Non-Auto Share</p>
              <p className="stat-value">
                {formatPercent(safeNumber(selectedCountyStats.avg_non_auto_share))}
              </p>
            </div>
            <div className="stats-card">
              <p className="stat-label">Transit Share</p>
              <p className="stat-value">
                {formatPercent(safeNumber(selectedCountyStats.avg_transit_share))}
              </p>
            </div>
            <div className="stats-card">
              <p className="stat-label">Drive-Alone Share</p>
              <p className="stat-value">
                {formatPercent(safeNumber(selectedCountyStats.avg_drive_alone_share))}
              </p>
            </div>
            <div className="stats-card">
              <p className="stat-label">Work-From-Home</p>
              <p className="stat-value">
                {formatPercent(safeNumber(selectedCountyStats.avg_work_from_home_share))}
              </p>
            </div>
          </div>
        </section>
      )}

      <section className="stats-section">
        <h3>Guidance ranges</h3>
        <table className="guidance-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Current value</th>
              <th>Good</th>
              <th>Caution</th>
              <th>Concern</th>
            </tr>
          </thead>
          <tbody>
            {guidance.map((item) => (
              <tr key={item.metric}>
                <td>{item.metric}</td>
                <td>{formatNumber(item.value, 2)}</td>
                <td>{item.good}</td>
                <td>{item.caution}</td>
                <td>{item.concern}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {metadata?.cdc?.cdc_latest_year && (
          <p className="section-note">
            CDC ozone/PM context updated {metadata.cdc.cdc_latest_year}.
          </p>
        )}
      </section>
    </div>
  );
}
