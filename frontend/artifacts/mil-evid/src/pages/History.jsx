import { useEffect, useMemo, useState } from "react";
import { Filter, Plus, Search } from "lucide-react";
import { Link } from "react-router-dom";

import { apiClient } from "../services/apiClient";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import AnalysisRow from "../components/AnalysisRow";
import EmptyState from "../components/EmptyState";
import ConfirmDialog from "../components/ConfirmDialog";

export default function History() {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [sort, setSort] = useState("Newest");

  const [deleteId, setDeleteId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadHistory() {
      try {
        setLoading(true);
        setError("");

        const analyses = await apiClient.listAnalyses();

        if (mounted) {
          setItems(analyses);
        }
      } catch (err) {
        console.error("Failed to load analysis history:", err);

        if (mounted) {
          setError(
            err.message ||
              "Failed to load analysis history."
          );
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadHistory();

    return () => {
      mounted = false;
    };
  }, []);

  const filtered = useMemo(() => {
    return [...items]
      .filter((item) => {
        const text =
          `${item.query_text} ${item.analysis_id}`
            .toLowerCase();

        const matchesSearch =
          text.includes(search.toLowerCase());

        const matchesFilter =
          filter === "All" ||
          item.status === filter;

        return (
          matchesSearch &&
          matchesFilter
        );
      })
      .sort((a, b) => {
        if (sort === "Newest") {
          return (
            new Date(
              b.completed_at || b.started_at
            ) -
            new Date(
              a.completed_at || a.started_at
            )
          );
        }

        if (sort === "Confidence") {
          return (
            b.overall_confidence -
            a.overall_confidence
          );
        }

        return a.query_text.localeCompare(
          b.query_text
        );
      });
  }, [items, search, filter, sort]);

  async function handleDelete() {
    if (!deleteId) return;

    try {
      await apiClient.deleteAnalysis(deleteId);

      setItems((current) =>
        current.filter(
          (item) =>
            item.analysis_id !== deleteId
        )
      );
    } catch (err) {
      console.error(
        "Failed to delete analysis:",
        err
      );

      setError(
        err.message ||
          "Failed to delete analysis."
      );
    } finally {
      setDeleteId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Analysis History"
        description="Review previously completed MIL-EVID analyses."
      />

      <Panel>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="relative">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />

              <input
                value={search}
                onChange={(e) =>
                  setSearch(e.target.value)
                }
                placeholder="Search analyses..."
                className="w-full rounded border bg-background py-2 pl-9 pr-3 text-sm md:w-80"
              />
            </div>

            <div className="flex gap-2">
              <select
                value={filter}
                onChange={(e) =>
                  setFilter(e.target.value)
                }
                className="rounded border bg-background px-3 py-2 text-sm"
              >
                <option value="All">All</option>
                <option value="completed">
                  Completed
                </option>
              </select>

              <select
                value={sort}
                onChange={(e) =>
                  setSort(e.target.value)
                }
                className="rounded border bg-background px-3 py-2 text-sm"
              >
                <option value="Newest">
                  Newest
                </option>
                <option value="Confidence">
                  Confidence
                </option>
                <option value="Query">
                  Query
                </option>
              </select>

              <Link
                to="/analysis/new"
                className="inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-white"
              >
                <Plus size={15} />
                New Analysis
              </Link>
            </div>
          </div>

          {loading && (
            <div className="py-12 text-center text-sm text-muted-foreground">
              Loading analysis history...
            </div>
          )}

          {!loading && error && (
            <div className="rounded border border-destructive/30 p-4 text-sm text-destructive">
              {error}
            </div>
          )}

          {!loading &&
            !error &&
            filtered.length === 0 && (
              <EmptyState
                title="No analyses found"
                description={
                  items.length === 0
                    ? "Run your first MIL-EVID analysis to see it here."
                    : "Try changing your search or filters."
                }
              />
            )}

          {!loading &&
            !error &&
            filtered.length > 0 && (
              <div className="divide-y">
                {filtered.map((item) => (
                  <AnalysisRow
                    key={item.analysis_id}
                    item={item}
                    onDelete={setDeleteId}
                  />
                ))}
              </div>
            )}
        </div>
      </Panel>

      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Delete analysis?"
        description="This will permanently remove the analysis and its stored evidence, claims, perspectives, and contradictions."
        onCancel={() => setDeleteId(null)}
        onConfirm={handleDelete}
      />
    </>
  );
}