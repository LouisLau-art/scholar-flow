import { defineConfig, devices } from '@playwright/test';

const playwrightPort = Number.parseInt(process.env.PLAYWRIGHT_PORT ?? process.env.PORT ?? '3000', 10);
const playwrightBaseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${playwrightPort}`;
const shouldStartWebServer = process.env.PLAYWRIGHT_WEB_SERVER !== '0';
// 默认不复用已有 dev server：
// - 避免误连到其他项目/残留进程占用的端口（会导致 404/空白页，且排查困难）
// - 需要复用时显式设置 PLAYWRIGHT_REUSE_EXISTING_SERVER=1
const reuseExistingServer = process.env.PLAYWRIGHT_REUSE_EXISTING_SERVER === '1';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: playwrightBaseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  ...(shouldStartWebServer
    ? {
        webServer: {
          command: `bun run dev -- --port ${playwrightPort}`,
          url: playwrightBaseURL,
          // 中文注释：CI 环境不允许复用“外部已有服务”，避免误连到其他项目的 3000/3001（导致 404/错误页面）。
          reuseExistingServer,
          timeout: 120000,
        },
      }
    : {}),
});
