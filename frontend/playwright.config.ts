import { defineConfig, devices } from '@playwright/test';

/**
 * Configuração dos smoke tests e2e do NexusAI.
 *
 * Variáveis de ambiente obrigatórias (ver .env.e2e.example na raiz):
 *   E2E_SLUG, E2E_EMAIL, E2E_PASSWORD, E2E_API_KEY
 *
 * Rodar localmente:
 *   export E2E_SLUG=... E2E_EMAIL=... E2E_PASSWORD=... E2E_API_KEY=...
 *   npm run test:e2e
 *
 * Rodar contra produção:
 *   BASE_URL=https://nexusai-gules-nine.vercel.app NEXT_PUBLIC_API_URL=https://nexusai-api-s5m9.onrender.com npm run test:e2e
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  timeout: 180_000,          // 3 min por teste — ingestão real pode demorar
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
    actionTimeout: 30_000,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
