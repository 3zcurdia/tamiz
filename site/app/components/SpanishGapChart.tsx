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
import { COLORS, TOOLTIP_STYLE_PURPLE, shortModel, useIsMobile, getXAxisProps, chartMinWidth, SINGLE_BAR_CATEGORY_GAP } from "./chartTheme";

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
  const isMobile = useIsMobile(640);
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
        model: shortModel(model, isMobile ? 18 : 24),
        delta: Math.round(avg * 10) / 10,
        n_tasks: deltas.length,
      };
    })
    .sort((a, b) => a.delta - b.delta);

  const xProps = getXAxisProps(isMobile);

  return (
    <div className="chart-card">
      <div className="chart-scroll-wrap">
        <div style={{ minWidth: chartMinWidth(data.length), width: "100%" }}>
          <ResponsiveContainer width="100%" height={isMobile ? 280 : 300}>
            <BarChart data={data} margin={{ top: 5, right: 16, left: 0, bottom: 5 }} barCategoryGap={SINGLE_BAR_CATEGORY_GAP}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="model" {...xProps} />
              <YAxis tick={{ fontSize: isMobile ? 10 : 11, fill: COLORS.tick }} stroke={COLORS.axis} width={36} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE_PURPLE.contentStyle}
                labelStyle={TOOLTIP_STYLE_PURPLE.labelStyle}
                itemStyle={TOOLTIP_STYLE_PURPLE.itemStyle}
                cursor={{ fill: "rgba(167, 139, 250, 0.08)" }}
              />
              <ReferenceLine y={0} stroke="#475569" />
              <Bar
                dataKey="delta"
                fill="#a78bfa"
                name="ES − EN"
                radius={[4, 4, 0, 0]}
                maxBarSize={56}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
