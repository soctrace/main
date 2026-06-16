import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import ts from "typescript";

const source = readFileSync(new URL("../src/auth/accessControl.ts", import.meta.url), "utf8");
const output = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;

const sandbox = {
  exports: {},
};
vm.runInNewContext(output, sandbox, { filename: "accessControl.ts" });

const { canAccessDashboard, getAuthorizedUser } = sandbox.exports;

const allowedEmails = [
  "soctrace@gmail.com",
  "espaciotania@gmail.com",
  "acatafal@gmail.com",
  "aureliano.daponte@gmail.com",
  "angelmartinezx2@gmail.com",
  "agantoniomaldonado@gmail.com",
  "guillermo.quero.resina@gmail.com",
  "antoniotorroles81@gmail.com",
];

for (const email of allowedEmails) {
  assert.equal(canAccessDashboard(email), true, `${email} should access dashboard`);
  assert.ok(getAuthorizedUser(email), `${email} should resolve an authorized profile`);
}

assert.equal(canAccessDashboard("not-authorized@example.com"), false);

console.log(`Demo access allowlist OK (${allowedEmails.length} authorized emails checked).`);
