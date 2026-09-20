import { ArrowRight, Fingerprint, Library, LogIn, Network, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import Logo from "../components/Logo";
import ThemeButton from "../components/ThemeButton";
import Pill from "../components/Pill";
import SectionLabel from "../components/SectionLabel";

function Feature({ icon, title, text }) {
  return (
    <div className="border border-border bg-card p-5 transition-transform hover:-translate-y-1">
      <div className="text-accent">{icon}</div>
      <h3 className="mt-7 font-medium">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p>
    </div>
  );
}

export default function Landing() {
  return (
    <div className="min-h-[100dvh] bg-background field-grid">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-10">
        <Logo />
        <div className="flex items-center gap-3">
          <ThemeButton />
          <Link to="/login" className="hidden px-3 py-2 text-sm text-muted-foreground hover:text-foreground" data-testid="link-landing-login">
            Sign in
          </Link>
          <Link to="/register" className="inline-flex h-9 items-center gap-2 bg-primary px-4 text-sm text-primary-foreground hover:opacity-90" data-testid="link-landing-register">
            Enter console <ArrowRight size={15} />
          </Link>
        </div>
      </header>

      <main>
        <section className="relative mx-auto grid max-w-7xl gap-14 px-5 pb-20 pt-16 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:px-10 lg:pb-28 lg:pt-24">
          <div className="animate-rise">
            <Pill tone="copper">MIL-EVID / v0.9 analyst preview</Pill>
            <h1 className="mt-7 max-w-3xl text-5xl font-semibold leading-[.98] tracking-[-.065em] sm:text-7xl">
              Know what the assessment is <span className="text-accent">standing on.</span>
            </h1>
            <p className="mt-7 max-w-xl text-base leading-7 text-muted-foreground">
              A rigorous evidence-grounded workspace for analysts who need every perspective, claim, and contradiction visible before a judgment leaves the room.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/register" className="inline-flex h-11 items-center gap-2 bg-accent px-5 text-sm font-medium text-accent-foreground" data-testid="link-hero-start">
                Start a local workspace <ArrowRight size={16} />
              </Link>
              <Link to="/login" className="inline-flex h-11 items-center gap-2 border border-border bg-card px-5 text-sm hover:bg-muted" data-testid="link-hero-login">
                View analyst console <LogIn size={15} />
              </Link>
            </div>
            <div className="mt-10 flex items-center gap-5 font-mono-ui text-[10px] uppercase tracking-[.12em] text-muted-foreground">
              <span>Multi-perspective</span><span className="h-1 w-1 rounded-full bg-accent" />
              <span>Claim-level citations</span><span className="h-1 w-1 rounded-full bg-accent" />
              <span>Local-first</span>
            </div>
          </div>

          <div className="animate-rise delay-1 relative min-h-[410px] border border-border bg-card p-5 shadow-[10px_10px_0_hsl(var(--primary)/.08)]">
            <div className="absolute inset-0 terrain-rule opacity-60" />
            <div className="relative">
              <div className="flex items-center justify-between border-b border-border pb-4">
                <div>
                  <div className="font-mono-ui text-[10px] uppercase tracking-[.14em] text-muted-foreground">Active assessment</div>
                  <div className="mt-1 text-lg font-medium">Baltic corridor posture</div>
                </div>
                <Pill tone="green"><span className="h-1.5 w-1.5 rounded-full bg-primary" />Complete</Pill>
              </div>

              <div className="grid grid-cols-3 gap-3 border-b border-border py-5">
                <div><div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Confidence</div><div className="mt-1 text-3xl font-semibold text-accent">78<span className="text-sm">%</span></div></div>
                <div><div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Evidence</div><div className="mt-1 text-3xl font-semibold">24</div></div>
                <div><div className="font-mono-ui text-[9px] uppercase text-muted-foreground">Views</div><div className="mt-1 text-3xl font-semibold">03</div></div>
              </div>

              <div className="py-5">
                <div className="mb-3 flex items-center justify-between font-mono-ui text-[10px] uppercase text-muted-foreground">
                  <span>Confidence by perspective</span><span>Last run 14:32Z</span>
                </div>
                {[["Operational",82],["Geopolitical",71],["Humanitarian",76]].map(([label,value], i) => (
                  <div className="mb-3" key={label}>
                    <div className="mb-1 flex justify-between text-xs"><span>{label}</span><span className="font-mono-ui text-muted-foreground">{value}%</span></div>
                    <div className="h-1 bg-muted"><div className={`h-full ${i === 1 ? "bg-accent" : "bg-primary"}`} style={{ width: `${value}%` }} /></div>
                  </div>
                ))}
                <div className="mt-6 border-l-2 border-accent bg-accent/5 p-3 text-xs leading-5 text-muted-foreground">
                  The corridor is experiencing elevated surveillance and readiness activity, but not an unambiguous pre-conflict posture.
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-border bg-card">
          <div className="mx-auto grid max-w-7xl gap-0 px-5 lg:grid-cols-3 lg:px-10">
            {[
              ["01","Frame the question","Define region, period, and the perspectives that should challenge your first read."],
              ["02","Trace the evidence","Read source provenance, relevance, and contradictions beside every claim."],
              ["03","Make the call","Export a measured assessment with confidence that explains itself."]
            ].map(([n,t,d]) => (
              <div key={n} className="border-border py-8 lg:border-r lg:px-8 lg:first:pl-0 lg:last:border-0">
                <div className="font-mono-ui text-[11px] text-accent">{n}</div>
                <h2 className="mt-4 text-lg font-medium">{t}</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{d}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 lg:px-10">
          <div className="grid gap-12 lg:grid-cols-[.75fr_1.25fr]">
            <div>
              <SectionLabel>Built for scrutiny</SectionLabel>
              <h2 className="max-w-md text-3xl font-semibold leading-tight tracking-[-.04em]">The provenance is part of the answer.</h2>
              <p className="mt-5 max-w-md text-sm leading-7 text-muted-foreground">
                MIL-EVID turns a pile of reports into a transparent working record. It keeps the analyst in the loop, and keeps the reasoning legible to the person who reviews it next.
              </p>
              <Link to="/register" className="mt-7 inline-flex items-center gap-2 text-sm font-medium text-accent hover:gap-3" data-testid="link-landing-learn">
                Open the evidence room <ArrowRight size={15} />
              </Link>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Feature icon={<Fingerprint />} title="Claim-level grounding" text="See exactly which records support or resist an assertion." />
              <Feature icon={<Network />} title="Perspective tension" text="Operational, legal, historical and humanitarian views share one table." />
              <Feature icon={<Library />} title="Source memory" text="A searchable evidence archive with provenance and health." />
              <Feature icon={<ShieldCheck />} title="Measured confidence" text="Confidence is a breakdown, not a decorative score." />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border px-5 py-6 lg:px-10">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-2 font-mono-ui text-[10px] uppercase tracking-[.14em] text-muted-foreground sm:flex-row">
          <span>MIL-EVID / Evidence-grounded analysis</span>
          <span>For careful questions and accountable answers</span>
        </div>
      </footer>
    </div>
  );
}