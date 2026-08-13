import { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { ProtectedRoute } from "@/auth/ProtectedRoute";
import { AuthenticatedRoute } from "@/auth/AuthenticatedRoute";
import { CampaignRoute } from "@/features/campaigns/components/CampaignAccess";

const LandingPage = lazy(async () => ({
  default: (await import("@/landing/LandingPage")).LandingPage,
}));

const DashboardPage = lazy(async () => ({
  default: (await import("@/pages/DashboardPage")).DashboardPage,
}));

const RequestDemoPage = lazy(async () => ({
  default: (await import("@/pages/RequestDemoPage")).RequestDemoPage,
}));

const LoginPage = lazy(async () => ({
  default: (await import("@/pages/LoginPage")).LoginPage,
}));

const CampaignReportPage = lazy(async () => ({ default: (await import("@/pages/CampaignReportPage")).CampaignReportPage }));
const CampaignStudioPage = lazy(async () => ({ default: (await import("@/pages/CampaignStudioPage")).CampaignStudioPage }));

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<div className="min-h-screen bg-[#05070c]" />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/demo" element={<Navigate to="/login" replace />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route path="/dashboard/campaigns" element={<AuthenticatedRoute><CampaignStudioPage /></AuthenticatedRoute>} />
            <Route path="/campaigns/:slug" element={<CampaignRoute><CampaignReportPage /></CampaignRoute>} />
            <Route path="/request-demo" element={<RequestDemoPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
