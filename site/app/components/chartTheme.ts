"use client";

export const COLORS = { en: "#22d3ee", es: "#a78bfa", grid: "#1e293b", tick: "#94a3b8", axis: "#334155" } as const;

export function shortModel(model: string, maxLen = 24) {
  if (model.length > maxLen) return model.slice(0, maxLen - 2) + "…";
  return model;
}

export const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: "#0d1420", border: "1px solid #22d3ee", borderRadius: "8px" } as const,
  labelStyle: { color: "#22d3ee" } as const,
  itemStyle: { color: "#e2e8f0" } as const,
};

export const TOOLTIP_STYLE_PURPLE = {
  contentStyle: { backgroundColor: "#0d1420", border: "1px solid #a78bfa", borderRadius: "8px" } as const,
  labelStyle: { color: "#a78bfa" } as const,
  itemStyle: { color: "#e2e8f0" } as const,
};

import { useEffect, useState } from "react";

export function useIsMobile(breakpoint = 640) {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpoint}px)`);
    const handler = () => setIsMobile(mql.matches);
    handler();
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [breakpoint]);
  return isMobile;
}

export function getXAxisProps(isMobile: boolean) {
  return {
    interval: 0 as const,
    angle: -35 as const,
    textAnchor: "end" as const,
    height: isMobile ? 78 : 68,
    tick: { fontSize: isMobile ? 10 : 11, fill: COLORS.tick },
    stroke: COLORS.axis,
  };
}

export const BAR_CATEGORY_GAP = "14%";
export const BAR_GAP = 3;
export const SINGLE_BAR_CATEGORY_GAP = "20%";
export const BREAKDOWN_BAR_CATEGORY_GAP = "18%";

export function chartMinWidth(itemCount: number, perItem = 72, min = 340) {
  return Math.max(min, itemCount * perItem);
}
