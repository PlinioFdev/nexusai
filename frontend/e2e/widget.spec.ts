import { test, expect } from '@playwright/test';

test.describe('Widget Embeddable', () => {
  test('embed com api-key válida → abrir chat → enviar pergunta → receber resposta', async ({ page }) => {
    const baseUrl = process.env.BASE_URL ?? 'http://localhost:3000';
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8001';
    const apiKey = process.env.E2E_API_KEY!;

    // Simula site externo do cliente com o widget embutido
    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head><meta charset="utf-8" /></head>
        <body>
          <p>Página do cliente</p>
          <script
            src="${baseUrl}/widget/embed.js"
            data-api-key="${apiKey}"
            data-base-url="${apiUrl}"
          ></script>
        </body>
      </html>
    `);

    // Botão flutuante aparece no canto inferior direito
    const openButton = page.getByRole('button', { name: 'Abrir chat' });
    await expect(openButton).toBeVisible({ timeout: 10_000 });
    await openButton.click();

    // Painel do widget abre com área de input
    const widgetTextarea = page.locator('textarea[placeholder="Digite sua pergunta..."]');
    await expect(widgetTextarea).toBeVisible();

    // Envia pergunta
    await widgetTextarea.fill('Olá! Pode me ajudar?');
    await page.getByRole('button', { name: 'Enviar mensagem' }).click();

    // Aguarda resposta: textarea fica desabilitada durante o envio e volta ao normal
    await expect(widgetTextarea).toBeDisabled({ timeout: 5_000 });
    await expect(widgetTextarea).toBeEnabled({ timeout: 30_000 });
  });
});
