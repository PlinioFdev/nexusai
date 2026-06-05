import { type Page } from '@playwright/test';

/**
 * Faz login com as credenciais das variáveis de ambiente e2e.
 * Aguarda o redirecionamento para /documents antes de retornar.
 */
export async function login(page: Page): Promise<void> {
  await page.goto('/login');
  await page.locator('#slug').fill(process.env.E2E_SLUG!);
  await page.locator('#email').fill(process.env.E2E_EMAIL!);
  await page.locator('#password').fill(process.env.E2E_PASSWORD!);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await page.waitForURL(/\/documents/);
}
