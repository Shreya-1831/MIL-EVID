const cn = (...items) => items.filter(Boolean).join(" ");

function Stat({ label, value, detail, accent = false }) {
  return (
    <div className="border border-border bg-card p-5">
      <div className="font-mono-ui text-[10px] uppercase tracking-[.12em] text-muted-foreground">
        {label}
      </div>

      <div
        className={cn(
          "mt-3 text-3xl font-semibold tracking-[-.05em]",
          accent && "text-accent"
        )}
      >
        {value}
      </div>

      <div className="mt-2 text-xs text-muted-foreground">{detail}</div>
    </div>
  );
}

export default Stat;