import { Activity, Check, TriangleAlert } from "lucide-react";
import { systemRecords, sources } from "../services/mockData";
import PageHeader from "../components/PageHeader";
import Stat from "../components/Stat";
import Panel from "../components/Panel";
import Pill from "../components/Pill";
import Button from "../components/Button";

export default function SystemStatus() {
  const healthy = systemRecords.filter((x) => x.status === "Operational").length;

  return (
    <>
      <PageHeader
        eyebrow="Infrastructure / local preview"
        title="System status."
        description="Operational view of the local retrieval, evidence, and analysis stack."
        action={<Pill tone="green"><Check size={12} /> All core systems operational</Pill>}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Stat label="Services" value={healthy} detail="Core services operational" accent />
        <Stat label="Sources" value={sources.length} detail="Configured evidence sources" />
        <Stat label="Index" value="Healthy" detail="Local retrieval index" accent />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Panel title="Retrieval stack" meta="Local services">
          <div className="divide-y divide-border">
            {systemRecords.map((item) => (
              <div key={item.name} className="flex items-center justify-between py-4">
                <div className="flex items-center gap-3">
                  <Activity size={15} className="text-accent" />
                  <div>
                    <div className="text-sm">{item.name}</div>
                    <div className="mt-1 font-mono-ui text-[9px] uppercase text-muted-foreground">
                      {item.detail}
                    </div>
                  </div>
                </div>
                <Pill tone={item.status === "Operational" ? "green" : "red"}>
                  {item.status}
                </Pill>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Source connectivity" meta="Configured sources">
          <div className="divide-y divide-border">
            {sources.map((source) => (
              <div key={source.name} className="flex items-center justify-between py-4">
                <div>
                  <div className="text-sm">{source.name}</div>
                  <div className="mt-1 font-mono-ui text-[9px] uppercase text-muted-foreground">
                    {source.type}
                  </div>
                </div>
                <Pill tone="green"><Check size={11} /> Connected</Pill>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="mt-5 flex justify-end">
        <Button variant="outline" onClick={() => window.location.reload()}>
          <Activity size={15} /> Refresh status
        </Button>
      </div>
    </>
  );
}