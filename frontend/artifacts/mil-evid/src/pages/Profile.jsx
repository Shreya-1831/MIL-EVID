import { useEffect, useState } from "react";

import {
  CalendarDays,
  CheckCircle2,
  Clock3,
  Mail,
  ShieldCheck,
  User,
  XCircle,
} from "lucide-react";

import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Pill from "../components/Pill";
import EmptyState from "../components/EmptyState";

import { apiClient } from "../services/apiClient";


const formatDate = (date) => {
  if (!date) {
    return "Not available";
  }

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parsedDate);
};


const formatDateTime = (date) => {
  if (!date) {
    return "Not available";
  }

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsedDate);
};


const getInitials = (name, email) => {
  const value = name?.trim() || email?.trim() || "A";

  const parts = value
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`
      .toUpperCase();
  }

  return value.slice(0, 2).toUpperCase();
};


export default function Profile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadProfile() {
      try {
        setLoading(true);
        setError("");

        const response = await apiClient.getCurrentUser();

        if (cancelled) {
          return;
        }

        setUser(response);
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        console.error(
          "Unable to load profile:",
          loadError
        );

        setError(
          loadError?.message ||
            "Unable to load your profile."
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      cancelled = true;
    };
  }, []);


  if (loading) {
    return (
      <EmptyState
        title="Loading profile..."
        text="Retrieving your account information."
      />
    );
  }


  if (error || !user) {
    return (
      <EmptyState
        title={error || "Profile unavailable."}
        text="Your account information could not be loaded."
      />
    );
  }


  const initials = getInitials(
    user.full_name,
    user.email
  );


  return (
    <>
      <PageHeader
        eyebrow="Account / Profile"
        title="Your profile."
        description="Account identity, access status, and session information."
        action={
          <Pill tone={user.is_active ? "green" : "copper"}>
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                user.is_active
                  ? "bg-primary"
                  : "bg-accent"
              }`}
            />
            {user.is_active
              ? "Active account"
              : "Inactive account"}
          </Pill>
        }
      />


      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,.8fr)]">

        {/* Identity */}
        <Panel
          title="Identity"
          meta="Account information"
        >
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center">

            <div className="flex h-20 w-20 shrink-0 items-center justify-center border border-border bg-muted font-mono-ui text-xl font-medium text-accent">
              {initials}
            </div>

            <div className="min-w-0">
              <h2 className="break-words text-xl font-medium text-foreground">
                {user.full_name ||
                  "Unnamed analyst"}
              </h2>

              <div className="mt-2 flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
                <Mail
                  size={14}
                  className="shrink-0"
                />

                <span className="break-all">
                  {user.email}
                </span>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <Pill tone="green">
                  <User size={12} />
                  Analyst
                </Pill>

                <Pill
                  tone={
                    user.is_verified
                      ? "green"
                      : "copper"
                  }
                >
                  {user.is_verified ? (
                    <CheckCircle2 size={12} />
                  ) : (
                    <XCircle size={12} />
                  )}

                  {user.is_verified
                    ? "Verified"
                    : "Email not verified"}
                </Pill>
              </div>
            </div>
          </div>
        </Panel>


        {/* Account status */}
        <Panel
          title="Account status"
          meta="Access information"
        >
          <div className="space-y-5">

            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center border border-border bg-muted">
                <ShieldCheck
                  size={15}
                  className="text-accent"
                />
              </div>

              <div className="min-w-0">
                <div className="font-mono-ui text-[9px] uppercase tracking-wide text-muted-foreground">
                  Account state
                </div>

                <div className="mt-1 text-sm">
                  {user.is_active
                    ? "Active"
                    : "Inactive"}
                </div>
              </div>
            </div>


            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center border border-border bg-muted">
                {user.is_verified ? (
                  <CheckCircle2
                    size={15}
                    className="text-primary"
                  />
                ) : (
                  <XCircle
                    size={15}
                    className="text-accent"
                  />
                )}
              </div>

              <div className="min-w-0">
                <div className="font-mono-ui text-[9px] uppercase tracking-wide text-muted-foreground">
                  Verification
                </div>

                <div className="mt-1 text-sm">
                  {user.is_verified
                    ? "Email verified"
                    : "Email not verified"}
                </div>
              </div>
            </div>

          </div>
        </Panel>
      </div>


      {/* Account timeline */}
      <div className="mt-5">
        <Panel
          title="Account timeline"
          meta="Session and registration history"
        >
          <div className="grid gap-4 md:grid-cols-2">

            <div className="border border-border bg-card p-5">
              <div className="flex items-start gap-3">

                <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-border bg-muted">
                  <CalendarDays
                    size={16}
                    className="text-accent"
                  />
                </div>

                <div className="min-w-0">
                  <div className="font-mono-ui text-[9px] uppercase tracking-wide text-muted-foreground">
                    Member since
                  </div>

                  <div className="mt-2 text-sm font-medium">
                    {formatDate(user.created_at)}
                  </div>

                  <div className="mt-1 text-xs text-muted-foreground">
                    Account creation date
                  </div>
                </div>

              </div>
            </div>


            <div className="border border-border bg-card p-5">
              <div className="flex items-start gap-3">

                <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-border bg-muted">
                  <Clock3
                    size={16}
                    className="text-accent"
                  />
                </div>

                <div className="min-w-0">
                  <div className="font-mono-ui text-[9px] uppercase tracking-wide text-muted-foreground">
                    Last login
                  </div>

                  <div className="mt-2 text-sm font-medium">
                    {formatDateTime(
                      user.last_login_at
                    )}
                  </div>

                  <div className="mt-1 text-xs text-muted-foreground">
                    Most recent authenticated session
                  </div>
                </div>

              </div>
            </div>

          </div>
        </Panel>
      </div>


      {/* Account identifier */}
      <div className="mt-5">
        <Panel
          title="Account identifier"
          meta="System reference"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

            <div>
              <div className="font-mono-ui text-[9px] uppercase tracking-wide text-muted-foreground">
                User ID
              </div>

              <div className="mt-2 break-all font-mono-ui text-xs text-foreground/80">
                {user.id}
              </div>
            </div>

            <Pill tone="green">
              Authentication enabled
            </Pill>

          </div>
        </Panel>
      </div>
    </>
  );
}