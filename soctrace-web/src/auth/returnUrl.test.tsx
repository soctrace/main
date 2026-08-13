import { describe, expect, it } from "vitest";
import { getSafeLoginReturnPath } from "@/auth/returnUrl";

describe("campaign login return URL", () => {
  it("preserves pathname, query, and chapter hash", () => expect(getSafeLoginReturnPath({ pathname: "/campaigns/mijas-2027", search: "?edition=draft", hash: "#opportunity-map" })).toBe("/campaigns/mijas-2027?edition=draft#opportunity-map"));
  it.each(["https://evil.example/x", "//evil.example/x", "\\evil.example"])("rejects unsafe external return path %s", (pathname) => expect(getSafeLoginReturnPath({ pathname })).toBe("/dashboard"));
});
