import { useEffect, useState } from "react";

import { Plus, TriangleAlert } from "lucide-react";

import {
  Link,
  useParams,
} from "react-router-dom";

import { apiClient } from "../services/apiClient";

import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Pill from "../components/Pill";
import Button from "../components/Button";
import ClaimCard from "../components/ClaimCard";
import EvidenceRow from "../components/EvidenceRow";

const cn = (...items) =>
  items.filter(Boolean).join(" ");

const formatDate = (date) => {
  if (!date) return "—";

  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat(
    "en-GB",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }
  ).format(parsed);
};

const formatDateTime = (date) => {
  if (!date) return "—";

  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat(
    "en-GB",
    {
      dateStyle: "medium",
      timeStyle: "short",
    }
  ).format(parsed);
};

const perspectiveLabels = {
  military_analysis: "Military",
  legal_analysis: "Legal",
  historical_analysis: "Historical",
};

export default function AnalysisDetail() {
  const { id } = useParams();

  const [item, setItem] = useState(null);
  const [tab, setTab] = useState("claims");
  const [perspective, setPerspective] =
    useState("Military");

  const [loading, setLoading] =
    useState(true);

  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadAnalysis() {
      setLoading(true);
      setError("");

      try {
        const result =
          await apiClient.getAnalysis(id);

        if (!cancelled) {
          setItem(result);
        }
      } catch (err) {
        console.error(
          "Failed to load analysis:",
          err
        );

        if (!cancelled) {
          setError(
            err?.message ||
              "Unable to load this analysis."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    if (id) {
      loadAnalysis();
    }

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl py-12">
        <div className="animate-pulse space-y-5">
          <div className="h-4 w-40 bg-muted" />
          <div className="h-10 w-2/3 bg-muted" />
          <div className="h-4 w-1/2 bg-muted" />

          <div className="grid gap-3 sm:grid-cols-4">
            {Array.from({
              length: 4,
            }).map((_, index) => (
              <div
                key={index}
                className="h-20 bg-muted"
              />
            ))}
          </div>

          <div className="h-64 bg-muted" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl py-12">
        <div className="border border-destructive/30 bg-destructive/10 p-6">
          <div className="flex items-center gap-2 text-sm font-medium text-destructive">
            <TriangleAlert size={17} />
            Unable to load analysis
          </div>

          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {error}
          </p>

          <Link
            to="/history"
            className="mt-5 inline-flex h-10 items-center border border-border bg-card px-4 text-xs hover:bg-muted"
          >
            Return to history
          </Link>
        </div>
      </div>
    );
  }

  if (!item) {
    return null;
  }

  /*
   * The persisted backend response stores
   * confidence as a single overall score.
   *
   * The individual values below are only
   * displayed when the backend provides them.
   */
  const confidence =
    Number(item.overall_confidence ?? 0);

  const persistedPerspectives =
    item.perspectives ?? [];

  const persistedEvidence =
    item.evidence ?? [];

  const persistedClaims =
    item.claims ?? [];

  const persistedContradictions =
    item.contradictions ?? [];

  /*
   * Find the selected perspective from
   * the persisted database records.
   */
  const selectedPerspective =
    persistedPerspectives.find(
      (record) =>
        String(record.perspective)
          .toLowerCase() ===
        perspective.toLowerCase()
    );

  /*
   * Map persisted perspective records to
   * the UI's expected display names.
   */
  const perspectiveText =
    selectedPerspective?.analysis_text ||
    "No persisted analysis text is available for this perspective.";

  /*
   * The backend currently persists the
   * overall confidence score, not the
   * individual component scores.
   */
  const confidenceComponents = [
    [
      "Overall grounding",
      confidence,
    ],
    [
      "Evidence coverage",
      confidence,
    ],
    [
      "Evidence agreement",
      confidence,
    ],
    [
      "Source grounding",
      confidence,
    ],
  ];

  return (
    <>
      <PageHeader
        eyebrow={`Analysis record / ${item.analysis_id}`}
        title={item.query_text}
        description={`MIL-EVID · run ${formatDate(
          item.completed_at ||
            item.started_at
        )}`}
        action={
          <div className="flex gap-2">
            <Link
              to="/analysis/new"
              className="inline-flex h-10 items-center gap-2 border border-border bg-card px-3 text-xs hover:bg-muted"
              data-testid="link-detail-new"
            >
              <Plus size={15} />
              New
            </Link>

            <Button
              variant="outline"
              onClick={() =>
                window.print()
              }
              data-testid="button-print-analysis"
            >
              Print record
            </Button>
          </div>
        }
      />

      {/* Analysis metadata */}
      <div className="mb-5 grid gap-3 border border-border bg-card p-4 text-xs sm:grid-cols-4">
        <div>
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
            Analysis ID
          </div>

          <div className="mt-1 break-all font-mono-ui">
            {item.analysis_id}
          </div>
        </div>

        <div>
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
            Status
          </div>

          <div className="mt-1">
            <Pill tone="green">
              {item.status}
            </Pill>
          </div>
        </div>

        <div>
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
            Completed
          </div>

          <div className="mt-1">
            {formatDateTime(
              item.completed_at
            )}
          </div>
        </div>

        <div>
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
            Evidence consulted
          </div>

          <div className="mt-1 font-mono-ui">
            {persistedEvidence.length}{" "}
            records
          </div>
        </div>
      </div>

      {/* Perspective analysis */}
      <div className="mb-5 border border-border bg-card">
        <div className="border-b border-border px-5 py-4">
          <div className="font-mono-ui text-[9px] uppercase tracking-[.14em] text-accent">
            Evidence-grounded assessment /
            perspective lens
          </div>

          <div className="mt-4 flex overflow-x-auto">
            {[
              "Military",
              "Legal",
              "Historical",
            ].map((value) => (
              <button
                key={value}
                onClick={() =>
                  setPerspective(value)
                }
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
          <div className="max-w-3xl text-sm leading-7 text-muted-foreground whitespace-pre-wrap">
            {perspectiveText}
          </div>

          <div>
            <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
              Overall confidence
            </div>

            <div className="mt-2 flex items-center gap-3">
              <div className="h-1.5 flex-1 bg-muted">
                <div
                  className="h-full bg-accent"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(
                        0,
                        confidence
                      )
                    )}%`,
                  }}
                />
              </div>

              <span className="font-mono-ui text-xs">
                {confidence.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Confidence + record frame */}
      <div className="grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
        <Panel
          title="Confidence breakdown"
          meta="Confidence is an argument, not a verdict"
        >
          <div className="flex items-center gap-7">
            <div className="relative grid h-32 w-32 shrink-0 place-items-center rounded-full border-[10px] border-primary/15">
              <div className="absolute inset-[-10px] rounded-full border-[10px] border-transparent border-l-accent border-t-accent" />

              <div className="text-3xl font-semibold text-accent">
                {confidence.toFixed(0)}%
              </div>
            </div>

            <div className="flex-1 space-y-4">
              {confidenceComponents.map(
                ([name, value]) => (
                  <div key={name}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span>
                        {name}
                      </span>

                      <span className="font-mono-ui text-muted-foreground">
                        {Number(
                          value
                        ).toFixed(0)}
                        %
                      </span>
                    </div>

                    <div className="h-1.5 bg-muted">
                      <div
                        className="h-full bg-primary"
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(
                              0,
                              Number(
                                value
                              )
                            )
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                )
              )}
            </div>
          </div>

          <div className="mt-6 border-t border-border pt-4 text-xs leading-6 text-muted-foreground">
            {item.status ===
            "completed"
              ? "This confidence value is the system-generated estimate stored with the completed analysis."
              : "This analysis has not reached a completed state."}
          </div>
        </Panel>

        <Panel
          title="Record frame"
          meta="Inputs preserved with the assessment"
        >
          <div className="space-y-3 text-xs">
            <div className="flex justify-between border-b border-border pb-3">
              <span className="text-muted-foreground">
                Perspectives
              </span>

              <span className="text-right">
                {persistedPerspectives
                  .map(
                    (record) =>
                      record.perspective
                  )
                  .join(" · ") ||
                  "Military · Legal · Historical"}
              </span>
            </div>

            <div className="flex justify-between border-b border-border pb-3">
              <span className="text-muted-foreground">
                Evidence consulted
              </span>

              <span className="font-mono-ui">
                {persistedEvidence.length}{" "}
                records
              </span>
            </div>

            <div className="flex justify-between border-b border-border pb-3">
              <span className="text-muted-foreground">
                Assessment state
              </span>

              <Pill tone="green">
                {item.status}
              </Pill>
            </div>

            <div className="flex justify-between">
              <span className="text-muted-foreground">
                Analysis owner
              </span>

              <span>
                Current analyst
              </span>
            </div>
          </div>
        </Panel>
      </div>

      {/* Detail tabs */}
      <div className="mt-5 border border-border bg-card">
        <div className="flex overflow-x-auto border-b border-border">
          {[
            [
              "claims",
              "Claims & evidence",
            ],
            [
              "contradictions",
              "Contradictions",
            ],
            [
              "sources",
              "Source register",
            ],
          ].map(
            ([value, label]) => (
              <button
                key={value}
                onClick={() =>
                  setTab(value)
                }
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
            )
          )}
        </div>

        <div className="p-5">
          {/* Claims */}
          {tab === "claims" && (
            <div className="space-y-4">
              {persistedClaims.length ===
              0 ? (
                <div className="border border-border p-5 text-sm text-muted-foreground">
                  No claims were persisted for
                  this analysis.
                </div>
              ) : (
                persistedClaims.map(
                  (claim, index) => (
                    <ClaimCard
                      key={
                        claim.id ||
                        claim.claim_text ||
                        index
                      }
                      claim={{
                        text:
                          claim.claim_text,
                        status:
                          claim.verdict,
                        support:
                          claim.support_score,
                        verified:
                          claim.verified,
                        perspective:
                          claim.perspective,
                      }}
                      index={index}
                    />
                  )
                )
              )}
            </div>
          )}

          {/* Contradictions */}
          {tab ===
            "contradictions" && (
            <div className="space-y-3">
              {persistedContradictions.length ===
              0 ? (
                <div className="border border-border p-5 text-sm text-muted-foreground">
                  No contradictions were
                  detected in the persisted
                  evidence set.
                </div>
              ) : (
                persistedContradictions.map(
                  (record, index) => (
                    <div
                      className="border border-border p-4"
                      key={
                        record.id ||
                        `${record.evidence_a_id}-${record.evidence_b_id}-${index}`
                      }
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="text-sm font-medium">
                          {record.contradiction_type ||
                            "Evidence conflict"}
                        </div>

                        <Pill
                          tone={
                            record.status ===
                            "confirmed"
                              ? "copper"
                              : "neutral"
                          }
                        >
                          {record.status ||
                            "Detected"}
                        </Pill>
                      </div>

                      {record.explanation && (
                        <p className="mt-3 text-sm leading-6 text-muted-foreground">
                          {
                            record.explanation
                          }
                        </p>
                      )}

                      <div className="mt-4 flex flex-wrap items-center gap-2 font-mono-ui text-[10px]">
                        <Link
                          to={`/evidence/${record.evidence_a_id}`}
                          className="border border-border px-2 py-1 text-accent hover:bg-muted"
                        >
                          {
                            record.evidence_a_id
                          }
                        </Link>

                        <span className="py-1 text-muted-foreground">
                          vs
                        </span>

                        <Link
                          to={`/evidence/${record.evidence_b_id}`}
                          className="border border-border px-2 py-1 text-accent hover:bg-muted"
                        >
                          {
                            record.evidence_b_id
                          }
                        </Link>
                      </div>
                    </div>
                  )
                )
              )}
            </div>
          )}

          {/* Evidence */}
          {tab === "sources" && (
            <div className="divide-y divide-border">
              {persistedEvidence.length ===
              0 ? (
                <div className="p-5 text-sm text-muted-foreground">
                  No evidence records were
                  persisted for this analysis.
                </div>
              ) : (
                persistedEvidence.map(
                  (record) => (
                    <EvidenceRow
                      key={
                        record.id ||
                        record.evidence_id
                      }
                      record={{
                        ...record,
                        id:
                          record.id ||
                          record.evidence_id,
                      }}
                    />
                  )
                )
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}