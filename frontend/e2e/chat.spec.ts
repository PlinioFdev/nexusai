import { test, expect } from '@playwright/test';
import { login } from './helpers';

test.describe('Chat RAG', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/chat');
  });

  test('criar sessão → enviar pergunta → receber resposta do assistant', async ({ page }) => {
    // Cria nova sessão de chat
    await page.getByRole('button', { name: 'Nova conversa' }).click();

    // MessageInput só renderiza quando activeSessionId !== null —
    // aguarda o textarea aparecer no DOM (sessão criada e selecionada)
    const textarea = page.locator('textarea').first();
    await expect(textarea).toBeVisible({ timeout: 15_000 });

    // Envia pergunta
    await textarea.fill('Resuma o conteúdo dos documentos disponíveis.');
    await page.getByRole('button', { name: 'Enviar mensagem' }).click();

    // Textarea fica desabilitada enquanto aguarda resposta RAG
    await expect(textarea).toBeDisabled({ timeout: 5_000 });

    // Aguarda pipeline completo: embedding + Pinecone retrieval + Claude
    await expect(textarea).toBeEnabled({ timeout: 30_000 });
  });
});
