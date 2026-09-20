import { useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { evidence } from "../services/mockData";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Button from "../components/Button";
import Pill from "../components/Pill";
import EvidenceRow from "../components/EvidenceRow";
import EmptyState from "../components/EmptyState";

export default function EvidenceExplorer() {
  const [search, setSearch] = useState(
    () => new URLSearchParams(window.location.search).get("search") || ""
  );
  const [perspective, setPerspective] = useState("All");
  const [type, setType] = useState("All");
  const [dateFilter, setDateFilter] = useState("Any date");

  const filtered = evidence.filter(
    (record) =>
      `${record.title} ${record.source} ${record.fullText}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (perspective === "All" || record.perspective === perspective) &&
      (type === "All" || record.type === type) &&
      (dateFilter === "Any date" ||
        (dateFilter === "2025" && record.date.startsWith("2025")) ||
        (dateFilter === "Last 90 days" && record.date >= "2025-01-01") ||
        (dateFilter === "Last 30 days" && record.date >= "2025-02-01"))
  );

  const reset = () => {
    setSearch("");
    setPerspective("All");
    setType("All");
    setDateFilter("Any date");
  };

  return (
    <>
      <PageHeader
        eyebrow="Evidence room / 126,307 records"
        title="Evidence explorer."
        description="Search the material behind the assessments. Relevance is a retrieval signal, not a substitute for reading."
        action={
          <Pill tone="green">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            Index healthy
          </Pill>
        }
      />

      <div className="grid gap-3 md:grid-cols-[1fr_190px_170px_160px_auto]">
        <label className="relative">
          <Search size={16} className="absolute left-3 top-3 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 w-full border border-input bg-card pl-9 pr-3 text-sm"
            placeholder="Search evidence, sources, full text…"
            data-testid="input-evidence-search"
          />
        </label>

        <select
          value={perspective}
          onChange={(e) => setPerspective(e.target.value)}
          className="h-10 border border-input bg-card px-3 text-sm"
          data-testid="select-evidence-perspective"
        >
          <option>All</option>
          {["Operational", "Geopolitical", "Legal", "Historical", "Humanitarian"].map(
            (x) => <option key={x}>{x}</option>
          )}
        </select>

        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="h-10 border border-input bg-card px-3 text-sm"
          data-testid="select-evidence-type"
        >
          <option>All</option>
          {[...new Set(evidence.map((x) => x.type))].map(
            (x) => <option key={x}>{x}</option>
          )}
        </select>

        <select
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
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
          <SlidersHorizontal size={15} /> Clear
        </Button>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_280px]">
        <Panel title={`${filtered.length} records surfaced`} meta="Sorted by relevance">
          <div className="divide-y divide-border">
            {filtered.map((record) => (
              <EvidenceRow record={record} key={record.id} />
            ))}

            {filtered.length === 0 && (
              <EmptyState
                title="No evidence surfaced."
                text="Broaden the query or clear the perspective filters."
                onReset={reset}
              />
            )}
          </div>
        </Panel>

        <Panel title="Archive notes" meta="How to read this room">
          <div className="space-y-5 text-xs leading-6 text-muted-foreground">
            <div>
              <span className="font-medium text-foreground">Relevance</span>
              <br />
              Similarity to the current retrieval terms. Always inspect provenance and date.
            </div>
            <div>
              <span className="font-medium text-foreground">Perspective</span>
              <br />
              The analytical lens assigned during ingestion. One source can inform multiple claims.
            </div>
            <div>
              <span className="font-medium text-foreground">Full text</span>
              <br />
              Preview mode shows representative excerpts; API mode will expose the complete record.
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}