import type { Tract } from "./api";

export type FeatureProperties = Partial<Tract> & {
  geoid?: string;
  county_name?: string | null;
  cluster_label?: string | null;
  quality_of_life_score?: number | null;
  walkability_index?: number | null;
  non_auto_share?: number | null;
  nri_risk_score?: number | null;
  nri_resilience_score?: number | null;
  PollutionScore?: number | null;
  [key: string]: unknown;
};

