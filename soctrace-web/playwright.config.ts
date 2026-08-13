import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  timeout: 30_000,
  fullyParallel: false,
  use: { baseURL: "http://127.0.0.1:4174", channel: "chrome", headless: true, trace: "retain-on-failure" },
  webServer: {
    command: "VITE_BYPASS_AUTH=false VITE_CAMPAIGN_TEST_MODE=true npm run dev -- --host 127.0.0.1 --port 4174",
    url: "http://127.0.0.1:4174",
    reuseExistingServer: false,
  },
});
