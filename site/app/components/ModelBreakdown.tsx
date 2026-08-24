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

const COLORS = { en: "#3b82f6", es: "#ef4444" };

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
      };
    });

  if (data.length === 0) return null;

  return (
    <div className="chart-card chart-card--small">
      <h3>{model}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="task" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#6b7280", border: "1px solid #4b5563" }}
            labelStyle={{ color: "#fff" }}
            itemStyle={{ color: "#fff" }}
            cursor={{ fill: "#9ca3af", fillOpacity: 0.3 }}
          />
          <Bar dataKey="en" fill={COLORS.en} name="EN" />
          <Bar dataKey="es" fill={COLORS.es} name="ES" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
