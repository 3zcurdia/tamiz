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
import { COLORS, TOOLTIP_STYLE, shortModel, useIsMobile, getXAxisProps, chartMinWidth, BAR_CATEGORY_GAP, BAR_GAP } from "./chartTheme";

interface ScoreRecord {
  model: string;
  lang: string;
  score: number;
  metric: string;
  n: number;
}

export function EnVsEsChart({
  label,
  description,
  records,
}: {
  task: string;
  label: string;
  description: string;
  records: ScoreRecord[];
}) {
  const isMobile = useIsMobile(640);
  const models = [...new Set(records.map((r) => r.model))].sort();

  const data = models
    .map((model) => {
      const en = records.find((r) => r.model === model && r.lang === "en");
      const es = records.find((r) => r.model === model && r.lang === "es");
      return {
        model: shortModel(model, isMobile ? 18 : 24),
        en: en?.score ?? null,
        es: es?.score ?? null,
        avg: ((en?.score ?? 0) + (es?.score ?? 0)) / 2,
        metric: en?.metric || es?.metric || "",
        n: (en?.n ?? 0) + (es?.n ?? 0),
      };
    })
    .sort((a, b) => a.avg - b.avg);

  const metric = records[0]?.metric ?? "";
  const maxN = Math.max(...records.map((r) => r.n));
  const xProps = getXAxisProps(isMobile);

  return (
    <div className="chart-card">
      <h3>{label}</h3>
      <p className="chart-desc">{description}</p>
      <p className="chart-meta">
        metric: {metric} · n ≤ {maxN}
      </p>
      <div className="chart-scroll-wrap">
        <div style={{ minWidth: chartMinWidth(data.length), width: "100%" }}>
          <ResponsiveContainer width="100%" height={isMobile ? 280 : 300}>
            <BarChart data={data} margin={{ top: 5, right: 16, left: 0, bottom: 5 }} barCategoryGap={BAR_CATEGORY_GAP} barGap={BAR_GAP}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="model" {...xProps} />
              <YAxis domain={[0, 100]} tick={{ fontSize: isMobile ? 10 : 11, fill: COLORS.tick }} stroke={COLORS.axis} width={32} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE.contentStyle}
                labelStyle={TOOLTIP_STYLE.labelStyle}
                itemStyle={TOOLTIP_STYLE.itemStyle}
                cursor={{ fill: "rgba(34, 211, 238, 0.08)" }}
              />
              <Legend wrapperStyle={{ fontSize: isMobile ? 11 : 12, paddingTop: 8 }} />
              <Bar dataKey="en" fill={COLORS.en} name="EN" radius={[4, 4, 0, 0]} maxBarSize={48} />
              <Bar dataKey="es" fill={COLORS.es} name="ES" radius={[4, 4, 0, 0]} maxBarSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
