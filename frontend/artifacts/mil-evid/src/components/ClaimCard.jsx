import { Check, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import Pill from "./Pill";

function ClaimCard({ claim, index }) {
  const supporting = Array.isArray(claim?.supporting)
    ? claim.supporting
    : [];

  const contradicting = Array.isArray(claim?.contradicting)
    ? claim.contradicting
    : [];

  const supportScore =
    typeof claim?.support_score === "number"
      ? claim.support_score
      : typeof claim?.confidence === "number"
        ? claim.confidence / 100
        : 0;

  const confidence = Math.round(
    Math.max(0, Math.min(1, supportScore)) * 100
  );

  const status = claim?.verdict || "Unverified";

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

          <p className="max-w-2xl text-sm leading-6">
            {claim?.text || claim?.claim_text || "No claim text available."}
          </p>
        </div>

        <Pill
          tone={
            status.toLowerCase() === "supported"
              ? "green"
              : "copper"
          }
        >
          {status}
        </Pill>
      </div>

      <div className="mt-4 grid gap-4 border-t border-border pt-4 sm:grid-cols-2">
        {/* Supporting evidence */}
        <div>
          <div className="mb-2 font-mono-ui text-[9px] uppercase text-muted-foreground">
            Supporting evidence
          </div>

          {supporting.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {supporting.map((id) => (
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
          ) : (
            <div className="font-mono-ui text-[10px] text-muted-foreground">
              Evidence references are available in the evidence section.
            </div>
          )}
        </div>

        {/* Confidence / verification */}
        <div>
          <div className="mb-2 font-mono-ui text-[9px] uppercase text-muted-foreground">
            Confidence / resistance
          </div>

          <div className="flex items-center gap-3">
            <div className="h-1.5 flex-1 bg-muted">
              <div
                className="h-full bg-accent"
                style={{ width: `${confidence}%` }}
              />
            </div>

            <span className="font-mono-ui text-xs">
              {confidence}%
            </span>
          </div>

          {claim?.verified && (
            <div className="mt-2 flex items-center gap-1 font-mono-ui text-[9px] text-primary">
              <ShieldCheck size={11} />
              Claim verified
            </div>
          )}

          {contradicting.length > 0 && (
            <div className="mt-2 font-mono-ui text-[9px] text-destructive">
              Resisted by {contradicting.join(", ")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ClaimCard;