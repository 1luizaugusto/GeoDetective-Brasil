// Partida rápida: N casos sorteados, jogados do zero, com placar final e recordes.
import type { Challenge } from "./types";

const KEY = "geodetective-run-v1";
const BEST = "geodetective-best-runs-v1";

export interface Run { ids: string[]; points: (number | null)[]; guesses: (number | null)[]; started: string }
export interface BestRun { total: number; max: number; at: string }

function load<T>(k: string, fb: T): T {
  try { return JSON.parse(localStorage.getItem(k) ?? "null") ?? fb; } catch { return fb; }
}
function save(k: string, v: unknown) {
  try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* modo privado */ }
}

export const run = $state<{ cur: Run | null; best: BestRun[] }>({ cur: load<Run | null>(KEY, null), best: load<BestRun[]>(BEST, []) });

// Mudança "clara": o modelo vê mais do que o dobro da tolerância (|Δ| ≥ 10 pp). Sem isso, quase todo caso
// tem Δ ≈ 0 e chutar 0 sempre dá nota alta (medido: 91% dos pontos na campanha).
export const CLEAR_PP = 10;
const shuffle = <T,>(a: T[]) => { const b = [...a]; for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };

export function startRun(pool: Challenge[], n = 5): string {
  // composição: 3 mudanças claras + 1 armadilha/ganho (se houver) + estáveis para completar
  const clear = shuffle(pool.filter((c) => Math.abs(c.model_estimate_pp) >= CLEAR_PP));
  const tricky = shuffle(pool.filter((c) => (c.kind === "trap" || c.kind === "gain") && !clear.includes(c)));
  const calm = shuffle(pool.filter((c) => !clear.includes(c) && !tricky.includes(c)));
  const picked = [...clear.slice(0, 3), ...tricky.slice(0, 1)];
  for (const c of [...calm, ...clear, ...tricky]) if (picked.length < n && !picked.includes(c)) picked.push(c);
  const order = shuffle(picked.slice(0, n));
  run.cur = { ids: order.map((c) => c.id), points: order.map(() => null), guesses: order.map(() => null), started: new Date().toISOString() };
  save(KEY, run.cur);
  return `#/partida/1`;
}

export function recordRun(i: number, guess: number, points: number) {
  if (!run.cur) return;
  run.cur.points[i] = points;
  run.cur.guesses[i] = guess;
  save(KEY, run.cur);
  if (run.cur.points.every((p) => p !== null)) {
    const total = run.cur.points.reduce<number>((s, p) => s + (p ?? 0), 0);
    run.best = [...run.best, { total, max: run.cur.ids.length * 100, at: new Date().toISOString() }]
      .sort((a, b) => b.total / b.max - a.total / a.max).slice(0, 5);
    save(BEST, run.best);
  }
}

export function clearRuns() {
  run.cur = null; run.best = [];
  try { localStorage.removeItem(KEY); localStorage.removeItem(BEST); } catch { /* ignora */ }
}
