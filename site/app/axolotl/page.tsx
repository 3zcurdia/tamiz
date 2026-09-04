import type { Metadata } from "next";
import manifest from "../../results/axolotl.json";

export const metadata: Metadata = {
  title: "Tamiz — Axolotl",
  description:
    "Un axolotl morado en patinete: el mismo prompt enviado directo a la API de LM Studio.",
};

interface AxolotlItem {
  model: string;
  harness: string;
  slug: string;
  file: string;
  bytes: number;
  xml_ok: boolean;
  error: string | null;
  latency_ms: number | null;
  generated_at: string | null;
}

const KEEP_MODELS = new Set([
  "google/gemma-4-12b-qat",
  "opencode-go/glm-5.3",
  "opencode-go/qwen3.8-max",
  "qwen/qwen3.6-27b",
  "qwen/qwen3.6-35b-a3b",
  "qwen/qwen3.8-27b",
]);

export default function AxolotlPage() {
  const items = (manifest.items ?? []) as AxolotlItem[];
  const filteredItems = items.filter((i) => KEEP_MODELS.has(i.model));
  const modelCount = new Set(filteredItems.map((i) => i.model)).size;

  return (
    <div className="container">
      <header>
        <h1>Axolotl</h1>
        <p className="subtitle">
          El clásico “pelican riding a bicycle”, versión tamiz: un axolotl morado en patinete.
        </p>
        <p className="goal">
          El mismo prompt se envía directo a la API de LM Studio (sin harness) y cada modelo
          escribe su SVG en <code>site/public/axolotl/</code>. Basta volver a correr{" "}
          <code>scripts/run_axolotl.py</code> y reconstruir el sitio para que aparezca aquí.
        </p>
        <p className="subtitle">
          {filteredItems.length > 0
            ? `${filteredItems.length} SVG de ${modelCount} modelo${modelCount !== 1 ? "s" : ""} · actualizado ${manifest.updated_at}`
            : "Aún no hay SVGs. Ejecuta scripts/run_axolotl.py primero."}
        </p>
      </header>

      <section>
        <h2>Prompt</h2>
        <pre className="code-block">{manifest.prompt}</pre>
      </section>

      <section>
        <h2>Resultados</h2>
        {filteredItems.length === 0 ? (
          <p className="note">
            Sin imágenes todavía: corre <code>.venv/bin/python scripts/run_axolotl.py</code> con
            LM Studio encendido.
          </p>
        ) : (
          <div className="axolotl-grid">
            {filteredItems.map((item) => (
              <figure className="chart-card axolotl-card" key={item.file}>
                <figcaption className="axolotl-head">
                  <span className="axolotl-model">{item.model}</span>
                </figcaption>
                <a href={item.file} target="_blank" rel="noreferrer">
                  <img
                    src={item.file}
                    alt={`Axolotl en patinete por ${item.model} (${item.harness})`}
                    loading="lazy"
                  />
                </a>
                <p className="axolotl-meta">
                  {item.error ? (
                    <span className="axolotl-error">SVG inválido ({item.error})</span>
                  ) : !item.xml_ok ? (
                    <span className="axolotl-error">XML no estricto</span>
                  ) : (
                    <>
                      {(item.bytes / 1024).toFixed(1)} KB
                      {item.latency_ms != null && (
                        <> · {(item.latency_ms / 1000).toFixed(1)} s</>
                      )}
                    </>
                  )}
                </p>
              </figure>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
