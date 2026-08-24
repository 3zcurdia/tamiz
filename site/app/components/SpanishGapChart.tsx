"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

interface ScoreRecord {
  model: string;
  task: string;
  lang: string;
  score: number;
}

export function SpanishGapChart({
  records,
  tasks,
}: {
  records: ScoreRecord[];
  tasks: string[];
}) {
  const models = [...new Set(records.map((r) => r.model))].sort();

  const data = models
    .map((model) => {
      const deltas: number[] = [];
      for (const task of tasks) {
        const en = records.find(
          (r) => r.model === model && r.task === task && r.lang === "en"
        );
        const es = records.find(
          (r) => r.model === model && r.task === task && r.lang === "es"
        );
        if (en && es) {
          deltas.push(es.score - en.score);
        }
      }
      const avg = deltas.length > 0
        ? deltas.reduce((a, b) => a + b, 0) / deltas.length
        : 0;
      return {
        model: shortModel(model),
        delta: Math.round(avg * 10) / 10,
        n_tasks: deltas.length,
      };
    })
    .sort((a, b) => a.delta - b.delta);

  return (
    <div className="chart-card">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="model" tick={{ fontSize: 12, fill: "#94a3b8" }} stroke="#334155" />
          <YAxis tick={{ fontSize: 12, fill: "#94a3b8" }} stroke="#334155" />
          <Tooltip
            contentStyle={{ backgroundColor: "#0d1420", border: "1px solid #a78bfa", borderRadius: "8px" }}
            labelStyle={{ color: "#a78bfa" }}
            itemStyle={{ color: "#e2e8f0" }}
            cursor={{ fill: "rgba(167, 139, 250, 0.08)" }}
          />
          <ReferenceLine y={0} stroke="#475569" />
          <Bar
            dataKey="delta"
            fill="#a78bfa"
            name="ES − EN"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function shortModel(model: string) {
  if (model.length > 24) return model.slice(0, 22) + "…";
  return model;
}
