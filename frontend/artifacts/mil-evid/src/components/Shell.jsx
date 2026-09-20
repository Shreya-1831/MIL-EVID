import { useState } from "react";

import {
  Activity,
  ClipboardList,
  FileSearch,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  Settings2,
  X,
} from "lucide-react";

import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "./Logo";
import ThemeButton from "./ThemeButton";

const cn = (...items) => items.filter(Boolean).join(" ");

function HeaderSearch() {
  const [value, setValue] = useState("");

  const submit = (e) => {
    e.preventDefault();

    if (value.trim()) {
      window.location.href = `/evidence?search=${encodeURIComponent(
        value.trim()
      )}`;
    }
  };

  return (
    <form
      onSubmit={submit}
      className="hidden min-w-0 max-w-sm flex-1 md:block"
      role="search"
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="h-9 w-full border border-border bg-card px-3 text-xs"
        placeholder="Search evidence room…"
        aria-label="Search evidence room"
      />
    </form>
  );
}

function Shell({ children }) {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const nav = [
    {
      href: "/dashboard",
      label: "Overview",
      icon: LayoutDashboard,
    },
    {
      href: "/analysis/new",
      label: "New analysis",
      icon: Plus,
    },
    {
      href: "/history",
      label: "Analysis history",
      icon: ClipboardList,
    },
    {
      href: "/evidence",
      label: "Evidence explorer",
      icon: FileSearch,
    },
    {
      href: "/system",
      label: "System status",
      icon: Activity,
    },
  ];

  const location = window.location.pathname;

  const isActive = (href) =>
    href === "/dashboard"
      ? location === href
      : location.startsWith(href);

  return (
    <div className="min-h-[100dvh] bg-background">

      {/* SIDEBAR */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 w-64 overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* LIGHT MODE FOREST */}
        <img
          src="/images/dark-forest.png"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 h-full w-full object-cover object-center opacity-35 dark:hidden"
        />

        {/* DARK MODE FOREST */}
        <img
          src="/images/light-forest.png"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 hidden h-full w-full object-cover object-center opacity-25 dark:block"
        />

        {/* IMAGE OVERLAY */}
        <div className="absolute inset-0 bg-sidebar/80" />

        {/* SIDEBAR CONTENT */}
        <div className="relative z-10 flex h-full flex-col">

          {/* LOGO */}
          <div className="flex items-center justify-between border-b border-sidebar-border px-5 py-5">
            <Logo />

            <button
              className="text-sidebar-foreground lg:hidden"
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
            >
              <X size={19} />
            </button>
          </div>

          {/* WORKSPACE */}
          <div className="border-b border-sidebar-border px-5 py-5">
            <div className="font-mono-ui text-[9px] uppercase tracking-[.15em] text-sidebar-foreground/60">
              Current workspace
            </div>

            <div className="mt-2 flex items-center gap-2 text-sm">
              <span className="h-2 w-2 rounded-full bg-accent" />
              Field room / local
            </div>
          </div>

          {/* NAVIGATION */}
          <nav className="flex-1 space-y-1 px-3 py-5">
            {nav.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                to={href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 border-l-2 px-3 py-3 text-sm transition-colors",
                  isActive(href)
                    ? "border-accent bg-sidebar-accent text-sidebar-foreground"
                    : "border-transparent text-sidebar-foreground/65 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                )}
              >
                <Icon size={17} strokeWidth={1.7} />

                <span>{label}</span>

                {href === "/analysis/new" && (
                  <span className="ml-auto font-mono-ui text-[10px] text-accent">
                    +
                  </span>
                )}
              </Link>
            ))}
          </nav>

          {/* USER / SIGN OUT */}
          <div className="border-t border-sidebar-border p-4">
            <div className="mb-3 flex items-center gap-3">
              <span className="grid h-8 w-8 place-items-center bg-accent text-xs font-semibold text-accent-foreground">
                {(user?.name || "A").slice(0, 1).toUpperCase()}
              </span>

              <div className="min-w-0">
                <div className="truncate text-xs">
                  {user?.name || "Analyst"}
                </div>

                <div className="font-mono-ui text-[9px] uppercase text-sidebar-foreground/55">
                  {user?.role || "Analyst"}
                </div>
              </div>
            </div>

            <button
              onClick={logout}
              className="flex w-full items-center gap-2 px-2 py-2 text-xs text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground"
            >
              <LogOut size={14} />
              Sign out
            </button>
          </div>

        </div>
      </aside>

      {/* MOBILE OVERLAY */}
      {mobileOpen && (
        <button
          className="fixed inset-0 z-20 bg-foreground/30 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Close navigation overlay"
        />
      )}

      {/* MAIN AREA */}
      <div className="lg:pl-64">

        {/* TOP HEADER */}
        <header className="sticky top-0 z-10 flex min-h-16 items-center justify-between gap-4 border-b border-border bg-background/95 px-5 py-3 backdrop-blur lg:px-9">

          <button
            className="grid h-9 w-9 shrink-0 place-items-center border border-border lg:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={18} />
          </button>

          <HeaderSearch />

          <div className="ml-auto flex items-center gap-3">

            <span className="hidden text-xs text-muted-foreground xl:block">
              {new Intl.DateTimeFormat("en-GB", {
                dateStyle: "medium",
              }).format(new Date())}
            </span>

            <span className="hidden items-center gap-2 border-l border-border pl-3 text-xs sm:flex">
              <span className="grid h-7 w-7 place-items-center bg-accent text-[11px] font-semibold text-accent-foreground">
                {(user?.name || "A").slice(0, 1).toUpperCase()}
              </span>

              <span className="hidden text-muted-foreground xl:block">
                {user?.name || "Analyst"}
              </span>
            </span>

            <ThemeButton />

            <Link
              to="/system"
              className="grid h-9 w-9 shrink-0 place-items-center border border-border text-muted-foreground hover:bg-muted"
              aria-label="System settings"
            >
              <Settings2 size={16} />
            </Link>

            <button
              onClick={logout}
              className="hidden h-9 items-center gap-2 border border-border px-3 text-xs text-muted-foreground hover:bg-muted hover:text-foreground sm:flex"
            >
              <LogOut size={14} />
              Sign out
            </button>

          </div>
        </header>

        {/* PAGE CONTENT */}
        <main className="mx-auto max-w-[1500px] px-5 py-8 lg:px-9 lg:py-10">
          {children}
        </main>

      </div>
    </div>
  );
}

export default Shell;