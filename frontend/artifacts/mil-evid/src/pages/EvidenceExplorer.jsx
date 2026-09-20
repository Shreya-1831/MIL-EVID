import { useEffect, useMemo, useState } from "react";

import {
  Search,
  SlidersHorizontal,
} from "lucide-react";

import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Button from "../components/Button";
import Pill from "../components/Pill";
import EvidenceRow from "../components/EvidenceRow";
import EmptyState from "../components/EmptyState";

import { apiClient } from "../services/apiClient";

const PERSPECTIVES = [
  "Military",
  "Legal",
  "Historical",
];

function normalizeEvidence(record) {
  return {
    ...record,

    id: record.id,

    title:
      record.title ||
      "Untitled evidence",

    source:
      record.source ||
      "Unknown source",

    type:
      record.source_type ||
      "Unknown",

    perspective:
      record.perspective ||
      "Unknown",

    date:
      record.date ||
      null,

    url:
      record.url ||
      null,

    fullText:
      record.evidence_text ||
      "",
  };
}

export default function EvidenceExplorer() {
  const [search, setSearch] = useState(
    () =>
      new URLSearchParams(
        window.location.search
      ).get("search") || ""
  );

  const [perspective, setPerspective] =
    useState("All");

  const [type, setType] =
    useState("All");

  const [dateFilter, setDateFilter] =
    useState("Any date");

  const [evidence, setEvidence] =
    useState([]);

  const [total, setTotal] =
    useState(0);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadEvidence() {
      try {
        setLoading(true);
        setError("");

        const response =
          await apiClient.listEvidence({
            limit: 500,
            offset: 0,
          });

        if (cancelled) return;

        const records =
          Array.isArray(response?.items)
            ? response.items.map(
                normalizeEvidence
              )
            : [];

        setEvidence(records);
        setTotal(
          Number(response?.total || records.length)
        );
      } catch (loadError) {
        if (cancelled) return;

        console.error(
          "Unable to load evidence:",
          loadError
        );

        setError(
          loadError?.message ||
            "Unable to load evidence."
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadEvidence();

    return () => {
      cancelled = true;
    };
  }, []);

  const types = useMemo(() => {
    return [
      ...new Set(
        evidence
          .map(
            (record) => record.type
          )
          .filter(Boolean)
      ),
    ].sort();
  }, [evidence]);

  const filtered = useMemo(() => {
    const query =
      search.trim().toLowerCase();

    return evidence.filter(
      (record) => {
        const searchableText =
          `${record.title} ${record.source}`
            .toLowerCase();

        const matchesSearch =
          !query ||
          searchableText.includes(query);

        const matchesPerspective =
          perspective === "All" ||
          record.perspective ===
            perspective;

        const matchesType =
          type === "All" ||
          record.type === type;

        let matchesDate = true;

        if (
          dateFilter !== "Any date" &&
          record.date
        ) {
          const recordDate =
            new Date(record.date);

          const now = new Date();

          if (
            dateFilter ===
            "Last 30 days"
          ) {
            const cutoff =
              new Date(now);

            cutoff.setDate(
              cutoff.getDate() - 30
            );

            matchesDate =
              recordDate >= cutoff;
          }

          if (
            dateFilter ===
            "Last 90 days"
          ) {
            const cutoff =
              new Date(now);

            cutoff.setDate(
              cutoff.getDate() - 90
            );

            matchesDate =
              recordDate >= cutoff;
          }

          if (
            dateFilter === "2025"
          ) {
            matchesDate =
              recordDate.getFullYear() ===
              2025;
          }
        }

        return (
          matchesSearch &&
          matchesPerspective &&
          matchesType &&
          matchesDate
        );
      }
    );
  }, [
    evidence,
    search,
    perspective,
    type,
    dateFilter,
  ]);

  const reset = () => {
    setSearch("");
    setPerspective("All");
    setType("All");
    setDateFilter("Any date");
  };

  return (
    <>
      <PageHeader
        eyebrow={`Evidence room / ${total.toLocaleString()} records`}
        title="Evidence explorer."
        description="Search the material behind the assessments. Relevance is a retrieval signal, not a substitute for reading."
        action={
          <Pill tone="green">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            {loading
              ? "Loading index"
              : "Index healthy"}
          </Pill>
        }
      />

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_190px_170px_160px_auto]">
        <label className="relative min-w-0">
          <Search
            size={16}
            className="absolute left-3 top-3 text-muted-foreground"
          />

          <input
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
            className="h-10 w-full border border-input bg-card pl-9 pr-3 text-sm"
            placeholder="Search evidence, sources…"
            data-testid="input-evidence-search"
          />
        </label>

        <select
          value={perspective}
          onChange={(event) =>
            setPerspective(
              event.target.value
            )
          }
          className="h-10 border border-input bg-card px-3 text-sm"
          data-testid="select-evidence-perspective"
        >
          <option>All</option>

          {PERSPECTIVES.map(
            (item) => (
              <option
                key={item}
                value={item}
              >
                {item}
              </option>
            )
          )}
        </select>

        <select
          value={type}
          onChange={(event) =>
            setType(event.target.value)
          }
          className="h-10 border border-input bg-card px-3 text-sm"
          data-testid="select-evidence-type"
        >
          <option>All</option>

          {types.map((item) => (
            <option
              key={item}
              value={item}
            >
              {item}
            </option>
          ))}
        </select>

        <select
          value={dateFilter}
          onChange={(event) =>
            setDateFilter(
              event.target.value
            )
          }
          className="h-10 border border-input bg-card px-3 text-sm"
          data-testid="select-evidence-date"
        >
          <option>Any date</option>
          <option>Last 30 days</option>
          <option>Last 90 days</option>
          <option>2025</option>
        </select>

        <Button
          variant="outline"
          onClick={reset}
          data-testid="button-clear-evidence-filters"
        >
          <SlidersHorizontal size={15} />
          Clear
        </Button>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_280px]">
        <Panel
          title={`${filtered.length} records surfaced`}
          meta={`Showing ${filtered.length} of ${total.toLocaleString()}`}
        >
          {loading ? (
            <EmptyState
              title="Loading evidence..."
              text="Retrieving evidence records from the backend."
            />
          ) : error ? (
            <EmptyState
              title="Unable to load evidence."
              text={error}
            />
          ) : (
            <div className="divide-y divide-border">
              {filtered.map(
                (record) => (
                  <EvidenceRow
                    record={record}
                    key={record.id}
                  />
                )
              )}

              {filtered.length === 0 && (
                <EmptyState
                  title="No evidence surfaced."
                  text="Broaden the query or clear the evidence filters."
                  onReset={reset}
                />
              )}
            </div>
          )}
        </Panel>

        <Panel
          title="Archive notes"
          meta="How to read this room"
        >
          <div className="space-y-5 text-xs leading-6 text-muted-foreground">
            <div>
              <span className="font-medium text-foreground">
                Relevance
              </span>
              <br />
              Similarity to retrieval terms.
              Always inspect provenance and
              date.
            </div>

            <div>
              <span className="font-medium text-foreground">
                Perspective
              </span>
              <br />
              The analytical lens assigned to
              the evidence record.
            </div>

            <div>
              <span className="font-medium text-foreground">
                Full text
              </span>
              <br />
              Open an evidence record to inspect
              its stored evidence text and
              provenance.
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}