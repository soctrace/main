import { useEffect } from "react";
import { useAuth } from "@/auth/AuthProvider";
import { trackDemoEvent } from "@/lib/demoAnalytics";

export function useDemoAccessTracking() {
  const { email } = useAuth();

  useEffect(() => {
    if (!email) return undefined;

    void trackDemoEvent("dashboard_enter", email);
    const heartbeatId = window.setInterval(() => {
      void trackDemoEvent("heartbeat", email);
    }, 60_000);

    return () => {
      window.clearInterval(heartbeatId);
      void trackDemoEvent("dashboard_exit", email);
    };
  }, [email]);
}
