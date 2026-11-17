import type { Attempt } from "./types";

const KEY = "geodetective-progress-v1";

function load(): Record<string, Attempt> {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "{}");
  } catch {
    return {};
  }
}

// Progresso só no navegador do jogador (sem servidor, sem dados pessoais).
export const progress = $state<{ attempts: Record<string, Attempt> }>({ attempts: load() });

export function record(id: string, a: Attempt) {
  progress.attempts[id] = a;
  try {
    localStorage.setItem(KEY, JSON.stringify(progress.attempts));
  } catch {
    /* modo privado: segue sem salvar */
  }
}

export function resetProgress() {
  progress.attempts = {};
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignora */
  }
}
