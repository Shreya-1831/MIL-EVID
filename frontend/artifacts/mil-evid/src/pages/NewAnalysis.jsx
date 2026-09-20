import { useState } from "react";
import { Check, Filter, TriangleAlert, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { sources } from "../services/mockData";
import { apiClient } from "../services/apiClient";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Pill from "../components/Pill";
import Button from "../components/Button";

const stages = [
  "Query Processing",
  "Perspective Selection",
  "Evidence Retrieval",
  "Hybrid Retrieval",
  "Evidence Fusion",
  "Reranking",
  "Multi-Perspective Analysis",
  "Claim Verification",
  "Contradiction Detection",
  "Confidence Scoring",
  "Response Generation",
];

const cn = (...items) => items.filter(Boolean).join(" ");

export default function NewAnalysis() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    query: "",
    region: "",
    period: "Last 90 days",
    perspectives: ["Operational", "Geopolitical"],
    sourceFilters: ["SIPRI", "UCDP GED", "ICRC"],
    dynamicEvidence: true,
  });
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState(0);

  const toggle = (p) =>
    setForm((f) => ({
      ...f,
      perspectives: f.perspectives.includes(p)
        ? f.perspectives.filter((x) => x !== p)
        : [...f.perspectives, p],
    }));

  const toggleSource = (source) =>
    setForm((f) => ({
      ...f,
      sourceFilters: f.sourceFilters.includes(source)
        ? f.sourceFilters.filter((x) => x !== source)
        : [...f.sourceFilters, source],
    }));

  const submit = async (e) => {
    e.preventDefault();

    if (form.query.trim().length < 20)
      return setError("Give the question enough detail to support a meaningful retrieval pass.");

    if (!form.perspectives.length)
      return setError("Select at least one analytical perspective.");

    setError("");
    setRunning(true);
    setStage(0);

    const timer = setInterval(() => {
      setStage((s) => {
        if (s >= stages.length - 1) {
          clearInterval(timer);
          return s;
        }
        return s + 1;
      });
    }, 650);

    setTimeout(async () => {
      const result = await apiClient.runAnalysis(form);
      navigate(`/analysis/${result.id}`);
    }, 3500);
  };

  if (running) {
    return (
      <div className="mx-auto max-w-3xl py-12">
        <PageHeader
          eyebrow="Analysis run / local processing"
          title="Building the evidence room."
          description="The mock retrieval layer is walking your question through each perspective. No source is hidden behind the final number."
        />

        <div className="mt-10 border border-border bg-card p-6">
          {stages.map((label, i) => (
            <div
              className={cn(
                "flex items-center gap-4 border-b border-border py-4 last:border-0",
                i > stage && "opacity-35"
              )}
              key={label}
            >
              <span
                className={cn(
                  "grid h-7 w-7 place-items-center border font-mono-ui text-[10px]",
                  i < stage
                    ? "border-primary bg-primary text-primary-foreground"
                    : i === stage
                      ? "border-accent text-accent"
                      : "border-border"
                )}
              >
                {i < stage ? <Check size={14} /> : `0${i + 1}`}
              </span>

              <span className="text-sm">{label}</span>

              {i === stage && (
                <span className="ml-auto font-mono-ui text-[9px] uppercase text-accent">
                  working
                </span>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 h-1 bg-muted">
          <div
            className="h-full bg-accent transition-all duration-500"
            style={{ width: `${((stage + 1) / stages.length) * 100}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Analysis workspace / New"
        title="Frame an analysis."
        description="Ask a question that can be tested from more than one angle. The resulting record will preserve your scope and retrieval choices."
        action={
          <Pill tone="green">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            Mock engine ready
          </Pill>
        }
      />

      <form onSubmit={submit} className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <Panel title="Research question" meta="Required">
          <label className="block">
            <span className="mb-2 block text-xs font-medium">
              What do you need to understand?
            </span>
            <textarea
              value={form.query}
              onChange={(e) => setForm({ ...form, query: e.target.value })}
              className="min-h-40 w-full resize-y border border-input bg-background p-4 text-sm leading-6"
              placeholder="Example: What is the likely operational posture around the Suwałki corridor, and where do public indicators disagree?"
              data-testid="input-analysis-query"
            />
          </label>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label>
              <span className="mb-2 block text-xs font-medium">Region or theatre</span>
              <input
                value={form.region}
                onChange={(e) => setForm({ ...form, region: e.target.value })}
                className="h-11 w-full border border-input bg-background px-3 text-sm"
                placeholder="Baltic region"
                data-testid="input-analysis-region"
              />
            </label>

            <label>
              <span className="mb-2 block text-xs font-medium">Time window</span>
              <select
                value={form.period}
                onChange={(e) => setForm({ ...form, period: e.target.value })}
                className="h-11 w-full border border-input bg-background px-3 text-sm"
                data-testid="select-analysis-period"
              >
                <option>Last 30 days</option>
                <option>Last 90 days</option>
                <option>2024–25</option>
                <option>Historical comparison</option>
              </select>
            </label>
          </div>
        </Panel>

        <Panel title="Perspectives" meta="Choose the voices that should test the question">
          <div className="space-y-2">
            {["Operational", "Geopolitical", "Legal", "Historical", "Humanitarian"].map(
              (perspective) => (
                <label
                  key={perspective}
                  className={cn(
                    "flex cursor-pointer items-center justify-between border p-4 transition-colors",
                    form.perspectives.includes(perspective)
                      ? "border-accent bg-accent/5"
                      : "border-border hover:bg-muted"
                  )}
                >
                  <span className="flex items-center gap-3 text-sm">
                    <input
                      type="checkbox"
                      checked={form.perspectives.includes(perspective)}
                      onChange={() => toggle(perspective)}
                      data-testid={`checkbox-perspective-${perspective.toLowerCase()}`}
                    />
                    <span>{perspective}</span>
                  </span>

                  <span className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                    {perspective === "Operational"
                      ? "force posture"
                      : perspective === "Geopolitical"
                        ? "intent & signal"
                        : perspective === "Legal"
                          ? "obligation"
                          : perspective === "Historical"
                            ? "precedent"
                            : "civilian impact"}
                  </span>
                </label>
              )
            )}
          </div>

          <div className="mt-6 border-t border-border pt-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="text-xs font-medium">Source filters</div>
                <div className="mt-1 text-[11px] text-muted-foreground">
                  Limit the first retrieval pass to selected records.
                </div>
              </div>
              <Filter size={15} className="text-accent" />
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              {sources.map((source) => (
                <label key={source.name} className="flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={form.sourceFilters.includes(source.name)}
                    onChange={() => toggleSource(source.name)}
                    data-testid={`checkbox-source-${source.name.toLowerCase().replaceAll(" ", "-")}`}
                  />
                  {source.name}
                </label>
              ))}
            </div>

            <label className="mt-4 flex items-center justify-between border border-border px-3 py-3 text-xs">
              <span>
                <span className="block font-medium">Dynamic evidence</span>
                <span className="mt-1 block text-muted-foreground">
                  Include fresh retrieval signals when available.
                </span>
              </span>
              <input
                type="checkbox"
                checked={form.dynamicEvidence}
                onChange={(e) => setForm({ ...form, dynamicEvidence: e.target.checked })}
                data-testid="input-dynamic-evidence"
              />
            </label>
          </div>

          {error && (
            <div
              className="mt-5 flex gap-2 border border-destructive/30 bg-destructive/10 px-3 py-3 text-sm text-destructive"
              data-testid="status-analysis-error"
            >
              <TriangleAlert size={16} />
              {error}
            </div>
          )}

          <Button type="submit" className="mt-6 w-full" data-testid="button-run-analysis">
            <Zap size={16} /> Run evidence-grounded analysis
          </Button>

          <p className="mt-3 text-center font-mono-ui text-[9px] uppercase tracking-[.12em] text-muted-foreground">
            Estimated local run time · 4 seconds
          </p>
        </Panel>
      </form>
    </>
  );
}