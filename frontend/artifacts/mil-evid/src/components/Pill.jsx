function Pill({ children, tone = "neutral" }) {
  const tones = {
    neutral: "border-border bg-muted/70 text-muted-foreground",
    green: "border-primary/25 bg-primary/10 text-primary",
    copper: "border-accent/30 bg-accent/10 text-accent",
    red: "border-destructive/30 bg-destructive/10 text-destructive",
  };

  return (
    <span
      className={`inline-flex items-center gap-1 border px-2 py-1 font-mono-ui text-[10px] uppercase tracking-[.08em] ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export default Pill;