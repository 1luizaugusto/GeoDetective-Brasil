// Opções do jogador — só no navegador (localStorage), sem servidor.
const KEY = "geodetective-settings-v1";
type CompareMode = "curtain" | "side" | "blink";
interface Settings { crt: boolean; compareMode: CompareMode; typewriter: boolean }
const DEFAULTS: Settings = { crt: true, compareMode: "curtain", typewriter: true };

function load(): Settings {
  try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") }; } catch { return { ...DEFAULTS }; }
}

export const settings = $state<Settings>(load());

export function saveSettings() {
  try { localStorage.setItem(KEY, JSON.stringify(settings)); } catch { /* modo privado */ }
  applySettings();
}

export function applySettings() {
  document.documentElement.classList.toggle("no-crt", !settings.crt);
}
