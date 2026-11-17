import type { Challenge } from "./types";

// Pontuação (docs/03 §3): FAIXA DE 100 PONTOS por caso = do valor do modelo ao do MapBiomas, ±3 pp.
// Fora da faixa: pontos = round(100 × max(0, 1 − distância até a faixa / 40)).
export function score(guess: number, b: [number, number]): number {
  const over = Math.max(0, b[0] - guess, guess - b[1]);
  return Math.round(100 * Math.max(0, 1 - over / 40));
}

/** Faixa de 100 pontos do caso (dados antigos sem score_band: modelo ± tolerância). */
export function band(c: Challenge): [number, number] {
  return c.score_band ?? [c.model_estimate_pp - c.model_uncertainty_pp, c.model_estimate_pp + c.model_uncertainty_pp];
}

export function rank(points: number): "S" | "A" | "B" | "C" | "D" {
  return points >= 95 ? "S" : points >= 80 ? "A" : points >= 60 ? "B" : points >= 35 ? "C" : "D";
}

export function pad(n: number, w = 6): string {
  return String(Math.max(0, Math.round(n))).padStart(w, "0");
}

export function fmtPP(v: number, digits = 0): string {
  const r = Number(v.toFixed(digits));
  if (r === 0) return "0 pp";
  return `${r > 0 ? "+" : "-"}${Math.abs(r).toLocaleString("pt-BR", { maximumFractionDigits: digits })} pp`;
}

// pp → hectares equivalentes no recorte (área do recorte = size_km² × 100 ha).
// A escala −100…+100 é um limite físico: é a fatia do recorte que mudou; hectares dão a noção de tamanho.
export function fmtHa(pp: number, sizeKm: number): string {
  const ha = (pp / 100) * sizeKm * sizeKm * 100;
  const r = Math.round(ha);
  if (r === 0) return "0 ha";
  return `${r > 0 ? "+" : "-"}${Math.abs(r).toLocaleString("pt-BR")} ha`;
}

export function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

/** Pontos de quem chuta 0 (nenhuma mudança) — o "adversário preguiçoso" que o detetive precisa vencer. */
export function zeroScore(c: Challenge): number {
  return score(0, band(c));
}
