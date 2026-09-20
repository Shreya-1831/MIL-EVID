import { useState } from "react";
import { Filter, Plus, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { analyses as initialAnalyses } from "../services/mockData";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import AnalysisRow from "../components/AnalysisRow";
import EmptyState from "../components/EmptyState";
import ConfirmDialog from "../components/ConfirmDialog";

export default function History() {
  const [items, setItems] = useState(initialAnalyses);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [sort, setSort] = useState("Newest");
  const [deleteId, setDeleteId] = useState(null);

  const filtered = items
    .filter(
      (item) =>
        `${item.query} ${item.region} ${item.id}`
          .toLowerCase()
          .includes(search.toLowerCase()) &&
        (filter === "All" || item.status === filter)
    )
    .sort((a, b) =>
      sort === "Newest"
        ? new Date(b.timestamp) - new Date(a.timestamp)
        : sort === "Confidence"
          ? b.confidence - a.confidence
          : a.query.localeCompare(b.query)
    );

  return (
    <>
      <PageHeader
        eyebrow="Research archive"
        title="Analysis history."
        description="Every question, scope, and outcome in one searchable register."
        action={
          <Link
            to="/analysis/new"
            className="inline-flex h-10 items-center gap-2 bg-accent px-4 text-sm text-accent-foreground"
            data-testid="link-history-new"
          >
            <Plus size={16} /> New analysis
          </Link>
        }
      />

      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search size={16} className="absolute left-3 top-3 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 w-full border border-input bg-card pl-9 pr-3 text-sm"
            placeholder="Search questions, regions, record IDs…"
            data-testid="input-history-search"
          />
        </label>

        <div className="flex flex-wrap items-center gap-2">
          <Filter size={15} className="text-muted-foreground" />

          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="h-10 border border-input bg-card px-3 text-sm"
            data-testid="select-history-status"
          >
            <option>All</option>
            <option>Complete</option>
            <option>Review</option>
          </select>

          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="h-10 border border-input bg-card px-3 text-sm"
            aria-label="Sort analysis history"
            data-testid="select-history-sort"
          >
            <option>Newest</option>
            <option>Confidence</option>
            <option>Question</option>
          </select>
        </div>
      </div>

      <Panel title={`${filtered.length} analysis records`} meta="Local archive">
        <div className="divide-y divide-border">
          {filtered.map((item) => (
            <AnalysisRow
              item={item}
              onDelete={setDeleteId}
              key={item.id}
            />
          ))}

          {filtered.length === 0 && (
            <EmptyState
              title="No records match this search."
              text="Try another phrase or clear the status filter."
              onReset={() => {
                setSearch("");
                setFilter("All");
              }}
            />
          )}
        </div>
      </Panel>

      {deleteId && (
        <ConfirmDialog
          title="Delete this analysis?"
          text="The local record will be removed from this archive. This cannot be undone."
          onCancel={() => setDeleteId(null)}
          onConfirm={() => {
            setItems(items.filter((item) => item.id !== deleteId));
            setDeleteId(null);
          }}
        />
      )}
    </>
  );
}