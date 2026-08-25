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
}

function mean(scores: number[]) {
  if (scores.length === 0) return null;
  return scores.reduce((a, b) => a + b, 0) / scores.length;
}

export function OverallScoreChart({ records }: { records: ScoreRecord[] }) {
  const isMobile = useIsMobile(640);
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
        model: shortModel(model, isMobile ? 18 : 24),
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

  const xProps = getXAxisProps(isMobile);

  return (
    <div className="chart-card">
      <div className="chart-scroll-wrap">
        <div style={{ minWidth: chartMinWidth(data.length), width: "100%" }}>
          <ResponsiveContainer width="100%" height={isMobile ? 320 : 360}>
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
