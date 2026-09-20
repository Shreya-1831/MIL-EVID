import { useEffect, useState } from "react";
import { CircleHelp, LogIn, LockKeyhole, UserPlus } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiClient } from "../services/apiClient";
import Logo from "../components/Logo";
import ThemeButton from "../components/ThemeButton";
import SectionLabel from "../components/SectionLabel";
import Button from "../components/Button";

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", remember: true });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (user) navigate("/dashboard");
  }, [user, navigate]);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (form.name.trim().length < 2)
      return setError("Enter your full name to create an analyst profile.");
    if (!/^\S+@\S+\.\S+$/.test(form.email))
      return setError("Use a valid work email address.");
    if (form.password.length < 6)
      return setError("Password must be at least 6 characters.");

    await register(form);
    setSuccess("Workspace created. Loading your console…");
  };

  return (
    <div className="min-h-[100dvh] bg-background field-grid">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-10">
        <Logo />
        <div className="flex items-center gap-3">
          <ThemeButton />
          <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground" data-testid="link-auth-switch">
            Already have access?
          </Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl px-5 pb-16 pt-10 lg:grid-cols-[.9fr_1.1fr] lg:gap-20 lg:px-10 lg:pt-20">
        <div className="hidden border-r border-border pr-16 lg:block">
          <SectionLabel>Secure analyst workspace</SectionLabel>
          <h1 className="max-w-md text-5xl font-semibold leading-[1] tracking-[-.06em]">
            Put your sources in order.
          </h1>
          <p className="mt-6 max-w-md text-sm leading-7 text-muted-foreground">
            Local mock mode is active. Your workspace persists in this browser and is ready for future API connectivity.
          </p>
          <div className="mt-16 border-l-2 border-accent pl-5 font-mono-ui text-xs leading-6 text-muted-foreground">
            AUTH / SESSION
            <br />
            <span className="text-primary">PERSISTENT LOCAL IDENTITY</span>
            <br />
            VITE_API_BASE_URL / {apiClient.baseUrl || "MOCK FALLBACK"}
          </div>
        </div>

        <div className="max-w-md">
          <SectionLabel>New analyst profile</SectionLabel>
          <h2 className="text-3xl font-semibold tracking-[-.04em]">
            Create access
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            A local account for this research environment.
          </p>

          <form onSubmit={submit} className="mt-8 space-y-5">
            <label className="block">
              <span className="mb-2 block text-xs font-medium">Full name</span>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="h-11 w-full border border-input bg-card px-3 text-sm"
                placeholder="Avery Mercer"
                data-testid="input-name"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-xs font-medium">Email address</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="h-11 w-full border border-input bg-card px-3 text-sm"
                placeholder="analyst@fieldroom.org"
                data-testid="input-email"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-xs font-medium">Password</span>
              <span className="relative block">
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="h-11 w-full border border-input bg-card px-3 pr-11 text-sm"
                  placeholder="••••••••"
                  data-testid="input-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-0 top-0 grid h-11 w-11 place-items-center text-muted-foreground"
                  aria-label="Toggle password visibility"
                  data-testid="button-password-visibility"
                >
                  {showPassword ? <LockKeyhole size={16} /> : <CircleHelp size={16} />}
                </button>
              </span>
            </label>

            {error && (
              <div className="border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive" data-testid="status-auth-error">
                {error}
              </div>
            )}

            {success && (
              <div className="border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-primary" data-testid="status-auth-success">
                {success}
              </div>
            )}

            <Button type="submit" className="w-full" data-testid="button-auth-submit">
              <UserPlus size={16} /> Create local account
            </Button>
          </form>

          <div className="mt-8 border-t border-border pt-5 font-mono-ui text-[10px] uppercase tracking-[.12em] text-muted-foreground">
            All records shown in preview mode · No external data transmitted
          </div>
        </div>
      </main>
    </div>
  );
}