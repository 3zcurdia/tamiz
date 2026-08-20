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
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="model" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <ReferenceLine y={0} stroke="#666" />
          <Bar
            dataKey="delta"
            fill="#8b5cf6"
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
