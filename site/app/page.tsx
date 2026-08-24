import scores from "../../results/scores.json";
import { EnVsEsChart } from "./components/EnVsEsChart";
import { SpanishGapChart } from "./components/SpanishGapChart";
import { ModelBreakdown } from "./components/ModelBreakdown";
import { ScoresTable } from "./components/ScoresTable";

const TASKS = ["qa_openbook", "commonsense_copa", "categorize", "translate"] as const;
const TASK_LABELS: Record<string, string> = {
  qa_openbook: "QA OpenBook",
  commonsense_copa: "COPA",
  categorize: "Categorize",
  translate: "Translate",
};

interface ScoreRecord {
  provider: string;
  model: string;
  quantization: string;
  task: string;
  lang: string;
  metric: string;
  score: number;
  n: number;
  format_failure_rate: number;
  avg_tokens_per_second: number | null;
  median_tokens_per_second: number | null;
  avg_latency_ms: number | null;
}

export default function Home() {
  const records = scores.records as unknown as ScoreRecord[];
  const hasData = records.length > 0;

  const models = [...new Set(records.map((r) => r.model))].sort();

  return (
    <div className="container">
      <header>
        <h1>Tamiz LLM Benchmark</h1>
        <p className="subtitle">
          {hasData
            ? `${models.length} model${models.length !== 1 ? "s" : ""} · generated ${scores.generated_at}`
            : "No benchmark results yet. Run scripts/run_bench.py and scripts/score.py first."}
        </p>
      </header>

      {hasData && (
        <>
          <section>
            <h2>EN vs ES per Task</h2>
            {TASKS.map((task) => {
              const taskRecords = records.filter((r) => r.task === task);
              if (taskRecords.length === 0) return null;
              return (
                <EnVsEsChart
                  key={task}
                  task={task}
                  label={TASK_LABELS[task]}
                  records={taskRecords}
                />
              );
            })}
          </section>

          <section>
            <h2>Spanish Gap (ES − EN)</h2>
            <p className="note">
              Average per-task delta per model. Negative = degrades in Spanish.
            </p>
            <SpanishGapChart records={records} tasks={[...TASKS]} />
          </section>

          <section>
            <h2>Per-Model Breakdown</h2>
            {models.map((model) => (
              <ModelBreakdown
                key={model}
                model={model}
                records={records.filter((r) => r.model === model)}
                tasks={[...TASKS]}
                taskLabels={TASK_LABELS}
              />
            ))}
          </section>

          <section>
            <h2>Results Table</h2>
            <ScoresTable records={records} />
          </section>
        </>
      )}
    </div>
  );
}
