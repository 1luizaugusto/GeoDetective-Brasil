// Contrato gerado por science/scripts/export_game.py (schema_version 1.x)
export interface Challenge {
  id: string;
  name: string;
  group: string;
  biome: string;
  uf: string | null;
  municipality: string | null;
  center_lonlat: [number, number];
  bbox_lonlat: [number, number, number, number];
  size_km: number;
  pixel_m: number;
  dates: [string, string];
  years: [number, number];
  images: {
    before: string; after: string; context_before: string; context_after: string;
    /** Outra época do ano (a mais verde que os dois anos têm em comum) — o modelo v2 também usa estas */
    before2?: string; after2?: string; context_before2?: string; context_after2?: string;
    /** botão MAPA: nativa no 1º ano / nativa + perdida + ganha no 2º ano (MapBiomas 10 m) */
    native_a?: string; native_b?: string;
  };
  dates2?: [string, string] | null;
  /** época 1 bem menos verde que a época 2 nos dois anos: avisar que mata sem folhas pode parecer pasto */
  season_hint?: boolean;
  products: { id: string; browser_url: string | null }[];
  model_estimate_pp: number;
  model_uncertainty_pp: number;
  /** faixa de 100 pontos: [min(modelo, MapBiomas) − 3, max(modelo, MapBiomas) + 3] */
  score_band?: [number, number];
  reference_pp: { mapbiomas_10m: number; mapbiomas_30m: number };
  native_pct: { model: [number, number]; mapbiomas_10m: [number, number] };
  kind: "loss" | "gain" | "stable_edge" | "trap";
  explanation: string;
  explanation_en?: string;
  hint?: string;
  hint_en?: string;
  name_en?: string;
  /** % do recorte por grupo de cobertura (MapBiomas 10 m), por ano: {"2020": {"forest": 8.2, ...}} */
  composition?: Record<string, Record<string, number>>;
  fire_pct?: Record<string, number>;
  protected?: { name: string; type: string; year: number; pct: number }[];
  /** pistas falsas e lições: fire, open, plantation, crop, season, water, regrowth, conversion */
  tags?: string[];
  qa_note: string;
  attribution: string;
  /** Dossiê de evidências (science/scripts/build_dossier.py): cada afirmação com veredito, porquê e fontes. */
  dossier: Claim[];
}

export interface Claim {
  afirmacao: string;
  veredito: "comprovado" | "corrigido" | "removido" | "não comprovado";
  porque: string;
  revisao?: string;
  fontes: { nome: string; url: string }[];
}

export interface Dataset {
  schema_version: string;
  generated_utc: string;
  target: string;
  scoring: { formula: string; tolerance_pp: number; margin_pp?: number; source: string };
  model: {
    name: string;
    validation: string;
    pixel: { overall_accuracy: number; f1_native: number; n_pixels: number };
    delta_vs_mapbiomas10m: { MAE_pp: number; bias_pp: number; RMSE_pp: number };
  };
  limitations: string[];
  limitations_en?: string[];
  licenses: string;
  challenges: Challenge[];
}

export interface Attempt {
  guess: number;
  points: number;
  at: string;
}
