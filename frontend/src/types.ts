import type { Tract } from "./api";

export type FeatureProperties = Partial<Tract> & {
  geoid?: string;
  county_name?: string | null;
  tract_label?: string | null;
  cluster_label?: string | null;
  quality_of_life_score?: number | null;
  walkability_index?: number | null;
  non_auto_share?: number | null;
  drive_alone_share?: number | null;
  public_transit_share?: number | null;
  active_commute_share?: number | null;
  work_from_home_share?: number | null;
  nri_risk_score?: number | null;
  nri_resilience_score?: number | null;
  PollutionScore?: number | null;
  cdc_ozone_exceedance_days?: number | null;
  cdc_pm25_person_days?: number | null;
  cdc_pm25_annual_avg?: number | null;
  [key: string]: unknown;
};
