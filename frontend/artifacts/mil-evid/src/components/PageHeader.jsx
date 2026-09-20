import SectionLabel from "./SectionLabel";

function PageHeader({ eyebrow, title, description, action }) {
  return (
    <header className="mb-8 flex flex-col justify-between gap-5 border-b border-border pb-6 sm:flex-row sm:items-end">
      <div>
        <SectionLabel>{eyebrow}</SectionLabel>
        <h1 className="text-3xl font-semibold tracking-[-.04em] sm:text-4xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {action}
    </header>
  );
}

export default PageHeader;