import { ArrowRight, Globe2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { claims, getEvidence } from "../services/mockData";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Pill from "../components/Pill";
import EmptyState from "../components/EmptyState";

const formatDate = (date) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(date));

export default function EvidenceDetail() {
  const { id } = useParams();
  const record = getEvidence(id);

  if (!record) return <EmptyState title="Evidence record not found." text="This record is not indexed in the workspace." />;

  const related = claims.filter((claim) =>
    [...claim.supporting, ...claim.contradicting].includes(record.id)
  );

  return (
    <>
      <PageHeader
        eyebrow={`Evidence record / ${record.id}`}
        title={record.title}
        description={`${record.source} · ${record.type} · captured ${formatDate(record.date)}`}
        action={
          <Link
            to="/evidence"
            className="inline-flex h-10 items-center gap-2 border border-border bg-card px-3 text-xs hover:bg-muted"
            data-testid="link-back-evidence"
          >
            <ArrowRight size={15} className="rotate-180" /> Back to explorer
          </Link>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[1.25fr_.75fr]">
        <Panel title="Record text" meta="Representative preview">
          <div className="border-l-2 border-accent pl-5 text-sm leading-8 text-foreground/85">
            {record.fullText}
          </div>

          <a
            href={record.url}
            target="_blank"
            rel="noreferrer"
            className="mt-7 inline-flex items-center gap-2 text-xs text-accent hover:underline"
            data-testid="link-open-source"
          >
            <Globe2 size={14} /> Open source reference <ArrowRight size={13} />
          </a>
        </Panel>

        <Panel title="Provenance" meta="Source attributes">
          <div className="space-y-4 text-xs">
            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Source</div>
              <div className="mt-1">{record.source}</div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Perspective</div>
              <div className="mt-1">
                <Pill tone="copper">{record.perspective}</Pill>
              </div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Relevance signal
              </div>
              <div className="mt-2 flex items-center gap-3">
                <div className="h-2 flex-1 bg-muted">
                  <div className="h-full bg-accent" style={{ width: `${record.relevance}%` }} />
                </div>
                <span className="font-mono-ui">{record.relevance}%</span>
              </div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Record date
              </div>
              <div className="mt-1">{formatDate(record.date)}</div>
            </div>
          </div>
        </Panel>
      </div>

      <div className="mt-5">
        <Panel title="Relationships" meta="Claims that reference this record">
          {related.length ? (
            related.map((claim) => (
              <div
                className="flex flex-col gap-3 border-b border-border py-4 last:border-0 sm:flex-row sm:items-center sm:justify-between"
                key={claim.text}
              >
                <p className="max-w-2xl text-sm leading-6">{claim.text}</p>
                <Pill tone={claim.supporting.includes(record.id) ? "green" : "red"}>
                  {claim.supporting.includes(record.id)
                    ? "Supports claim"
                    : "Contradicts claim"}
                </Pill>
              </div>
            ))
          ) : (
            <EmptyState
              title="No claim relationships yet."
              text="This record is indexed but has not been cited in a completed assessment."
            />
          )}
        </Panel>
      </div>
    </>
  );
}