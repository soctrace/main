import { LeftSidebar } from "@/components/layout/LeftSidebar";
import { RightSidebar } from "@/components/layout/RightSidebar";
import { Topbar } from "@/components/layout/Topbar";
import { AiDock } from "@/components/layout/AiDock";
import { SocTraceMap } from "@/components/map/SocTraceMap";
import { useDashboardBootstrap } from "@/hooks/useDashboardBootstrap";
import { useDemoAccessTracking } from "@/hooks/useDemoAccessTracking";

export function DashboardPage() {
  useDashboardBootstrap();
  useDemoAccessTracking();

  return (
    <div className="dashboard-shell min-h-screen p-3 text-slate-100 lg:p-3">
      <div className="mx-auto flex max-w-[1800px] flex-col gap-3">
        <Topbar />

        <div className="grid min-h-[calc(100vh-7rem)] gap-3 xl:grid-cols-[344px_minmax(0,1fr)_390px]">
          <div className="min-h-fit xl:sticky xl:top-3 xl:h-auto">
            <LeftSidebar />
          </div>

          <div className="grid gap-3 self-start xl:grid-rows-[520px_auto]">
            <SocTraceMap />
            <AiDock />
          </div>

          <div className="min-h-[300px] xl:sticky xl:top-3 xl:h-[calc(100vh-6.25rem)]">
            <RightSidebar />
          </div>
        </div>
      </div>
    </div>
  );
}
