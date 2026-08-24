"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface ScoreRecord {
  model: string;
  lang: string;
  score: number;
}

const COLORS = { en: "#22d3ee", es: "#a78bfa" };

function mean(scores: number[]) {
  if (scores.length === 0) return null;
  return scores.reduce((a, b) => a + b, 0) / scores.length;
}

export function OverallScoreChart({ records }: { records: ScoreRecord[] }) {
  const models = [...new Set(records.map((r) => r.model))].sort();

  const data = models
    .map((model) => {
      const en = mean(
        records.filter((r) => r.model === model && r.lang === "en").map((r) => r.score)
      );
      const es = mean(
        records.filter((r) => r.model === model && r.lang === "es").map((r) => r.score)
      );
      return {
        model: shortModel(model),
        fullModel: model,
        en,
        es,
      };
    })
    .filter((d) => d.en !== null || d.es !== null)
    .sort((a, b) => {
      const avgA = ((a.en ?? 0) + (a.es ?? 0)) / 2;
      const avgB = ((b.en ?? 0) + (b.es ?? 0)) / 2;
      return avgA - avgB;
    });

  return (
    <div className="chart-card">
      <ResponsiveContainer width="100%" height={360}>
        <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="model"
            tick={{ fontSize: 12, fill: "#94a3b8" }}
            stroke="#334155"
            interval={0}
            angle={-20}
            textAnchor="end"
            height={60}
          />
          <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#94a3b8" }} stroke="#334155" />
          <Tooltip
            contentStyle={{ backgroundColor: "#0d1420", border: "1px solid #22d3ee", borderRadius: "8px" }}
            labelStyle={{ color: "#22d3ee" }}
            itemStyle={{ color: "#e2e8f0" }}
            cursor={{ fill: "rgba(34, 211, 238, 0.08)" }}
          />
          <Legend />
          <Bar dataKey="en" fill={COLORS.en} name="EN" radius={[4, 4, 0, 0]} />
          <Bar dataKey="es" fill={COLORS.es} name="ES" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function shortModel(model: string) {
  if (model.length > 24) return model.slice(0, 22) + "…";
  return model;
}
