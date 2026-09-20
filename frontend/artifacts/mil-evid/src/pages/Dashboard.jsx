import { ChevronDown, ChevronRight, Plus } from "lucide-react";
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

import {
    analyses as initialAnalyses,
    perspectiveDistribution,
    sources,
    trend,
} from "../services/mockData";

import Panel from "../components/Panel";
import Stat from "../components/Stat";
import Pill from "../components/Pill";
import AnalysisRow from "../components/AnalysisRow";
export default function Dashboard() {
    return (
        <div className="min-h-screen bg-background">

            {/* =========================================================
                HERO / MOUNTAIN BACKGROUND
            ========================================================= */}

            <div className="relative min-h-[300px] overflow-hidden border-b border-border">

                {/* Light-mode mountains */}
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
            opacity-100
            dark:hidden
        "
                />

                {/* Dark-mode mountains */}
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

                {/* LEFT DARK → RIGHT TRANSPARENT GRADIENT */}
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

                {/* Hero content */}
                <div
                    className="
            relative
            z-10
            flex
            min-h-[300px]
            flex-col
            justify-between
            px-6
            py-7
            sm:px-8
            sm:py-9
            lg:px-10
            lg:py-10
        "
                >

                    <div className="max-w-2xl">

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
                            <span className="h-px w-6 bg-accent" />
                            Analyst overview / 18 Mar 2025
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
                            Good morning, Cheyu.
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
                            A clear view of your current research surface. Five analyses
                            are in the room; one is waiting for a closer read.
                        </p>

                    </div>

                    <div className="mt-8 flex justify-end">

                        <Link
                            to="/analysis/new"
                            className="
                    inline-flex
                    h-10
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


            {/* =========================================================
                STATS
            ========================================================= */}

            <div className="grid gap-3 bg-background p-4 sm:grid-cols-2 xl:grid-cols-4">

                <Stat
                    label="Total analyses"
                    value="27"
                    detail="+6 from February"
                    accent
                />

                <Stat
                    label="Completed"
                    value="24"
                    detail="89% of all runs"
                />

                <Stat
                    label="Average confidence"
                    value="78.4%"
                    detail="+3.1 points over baseline"
                />

                <Stat
                    label="Evidence sources"
                    value="126.3k"
                    detail="Across 6 connected sources"
                />

            </div>

            {/* =========================================================
          DASHBOARD CONTENT
      ========================================================= */}

            <div className="bg-background px-4 pb-4">

                {/* =======================================================
            CHARTS
        ======================================================= */}

                <div className="grid gap-5 xl:grid-cols-[1.35fr_.65fr]">

                    {/* ANALYSIS ACTIVITY */}

                    <Panel
                        title="Analysis Trends"
                        meta="Analyses and confidence over time"
                        action={
                            <div className="relative">
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
                                    defaultValue="30"
                                    onChange={(e) => {
                                        console.log("Selected range:", e.target.value);
                                    }}
                                >
                                    <option value="7">Last 7 days</option>
                                    <option value="30">Last 30 days</option>
                                    <option value="90">Last 90 days</option>
                                    <option value="180">Last 6 months</option>
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
                        }
                    >
                        <div className="h-64 w-full">
                            <ResponsiveContainer width="100%" height="100%">
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
                                        vertical={true}
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

                                    {/* LEFT AXIS — ANALYSES */}
                                    <YAxis
                                        yAxisId="left"
                                        orientation="left"
                                        domain={[0, "auto"]}
                                        tick={{
                                            fill: "hsl(var(--muted-foreground))",
                                            fontSize: 9,
                                        }}
                                        axisLine={false}
                                        tickLine={false}
                                        width={28}
                                    />

                                    {/* RIGHT AXIS — CONFIDENCE */}
                                    <YAxis
                                        yAxisId="right"
                                        orientation="right"
                                        domain={[0, 100]}
                                        tick={{
                                            fill: "hsl(var(--muted-foreground))",
                                            fontSize: 9,
                                        }}
                                        tickFormatter={(value) => `${value}%`}
                                        axisLine={false}
                                        tickLine={false}
                                        width={32}
                                    />

                                    <Tooltip
                                        contentStyle={{
                                            background: "hsl(var(--card))",
                                            border: "1px solid hsl(var(--border))",
                                            borderRadius: "6px",
                                            fontSize: 10,
                                        }}
                                        formatter={(value, name) => {
                                            if (name === "Average Confidence") {
                                                return [`${value}%`, name];
                                            }

                                            return [value, name];
                                        }}
                                    />

                                    {/* ANALYSIS BARS */}
                                    <Bar
                                        yAxisId="left"
                                        dataKey="analyses"
                                        name="Analyses"
                                        fill="hsl(var(--chart-3))"
                                        barSize={10}
                                        radius={[1, 1, 0, 0]}
                                    />

                                    {/* CONFIDENCE LINE */}
                                    <Line
                                        yAxisId="right"
                                        type="monotone"
                                        dataKey="confidence"
                                        name="Average Confidence"
                                        stroke="hsl(var(--accent))"
                                        strokeWidth={2}
                                        dot={{
                                            r: 2.5,
                                            fill: "hsl(var(--accent))",
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
                                            color: "hsl(var(--muted-foreground))",
                                            paddingTop: "8px",
                                        }}
                                    />
                                </ComposedChart>
                            </ResponsiveContainer>
                        </div>
                    </Panel>


                    {/* PERSPECTIVE DISTRIBUTION */}

                    <Panel
                        title="Perspective distribution"
                        meta="All completed analyses"
                    >

                        <div className="flex h-64 items-center">

                            <div className="h-52 w-1/2">

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

                                            <Cell fill="hsl(var(--primary))" />
                                            <Cell fill="hsl(var(--accent))" />
                                            <Cell fill="hsl(var(--chart-3))" />
                                            <Cell fill="hsl(var(--chart-4))" />
                                            <Cell fill="hsl(var(--chart-5))" />

                                        </Pie>


                                        <Tooltip
                                            contentStyle={{
                                                background: "hsl(var(--card))",
                                                border: "1px solid hsl(var(--border))",
                                                borderRadius: "8px",
                                                fontSize: 11,
                                            }}
                                        />

                                    </PieChart>

                                </ResponsiveContainer>

                            </div>


                            <div className="space-y-3 text-xs">

                                {perspectiveDistribution.map((item, i) => (

                                    <div
                                        className="flex items-center justify-between gap-4"
                                        key={item.name}
                                    >

                                        <span className="flex items-center gap-2">

                                            <span
                                                className="h-2 w-2 rounded-full"
                                                style={{
                                                    background: [
                                                        "hsl(var(--primary))",
                                                        "hsl(var(--accent))",
                                                        "hsl(var(--chart-3))",
                                                        "hsl(var(--chart-4))",
                                                        "hsl(var(--chart-5))",
                                                    ][i],
                                                }}
                                            />

                                            {item.name}

                                        </span>


                                        <span className="font-mono-ui text-muted-foreground">
                                            {item.value}%
                                        </span>

                                    </div>

                                ))}

                            </div>

                        </div>

                    </Panel>

                </div>


                {/* =======================================================
            EVIDENCE SOURCES
        ======================================================= */}

                <div className="mt-5">

                    <Panel
                        title="Evidence sources"
                        meta="Connector register"
                    >

                        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">

                            {sources.map((source) => (

                                <div
                                    className="
                    rounded-md
                    border
                    border-border
                    bg-card
                    p-4
                  "
                                    key={source.name}
                                >

                                    <div className="flex items-center justify-between gap-3">

                                        <div className="text-sm font-medium">
                                            {source.name}
                                        </div>


                                        <Pill
                                            tone={
                                                source.status === "Connected"
                                                    ? "green"
                                                    : "copper"
                                            }
                                        >
                                            {source.status}
                                        </Pill>

                                    </div>


                                    <div
                                        className="
                      mt-3
                      flex
                      items-center
                      justify-between
                      font-mono-ui
                      text-[9px]
                      uppercase
                      text-muted-foreground
                    "
                                    >

                                        <span>
                                            {source.category}
                                        </span>

                                        <span>
                                            {source.recordCount}
                                        </span>

                                    </div>


                                    <div className="mt-2 text-[11px] text-muted-foreground">
                                        Last sync {source.lastSync}
                                    </div>

                                </div>

                            ))}

                        </div>

                    </Panel>

                </div>


                {/* =======================================================
            RECENT ANALYSES + SOURCE HEALTH
        ======================================================= */}

                <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_.65fr]">

                    {/* RECENT ANALYSES */}

                    <Panel
                        title="Recent analyses"
                        meta="Sorted by most recent"
                        action={
                            <Link
                                to="/history"
                                className="text-xs text-accent hover:underline"
                                data-testid="link-dashboard-history"
                            >
                                View history
                            </Link>
                        }
                    >

                        <div className="divide-y divide-border">

                            {initialAnalyses
                                .slice(0, 4)
                                .map((item) => (

                                    <AnalysisRow
                                        item={item}
                                        key={item.id}
                                    />

                                ))}

                        </div>

                    </Panel>


                    {/* SOURCE HEALTH */}

                    <Panel
                        title="Source health"
                        meta="Last sync status"
                    >

                        <div className="space-y-1">

                            {sources
                                .slice(0, 4)
                                .map((source) => (

                                    <div
                                        className="
                      flex
                      items-center
                      justify-between
                      border-b
                      border-border
                      py-3
                      last:border-0
                    "
                                        key={source.name}
                                    >

                                        <div>

                                            <div className="text-xs">
                                                {source.name}
                                            </div>

                                            <div className="mt-1 font-mono-ui text-[9px] text-muted-foreground">
                                                {source.lastSync}
                                            </div>

                                        </div>


                                        <Pill
                                            tone={
                                                source.status === "Connected"
                                                    ? "green"
                                                    : "copper"
                                            }
                                        >
                                            {source.status}
                                        </Pill>

                                    </div>

                                ))}

                        </div>


                        <Link
                            to="/system"
                            className="
                mt-3
                inline-flex
                items-center
                gap-1
                text-xs
                text-accent
              "
                            data-testid="link-dashboard-system"
                        >
                            Inspect system
                            <ChevronRight size={13} />
                        </Link>

                    </Panel>

                </div>

            </div>

        </div >
    );
}