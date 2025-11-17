import { useMemo } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import type { Tract } from "../api";

type FeatureLike = {
  geoid: string;
  county_name: string;
  quality_of_life_score: number;
  walkability_index: number;
  nri_risk_score: number;
  nri_resilience_score: number;
  PollutionScore: number;
  cluster_label?: string | null;
};

export default function TractStatsPage({ tracts }: { tracts: Tract[] }) {
  const { geoid } = useParams();
  const { state } = useLocation() as { state?: { tract?: FeatureLike } };
  const tract = useMemo<FeatureLike | undefined>(() => {
    if (state?.tract) return state.tract;        // fast when navigated from map
    if (!geoid) return undefined;
    return tracts.find(t => t.geoid === geoid);  // works after App loads tracts
  }, [state, geoid, tracts]);
  if (true) {
    return (
      <div className="container">
        <h2>Tract {geoid}</h2>
        <p>Tract data isn’t loaded yet. Return to the map and open again.</p>
        <Link to="/">← Back to Map</Link>
      </div>
    );
  }
}