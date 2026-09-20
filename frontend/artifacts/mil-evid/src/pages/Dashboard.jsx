import { useEffect, useMemo, useState } from "react";

import {
  ChevronDown,
  ChevronRight,
  Plus,
  RefreshCw,
} from "lucide-react";

import { Link } from "react-router-dom";

import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiClient } from "../services/apiClient";

import Panel from "../components/Panel";
import Stat from "../components/Stat";
import Pill from "../components/Pill";
import AnalysisRow from "../components/AnalysisRow";

const PERSPECTIVES = [
  {
    key: "military",
    name: "Military",
    color: "hsl(var(--primary))",
  },
  {
    key: "legal",
    name: "Legal",
    color: "hsl(var(--accent))",
  },
  {
    key: "historical",
    name: "Historical",
    color: "hsl(var(--chart-3))",
  },
];

function formatDate(date) {
  if (!date) return "—";

  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function formatShortDate(date) {
  if (!date) return "—";

  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
  }).format(parsed);
}

function getDateKey(date, range) {
  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  if (range > 30) {
    return `${parsed.getFullYear()}-${String(
      parsed.getMonth() + 1
    ).padStart(2, "0")}`;
  }

  return `${parsed.getFullYear()}-${String(
    parsed.getMonth() + 1
  ).padStart(2, "0")}-${String(
    parsed.getDate()
  ).padStart(2, "0")}`;
}

function formatTrendLabel(key, range) {
  if (!key) return "";

  if (range > 30) {
    const [year, month] = key.split("-");

    const date = new Date(
      Number(year),
      Number(month) - 1,
      1
    );

    return new Intl.DateTimeFormat("en-GB", {
      month: "short",
      year: range > 90 ? "2-digit" : undefined,
    }).format(date);
  }

  const [year, month, day] = key.split("-");

  const date = new Date(
    Number(year),
    Number(month) - 1,
    Number(day)
  );

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
  }).format(date);
}

function Dashboard() {
  const [analyses, setAnalyses] = useState([]);
  const [details, setDetails] = useState([]);

  const [range, setRange] = useState(30);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadDashboard(isRefresh = false) {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const history = await apiClient.listAnalyses();

      const historyData = Array.isArray(history)
        ? history
        : [];

      setAnalyses(historyData);

      const completed = historyData.filter(
        (item) =>
          String(item?.status).toLowerCase() ===
          "completed"
      );

      const results = await Promise.allSettled(
        completed.map((item) =>
          apiClient.getAnalysis(item.analysis_id)
        )
      );

      const successfulDetails = results
        .filter(
          (result) =>
            result.status === "fulfilled"
        )
        .map((result) => result.value)
        .filter(Boolean);

      setDetails(successfulDetails);
    } catch (err) {
      console.error(
        "Failed to load dashboard:",
        err
      );

      setError(
        err?.message ||
          "Failed to load dashboard data."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  /* =========================================================
     BASIC STATISTICS
  ========================================================= */

  const completedAnalyses = useMemo(() => {
    return analyses.filter(
      (item) =>
        String(item?.status).toLowerCase() ===
        "completed"
    );
  }, [analyses]);

  const totalAnalyses = analyses.length;

  const completedCount = completedAnalyses.length;

  const averageConfidence = useMemo(() => {
    if (completedCount === 0) {
      return 0;
    }

    const total = completedAnalyses.reduce(
      (sum, item) =>
        sum +
        Number(item?.overall_confidence || 0),
      0
    );

    return (
      (total / completedCount) 
    );
  }, [completedAnalyses, completedCount]);

  const totalEvidence = useMemo(() => {
    return completedAnalyses.reduce(
      (sum, item) =>
        sum +
        Number(item?.evidence_count || 0),
      0
    );
  }, [completedAnalyses]);

  /* =========================================================
     PERSPECTIVE DISTRIBUTION
  ========================================================= */

  const perspectiveDistribution = useMemo(() => {
    const counts = {
      military: 0,
      legal: 0,
      historical: 0,
    };

    details.forEach((analysis) => {
      const perspectives = Array.isArray(
        analysis?.perspectives
      )
        ? analysis.perspectives
        : [];

      perspectives.forEach((perspective) => {
        const key = String(
          perspective?.perspective || ""
        ).toLowerCase();

        if (
          Object.prototype.hasOwnProperty.call(
            counts,
            key
          )
        ) {
          counts[key] += 1;
        }
      });
    });

    const total =
      counts.military +
      counts.legal +
      counts.historical;

    return PERSPECTIVES.map((perspective) => ({
      ...perspective,
      value:
        total > 0
          ? Number(
              (
                (counts[perspective.key] / total) *
                100
              ).toFixed(1)
            )
          : 0,
      count: counts[perspective.key],
    }));
  }, [details]);

  /* =========================================================
     ANALYSIS TREND
  ========================================================= */

  const trend = useMemo(() => {
    const now = new Date();

    const start = new Date(now);

    start.setDate(
      start.getDate() - (range - 1)
    );

    const relevant = analyses.filter((item) => {
      const date = new Date(
        item?.completed_at ||
          item?.started_at
      );

      return (
        !Number.isNaN(date.getTime()) &&
        date >= start &&
        date <= now
      );
    });

    const grouped = new Map();

    relevant.forEach((item) => {
      const date =
        item?.completed_at ||
        item?.started_at;

      const key = getDateKey(date, range);

      if (!key) return;

      if (!grouped.has(key)) {
        grouped.set(key, {
          key,
          analyses: 0,
          confidenceTotal: 0,
          confidenceCount: 0,
        });
      }

      const bucket = grouped.get(key);

      bucket.analyses += 1;

      if (
        item?.overall_confidence !== null &&
        item?.overall_confidence !== undefined
      ) {
        bucket.confidenceTotal +=
          Number(item.overall_confidence);

        bucket.confidenceCount += 1;
      }
    });

    return Array.from(grouped.values())
      .sort((a, b) =>
        a.key.localeCompare(b.key)
      )
      .map((bucket) => ({
        month: formatTrendLabel(
          bucket.key,
          range
        ),
        analyses: bucket.analyses,
        confidence:
          bucket.confidenceCount > 0
            ? Number(
                (
                  bucket.confidenceTotal /
                  bucket.confidenceCount
                ).toFixed(1)
              )
            : 0,
      }));
  }, [analyses, range]);

  /* =========================================================
     EVIDENCE SOURCES
  ========================================================= */

  const evidenceSources = useMemo(() => {
    const sourceMap = new Map();

    details.forEach((analysis) => {
      const evidence = Array.isArray(
        analysis?.evidence
      )
        ? analysis.evidence
        : [];

      evidence.forEach((record) => {
        const name =
          record?.source_name ||
          record?.source_type ||
          "Unknown source";

        if (!sourceMap.has(name)) {
          sourceMap.set(name, {
            name,
            sourceType:
              record?.source_type ||
              "Evidence source",
            count: 0,
            lastDate:
              record?.publication_date ||
              null,
          });
        }

        const source = sourceMap.get(name);

        source.count += 1;

        if (
          record?.publication_date &&
          (
            !source.lastDate ||
            new Date(
              record.publication_date
            ) >
              new Date(source.lastDate)
          )
        ) {
          source.lastDate =
            record.publication_date;
        }
      });
    });

    return Array.from(
      sourceMap.values()
    ).sort(
      (a, b) => b.count - a.count
    );
  }, [details]);

  /* =========================================================
     RECENT ANALYSES
  ========================================================= */

  const recentAnalyses = useMemo(() => {
    return [...analyses]
      .sort(
        (a, b) =>
          new Date(
            b?.completed_at ||
              b?.started_at
          ) -
          new Date(
            a?.completed_at ||
              a?.started_at
          )
      )
      .slice(0, 4);
  }, [analyses]);

  const rangeLabel = useMemo(() => {
    switch (range) {
      case 7:
        return "Last 7 days";
      case 30:
        return "Last 30 days";
      case 90:
        return "Last 90 days";
      case 180:
        return "Last 6 months";
      default:
        return "Selected period";
    }
  }, [range]);

  /* =========================================================
     RENDER
  ========================================================= */

  return (
    <div className="min-h-screen min-w-0 max-w-full overflow-x-hidden bg-background">
      {/* =====================================================
          HERO
      ===================================================== */}

      <div className="relative min-h-[300px] max-w-full overflow-hidden border-b border-border">
        <img
          src="/images/dark-mountains.png"
          alt=""
          aria-hidden="true"
          className="
            absolute
            inset-0
            h-full
            w-full
            object-cover
            object-center
            opacity-300
            dark:hidden
          "
        />

        <img
          src="/images/light-mountains.png"
          alt=""
          aria-hidden="true"
          className="
            absolute
            inset-0
            hidden
            h-full
            w-full
            object-cover
            object-center
            opacity-60
            dark:block
          "
        />

        <div
          className="
            absolute
            inset-0
            bg-gradient-to-r
            from-background
            via-background/80
            to-background/10
            dark:from-background
            dark:via-background/75
            dark:to-background/10
          "
        />

        <div
          className="
            relative
            z-10
            flex
            min-h-[300px]
            min-w-0
            max-w-full
            flex-col
            justify-between
            overflow-hidden
            px-6
            py-7
            sm:px-8
            sm:py-9
            lg:px-10
            lg:py-10
          "
        >
          <div className="min-w-0 max-w-2xl">
            <div
              className="
                mb-4
                flex
                items-center
                gap-2
                font-mono-ui
                text-[10px]
                uppercase
                tracking-[.18em]
                text-accent
              "
            >
              <span className="h-px w-6 shrink-0 bg-accent" />
              Analyst overview
            </div>

            <h1
              className="
                text-4xl
                font-semibold
                tracking-tight
                text-foreground
                sm:text-5xl
              "
            >
              MIL-EVID Dashboard
            </h1>

            <p
              className="
                mt-4
                max-w-xl
                text-sm
                leading-6
                text-muted-foreground
                sm:text-base
              "
            >
              A clear view of your current
              evidence-grounded military
              research surface.
            </p>

            {analyses.length > 0 && (
              <p className="mt-3 font-mono-ui text-[10px] uppercase tracking-[.12em] text-muted-foreground">
                Last updated{" "}
                {formatDate(
                  analyses[0]?.completed_at ||
                    analyses[0]?.started_at
                )}
              </p>
            )}
          </div>

          <div className="mt-8 flex justify-end">
            <Link
              to="/analysis/new"
              className="
                inline-flex
                h-10
                shrink-0
                items-center
                gap-2
                bg-accent
                px-5
                text-sm
                text-accent-foreground
                transition-opacity
                hover:opacity-90
              "
            >
              <Plus size={16} />
              New analysis
            </Link>
          </div>
        </div>
      </div>

      {/* =====================================================
          LOADING
      ===================================================== */}

      {loading && (
        <div className="max-w-full overflow-hidden border-b border-border bg-background p-8">
          <div className="mx-auto max-w-xl space-y-4">
            <div className="h-3 w-32 animate-pulse bg-muted" />
            <div className="h-12 w-full animate-pulse bg-muted" />
            <div className="h-12 w-2/3 animate-pulse bg-muted" />
          </div>
        </div>
      )}

      {/* =====================================================
          ERROR
      ===================================================== */}

      {!loading && error && (
        <div className="mx-4 mt-4 max-w-full overflow-hidden border border-destructive/30 bg-destructive/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="font-medium text-destructive">
                Unable to load dashboard
              </div>

              <div className="mt-1 break-words text-sm text-muted-foreground">
                {error}
              </div>
            </div>

            <button
              type="button"
              onClick={() => loadDashboard(true)}
              className="
                inline-flex
                shrink-0
                items-center
                gap-2
                border
                border-border
                px-3
                py-2
                text-xs
                hover:border-accent
                hover:text-accent
              "
            >
              <RefreshCw size={13} />
              Retry
            </button>
          </div>
        </div>
      )}

      {/* =====================================================
          DASHBOARD CONTENT
      ===================================================== */}

      {!loading && !error && (
        <div className="min-w-0 max-w-full overflow-x-hidden">
          {/* =================================================
              STATS
          ================================================= */}

          <div className="grid min-w-0 max-w-full gap-3 bg-background p-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Total analyses"
              value={String(totalAnalyses)}
              detail={
                totalAnalyses === 0
                  ? "No analyses yet"
                  : "Across your analysis history"
              }
              accent
            />

            <Stat
              label="Completed"
              value={String(completedCount)}
              detail={
                totalAnalyses > 0
                  ? `${Math.round(
                      (completedCount /
                        totalAnalyses) *
                        100
                    )}% of all runs`
                  : "No completed runs"
              }
            />

            <Stat
              label="Average confidence"
              value={`${averageConfidence.toFixed(
                1
              )}%`}
              detail={
                completedCount > 0
                  ? "Across completed analyses"
                  : "No confidence data yet"
              }
            />

            <Stat
              label="Evidence records"
              value={totalEvidence.toLocaleString()}
              detail={
                evidenceSources.length > 0
                  ? `Across ${evidenceSources.length} sources`
                  : "No evidence yet"
              }
            />
          </div>

          <div className="min-w-0 max-w-full overflow-x-hidden bg-background px-4 pb-4">
            {/* =================================================
                CHARTS
            ================================================= */}

            <div className="grid min-w-0 max-w-full gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,.65fr)]">
              {/* ANALYSIS ACTIVITY */}

              <div className="min-w-0 max-w-full overflow-hidden">
                <Panel
                  title="Analysis Trends"
                  meta={`${rangeLabel} · real completed analysis data`}
                  action={
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          loadDashboard(true)
                        }
                        disabled={refreshing}
                        className="
                          inline-flex
                          h-8
                          shrink-0
                          items-center
                          gap-1.5
                          border
                          border-border
                          px-2
                          text-[10px]
                          text-muted-foreground
                          hover:border-accent
                          hover:text-accent
                          disabled:opacity-50
                        "
                      >
                        <RefreshCw
                          size={12}
                          className={
                            refreshing
                              ? "animate-spin"
                              : ""
                          }
                        />
                        Refresh
                      </button>

                      <div className="relative shrink-0">
                        <select
                          className="
                            h-8
                            appearance-none
                            border
                            border-border
                            bg-card
                            px-3
                            pr-7
                            text-[10px]
                            text-muted-foreground
                            outline-none
                            focus:border-accent
                          "
                          value={range}
                          onChange={(event) =>
                            setRange(
                              Number(
                                event.target.value
                              )
                            )
                          }
                        >
                          <option value="7">
                            Last 7 days
                          </option>
                          <option value="30">
                            Last 30 days
                          </option>
                          <option value="90">
                            Last 90 days
                          </option>
                          <option value="180">
                            Last 6 months
                          </option>
                        </select>

                        <ChevronDown
                          size={13}
                          className="
                            pointer-events-none
                            absolute
                            right-2
                            top-1/2
                            -translate-y-1/2
                            text-muted-foreground
                          "
                        />
                      </div>
                    </div>
                  }
                >
                  {trend.length === 0 ? (
                    <div className="flex h-64 items-center justify-center px-4 text-center text-sm text-muted-foreground">
                      No analyses were completed during this period.
                    </div>
                  ) : (
                    <div className="h-64 min-w-0 w-full max-w-full">
                      <ResponsiveContainer
                        width="100%"
                        height="100%"
                      >
                        <ComposedChart
                          data={trend}
                          margin={{
                            top: 10,
                            right: 8,
                            left: -18,
                            bottom: 20,
                          }}
                        >
                          <CartesianGrid
                            stroke="hsl(var(--border))"
                            strokeDasharray="2 4"
                            vertical
                          />

                          <XAxis
                            dataKey="month"
                            tick={{
                              fill: "hsl(var(--muted-foreground))",
                              fontSize: 9,
                            }}
                            axisLine={false}
                            tickLine={false}
                          />

                          <YAxis
                            yAxisId="left"
                            orientation="left"
                            domain={[0, "auto"]}
                            allowDecimals={false}
                            tick={{
                              fill: "hsl(var(--muted-foreground))",
                              fontSize: 9,
                            }}
                            axisLine={false}
                            tickLine={false}
                            width={28}
                          />

                          <YAxis
                            yAxisId="right"
                            orientation="right"
                            domain={[0, 100]}
                            tick={{
                              fill: "hsl(var(--muted-foreground))",
                              fontSize: 9,
                            }}
                            tickFormatter={(value) =>
                              `${value}%`
                            }
                            axisLine={false}
                            tickLine={false}
                            width={32}
                          />

                          <Tooltip
                            contentStyle={{
                              background:
                                "hsl(var(--card))",
                              border:
                                "1px solid hsl(var(--border))",
                              borderRadius: "6px",
                              fontSize: 10,
                            }}
                          />

                          <Bar
                            yAxisId="left"
                            dataKey="analyses"
                            name="Analyses"
                            fill="hsl(var(--chart-3))"
                            barSize={10}
                            radius={[
                              1,
                              1,
                              0,
                              0,
                            ]}
                          />

                          <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="confidence"
                            name="Average Confidence"
                            stroke="hsl(var(--accent))"
                            strokeWidth={2}
                            dot={{
                              r: 2.5,
                              fill:
                                "hsl(var(--accent))",
                              strokeWidth: 0,
                            }}
                            activeDot={{
                              r: 4,
                            }}
                          />

                          <Legend
                            verticalAlign="bottom"
                            align="center"
                            iconType="circle"
                            iconSize={7}
                            wrapperStyle={{
                              fontSize: "10px",
                              color:
                                "hsl(var(--muted-foreground))",
                              paddingTop: "8px",
                            }}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Panel>
              </div>

              {/* PERSPECTIVE DISTRIBUTION */}

              <div className="min-w-0 max-w-full overflow-hidden">
                <Panel
                  title="Perspective distribution"
                  meta="Military · Legal · Historical"
                >
                  <div className="flex min-w-0 h-64 items-center">
                    <div className="h-52 min-w-0 w-1/2">
                      <ResponsiveContainer
                        width="100%"
                        height="100%"
                      >
                        <PieChart>
                          <Pie
                            data={perspectiveDistribution}
                            dataKey="value"
                            nameKey="name"
                            innerRadius={56}
                            outerRadius={80}
                            paddingAngle={3}
                          >
                            {perspectiveDistribution.map(
                              (item) => (
                                <Cell
                                  key={item.key}
                                  fill={item.color}
                                />
                              )
                            )}
                          </Pie>

                          <Tooltip
                            contentStyle={{
                              background:
                                "hsl(var(--card))",
                              border:
                                "1px solid hsl(var(--border))",
                              borderRadius: "8px",
                              fontSize: 11,
                            }}
                            formatter={(value) => [
                              `${value}%`,
                              "Share",
                            ]}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="min-w-0 flex-1 space-y-3 pl-3 text-xs">
                      {perspectiveDistribution.map(
                        (item) => (
                          <div
                            className="flex min-w-0 items-center justify-between gap-3"
                            key={item.key}
                          >
                            <span className="flex min-w-0 items-center gap-2">
                              <span
                                className="h-2 w-2 shrink-0 rounded-full"
                                style={{
                                  background:
                                    item.color,
                                }}
                              />

                              <span className="truncate">
                                {item.name}
                              </span>
                            </span>

                            <span className="shrink-0 font-mono-ui text-muted-foreground">
                              {item.value}%
                            </span>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                </Panel>
              </div>
            </div>

            {/* =================================================
                EVIDENCE SOURCES
            ================================================= */}

            <div className="mt-5 min-w-0 max-w-full overflow-hidden">
              <Panel
                title="Evidence sources"
                meta="Derived from persisted analysis evidence"
              >
                {evidenceSources.length === 0 ? (
                  <div className="py-10 text-center text-sm text-muted-foreground">
                    No evidence sources are available yet.
                  </div>
                ) : (
                  <div className="grid min-w-0 max-w-full gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {evidenceSources
                      .slice(0, 9)
                      .map((source) => (
                        <div
                          className="
                            min-w-0
                            max-w-full
                            overflow-hidden
                            rounded-md
                            border
                            border-border
                            bg-card
                            p-4
                          "
                          key={source.name}
                        >
                          <div className="flex min-w-0 items-center justify-between gap-3">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium">
                                {source.name}
                              </div>

                              <div className="mt-1 truncate font-mono-ui text-[9px] uppercase text-muted-foreground">
                                {source.sourceType}
                              </div>
                            </div>

                            <Pill tone="green">
                              Used
                            </Pill>
                          </div>

                          <div
                            className="
                              mt-3
                              flex
                              min-w-0
                              items-center
                              justify-between
                              gap-3
                              font-mono-ui
                              text-[9px]
                              uppercase
                              text-muted-foreground
                            "
                          >
                            <span className="truncate">
                              Evidence records
                            </span>

                            <span className="shrink-0">
                              {source.count.toLocaleString()}
                            </span>
                          </div>

                          {source.lastDate && (
                            <div className="mt-2 truncate text-[11px] text-muted-foreground">
                              Latest publication{" "}
                              {formatShortDate(
                                source.lastDate
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                  </div>
                )}
              </Panel>
            </div>

            {/* =================================================
                RECENT ANALYSES + PERSPECTIVE COVERAGE
            ================================================= */}

            <div className="mt-5 grid min-w-0 max-w-full gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,.65fr)]">
              {/* RECENT ANALYSES */}

              <div className="min-w-0 max-w-full overflow-hidden">
                <Panel
                  title="Recent analyses"
                  meta="Sorted by most recent"
                  action={
                    <Link
                      to="/history"
                      className="shrink-0 text-xs text-accent hover:underline"
                    >
                      View history
                    </Link>
                  }
                >
                  {recentAnalyses.length === 0 ? (
                    <div className="py-10 text-center text-sm text-muted-foreground">
                      No analyses have been created yet.
                    </div>
                  ) : (
                    <div className="min-w-0 max-w-full divide-y divide-border overflow-hidden">
                      {recentAnalyses.map((item) => (
                        <AnalysisRow
                          item={item}
                          key={item.analysis_id}
                        />
                      ))}
                    </div>
                  )}
                </Panel>
              </div>

              {/* PERSPECTIVE COVERAGE */}

              <div className="min-w-0 max-w-full overflow-hidden">
                <Panel
                  title="Perspective coverage"
                  meta="Actual persisted analysis perspectives"
                >
                  <div className="space-y-1">
                    {perspectiveDistribution.map(
                      (item) => (
                        <div
                          className="
                            border-b
                            border-border
                            py-4
                            last:border-0
                          "
                          key={item.key}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex min-w-0 items-center gap-2">
                              <span
                                className="h-2 w-2 shrink-0 rounded-full"
                                style={{
                                  background:
                                    item.color,
                                }}
                              />

                              <span className="truncate text-xs">
                                {item.name}
                              </span>
                            </div>

                            <span className="shrink-0 font-mono-ui text-[10px] text-muted-foreground">
                              {item.count} analyses
                            </span>
                          </div>

                          <div className="mt-3 h-1.5 overflow-hidden bg-muted">
                            <div
                              className="h-full"
                              style={{
                                width: `${Math.min(
                                  item.value,
                                  100
                                )}%`,
                                background:
                                  item.color,
                              }}
                            />
                          </div>
                        </div>
                      )
                    )}
                  </div>

                  <Link
                    to="/history"
                    className="
                      mt-4
                      inline-flex
                      items-center
                      gap-1
                      text-xs
                      text-accent
                    "
                  >
                    View all analyses
                    <ChevronRight size={13} />
                  </Link>
                </Panel>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;