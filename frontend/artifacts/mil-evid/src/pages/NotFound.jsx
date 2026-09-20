import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import Logo from "../components/Logo";

export default function NotFound() {
  return (
    <div className="min-h-[100dvh] bg-background field-grid">
      <header className="mx-auto max-w-7xl px-5 py-5 lg:px-10">
        <Logo />
      </header>

      <main className="mx-auto max-w-2xl px-5 py-24 lg:px-10">
        <div className="font-mono-ui text-sm text-accent">
          404 / FIELD NOTE MISSING
        </div>

        <h1 className="mt-5 text-6xl font-semibold tracking-[-.06em]">
          This page is not in the archive.
        </h1>

        <p className="mt-5 max-w-md text-sm leading-7 text-muted-foreground">
          The route may have moved, or the record was never indexed in this
          workspace.
        </p>

        <Link
          to="/"
          className="mt-8 inline-flex items-center gap-2 bg-primary px-5 py-3 text-sm text-primary-foreground"
          data-testid="link-not-found-home"
        >
          Return to the field room <ArrowRight size={16} />
        </Link>
      </main>
    </div>
  );
}