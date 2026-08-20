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
  metric: string;
  n: number;
}

const COLORS = { en: "#3b82f6", es: "#ef4444" };

export function EnVsEsChart({
  task,
  label,
  records,
}: {
  task: string;
  label: string;
  records: ScoreRecord[];
}) {
  const models = [...new Set(records.map((r) => r.model))].sort();

  const data = models.map((model) => {
    const en = records.find((r) => r.model === model && r.lang === "en");
    const es = records.find((r) => r.model === model && r.lang === "es");
    return {
      model: shortModel(model),
      en: en?.score ?? null,
      es: es?.score ?? null,
      metric: en?.metric || es?.metric || "",
      n: (en?.n ?? 0) + (es?.n ?? 0),
    };
  });

  const metric = records[0]?.metric ?? "";
  const maxN = Math.max(...records.map((r) => r.n));

  return (
    <div className="chart-card">
      <h3>{label}</h3>
      <p className="chart-meta">
        metric: {metric} · n ≤ {maxN}
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="model" tick={{ fontSize: 12 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="en" fill={COLORS.en} name="EN" />
          <Bar dataKey="es" fill={COLORS.es} name="ES" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function shortModel(model: string) {
  if (model.length > 24) return model.slice(0, 22) + "…";
  return model;
}
