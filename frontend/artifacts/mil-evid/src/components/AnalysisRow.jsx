import { ChevronRight, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import Pill from "./Pill";

const formatDate = (date) => {
  if (!date) return "—";

  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
};

function AnalysisRow({ item, onDelete }) {
  const id = item?.analysis_id;

  const confidence = Number(item?.overall_confidence);

  const formattedConfidence = Number.isFinite(confidence)
    ? `${(confidence).toFixed(1)}%`
    : "—";

  const status = String(item?.status || "unknown").toLowerCase();

  return (
    <div
      className="
        grid
        min-w-0
        max-w-full
        grid-cols-1
        gap-4
        overflow-hidden
        py-5
        sm:grid-cols-[minmax(0,1fr)_auto]
        sm:items-center
      "
      data-testid={`row-analysis-${id}`}
    >
      {/* =====================================================
          LEFT — ANALYSIS INFORMATION
      ===================================================== */}

      <div className="min-w-0 max-w-full overflow-hidden">
        <div className="flex min-w-0 max-w-full items-center gap-2">
          <Link
            to={`/analysis/${id}`}
            title={item?.query_text || "View analysis"}
            className="
              block
              min-w-0
              max-w-full
              truncate
              text-sm
              font-medium
              leading-6
              hover:text-accent
            "
          >
            {item?.query_text || "Untitled analysis"}
          </Link>

          <Pill
            tone={
              status === "completed"
                ? "green"
                : "copper"
            }
          >
            {status}
          </Pill>
        </div>

        <div
          className="
            mt-2
            flex
            min-w-0
            max-w-full
            flex-wrap
            gap-x-4
            gap-y-1
            overflow-hidden
            font-mono-ui
            text-[10px]
            uppercase
            text-muted-foreground
          "
        >
          <span className="max-w-full truncate">
            {id}
          </span>

          <span className="shrink-0">
            {Number(item?.evidence_count || 0)} sources
          </span>

          <span className="shrink-0">
            {formatDate(
              item?.completed_at ||
                item?.started_at
            )}
          </span>
        </div>
      </div>

      {/* =====================================================
          RIGHT — CONFIDENCE + ACTIONS
      ===================================================== */}

      <div
        className="
          flex
          shrink-0
          items-center
          justify-between
          gap-4
          sm:justify-end
        "
      >
        <div className="min-w-18 text-right">
          <div
            className="
              font-mono-ui
              text-[9px]
              uppercase
              text-muted-foreground
            "
          >
            Confidence
          </div>

          <div className="mt-1 text-lg font-semibold text-accent">
            {formattedConfidence}
          </div>
        </div>

        {onDelete && (
          <button
            type="button"
            onClick={() => onDelete(id)}
            className="
              shrink-0
              text-muted-foreground
              transition-colors
              hover:text-destructive
            "
            aria-label={`Delete ${id}`}
          >
            <Trash2 size={15} />
          </button>
        )}

        <Link
          to={`/analysis/${id}`}
          className="
            shrink-0
            text-muted-foreground
            transition-colors
            hover:text-accent
          "
          aria-label={`View ${id}`}
        >
          <ChevronRight size={17} />
        </Link>
      </div>
    </div>
  );
}

export default AnalysisRow;