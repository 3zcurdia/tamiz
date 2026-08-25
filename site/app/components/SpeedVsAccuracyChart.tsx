"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { COLORS, useIsMobile } from "./chartTheme";

interface ScoreRecord {
  model: string;
  lang: string;
  score: number;
  avg_tokens_per_second: number | null;
}

interface Point {
  model: string;
  lang: "en" | "es";
  tps: number;
  score: number;
}

function buildSeries(records: ScoreRecord[], lang: "en" | "es"): Point[] {
  const models = [...new Set(records.map((r) => r.model))].sort();
  return models
    .map((model) => {
      const rows = records.filter(
        (r) => r.model === model && r.lang === lang && r.avg_tokens_per_second != null
      );
      if (rows.length === 0) return null;
      const tps =
        rows.reduce((a, r) => a + (r.avg_tokens_per_second as number), 0) / rows.length;
      const score = rows.reduce((a, r) => a + r.score, 0) / rows.length;
      return { model, lang, tps: Math.round(tps * 10) / 10, score: Math.round(score * 10) / 10 };
    })
    .filter((p): p is Point => p !== null);
}

export function SpeedVsAccuracyChart({ records }: { records: ScoreRecord[] }) {
  const isMobile = useIsMobile(640);
  const enData = buildSeries(records, "en");
  const esData = buildSeries(records, "es");

  return (
    <div className="chart-card">
      <div className="chart-scroll-wrap chart-scroll-wrap--no-min">
        <ResponsiveContainer width="100%" height={isMobile ? 300 : 360}>
          <ScatterChart margin={{ top: 5, right: isMobile ? 12 : 30, left: isMobile ? 0 : 10, bottom: isMobile ? 22 : 15 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              type="number"
              dataKey="tps"
              name="tok/s"
              tick={{ fontSize: isMobile ? 10 : 12, fill: "#94a3b8" }}
              stroke="#334155"
              label={{
                value: isMobile ? "tok/s" : "tokens/segundo (promedio)",
                position: "insideBottom",
                offset: isMobile ? -12 : -10,
                fill: "#94a3b8",
                fontSize: isMobile ? 11 : 12,
              }}
            />
            <YAxis
              type="number"
              dataKey="score"
              domain={[0, 100]}
              tick={{ fontSize: isMobile ? 10 : 12, fill: "#94a3b8" }}
              stroke="#334155"
              width={isMobile ? 32 : 42}
              label={{
                value: isMobile ? "Puntaje" : "Puntaje agregado",
                angle: -90,
                position: "insideLeft",
                fill: "#94a3b8",
                fontSize: isMobile ? 11 : 12,
              }}
            />
            <Tooltip content={<SpeedAccuracyTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "#334155" }} />
            <Legend wrapperStyle={{ fontSize: isMobile ? 11 : 12 }} />
            <Scatter name="EN" data={enData} fill={COLORS.en} />
            <Scatter name="ES" data={esData} fill={COLORS.es} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function SpeedAccuracyTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: Point }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload;
  return (
    <div
      style={{
        backgroundColor: "#0d1420",
        border: `1px solid ${point.lang === "en" ? COLORS.en : COLORS.es}`,
        borderRadius: "8px",
        padding: "8px 12px",
        color: "#e2e8f0",
      }}
    >
      <p style={{ fontWeight: 600 }}>
        {point.model} ({point.lang.toUpperCase()})
      </p>
      <p>{point.tps.toFixed(1)} tok/s</p>
      <p>puntaje: {point.score.toFixed(1)}</p>
    </div>
  );
}
