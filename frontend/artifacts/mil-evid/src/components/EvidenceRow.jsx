import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

const formatDate = (date) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(date));

function EvidenceRow({ record }) {
  return (
    <div
      className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between"
      data-testid={`row-evidence-${record.id}`}
    >
      <div className="min-w-0">
        <Link
          to={`/evidence/${record.id}`}
          className="text-sm font-medium hover:text-accent"
        >
          {record.title}
        </Link>

        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono-ui text-[10px] uppercase text-muted-foreground">
          <span>{record.id}</span>
          <span>{record.source}</span>
          <span>{record.perspective}</span>
          <span>{formatDate(record.date)}</span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <span className="font-mono-ui text-xs text-accent">
          {record.relevance}% match
        </span>

        <Link
          to={`/evidence/${record.id}`}
          className="text-muted-foreground hover:text-accent"
          data-testid={`link-evidence-view-${record.id}`}
        >
          <ChevronRight size={16} />
        </Link>
      </div>
    </div>
  );
}

export default EvidenceRow;