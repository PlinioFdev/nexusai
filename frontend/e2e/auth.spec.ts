import { test, expect } from '@playwright/test';
import { login } from './helpers';

test.describe('Autenticação', () => {
  test('login com credenciais válidas redireciona para /documents', async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(/\/documents/);
  });

  test('login com senha errada exibe mensagem de erro', async ({ page }) => {
    await page.goto('/login');
    await page.locator('#slug').fill(process.env.E2E_SLUG!);
    await page.locator('#email').fill(process.env.E2E_EMAIL!);
    await page.locator('#password').fill('senha-invalida-000');
    await page.getByRole('button', { name: 'Entrar' }).click();
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });
});
