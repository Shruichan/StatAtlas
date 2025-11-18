import { useState, useEffect } from "react";

export interface Statistic {
  label: string;
  value: number | string |null;
  format: (val: number) => string;
  description: string;
  getColor?: (val: number) => "Good" | "Caution" | "Concern";
}

interface StatisticsCarouselProps {
  stats: Statistic[];
}

export function StatisticsCarousel({ stats }: StatisticsCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Handle arrow key navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setCurrentIndex((prev) => (prev - 1 + stats.length) % stats.length);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setCurrentIndex((prev) => (prev + 1) % stats.length);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [stats.length]);

  if (stats.length === 0) {
    return <p>No statistics available.</p>;
  }

  const current = stats[currentIndex];
  const progress = ((currentIndex + 1) / stats.length) * 100;
  const statusColor =
    current.value !== null && current.getColor
      ? current.getColor(current.value)
      : null;

  return (
    <div className="carousel-container">
      <h3>📊 Key Statistics</h3>
      
      <div className="carousel-display">
        <button
          className="carousel-btn prev"
          onClick={() =>
            setCurrentIndex((prev) => (prev - 1 + stats.length) % stats.length)
          }
          title="Previous (← arrow key)"
        >
          ◀
        </button>

        <div className={`carousel-content ${statusColor ? `status-${statusColor}` : ""}`}>
          <p className="carousel-label">{current.label}</p>
          <p className="carousel-value">
            {current.value !== null ? current.format(current.value) : "n/a"}
          </p>
          <p className="carousel-description">{current.description}</p>
        </div>

        <button
          className="carousel-btn next"
          onClick={() =>
            setCurrentIndex((prev) => (prev + 1) % stats.length)
          }
          title="Next (→ arrow key)"
        >
          ▶
        </button>
      </div>

      <div className="carousel-progress">
        <div className={`progress-bar ${statusColor ? `progress-${statusColor}` : ""}`} style={{ width: `${progress}%` }}></div>
      </div>
      
      <p className="carousel-indicator">
        Stat {currentIndex + 1} of {stats.length}
      </p>

      <p className="carousel-hint">💡 Use ← and → arrow keys or click buttons to navigate</p>
    </div>
  );
}
