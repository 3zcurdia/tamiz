import scores from "../results/scores.json";
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

const TASK_DESCRIPTIONS: Record<string, string> = {
  qa_openbook:
    "Preguntas de opción múltiple sobre ciencia que requieren conocimiento de sentido común. Mide si el modelo puede razonar sobre hechos cotidianos y elegir la respuesta correcta en cada idioma.",
  commonsense_copa:
    "Elección de alternativas plausibles: selecciona la premisa (causa o efecto) que mejor completa una situación. Evalúa el razonamiento causal cotidiano y la inferencia pragmática.",
  categorize:
    "Clasifica una petición de usuario en lenguaje hablado (intents de asistente de hogar) en una de 60 categorías. Evalúa la comprensión de comandos coloquiales y el reconocimiento de intención, con los mismos enunciados localizados en cada idioma.",
  translate:
    "Traducción de fragmentos de noticias del inglés al español mexicano contra referencias corregidas por humanos. Evalúa fluidez, exactitud y el registro local (latinoamericano) en el idioma de destino.",
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
          Yet Another Trust Me Bro Benchmark: but for spanish speaking audiences
        </p>
        <p className="goal">
          Este proyecto tiene como objetivo mostrar las capacidades de diversos modelos abiertos y locales
          para el procesamiento en tareas cotidianas y destacar la brecha existente entre resultados entre el español
          y el inglés, ayudándote a elegir el mejor modelo para el contexto hispano hablante.
        </p>
        <p className="subtitle">
          {hasData
            ? `${models.length} modelo${models.length !== 1 ? "s" : ""} · generado ${scores.generated_at}`
            : "Aún no hay resultados del benchmark. Ejecuta scripts/run_bench.py y scripts/score.py primero."}
        </p>
      </header>

      {hasData && (
        <>
          <section>
            <h2>EN vs ES por tarea</h2>
            {TASKS.map((task) => {
              const taskRecords = records.filter((r) => r.task === task);
              if (taskRecords.length === 0) return null;
              return (
                <EnVsEsChart
                  key={task}
                  task={task}
                  label={TASK_LABELS[task]}
                  description={TASK_DESCRIPTIONS[task]}
                  records={taskRecords}
                />
              );
            })}
          </section>

          <section>
            <h2>Brecha en español (ES − EN)</h2>
            <p className="note">
              Delta promedio por tarea y por modelo. Negativo = degrada en español.
            </p>
            <SpanishGapChart records={records} tasks={[...TASKS]} />
          </section>

          <section>
            <h2>Desglose por modelo</h2>
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
            <h2>Tabla de resultados</h2>
            <ScoresTable records={records} />
          </section>
        </>
      )}
    </div>
  );
}
