export {
  AUTHORIZED_USERS as ALLOWED_DEMO_USERS,
  canAccessDashboard as isAllowedDemoUser,
  getAuthorizedUser,
  mockUser,
} from "@/auth/accessControl";

const bypassAuthEnv = import.meta.env.VITE_BYPASS_AUTH;

export const shouldBypassAuth = import.meta.env.DEV && bypassAuthEnv === "true";
