// Entry point do widget embeddable.
// Lê data-api-key e data-base-url do script tag e monta o Widget React no DOM.
// Uso:
//   <script
//     src="https://nexusai.vercel.app/widget.js"
//     data-api-key="sua-chave"
//     data-base-url="https://api.nexusai.com"
//   ></script>
//
// IMPORTANTE: document.currentScript é null após qualquer operação assíncrona.
// Por isso é capturado imediatamente na execução síncrona do módulo.

import React from "react";
import ReactDOM from "react-dom/client";
import { Widget } from "./Widget";

// Captura síncrona — deve ser a primeira linha executável
const _scriptEl = document.currentScript as HTMLScriptElement | null;

function mount() {
  const apiKey = _scriptEl?.dataset.apiKey ?? "";
  const baseUrl = _scriptEl?.dataset.baseUrl ?? "http://localhost:8000";

  if (!apiKey) {
    console.warn("[NexusAI Widget] data-api-key não informado — widget não será montado.");
    return;
  }

  // Evita montar duas vezes se o script for carregado múltiplas vezes
  if (document.getElementById("nexusai-widget-root")) {
    console.warn("[NexusAI Widget] Widget já montado — ignorando chamada dupla.");
    return;
  }

  const container = document.createElement("div");
  container.id = "nexusai-widget-root";
  document.body.appendChild(container);

  const root = ReactDOM.createRoot(container);
  root.render(React.createElement(Widget, { apiKey, baseUrl }));
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mount);
} else {
  mount();
}
