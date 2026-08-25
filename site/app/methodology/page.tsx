import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tamiz — Metodología",
  description:
    "Cómo se construye el benchmark Tamiz: datasets EN/ES emparejados, protocolo de evaluación local y métricas",
};

const HIGHLIGHTS = [
  {
    title: "6 tareas · ~8 000 ejemplos",
    desc: "Tareas cotidianas de uso real, sin código ni matemáticas.",
  },
  {
    title: "EN/ES emparejados",
    desc: "El mismo ítem en ambos idiomas vía la clave pair_id.",
  },
  {
    title: "Evaluación 100% local",
    desc: "LM Studio o el puente de Apple, en hardware ≤ 32 GB VRAM.",
  },
  {
    title: "Métricas transparentes",
    desc: "Exact match y chrF++, con tasa de fallo de formato visible.",
  },
];

const TASKS = [
  {
    id: "qa_openbook",
    label: "QA OpenBook",
    what: "Preguntas de opción múltiple sobre ciencia cotidiana (4 opciones).",
    en: "allenai/openbookqa",
    es: "BSC-LT/openbookqa-es",
    rows: "962",
    parallel: "Sí — por id original",
  },
  {
    id: "commonsense_copa",
    label: "COPA",
    what: "Elección de causa/efecto más plausible para una premisa (2 opciones).",
    en: "aps/super_glue (copa)",
    es: "BSC-LT/COPA-es",
    rows: "600",
    parallel:
      "Sí — por (split, id); etiquetas ocultas del test EN recuperadas del release ES",
  },
  {
    id: "categorize",
    label: "Categorize",
    what: "Clasificar una petición hablada en una de 60 intenciones de asistente.",
    en: "AmazonScience/massive (en-US)",
    es: "massive (es-ES)",
    rows: "500",
    parallel: "Sí — enunciados localizados profesionalmente",
  },
  {
    id: "translate",
    label: "Translate",
    what: "Traducción EN → español contra referencias post-editadas por humanos.",
    en: "google/wmt24pp (en→es_MX)",
    es: "misma fuente (referencia)",
    rows: "960",
    parallel: "Sí — español mexicano",
  },
  {
    id: "summarize",
    label: "Summarize",
    what: "Resumir un artículo de la BBC en una o dos frases.",
    en: "csebuetnlp/xlsum (english)",
    es: "xlsum (spanish)",
    rows: "500",
    parallel: "No — misma tarea, artículos distintos por idioma",
  },
  {
    id: "polish",
    label: "Polish",
    what: "Reescritura: gramática, paráfrasis, formalidad, simplificación, claridad, coherencia.",
    en: "grammarly/coedit",
    es: "sin dataset público aún",
    rows: "500 (solo EN)",
    parallel: "— borrador ES en revisión humana",
  },
];

export default function MethodologyPage() {
  return (
    <div className="container">
      <header>
        <h1>Metodología</h1>
        <p className="subtitle">Cómo está construido Tamiz y cómo interpretar sus resultados</p>
        <p className="goal">
          Tamiz evalúa modelos de lenguaje abiertos y locales (que caben en ≤ 32 GB de VRAM)
          en tareas cotidianas con los mismos ítems en inglés y español. La meta es medir la
          brecha real de calidad ES↔EN que enfrenta un usuario hispanohablante al correr
          modelos en su propia máquina.
        </p>
      </header>

      <section>
        <h2>Resumen</h2>
        <div className="highlights-grid">
          {HIGHLIGHTS.map((h) => (
            <div key={h.title} className="chart-card chart-card--small">
              <h3>{h.title}</h3>
              <p className="chart-desc">{h.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>Las tareas</h2>
        <p className="note">
          Cada tarea vive en <code>data/&lt;tarea&gt;.&lt;idioma&gt;.jsonl</code>, un objeto JSON por línea.
        </p>
        <p className="table-hint">← desliza para ver más columnas →</p>
        <div className="table-wrap table-wrap--methodology table-static">
          <table>
            <thead>
              <tr>
                <th>Tarea</th>
                <th>Qué evalúa</th>
                <th>Fuente EN</th>
                <th>Fuente ES</th>
                <th>Ítems/idioma</th>
                <th>Emparejada</th>
              </tr>
            </thead>
            <tbody>
              {TASKS.map((t) => (
                <tr key={t.id}>
                  <td>{t.label}</td>
                  <td>{t.what}</td>
                  <td className="model-cell">{t.en}</td>
                  <td className="model-cell">{t.es}</td>
                  <td className="score-cell">{t.rows}</td>
                  <td>{t.parallel}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note">
          <code>polish</code> cuenta además con un borrador de 500 ítems traducido
          automáticamente (<code>data/polish.es.draft.jsonl</code>) que pasa hoy por revisión humana.
        </p>
      </section>

      <section>
        <h2>Esquema de datos</h2>
        <pre className="code-block">
          {`{
  "task": "categorize",   // qa_openbook | commonsense_copa | categorize | summarize | translate | polish
  "lang": "es",           // en | es
  "id": "31",
  "pair_id": "31",        // misma clave en los archivos .en/.es = mismo ítem de prueba
  "split": "test",
  "instruction": "Clasifica la petición del usuario…",
  "input": "aspira el pasillo",
  "choices": null,        // dict solo en tareas de opción múltiple
  "answer": "iot_cleaning",
  "source": "AmazonScience/massive"
}`}
        </pre>
        <ul className="methodology-list">
          <li>
            <code>pair_id</code> es la clave de unión entre idiomas: permite comparar el mismo
            ítem lado a lado y calcular la brecha ES−EN por modelo.
          </li>
          <li>
            Las instrucciones están escritas nativamente en cada idioma (no son traducidas a
            máquina), así que el propio prompt también pone a prueba el seguimiento de
            instrucciones en español.
          </li>
        </ul>
      </section>

      <section>
        <h2>Emparejamiento y calidad del dataset</h2>
        <ul className="methodology-list">
          <li>
            <strong>Item-paralelas:</strong> QA OpenBook, COPA, Categorize y Translate alinean
            índices por id original, (split,&nbsp;id), localización profesional o referencia compartida.
          </li>
          <li>
            <strong>COPA:</strong> las etiquetas del split de test oculto en inglés se recuperaron
            gracias al release paralelo en español de BSC-LT.
          </li>
          <li>
            <strong>Summarize</strong> es paralelo a nivel de tarea pero no de ítem: XL-Sum no
            ofrece alineación de artículos entre idiomas.
          </li>
          <li>
            <strong>Variedad dialectal:</strong> openbookqa-es y COPA-es son traducciones
            profesionales peninsulares (BSC); solo Translate apunta explícitamente al español
            latinoamericano (es-MX).
          </li>
          <li>
            Los archivos <code>data/*.jsonl</code> están versionados en git y se regeneran de
            forma reproducible (semilla 72); nunca se editan a mano.
          </li>
        </ul>
      </section>

      <section>
        <h2>Protocolo de evaluación</h2>
        <p className="note">
          Lo implementa <code>scripts/run_bench.py</code>; las salidas crudas quedan en{" "}
          <code>results/raw/</code>.
        </p>
        <ul className="methodology-list">
          <li>
            Servidor local expuesto como API compatible con OpenAI: LM Studio
            (<code>:1234/v1</code>) o el puente de Apple Foundation Models (<code>:1976/v1</code>).
          </li>
          <li>
            Cada ítem se envía como un único mensaje de usuario: sin system prompt ni few-shot,
            construyendo el prompt desde la instrucción, opciones e input del dataset.
          </li>
          <li>
            Decoding determinista: <code>temperature=0</code> y <code>seed=72</code> (ambos se
            omiten si el servidor los rechaza) y <code>reasoning_effort=none</code> para suprimir
            el razonamiento extendido donde el servidor lo soporta.
          </li>
          <li>
            Techo de salida por tarea: 512 tokens en QA/COPA/Categorize y 1024 en Translate,
            recortado al contexto realmente cargado. El techo es holgado a propósito: truncar un
            preámbulo de razonamiento vacía la respuesta (gpt-oss-20b pasó de 93.8 a 3.1 en QA con
            un cap de 32 tokens).
          </li>
          <li>
            Ejecución reanudable e idempotente: registra los ids ya completados por
            modelo/tarea/idioma, reintenta errores transitorios y puede auto-cargar el modelo vía
            CLI de LM Studio. Concurrencia opcional.
          </li>
          <li>
            Los modelos evaluados caben en ≤ 32 GB de VRAM, en general cuantizados (q4_k_m,
            mxfp4); la cuantización se detecta automáticamente y se reporta junto a cada resultado.
          </li>
        </ul>
      </section>

      <section>
        <h2>Cómo se puntúa</h2>
        <p className="note">
          Lo implementa <code>scripts/score.py</code> y produce <code>results/scores.json</code>,
          el archivo que consume este sitio.
        </p>
        <ul className="methodology-list">
          <li>
            <strong>QA OpenBook y COPA — exact match</strong> sobre la letra/número elegido. El
            extractor tolera markdown y puntuación sobrante, acepta formatos tipo{" "}
            <em>(B)</em> / <em>B.</em>, prioriza frases explícitas como “the answer is X” o “la
            respuesta es X” y, como último recurso, recurre al texto literal de la opción (solo si
            una única opción coincide).
          </li>
          <li>
            <strong>Categorize — exact match</strong> sobre la etiqueta de intención (60 clases);
            una subcadena cuenta solo si identifica exactamente una clase.
          </li>
          <li>
            <strong>Translate — chrF++</strong> (sacrebleu, caracteres + palabras) contra la
            referencia post-editada; se limpian prefijos como “Traducción:”.
          </li>
          <li>
            Errores de API y respuestas ilegibles cuentan como incorrecto y se publican como{" "}
            <em>tasa de fallo de formato</em>, visible en la tabla de resultados.
          </li>
          <li>
            Cada puntaje se acompaña de latencia media y tokens/s (media y mediana).
          </li>
          <li>
            Summarize y Polish todavía no se puntúan automáticamente: el plan es usar un juez LLM
            fijo y más fuerte que los modelos evaluados (ROUGE se considera débil). Por eso el
            tablero muestra cuatro tareas.
          </li>
        </ul>
      </section>

      <section>
        <h2>Limitaciones y siguientes pasos</h2>
        <ul className="methodology-list">
          <li>
            Polish sigue sin lado ES definitivo: existe el borrador automático en revisión humana;
            los ítems de corrección gramatical se marcan porque la MT suele corregir el error y
            vuelve trivial el ejercicio.
          </li>
          <li>
            Solo Translate usa variedad latinoamericana; QA y COPA usan español peninsular
            profesional.
          </li>
          <li>
            Quedan pendientes tareas del plan original sin dataset público en español:
            needle-in-a-haystack, lluvia de ideas, tutoría, triage de correo/reuniones y análisis
            de hojas de cálculo — requerirán autoría propia.
          </li>
        </ul>
      </section>
    </div>
  );
}
