export type SocTraceRole = "admin" | "demo_full" | "demo_limited" | "pro" | "premium";

export type SocTraceAccess = {
  email: string;
  role: SocTraceRole;
  access: "full" | "limited";
  allowedLayers?: string[];
  deniedLayers?: string[];
};

type DemoAccessIdentity = {
  email?: string | null;
  user_metadata?: {
    email?: unknown;
  } | null;
  identities?: unknown[] | null;
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

export const FRIENDS_AND_FAMILY_ALLOWED_EMAIL_SET = new Set<string>(
  FRIENDS_AND_FAMILY_ALLOWED_EMAILS.map((email) => email.trim().toLowerCase()),
);

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

const AUTHORIZED_EMAILS = AUTHORIZED_USERS.map((user) => user.email.trim().toLowerCase());

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export function getRawDemoAccessEmail(identity?: string | DemoAccessIdentity | null): string | null {
  if (!identity) return null;
  if (typeof identity === "string") return stringValue(identity);
  const firstIdentity = identity.identities?.[0] as { email?: unknown } | undefined;

  return (
    stringValue(identity.email) ??
    stringValue(identity.user_metadata?.email) ??
    stringValue(firstIdentity?.email) ??
    null
  );
}

export function normalizeDemoAccessEmail(identity?: string | DemoAccessIdentity | null): string | null {
  return getRawDemoAccessEmail(identity)?.trim().toLowerCase() ?? null;
}

export function getAuthorizedUser(identity?: string | DemoAccessIdentity | null): SocTraceAccess | null {
  const normalizedEmail = normalizeDemoAccessEmail(identity);
  if (!normalizedEmail) return null;
  return AUTHORIZED_USERS.find((user) => user.email.toLowerCase() === normalizedEmail) ?? null;
}

export function canAccessDashboard(identity?: string | DemoAccessIdentity | null): boolean {
  const rawEmail = getRawDemoAccessEmail(identity);
  const normalizedEmail = normalizeDemoAccessEmail(identity);
  const allowed = Boolean(normalizedEmail && getAuthorizedUser(normalizedEmail));

  console.info("[DemoAccess]", {
    rawEmail,
    normalizedEmail,
    allowed,
    allowedEmails: AUTHORIZED_EMAILS,
  });

  return allowed;
}

export function canAccessLayer(identity: string | DemoAccessIdentity | null | undefined, layerId: string): boolean {
  const user = getAuthorizedUser(identity);
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
