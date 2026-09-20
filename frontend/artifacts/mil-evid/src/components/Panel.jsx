function Panel({ title, meta, action, children }) {
  return (
    <section className="border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div>
          <h2 className="text-sm font-medium">{title}</h2>
          {meta && (
            <div className="mt-1 font-mono-ui text-[9px] uppercase tracking-[.1em] text-muted-foreground">
              {meta}
            </div>
          )}
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

export default Panel;