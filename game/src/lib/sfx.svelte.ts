// Bipes 8-bit gerados na hora (WebAudio, onda quadrada) — sem arquivos de áudio.
const KEY = "geodetective-sound";
export const sound = $state({ on: (() => { try { return localStorage.getItem(KEY) !== "off"; } catch { return true; } })() });

let ctx: AudioContext | null = null;
function tone(freq: number, start: number, dur: number, vol = 0.05, type: OscillatorType = "square") {
  if (!ctx) return;
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.type = type; o.frequency.value = freq;
  g.gain.setValueAtTime(vol, ctx.currentTime + start);
  g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + dur);
  o.connect(g).connect(ctx.destination);
  o.start(ctx.currentTime + start); o.stop(ctx.currentTime + start + dur + 0.02);
}

export function sfx(kind: "move" | "select" | "good" | "ok" | "bad" | "tick") {
  if (!sound.on) return;
  try {
    ctx ??= new AudioContext();
    if (kind === "move") tone(660, 0, 0.04, 0.03);
    else if (kind === "tick") tone(1200, 0, 0.02, 0.02);
    else if (kind === "select") { tone(523, 0, 0.06); tone(784, 0.06, 0.08); }
    else if (kind === "good") [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.08, 0.12));
    else if (kind === "ok") [523, 659, 784].forEach((f, i) => tone(f, i * 0.09, 0.1));
    else tone(220, 0, 0.18, 0.05), tone(165, 0.16, 0.25, 0.05);
  } catch { /* sem áudio: segue */ }
}

export function toggleSound() {
  sound.on = !sound.on;
  try { localStorage.setItem(KEY, sound.on ? "on" : "off"); } catch { /* ignora */ }
  if (sound.on) sfx("select");
}
