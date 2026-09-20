import { Check } from "lucide-react";
import { Link } from "react-router-dom";
import Pill from "./Pill";

function ClaimCard({ claim, index }) {
  return (
    <div
      className="border border-border p-4"
      data-testid={`card-claim-${index}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex gap-3">
          <span className="font-mono-ui text-[10px] text-accent">
            C0{index + 1}
          </span>
          <p className="max-w-2xl text-sm leading-6">{claim.text}</p>
        </div>

        <Pill tone={claim.status === "Supported" ? "green" : "copper"}>
          {claim.status}
        </Pill>
      </div>

      <div className="mt-4 grid gap-4 border-t border-border pt-4 sm:grid-cols-2">
        <div>
          <div className="mb-2 font-mono-ui text-[9px] uppercase text-muted-foreground">
            Supporting evidence
          </div>

          <div className="flex flex-wrap gap-2">
            {claim.supporting.map((id) => (
              <Link
                to={`/evidence/${id}`}
                className="inline-flex items-center gap-1 border border-primary/25 bg-primary/5 px-2 py-1 font-mono-ui text-[10px] text-primary"
                key={id}
              >
                <Check size={11} />
                {id}
              </Link>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 font-mono-ui text-[9px] uppercase text-muted-foreground">
            Confidence / resistance
          </div>

          <div className="flex items-center gap-3">
            <div className="h-1.5 flex-1 bg-muted">
              <div
                className="h-full bg-accent"
                style={{ width: `${claim.confidence}%` }}
              />
            </div>
            <span className="font-mono-ui text-xs">
              {claim.confidence}%
            </span>
          </div>

          {claim.contradicting.length > 0 && (
            <div className="mt-2 font-mono-ui text-[9px] text-destructive">
              Resisted by {claim.contradicting.join(", ")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ClaimCard;