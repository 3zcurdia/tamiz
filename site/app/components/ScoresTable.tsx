"use client";

import { useState } from "react";

interface ScoreRecord {
  provider: string;
  model: string;
  task: string;
  lang: string;
  metric: string;
  score: number;
  n: number;
  format_failure_rate: number;
}

type SortKey = keyof ScoreRecord;

const TASK_LABELS: Record<string, string> = {
  qa_openbook: "QA OpenBook",
  commonsense_copa: "COPA",
  categorize: "Categorize",
  translate: "Translate",
};

export function ScoresTable({ records }: { records: ScoreRecord[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = [...records].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (typeof av === "number" && typeof bv === "number") {
      return sortDir === "asc" ? av - bv : bv - av;
    }
    const cmp = String(av).localeCompare(String(bv));
    return sortDir === "asc" ? cmp : -cmp;
  });

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  function arrow(key: SortKey) {
    if (sortKey !== key) return "";
    return sortDir === "asc" ? " ▲" : " ▼";
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th onClick={() => handleSort("model")}>Model{arrow("model")}</th>
            <th onClick={() => handleSort("task")}>Task{arrow("task")}</th>
            <th onClick={() => handleSort("lang")}>Lang{arrow("lang")}</th>
            <th onClick={() => handleSort("metric")}>Metric{arrow("metric")}</th>
            <th onClick={() => handleSort("score")}>Score{arrow("score")}</th>
            <th onClick={() => handleSort("n")}>n{arrow("n")}</th>
            <th onClick={() => handleSort("format_failure_rate")}>
              FF%{arrow("format_failure_rate")}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr key={i}>
              <td className="model-cell">{r.model}</td>
              <td>{TASK_LABELS[r.task] || r.task}</td>
              <td>{r.lang.toUpperCase()}</td>
              <td>{r.metric}</td>
              <td className="score-cell">{r.score.toFixed(1)}</td>
              <td>{r.n}</td>
              <td>{r.format_failure_rate.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
