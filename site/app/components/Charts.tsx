"use client";

import dynamic from "next/dynamic";

function Skeleton({ variant }: { variant: "overall" | "task" | "speed" | "breakdown" }) {
  return <div className={`chart-skeleton chart-skeleton--${variant}`} aria-hidden="true" />;
}

export const OverallScoreChart = dynamic(
  () => import("./OverallScoreChart").then((m) => m.OverallScoreChart),
  {
    ssr: false,
    loading: () => (
      <div className="chart-card">
        <div className="chart-scroll-wrap">
          <Skeleton variant="overall" />
        </div>
      </div>
    ),
  }
);

export const EnVsEsChart = dynamic(
  () => import("./EnVsEsChart").then((m) => m.EnVsEsChart),
  {
    ssr: false,
    loading: () => (
      <div className="chart-scroll-wrap">
        <Skeleton variant="task" />
      </div>
    ),
  }
);

export const SpanishGapChart = dynamic(
  () => import("./SpanishGapChart").then((m) => m.SpanishGapChart),
  {
    ssr: false,
    loading: () => (
      <div className="chart-card">
        <div className="chart-scroll-wrap">
          <Skeleton variant="task" />
        </div>
      </div>
    ),
  }
);

export const SpeedVsAccuracyChart = dynamic(
  () => import("./SpeedVsAccuracyChart").then((m) => m.SpeedVsAccuracyChart),
  {
    ssr: false,
    loading: () => (
      <div className="chart-card">
        <div className="chart-scroll-wrap chart-scroll-wrap--no-min">
          <Skeleton variant="speed" />
        </div>
      </div>
    ),
  }
);

export const ModelBreakdown = dynamic(
  () => import("./ModelBreakdown").then((m) => m.ModelBreakdown),
  {
    ssr: false,
    loading: () => <Skeleton variant="breakdown" />,
  }
);
