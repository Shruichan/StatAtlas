import { MapContainer, TileLayer, GeoJSON, ZoomControl } from "react-leaflet";
import type { GeoJsonObject, Feature, Geometry } from "geojson";
import type { LatLngBoundsExpression } from "leaflet";
import "leaflet/dist/leaflet.css";

import type { FeatureProperties } from "./types";

interface Props {
  data: GeoJsonObject | null;
  selectedGeoid: string | null;
  onSelectFeature: (featureProps: FeatureProperties) => void;
}

const CA_BOUNDS: LatLngBoundsExpression = [
  [32.0, -125.0],
  [42.5, -113.5],
];

export function MapView({ data, selectedGeoid, onSelectFeature }: Props) {
  if (!data) {
    return <div className="map-placeholder">Loading map…</div>;
  }

  return (
    <div className="map-wrapper">
      <MapContainer
        bounds={CA_BOUNDS}
        maxBounds={CA_BOUNDS}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        <GeoJSON
          key={selectedGeoid ?? "geojson-layer"}
          data={data}
          style={(feature) => createFeatureStyle(feature, selectedGeoid)}
          onEachFeature={(feature, layer) => {
            layer.on({
              click: () => {
                if (feature?.properties) {
                  onSelectFeature(feature.properties as FeatureProperties);
                }
              },
            });
            const props = feature?.properties as FeatureProperties | undefined;
            const score = toNumber(props?.quality_of_life_score) ?? 0;
            const label = props?.geoid ?? "Unknown tract";
            layer.bindTooltip(`Tract ${label}<br/>QoL ${score.toFixed(2)}`, {
              sticky: true,
            });
          }}
        />
        <ZoomControl position="topright" />
      </MapContainer>
    </div>
  );
}

function createFeatureStyle(
  feature: Feature<Geometry, FeatureProperties> | undefined,
  selectedGeoid: string | null,
) {
  const props = feature?.properties;
  const geoid = (props?.geoid as string) ?? null;
  const score = toNumber(props?.quality_of_life_score) ?? 0;
  const isSelected = Boolean(selectedGeoid && geoid === selectedGeoid);
  return {
    color: isSelected ? "#0f172a" : "#0ea5e9",
    weight: isSelected ? 2 : 0.75,
    fillColor: scoreToColor(score),
    fillOpacity: isSelected ? 0.55 : 0.35,
  };
}

function scoreToColor(score: number) {
  if (!Number.isFinite(score)) {
    return "#bae6fd";
  }
  if (score >= 0.9) return "#166534";
  if (score >= 0.7) return "#22c55e";
  if (score >= 0.5) return "#84cc16";
  if (score >= 0.3) return "#f97316";
  return "#dc2626";
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

