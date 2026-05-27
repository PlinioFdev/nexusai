import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NexusAI",
  description: "Multi-tenant RAG Chatbot",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
