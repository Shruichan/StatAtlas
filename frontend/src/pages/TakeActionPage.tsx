import { FeatureLike, formatNumber, safeNumber, TractStatsPageProps } from "./StatsPage";
import { useMemo } from "react";
import { useParams, useLocation, Link, useNavigate } from "react-router-dom";
import type { Tract, CountyStat, SummaryResponse } from "../api";

export function TakeActionPage({
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

    const navigate = useNavigate();
    return (
        <div className="takeaction-page container">
            <div className="mt-2">
                <button
                    className="btn btn-outline-primary"
                    onClick={() => navigate(`/tract/${tract.geoid}/stats/`, {
                        state: { tract: tract }
                    })}>
                    ← Back to Stats
                </button>
            </div>
            <div className="stats-header">
                <div>
                    <p className="eyebrow">{tract.tract_label ?? `Census tract ${tract.geoid}`}</p>
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
            <div className="container">
                <a href="https://content.sph.harvard.edu/wwwhsph/sites/1267/2022/06/S.2669-Advocacy-Email.pdf">Email Template is adapted from Harvard University</a><br/>
                <a href="https://ceja.org/what-we-do/green-zones/fighting-toxic-pollution-the-indirect-sources-rule/">Source of Indrect Pollution Information</a><br/>
                <a href="https://calmatters.digitaldemocracy.org/bills/ca_202520260ab914">CA Assembly Bill 914</a><br/>
                <a href="https://www.lung.org/research/sota/city-rankings/states/california">CA State of the Air Report Card</a>
                <section>
                    <h2>Email Template For Legislator</h2>
                    <p>
                        Find your Legislator's name and email at this link:<br />
                        <a href="https://malegislature.gov/search/findmylegislator">
                            https://malegislature.gov/search/findmylegislator</a><br />
                        Please feel free to edit the below template, especially if you'd like to include your personal
                        reasons for supporting this bill, or how it relates to your life/work/family/etc.<br />
                        The bolded and italicized text parts is where you have to insert a name, town, or other personal detail. 
                        Copy
                        and paste the text into the body of your email.<br /><br />

                        Subject Line: Please support CA AB 914: Air pollution: indirect sources.<br /><br />

                        Dear <b><i>[insert Title and Legislator's name]</i></b>,<br /><br />

                        My name is <b><i>[insert your name]</i></b> and I am a constituent of yours in <b><i>[insert your town/city, tract]</i></b>, {tract.county_name}.
                        Based on the Census {tract.tract_label} information available to me, I am writing today to ask you to support,
                        California AB 914: Air pollution: indirect sources authored by Assembly Member Robert Garcia this
                        session. This bill currently sits in the inactive file. I urge you to
                        support this bill and let Assembly Member Robert Garcia
                        know you want him to pass S.2669 as soon as possible.<br /><br />
                        AB 914 addresses a vital human rights issue: individuals deserve a healthy environment.
                        If passed, the bill will enable the State Air Resources Board to achieve air quality standards
                        by regulating indirect sources of toxic air contaminants and protect all California residents by
                        holding polluting groups accountable. In California, more than 20 
                        of our counties have an F for High Ozone Days and Particle Pollution. My county is {tract.county_name} and
                        we have had {tract.cdc_ozone_exceedance_days} High Ozone Days and suffered from {tract.cdc_pm25_person_days} exceedingly high PM2.5 (fine particulate matter) person days.
                        Our overall pollution burden is {tract.PollutionScore}. <b><i>[if you'd like insert why this bill is important to you]</i></b>.<br/><br/>
                        Indirect sources of air pollution shows up everywhere but are hard to track: trucks from warehouses, 
                        powerplants, and factories. These are linked to "diesel death zones" and is strikingly common; as
                        everyone suffers when there is air pollution.
                        Unfortunately, there are little legal protections for folks in CA who experience negative effects
                        based on indirect pollution. We must change this and make California the first state in the
                        nation to control and diminish indirect sources of air pollution, setting the precedent that 
                        indirect sources are held responsible, regulated, and changed for the better.<br /><br />
                        Thank you for your leadership. Can I count on you to convey your support of this bill to
                        Assembly Member Robert Garcia? I look forward to hearing back
                        from you.<br /><br />

                        Sincerely,<br /><br />
                        <b><i>[your name]</i></b><br /><br />
                        <b><i>[your address]</i></b>

                        </p>
                </section>
            </div>
        </div>
    );
}