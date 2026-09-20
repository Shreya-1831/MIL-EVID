import { ChevronRight } from "lucide-react";

import { Link } from "react-router-dom";

const formatDate = (date) => {
  if (!date) {
    return "Unknown date";
  }

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "Unknown date";
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parsedDate);
};

function EvidenceRow({ record }) {
  return (
    <div
      className="flex min-w-0 flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between"
      data-testid={`row-evidence-${record.id}`}
    >
      <div className="min-w-0 flex-1">
        <Link
          to={`/evidence/${record.id}`}
          className="break-words text-sm font-medium hover:text-accent"
        >
          {record.title ||
            "Untitled evidence"}
        </Link>

        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono-ui text-[10px] uppercase text-muted-foreground">
          <span className="break-all">
            {record.id}
          </span>

          <span>
            {record.source ||
              "Unknown source"}
          </span>

          <span>
            {record.source_type ||
              "Unknown type"}
          </span>

          {record.perspective && (
            <span>
              {record.perspective}
            </span>
          )}

          <span>
            {formatDate(record.date)}
          </span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <span className="font-mono-ui text-[10px] uppercase text-muted-foreground">
          Chunk{" "}
          {record.chunk_index ??
            "—"}
        </span>

        <Link
          to={`/evidence/${record.id}`}
          className="text-muted-foreground hover:text-accent"
          data-testid={`link-evidence-view-${record.id}`}
          aria-label={`View evidence ${record.id}`}
        >
          <ChevronRight size={16} />
        </Link>
      </div>
    </div>
  );
}

export default EvidenceRow;