export type LoginReturnLocation = { pathname?: string; search?: string; hash?: string };

export function getSafeLoginReturnPath(from?: LoginReturnLocation | null): string {
  const pathname = from?.pathname;
  if (!pathname || !pathname.startsWith("/") || pathname.startsWith("//") || pathname.includes("\\")) return "/dashboard";
  const search = from?.search?.startsWith("?") ? from.search : "";
  const hash = from?.hash?.startsWith("#") ? from.hash : "";
  return `${pathname}${search}${hash}`;
}
