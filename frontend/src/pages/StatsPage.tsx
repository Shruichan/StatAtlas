import { useMemo, useState } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import type { Tract } from "../api";
import { StatisticsCarousel } from "../components/StatisticsCarousel";
import { CountyStat } from "../api";
import type { Statistic } from "../components/StatisticsCarousel";

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
        if (state?.tract) return state.tract;       
        if (!geoid) return undefined;
        return tracts.find(t => t.geoid === geoid);
    }, [state, geoid, tracts]);
    if (!tract) {
        return (
            <div className="container">
                <h2>Tract {geoid}</h2>
                <p>Tract data isn’t loaded yet. Return to the map and open again.</p>
                <Link to="/">← Back to Map</Link>
            </div>
        );
    }
    const stats: Statistic[] = [
        {
            label: "Quality of Life Score",
            value: tract.quality_of_life_score,
            format: (val: number) => val.toFixed(3),
            description: "",
            getColor: (val: number) => {
                if (val >= 0.7) return "Good";
                if (val >= 0.4) return "Caution";
                return "Concern";
            }
        },
        {
            label: "Walkability Index",
            value: tract.walkability_index,
            format: (val: number) => val.toFixed(3),
            description: "Good: ≥ 0.05 is excellent for pedestrians., Caution: 0.02 - 0.05 suggests moderate walkability., Concern: < 0.02 indicates auto dependence.",
            getColor: (val: number) => {
                if (val >= 0.05) return "Good";
                if (val >= 0.02) return "Caution";
                return "Concern";
            }
        },
        {
            label: "SNRI Risk Score",
            value: tract.nri_risk_score,
            format: (val: number) => val.toFixed(3),
            description: "Good: < 25 (low hazard exposure)., Caution: 25 - 60 monitor for localized hazards., Concern: > 60 indicates elevated hazard vulnerability.",
            getColor: (val: number) => {
                if (val < 25) return "Good";
                if (val <= 60) return "Caution";
                return "Concern";
            }
        },
        {
            label: "SNRI Resilience Score",
            value: tract.nri_resilience_score,
            format: (val: number) => val.toFixed(3),
            description: "Good: > 60 strong recovery capacity., Caution: 30 - 60 improving infrastructure helps., Concern: < 30 indicates challenges recovering from events.",
            getColor: (val: number) => {
                if (val > 60) return "Good";
                if (val >= 30) return "Caution";
                return "Concern";
            }
        },
        {
            label: "Pollution Burden",
            value: tract.PollutionScore,
            format: (val: number) => val.toFixed(3),
            description: "Good: < 3 clean air and water context., Caution: 3 - 6 moderate impacts; monitor sensitive groups., Concern: > 6 sustained exposure Concerns.",
            getColor: (val: number) => {
                if (val < 3) return "Good";
                if (val <= 6) return "Caution";
                return "Concern";
            }
        },
        {
            label: "Cluster Label",
            value: tract.cluster_label ?? "N/A",
            format: (val: number) => val.toFixed(3),
            description: tract.cluster_label ? "" : "N/A",
            getColor: (val: number) => {
                if (val >= 0.7) return "Good";
                if (val >= 0.4) return "Caution";
                return "Concern";
            }
        },
    ]
    const [countyStats, setCountyStats] = useState<CountyStat[]>([]);

    const countyLookup = useMemo(() => {
        return countyStats.reduce<Record<string, CountyStat>>((acc, county) => {
            acc[county.county_name] = county;
            return acc;
        }, {});
    }, [countyStats]);
    const selectedCounty = tract.county_name ?? null;
    const selectedCountyStats = selectedCounty
        ? countyLookup[selectedCounty]
        : null;

    const guidance = useMemo(
        () => [
            {
                metric: "Walkability Index",
                Good: "≥ 0.05 is excellent for pedestrians.",
                Caution: "0.02 - 0.05 suggests moderate walkability.",
                Concern: "< 0.02 indicates auto dependence.",
                value: tract.walkability_index,
            },
            {
                metric: "FEMA Risk Score",
                Good: "< 25 (low hazard exposure).",
                Caution: "25 - 60 monitor for localized hazards.",
                Concern: "> 60 indicates elevated hazard vulnerability.",
                value: (tract.nri_risk_score),
            },
            {
                metric: "FEMA Resilience",
                Good: "> 60 strong recovery capacity.",
                Caution: "30 - 60 improving infrastructure helps.",
                Concern: "< 30 indicates challenges recovering from events.",
                value: tract.nri_resilience_score,
            },
            {
                metric: "Pollution Burden",
                Good: "< 3 clean air and water context.",
                Caution: "3 - 6 moderate impacts; monitor sensitive groups.",
                Concern: "> 6 sustained exposure Concerns.",
                value: tract.PollutionScore,
            },
            {
                metric: "Ozone Days (CDC)",
                Good: "< 10 days above standard.",
                Caution: "10 - 40 moderate, plan for alerts.",
                Concern: "> 40 indicates frequent unhealthy ozone.",
                value: selectedCountyStats?.avg_ozone,
            },
            {
                metric: "PM2.5 Person-Days",
                Good: "< 1e7 (manageable exposure).",
                Caution: "1e7 - 3e7 moderate Concern.",
                Concern: "> 3e7 indicates chronic particulate exposure.",
                value: selectedCountyStats?.avg_pm25,
            },
        ],
        [selectedCountyStats, tract],
    );
    return (
        <div><h1>{tract.county_name} {tract.geoid}</h1>
            <StatisticsCarousel stats={stats}></StatisticsCarousel></div>
    );
}