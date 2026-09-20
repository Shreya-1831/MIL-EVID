import { Radar } from "lucide-react";
import { Link } from "react-router-dom";

export default function Logo({ compact = false }) {
  return (
    <Link to="/" className="flex items-center gap-3 group" data-testid="link-logo">
      <span className="grid h-9 w-9 place-items-center border border-accent/60 bg-accent/10 text-accent">
        <Radar size={20} strokeWidth={1.6} />
      </span>
      {!compact && (
        <span>
          <span className="block text-[15px] font-semibold tracking-[.18em]">MIL-EVID</span>
          <span className="block font-mono-ui text-[9px] uppercase tracking-[.16em] text-muted-foreground">Evidence room</span>
        </span>
      )}
    </Link>
  );
}