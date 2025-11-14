import axios from "axios";
import type { GeoJsonObject } from "geojson";

const envBase = import.meta.env.VITE_API_BASE;
const API_BASE = envBase && envBase.length > 0 ? envBase : "http://localhost:8000";

export interface Tract {
  geoid: string;
  county_name: string;
  cluster_label: string;
  quality_of_life_score: number;
  walkability_index: number;
  non_auto_share: number;
  nri_risk_score: number;
  nri_resilience_score: number;
  PollutionScore: number;
  personalized_score?: number;
}

export interface CountyStat {
  county_name: string;
  tracts: number;
  avg_quality: number;
  avg_walkability: number | null;
  avg_risk: number | null;
  avg_resilience: number | null;
  avg_pollution: number | null;
  avg_ozone: number | null;
  avg_pm25: number | null;
  population: number | null;
}

export interface ClusterStat {
  cluster_label: string;
  tracts: number;
  avg_quality: number;
  avg_pollution: number;
  avg_walkability: number;
  avg_risk: number;
  avg_resilience: number;
}

export interface InsightMetadata {
  who?: {
    world_pm25_mean?: number;
    usa_pm25_mean?: number;
    california_pm25_mean?: number;
    california_no2_mean?: number;
  };
  cdc?: {
    cdc_latest_year?: number;
    measures?: Record<string, string>;
  };
  [key: string]: unknown;
}

export interface SummaryResponse {
  aggregates: Record<string, number>;
  metadata?: InsightMetadata;
  counties?: CountyStat[];
  clusters?: ClusterStat[];
}

export async function fetchTracts(limit = 100) {
  const { data } = await axios.get<{ results: Tract[] }>(`${API_BASE}/api/tracts`, {
    params: { limit },
  });
  return data.results;
}

export async function fetchSummary() {
  const { data } = await axios.get<SummaryResponse>(`${API_BASE}/api/summary`);
  return data;
}

export async function fetchGeojson() {
  const { data } = await axios.get<GeoJsonObject>(`${API_BASE}/api/geojson`);
  return data;
}

export async function fetchRecommendations(payload: {
  weights: Record<string, number>;
  counties: string[];
  top_n: number;
}) {
  const { data } = await axios.post<{ results: Tract[] }>(
    `${API_BASE}/api/recommendations`,
    payload,
  );
  return data.results;
}
