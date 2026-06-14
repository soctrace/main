import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ArrowUpRight, Bot, Sparkles, UserRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { useDashboardStore } from "@/store/useDashboardStore";
import { useAskSocTrace } from "../hooks/useAskSocTrace";
import type { AskSocTraceResponse, AskSocTraceTable } from "../types";

function ResultTable({ table }: { table: AskSocTraceTable }) {
  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-white/[0.07]">
      <p className="bg-white/[0.035] px-3 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.1em] text-slate-400">{table.title}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="border-y border-white/[0.06] bg-[#0c1422]/70 text-[0.62rem] uppercase tracking-[0.08em] text-slate-500">
            <tr>{table.columns.map((column) => <th key={column} className="px-3 py-2 font-semibold">{column}</th>)}</tr>
          </thead>
          <tbody>{table.rows.map((row, rowIndex) => (
            <tr key={`${row.join("-")}-${rowIndex}`} className="border-b border-white/[0.045] last:border-0">
              {row.map((cell, cellIndex) => <td key={`${cell}-${cellIndex}`} className="px-3 py-2 tabular-nums">{cell}</td>)}
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

function splitAnswer(answer: string) {
  return answer
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);
}

function useParagraphReveal(answer: string, enabled: boolean) {
  const blocks = useMemo(() => splitAnswer(answer), [answer]);
  const [visibleCount, setVisibleCount] = useState(enabled ? 0 : blocks.length);

  useEffect(() => {
    if (!enabled) {
      setVisibleCount(blocks.length);
      return;
    }
    setVisibleCount(0);
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setVisibleCount(Math.min(index, blocks.length));
      if (index >= blocks.length) {
        window.clearInterval(timer);
      }
    }, 140);
    return () => window.clearInterval(timer);
  }, [answer, blocks.length, enabled]);

  return {
    visibleBlocks: enabled ? blocks.slice(0, visibleCount) : blocks,
    isRevealing: enabled && visibleCount < blocks.length,
  };
}

function AnswerText({ answer, streaming }: { answer: string; streaming: boolean }) {
  const { visibleBlocks, isRevealing } = useParagraphReveal(answer, streaming);
  const sectionHeadings = new Set([
    "Resultados principales",
    "Indicadores principales",
    "Qué significa",
    "Como se ha calculado",
    "Cómo se ha calculado",
    "Interpretación útil",
    "Lectura estratégica",
    "Cautela metodológica",
    "Preguntas relacionadas",
    "Conclusión",
  ]);
  return (
    <div className="max-w-[68ch] space-y-3 text-sm leading-6 text-slate-200">
      {visibleBlocks.map((block, blockIndex) => {
        const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
        const isBulletList = lines.every((line) => line.startsWith("•"));
        if (isBulletList) {
          return (
            <ul key={`${block}-${blockIndex}`} className="space-y-1.5">
              {lines.map((line) => (
                <li key={line} className="flex gap-2">
                  <span className="text-cyan-200">•</span>
                  <span>{line.replace(/^•\s*/, "")}</span>
                </li>
              ))}
            </ul>
          );
        }
        if (lines.length > 1 && lines.slice(1).every((line) => line.startsWith("•"))) {
          return (
            <div key={`${block}-${blockIndex}`} className="space-y-2">
              <p className="font-semibold text-slate-100">{lines[0]}</p>
              <ul className="space-y-1.5">
                {lines.slice(1).map((line) => (
                  <li key={line} className="flex gap-2">
                    <span className="text-cyan-200">•</span>
                    <span>{line.replace(/^•\s*/, "")}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        }
        if (sectionHeadings.has(block)) {
          return <p key={`${block}-${blockIndex}`} className="pt-1 text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-cyan-100">{block}</p>;
        }
        return <p key={`${block}-${blockIndex}`} className={block.startsWith("Conclusión") ? "font-semibold text-slate-100" : ""}>{block}</p>;
      })}
      {isRevealing ? <span className="inline-block h-4 w-1 animate-pulse rounded-full bg-cyan-200 align-[-0.15rem]" aria-hidden="true" /> : null}
    </div>
  );
}

function AssistantResponse({
  response,
  onSuggestedQuestion,
  disabled,
  showSuggested = true,
}: {
  response: AskSocTraceResponse;
  onSuggestedQuestion: (prompt: string) => void;
  disabled?: boolean;
  showSuggested?: boolean;
}) {
  const caveats = response.caveats ?? [];
  const entities = response.entities ?? [];
  const suggestedQuestions = response.suggested_follow_ups ?? [];
  const ctas = response.ctas ?? [];
  const isDetailed = response.mode === "detailed" || response.mode === "debug";
  const isDebug = import.meta.env.DEV && response.mode === "debug";

  return (
    <div className="rounded-2xl border border-cyan-200/10 bg-cyan-200/[0.045] px-4 py-3">
      <AnswerText answer={response.answer} streaming={showSuggested && !disabled} />
      {entities.length ? (
        <ul className="mt-3 space-y-1.5 text-sm leading-5 text-slate-200">
          {entities.map((entity, index) => {
            const detail = entity.description ?? entity.value;
            return (
              <li key={`${entity.name}-${index}`} className="flex gap-2">
                <span className="mt-[0.45rem] h-1 w-1 shrink-0 rounded-full bg-cyan-200/70" />
                <span>
                  <span>{entity.name}</span>
                  {detail ? <span className="text-slate-400"> — {detail}</span> : null}
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}
      {response.mode === "simple" && response.short_caveat ? (
        <p className="mt-2 text-xs leading-5 text-slate-400">{response.short_caveat}</p>
      ) : null}
      {showSuggested && ctas.length ? (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-white/[0.06] pt-3">
          {ctas.map((cta) => (
            <button
              key={`${cta.label}-${cta.question}`}
              type="button"
              disabled={disabled}
              onClick={() => onSuggestedQuestion(cta.question)}
              className="rounded-full border border-cyan-200/20 bg-cyan-200/[0.08] px-3 py-1.5 text-left text-[0.72rem] font-semibold leading-4 text-cyan-50 transition hover:border-cyan-200/40 hover:bg-cyan-200/[0.13] disabled:cursor-not-allowed disabled:opacity-45"
            >
              {cta.label}
            </button>
          ))}
        </div>
      ) : null}
      {showSuggested && suggestedQuestions.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestedQuestions.map((question) => (
            <button
              key={question}
              type="button"
              disabled={disabled}
              onClick={() => onSuggestedQuestion(question)}
              aria-label={`Preguntar: ${question}`}
              className="rounded-full border border-cyan-200/15 bg-cyan-200/[0.06] px-3 py-1.5 text-left text-[0.72rem] font-medium leading-4 text-cyan-100 transition hover:border-cyan-200/35 hover:bg-cyan-200/[0.1] disabled:cursor-not-allowed disabled:opacity-45"
            >
              {question}
            </button>
          ))}
        </div>
      ) : null}

      {isDetailed && response.methodology ? (
        <div className="mt-4 rounded-xl border border-white/[0.07] bg-white/[0.025] px-3 py-2.5">
          <p className="text-[0.64rem] font-semibold uppercase tracking-[0.12em] text-slate-500">Metodologia</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">{response.methodology}</p>
        </div>
      ) : null}
      {isDetailed && response.table ? <ResultTable table={response.table} /> : null}
      {isDetailed && caveats.length ? (
        <div className="mt-4">
          <p className="text-[0.64rem] font-semibold uppercase tracking-[0.12em] text-slate-500">Cautelas</p>
          {caveats.map((note) => <p key={note} className="mt-1 text-[0.7rem] leading-5 text-slate-500">· {note}</p>)}
        </div>
      ) : null}
      {isDetailed && response.data_origin.length ? (
        <p className="mt-3 border-t border-white/[0.06] pt-3 text-[0.68rem] leading-5 text-slate-500">
          Fuentes internas disponibles bajo petición técnica.
        </p>
      ) : null}
      {isDebug ? (
        <pre className="mt-4 max-h-80 overflow-auto rounded-xl border border-white/[0.07] bg-black/30 p-3 text-[0.68rem] leading-5 text-slate-400">
          {JSON.stringify(response.debug ?? {}, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

export function AskSocTracePanel() {
  const aiInput = useDashboardStore((state) => state.aiInput);
  const setAiInput = useDashboardStore((state) => state.setAiInput);
  const queuedAskPrompt = useDashboardStore((state) => state.queuedAskPrompt);
  const clearQueuedAskPrompt = useDashboardStore((state) => state.clearQueuedAskPrompt);
  const setRightPanelMode = useDashboardStore((state) => state.setRightPanelMode);
  const setAskChartResponse = useDashboardStore((state) => state.setAskChartResponse);
  const municipalityId = useDashboardStore((state) => state.selectedMunicipalityId);
  const currentCollection = useDashboardStore((state) => state.sectionCollection);
  const activeLayer = useDashboardStore((state) => state.activeLayer);
  const filters = useDashboardStore((state) => state.filters);
  const selectedSectionId = useDashboardStore((state) => state.selectedSectionId);
  const activeYear = useMemo(() => {
    const year =
      activeLayer === "ageStructure"
        ? filters.ageStructureYear
        : activeLayer === "incomeLevel"
          ? filters.incomeYear
          : activeLayer === "electoralBehavior"
            ? filters.year
            : activeLayer === "population"
              ? filters.populationYear
              : filters.year;
    const numericYear = Number(year);
    return Number.isFinite(numericYear) ? numericYear : null;
  }, [activeLayer, filters.ageStructureYear, filters.incomeYear, filters.populationYear, filters.year]);
  const context = useMemo(
    () => ({ municipalityId, currentCollection, activeLayer, activeYear, selectedSectionId }),
    [municipalityId, currentCollection, activeLayer, activeYear, selectedSectionId],
  );
  const { messages, isThinking, ask } = useAskSocTrace(context);
  const scrollRef = useRef<HTMLDivElement>(null);
  const latestAssistantId = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant" && !message.loading)?.id,
    [messages],
  );

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    if (!queuedAskPrompt || isThinking) return;
    const prompt = queuedAskPrompt;
    clearQueuedAskPrompt();
    setAiInput("");
    void ask(prompt).then((response) => {
      if (response) {
        setAskChartResponse(response);
      } else {
        setRightPanelMode("askTests");
      }
    });
  }, [ask, clearQueuedAskPrompt, isThinking, queuedAskPrompt, setAiInput, setAskChartResponse, setRightPanelMode]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const question = aiInput.trim();
    setAiInput("");
    void ask(question).then((response) => {
      if (response?.chart_spec && response.chart_spec.kind !== "none") {
        setAskChartResponse(response);
      }
    });
  };

  const askSuggestedQuestion = (prompt: string) => {
    if (isThinking) return;
    setAiInput("");
    void ask(prompt).then((response) => {
      if (response?.chart_spec && response.chart_spec.kind !== "none") {
        setAskChartResponse(response);
      }
    });
  };

  return (
    <Panel id="ask-soctrace" tone="elevated" className="relative overflow-hidden p-4">
      <div className="absolute inset-x-0 top-0 h-24 bg-[linear-gradient(180deg,rgba(37,99,235,0.16),transparent)]" />
      <div className="relative flex flex-col">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/20 bg-[radial-gradient(circle_at_30%_30%,rgba(96,165,250,0.35),rgba(17,24,39,0.8))] text-cyan-200 shadow-[0_0_30px_rgba(56,189,248,0.18)]">
              <Bot className="h-4 w-4" />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-base font-semibold text-white">Pregunta a soctrace</p>
              <span className="rounded-full border border-violet-300/16 bg-violet-400/10 px-2 py-0.5 text-[0.6rem] font-semibold uppercase tracking-[0.16em] text-violet-200">Beta</span>
              <p className="max-w-[34rem] text-[0.66rem] font-normal leading-4 text-slate-500">
                El agente inteligente soctrace está en pruebas. Consulta la lista de tests predefinidos en entrenamiento
              </p>
              <button
                type="button"
                onClick={() => setRightPanelMode("askTests")}
                className="rounded-full border border-cyan-200/15 bg-cyan-200/[0.07] px-2.5 py-1 text-[0.64rem] font-semibold text-cyan-100 transition hover:border-cyan-200/30 hover:bg-cyan-200/[0.12]"
              >
                Lista de tests
              </button>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-[0.68rem] text-slate-500">
            <Sparkles className="h-3.5 w-3.5 text-cyan-300" />
            Analista IA
          </div>
        </div>

        <div ref={scrollRef} className="mt-4 max-h-[440px] min-h-[250px] space-y-3 overflow-y-auto rounded-2xl border border-white/[0.07] bg-[#080f1c]/72 p-3">
          {messages.length === 0 ? (
            <div className="flex min-h-[220px] items-center justify-center px-4 text-center">
              <p className="max-w-xl text-sm leading-6 text-slate-500">Pregunta por datos observados, comparaciones electorales, metodología, escenarios forecast o el reparto municipal D'Hondt.</p>
            </div>
          ) : messages.map((message) => (
            <div key={message.id} className={`flex gap-2 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              {message.role === "assistant" ? <Bot className="mt-2 h-4 w-4 shrink-0 text-cyan-300/75" /> : null}
              {message.role === "user" ? (
                <div className="max-w-[82%] rounded-2xl border border-white/[0.08] bg-white/[0.055] px-4 py-3 text-sm text-slate-200">{message.content}</div>
              ) : (
                <div className="max-w-[92%] flex-1">
                  <AssistantResponse
                    response={message.response}
                    onSuggestedQuestion={askSuggestedQuestion}
                    disabled={isThinking || message.loading}
                    showSuggested={message.id === latestAssistantId}
                  />
                  {message.error ? <p className="mt-2 text-xs text-rose-200/80">{message.error}</p> : null}
                </div>
              )}
              {message.role === "user" ? <UserRound className="mt-2 h-4 w-4 shrink-0 text-slate-500" /> : null}
            </div>
          ))}
          {isThinking ? <p role="status" className="px-6 py-2 text-xs text-cyan-100/55">soctrace está analizando los datos...</p> : null}
        </div>

        <form className="mt-3 flex gap-3" onSubmit={submit}>
          <label className="flex h-14 flex-1 items-center gap-3 rounded-2xl border border-white/10 bg-[#111827]/88 px-4">
            <input id="ask-soctrace-input" type="text" value={aiInput} onChange={(event) => setAiInput(event.target.value)} placeholder="Pregunta sobre Mijas..." className="w-full border-none bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500" />
          </label>
          <Button type="submit" variant="primary" className="h-14 px-5" disabled={!aiInput.trim() || isThinking} aria-label="Enviar pregunta">
            <ArrowUpRight className="h-4 w-4" />
          </Button>
        </form>
        <p className="mt-2 text-center text-[0.62rem] leading-4 text-slate-600">
          soctrace puede cometer errores. Verifica la información importante con el análisis directo de variables del panel.
        </p>
      </div>
    </Panel>
  );
}
