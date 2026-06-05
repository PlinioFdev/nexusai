import { test, expect } from '@playwright/test';
import path from 'path';
import { login } from './helpers';

test.describe('Documentos', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('upload PDF → status evolui para Pronto', async ({ page }) => {
    const fileInput = page.locator('input[aria-label="Selecionar arquivo para upload"]');
    await fileInput.setInputFiles(path.join(__dirname, 'fixtures/sample.pdf'));

    // Documento aparece na lista com status inicial (Pendente ou Processando)
    await expect(page.getByText(/Pendente|Processando/).first()).toBeVisible({ timeout: 15_000 });

    // Aguarda o pipeline Celery concluir — ingestão real pode levar até 2 min
    await expect(page.getByText('Pronto').first()).toBeVisible({ timeout: 120_000 });
  });
});
