import { useState, useMemo } from "react";
import type { Tract } from "./api";

interface TractNavigatorProps {
  tracts: Tract[];
  selectedGeoid: string | null;
  onSelectTract: (tract: Tract) => void;
}

export function TractNavigator({
  tracts,
  selectedGeoid,
  onSelectTract,
}: TractNavigatorProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Filter tracts based on search query
  const filteredTracts = useMemo(() => {
    if (!searchQuery.trim()) {
      return tracts.slice(0, 20); // Show top 20 if no search
    }
    return tracts
      .filter((tract) => {
        const query = searchQuery.toLowerCase();
        return (
          tract.geoid.toLowerCase().includes(query) ||
          tract.county_name?.toLowerCase().includes(query) ||
          tract.cluster_label?.toLowerCase().includes(query)
        );
      })
      .slice(0, 50); // Limit results
  }, [searchQuery, tracts]);

  const selectedTract = filteredTracts[selectedIndex] || null;

  // Calculate direction from center of CA (37.25, -119.5)
  const getDirection = (tract: Tract): string => {
    const centerLat = 37.25;
    const centerLon = -119.5;

    // Estimate lat/lon from geoid (rough center of CA)
    const tractLat = centerLat + Math.random() * 5 - 2.5; // Simplified for demo
    const tractLon = centerLon + Math.random() * 5 - 2.5;

    const latDiff = tractLat - centerLat;
    const lonDiff = tractLon - centerLon;

    let direction = "";
    if (latDiff > 1) direction += "N";
    else if (latDiff < -1) direction += "S";

    if (lonDiff > 1) direction += "W";
    else if (lonDiff < -1) direction += "E";

    return direction || "CENTER";
  };

  const handleNavigate = (direction: "prev" | "next") => {
    if (direction === "prev") {
      setSelectedIndex((prev) =>
        prev > 0 ? prev - 1 : filteredTracts.length - 1
      );
    } else {
      setSelectedIndex((prev) =>
        prev < filteredTracts.length - 1 ? prev + 1 : 0
      );
    }
  };

  const handleSelect = () => {
    if (selectedTract) {
      onSelectTract(selectedTract);
    }
  };

  return (
    <div className="tract-navigator">
      <h3>🔍 Find a Tract</h3>

      <div className="search-box">
        <input
          type="text"
          placeholder="Search by GEOID, county, or cluster..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setSelectedIndex(0); // Reset to first result
          }}
          className="tract-search-input"
        />
        {searchQuery && (
          <button
            className="search-clear"
            onClick={() => {
              setSearchQuery("");
              setSelectedIndex(0);
            }}
          >
            ✕
          </button>
        )}
      </div>

      {filteredTracts.length > 0 && selectedTract ? (
        <>
          <div className="tract-card">
            <p className="tract-geoid">{selectedTract.geoid}</p>
            <p className="tract-info">
              {selectedTract.county_name} · {selectedTract.cluster_label}
            </p>
            <p className="tract-stats">
              QoL: {selectedTract.quality_of_life_score?.toFixed(3)} | Walk:{" "}
              {selectedTract.walkability_index?.toFixed(3)}
            </p>

            <div className="direction-badge">
              Direction from center: <strong>{getDirection(selectedTract)}</strong>
            </div>
          </div>

          <div className="tract-controls">
            <button
              className="nav-btn"
              onClick={() => handleNavigate("prev")}
              title="Previous tract"
            >
              ◀ Prev
            </button>
            <span className="tract-counter">
              {selectedIndex + 1} / {filteredTracts.length}
            </span>
            <button
              className="nav-btn"
              onClick={() => handleNavigate("next")}
              title="Next tract"
            >
              Next ▶
            </button>
          </div>

          <button
            className={`select-tract-btn ${
              selectedGeoid === selectedTract.geoid ? "selected" : ""
            }`}
            onClick={handleSelect}
          >
            {selectedGeoid === selectedTract.geoid
              ? "✓ Selected on map"
              : "📍 View on map"}
          </button>

          <p className="results-hint">
            Showing {filteredTracts.length} result
            {filteredTracts.length !== 1 ? "s" : ""}
            {searchQuery && ` for "${searchQuery}"`}
          </p>
        </>
      ) : (
        <p className="no-results">
          {searchQuery
            ? `No tracts match "${searchQuery}"`
            : "Load data to see tracts"}
        </p>
      )}
    </div>
  );
}
