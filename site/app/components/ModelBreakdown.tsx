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
import { COLORS, TOOLTIP_STYLE, useIsMobile, BREAKDOWN_BAR_CATEGORY_GAP, BAR_GAP } from "./chartTheme";

interface ScoreRecord {
  task: string;
  lang: string;
  score: number;
  metric: string;
  n: number;
}

export function ModelBreakdown({
  records,
  tasks,
  taskLabels,
}: {
  records: ScoreRecord[];
  tasks: string[];
  taskLabels: Record<string, string>;
}) {
  const isMobile = useIsMobile(640);
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
    .sort((a, b) => b.avg - a.avg);

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={isMobile ? 180 : 200}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }} barCategoryGap={BREAKDOWN_BAR_CATEGORY_GAP} barGap={BAR_GAP}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
        <XAxis dataKey="task" tick={{ fontSize: isMobile ? 10 : 11, fill: COLORS.tick }} stroke={COLORS.axis} interval={0} />
        <YAxis domain={[0, 100]} tick={{ fontSize: isMobile ? 10 : 11, fill: COLORS.tick }} stroke={COLORS.axis} width={30} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE.contentStyle}
          labelStyle={TOOLTIP_STYLE.labelStyle}
          itemStyle={TOOLTIP_STYLE.itemStyle}
          cursor={{ fill: "rgba(34, 211, 238, 0.08)" }}
        />
        <Bar dataKey="en" fill={COLORS.en} name="EN" radius={[4, 4, 0, 0]} maxBarSize={40} />
        <Bar dataKey="es" fill={COLORS.es} name="ES" radius={[4, 4, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  );
}
