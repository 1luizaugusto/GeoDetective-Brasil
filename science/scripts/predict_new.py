"""Estimativa do modelo FINAL (models/rf_native_v1.joblib) para desafios NOVOS, que não entraram no treino.
Como o local nunca foi visto pelo modelo, a estimativa é fora da amostra — tão honesta quanto a out-of-fold.
Grava metadata.model_estimate (method = "modelo final; desafio fora do treino") e imprime a diferença para o MapBiomas.
Requer rótulos (export_labels.py) só para comparar com o MapBiomas; o modelo usa apenas a imagem.
Uso: python predict_new.py ID [ID ...]"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_rf import load, predict_delta  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
bundle = joblib.load(ROOT / "models" / "rf_native_v1.joblib")
rf = bundle["model"]
trained_at = bundle["report"]["generated_utc"]
for cid in sys.argv[1:]:
    d = ROOT / "data" / "pairs" / cid
    c = load(d)
    if c is None:
        print(cid, "sem rótulos/refletância — rode export_labels.py"); continue
    if cid in {r for r in bundle["report"].get("challenge_ids", [])}:
        print(cid, "ESTEVE NO TREINO — use a out-of-fold do train_rf"); continue
    r = predict_delta(rf, c)
    mp = d / "metadata.json"; m = json.loads(mp.read_text(encoding="utf-8"))
    m["model_estimate"] = {"model": "rf_native_v1", "method": "modelo final; desafio fora do treino",
                           "model_trained_utc": trained_at, "native_pct_a": round(float(r["pred_a"]), 2),
                           "native_pct_b": round(float(r["pred_b"]), 2), "delta_pp": round(float(r["delta_pred"]), 2),
                           "computed_utc": datetime.now(timezone.utc).isoformat()}
    mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    gap = r["delta_pred"] - r["delta_ref10"]
    print(f"{cid}: modelo {r['delta_pred']:+.1f} pp | MapBiomas 10 m {r['delta_ref10']:+.1f} | 30 m {r['delta_ref30']:+.1f} "
          f"| gap {gap:+.1f} {'OK' if abs(gap) <= 15 else 'FORA'} | nível {r['pred_a']:.0f}→{r['pred_b']:.0f}%")
