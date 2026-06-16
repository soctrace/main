export type SocTraceRole = "admin" | "demo_full" | "demo_limited" | "pro" | "premium";

export type SocTraceAccess = {
  email: string;
  role: SocTraceRole;
  access: "full" | "limited";
  allowedLayers?: string[];
  deniedLayers?: string[];
};

export const FRIENDS_AND_FAMILY_ALLOWED_EMAILS = [
  "espaciotania@gmail.com",
  "acatafal@gmail.com",
  "aureliano.daponte@gmail.com",
  "angelmartinezx2@gmail.com",
  "agantoniomaldonado@gmail.com",
  "guillermo.quero.resina@gmail.com",
  "antoniotorroles81@gmail.com",
] as const;

export const AUTHORIZED_USERS: SocTraceAccess[] = [
  {
    email: "soctrace@gmail.com",
    role: "admin",
    access: "full",
  },
  ...FRIENDS_AND_FAMILY_ALLOWED_EMAILS.map((email) => ({
    email,
    role: "demo_full" as const,
    access: "full" as const,
  })),
];

export function getAuthorizedUser(email?: string | null): SocTraceAccess | null {
  if (!email) return null;
  const normalizedEmail = email.trim().toLowerCase();
  return AUTHORIZED_USERS.find((user) => user.email.toLowerCase() === normalizedEmail) ?? null;
}

export function canAccessDashboard(email?: string | null): boolean {
  return Boolean(getAuthorizedUser(email));
}

export function canAccessLayer(email: string | null | undefined, layerId: string): boolean {
  const user = getAuthorizedUser(email);
  if (!user) return false;
  if (user.role === "admin") return true;
  if (user.access === "full") return true;
  if (user.deniedLayers?.includes(layerId)) return false;
  if (user.allowedLayers?.includes(layerId)) return true;
  return false;
}

export const mockUser: SocTraceAccess = {
  email: "dev@soctrace.local",
  role: "admin",
  access: "full",
};
