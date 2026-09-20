import { ChevronRight, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import Pill from "./Pill";

const formatDate = (date) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(date));

function AnalysisRow({ item, onDelete }) {
  return (
    <div
      className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between"
      data-testid={`row-analysis-${item.id}`}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to={`/analysis/${item.id}`}
            className="truncate text-sm font-medium hover:text-accent"
          >
            {item.query}
          </Link>
          <Pill tone={item.status === "Complete" ? "green" : "copper"}>
            {item.status}
          </Pill>
        </div>

        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono-ui text-[10px] uppercase text-muted-foreground">
          <span>{item.id}</span>
          <span>{item.region}</span>
          <span>{item.evidenceCount} sources</span>
          <span>{formatDate(item.timestamp)}</span>
        </div>
      </div>

      <div className="flex items-center gap-4 sm:pl-5">
        <div className="text-right">
          <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
            Confidence
          </div>
          <div className="mt-1 text-lg font-semibold text-accent">
            {item.confidence}%
          </div>
        </div>

        {onDelete && (
          <button
            onClick={() => onDelete(item.id)}
            className="text-muted-foreground hover:text-destructive"
            aria-label={`Delete ${item.id}`}
          >
            <Trash2 size={15} />
          </button>
        )}

        <Link
          to={`/analysis/${item.id}`}
          className="text-muted-foreground hover:text-accent"
          aria-label={`View ${item.id}`}
        >
          <ChevronRight size={17} />
        </Link>
      </div>
    </div>
  );
}

export default AnalysisRow;