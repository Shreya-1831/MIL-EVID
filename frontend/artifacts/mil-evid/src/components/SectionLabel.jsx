function SectionLabel({ children }) {
  return (
    <div className="mb-3 flex items-center gap-2 font-mono-ui text-[10px] uppercase tracking-[.18em] text-accent">
      <span className="h-px w-5 bg-accent" />
      {children}
    </div>
  );
}

export default SectionLabel;