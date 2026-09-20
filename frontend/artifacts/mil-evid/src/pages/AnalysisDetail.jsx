import { useState } from "react";
import { Plus } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { claims, contradictions, evidence, getAnalysis } from "../services/mockData";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Pill from "../components/Pill";
import Button from "../components/Button";
import ClaimCard from "../components/ClaimCard";
import EvidenceRow from "../components/EvidenceRow";

const cn = (...items) => items.filter(Boolean).join(" ");
const formatDate = (date) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(date));

export default function AnalysisDetail() {
  const { id } = useParams();
  const item = getAnalysis(id);
  const [tab, setTab] = useState("claims");
  const [perspective, setPerspective] = useState("Military");

  if (!item) return null;

  const perspectiveNotes = {
    Military:
      "Readiness indicators are elevated around key access routes, but the evidence does not establish a single mobilization intent.",
    Legal:
      "The record points to consultation and proportionality obligations without prescribing one operational response.",
    Historical:
      "Comparable corridor crises show logistics constraints becoming strategically decisive before a formal force-posture shift.",
  };

  const lensConfidence =
    perspective === "Military" ? 82 : perspective === "Legal" ? 71 : 76;

  return (
    <>
      <PageHeader
        eyebrow={`Analysis record / ${item.id}`}
        title={item.query}
        description={`${item.region} · ${item.period} · run ${formatDate(item.timestamp)}`}
        action={
          <div className="flex gap-2">
            <Link
              to="/analysis/new"
              className="inline-flex h-10 items-center gap-2 border border-border bg-card px-3 text-xs hover:bg-muted"
              data-testid="link-detail-new"
            >
              <Plus size={15} /> New
            </Link>
            <Button
              variant="outline"
              onClick={() => window.print()}
              data-testid="button-print-analysis"
            >
              Print record
            </Button>
          </div>
        }
      />

      <div className="mb-5 grid gap-3 border border-border bg-card p-4 text-xs sm:grid-cols-4">
        <div>
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Analysis ID</div>
          <div className="mt-1 font-mono-ui">{item.id}</div>
        </div>
        <div>
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Status</div>
          <div className="mt-1"><Pill tone="green">{item.status}</Pill></div>
        </div>
        <div>
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Timestamp</div>
          <div className="mt-1">
            {new Intl.DateTimeFormat("en-GB", {
              dateStyle: "medium",
              timeStyle: "short",
            }).format(new Date(item.timestamp))}
          </div>
        </div>
        <div>
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Evidence consulted</div>
          <div className="mt-1 font-mono-ui">{item.evidenceCount} records</div>
        </div>
      </div>

      <div className="mb-5 border border-border bg-card">
        <div className="border-b border-border px-5 py-4">
          <div className="font-mono-ui text-[9px] uppercase tracking-[.14em] text-accent">
            Evidence-grounded assessment / perspective lens
          </div>
          <div className="mt-4 flex overflow-x-auto">
            {["Military", "Legal", "Historical"].map((value) => (
              <button
                key={value}
                onClick={() => setPerspective(value)}
                className={cn(
                  "border-b-2 px-5 py-3 text-sm first:pl-0",
                  perspective === value
                    ? "border-accent text-foreground"
                    : "border-transparent text-muted-foreground"
                )}
                data-testid={`button-perspective-${value.toLowerCase()}`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-5 p-5 lg:grid-cols-[1fr_220px]">
          <p className="max-w-3xl text-sm leading-7 text-muted-foreground">
            {perspectiveNotes[perspective]}
          </p>
          <div>
            <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
              Lens confidence
            </div>
            <div className="mt-2 flex items-center gap-3">
              <div className="h-1.5 flex-1 bg-muted">
                <div
                  className="h-full bg-accent"
                  style={{ width: `${lensConfidence}%` }}
                />
              </div>
              <span className="font-mono-ui text-xs">{lensConfidence}%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
        <Panel title="Confidence breakdown" meta="Confidence is an argument, not a verdict">
          <div className="flex items-center gap-7">
            <div className="relative grid h-32 w-32 shrink-0 place-items-center rounded-full border-[10px] border-primary/15">
              <div className="absolute inset-[-10px] rounded-full border-[10px] border-transparent border-l-accent border-t-accent" />
              <div className="text-3xl font-semibold text-accent">{item.confidence}%</div>
            </div>

            <div className="flex-1 space-y-4">
              {[["Relevance",84],["Agreement",77],["Freshness",73],["Source reliability",88]].map(
                ([name, value]) => (
                  <div key={name}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span>{name}</span>
                      <span className="font-mono-ui text-muted-foreground">{value}%</span>
                    </div>
                    <div className="h-1.5 bg-muted">
                      <div className="h-full bg-primary" style={{ width: `${value}%` }} />
                    </div>
                  </div>
                )
              )}
            </div>
          </div>

          <div className="mt-6 border-t border-border pt-4 text-xs leading-6 text-muted-foreground">
            Confidence is held back by a contested interpretation of convoy activity and limited independent verification of intent.
          </div>
        </Panel>

        <Panel title="Record frame" meta="Inputs preserved with the assessment">
          <div className="space-y-3 text-xs">
            <div className="flex justify-between border-b border-border pb-3">
              <span className="text-muted-foreground">Perspectives</span>
              <span className="text-right">{item.perspectives.join(" · ")}</span>
            </div>
            <div className="flex justify-between border-b border-border pb-3">
              <span className="text-muted-foreground">Evidence consulted</span>
              <span className="font-mono-ui">{item.evidenceCount} records</span>
            </div>
            <div className="flex justify-between border-b border-border pb-3">
              <span className="text-muted-foreground">Assessment state</span>
              <Pill tone="green">{item.status}</Pill>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Analyst owner</span>
              <span>Avery Mercer</span>
            </div>
          </div>
        </Panel>
      </div>

      <div className="mt-5 border border-border bg-card">
        <div className="flex overflow-x-auto border-b border-border">
          {[
            ["claims", "Claims & evidence"],
            ["contradictions", "Contradictions"],
            ["sources", "Source register"],
          ].map(([value, label]) => (
            <button
              key={value}
              onClick={() => setTab(value)}
              className={cn(
                "whitespace-nowrap border-b-2 px-5 py-4 text-sm",
                tab === value
                  ? "border-accent text-foreground"
                  : "border-transparent text-muted-foreground"
              )}
              data-testid={`button-detail-tab-${value}`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {tab === "claims" && (
            <div className="space-y-4">
              {claims.map((claim, i) => (
                <ClaimCard claim={claim} index={i} key={claim.text} />
              ))}
            </div>
          )}

          {tab === "contradictions" && (
            <div className="space-y-3">
              {contradictions.map((record, i) => (
                <div className="border border-border p-4" key={record.claim}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="text-sm font-medium">{record.claim}</div>
                    <Pill tone={record.severity === "Moderate" ? "copper" : "neutral"}>
                      {record.severity}
                    </Pill>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">
                    {record.conflict}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2 font-mono-ui text-[10px]">
                    <Link
                      to={`/evidence/${record.evidenceA}`}
                      className="border border-border px-2 py-1 text-accent hover:bg-muted"
                      data-testid={`link-contradiction-a-${i}`}
                    >
                      {record.evidenceA}
                    </Link>
                    <span className="py-1 text-muted-foreground">vs</span>
                    <Link
                      to={`/evidence/${record.evidenceB}`}
                      className="border border-border px-2 py-1 text-accent hover:bg-muted"
                      data-testid={`link-contradiction-b-${i}`}
                    >
                      {record.evidenceB}
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "sources" && (
            <div className="divide-y divide-border">
              {evidence.slice(0, 5).map((record) => (
                <EvidenceRow key={record.id} record={record} />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}