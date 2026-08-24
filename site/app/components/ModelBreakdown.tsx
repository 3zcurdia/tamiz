"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ScoreRecord {
  task: string;
  lang: string;
  score: number;
  metric: string;
  n: number;
}

const COLORS = { en: "#22d3ee", es: "#a78bfa" };

export function ModelBreakdown({
  model,
  records,
  tasks,
  taskLabels,
}: {
  model: string;
  records: ScoreRecord[];
  tasks: string[];
  taskLabels: Record<string, string>;
}) {
  const data = tasks
    .filter((t) => records.some((r) => r.task === t))
    .map((task) => {
      const en = records.find((r) => r.task === task && r.lang === "en");
      const es = records.find((r) => r.task === task && r.lang === "es");
      return {
        task: taskLabels[task] || task,
        en: en?.score ?? null,
        es: es?.score ?? null,
        avg: ((en?.score ?? 0) + (es?.score ?? 0)) / 2,
      };
    })
    .sort((a, b) => a.avg - b.avg);

  if (data.length === 0) return null;

  return (
    <div className="chart-card chart-card--small">
      <h3>{model}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="task" tick={{ fontSize: 11, fill: "#94a3b8" }} stroke="#334155" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#94a3b8" }} stroke="#334155" />
          <Tooltip
            contentStyle={{ backgroundColor: "#0d1420", border: "1px solid #22d3ee", borderRadius: "8px" }}
            labelStyle={{ color: "#22d3ee" }}
            itemStyle={{ color: "#e2e8f0" }}
            cursor={{ fill: "rgba(34, 211, 238, 0.08)" }}
          />
          <Bar dataKey="en" fill={COLORS.en} name="EN" />
          <Bar dataKey="es" fill={COLORS.es} name="ES" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
