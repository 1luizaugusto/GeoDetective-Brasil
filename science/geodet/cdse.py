"""Copernicus Data Space Ecosystem (CDSE) — Sentinel Hub APIs (plano gratuito "Copernicus General User").

Uso aqui: TRIAGEM DE CENAS no servidor do Copernicus. Uma única chamada à Statistical API devolve,
para cada data da janela, a fração de pixels limpos (SCL) e a fração de "névoa/fumaça" no AOI —
em vez de baixar o SCL de cada cena (gargalo do método via Earth Search).

Cotas (doc. CDSE "Quotas", consultada em 2026-11-12): 10 000 PU/mês, 300 PU/min,
50 000 requisições/mês, 300 requisições/min. Batch API não disponível no plano gratuito.

Credenciais (nunca no código nem no git): variáveis de ambiente CDSE_CLIENT_ID e CDSE_CLIENT_SECRET,
ou arquivo science/.env (gitignored) com essas duas linhas. Criação do cliente OAuth:
https://shapps.dataspace.copernicus.eu/dashboard/#/account/settings → OAuth clients → Create.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SH = "https://sh.dataspace.copernicus.eu"
_tok = {"value": None, "exp": 0.0}

# Mesmos critérios do pipeline (geodet.s2.SCL_VALID e pairing.haze_fraction)
EVAL_SCREEN = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B02", "B04", "B08", "SCL", "CLM", "dataMask"] }],
    output: [
      { id: "valid", bands: 1, sampleType: "FLOAT32" },
      { id: "haze", bands: 1, sampleType: "FLOAT32" },
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "clm", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(s) {
  var ok = (s.SCL == 4 || s.SCL == 5 || s.SCL == 6 || s.SCL == 7) ? 1 : 0;
  var hz = (ok == 1 && s.B02 > 0.06 && s.B02 >= 0.95 * s.B04) ? 1 : 0;
  // NDVI só em pixel válido (média/valid = NDVI médio do que é limpo): mede o "verde" da data
  var nd = ok == 1 ? (s.B08 - s.B04) / (s.B08 + s.B04 + 1e-6) : 0;
  // CLM = máscara s2cloudless: pega nuvenzinha que o SCL deixa passar (só conta onde o SCL diz "limpo")
  var cl = (ok == 1 && s.CLM == 1) ? 1 : 0;
  return { valid: [ok], haze: [hz], ndvi: [nd], clm: [cl], dataMask: [s.dataMask] };
}"""


def _creds():
    cid, sec = os.environ.get("CDSE_CLIENT_ID"), os.environ.get("CDSE_CLIENT_SECRET")
    env = Path(__file__).resolve().parents[1] / ".env"
    if (not cid or not sec) and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == "CDSE_CLIENT_ID":
                cid = v.strip()
            elif k.strip() == "CDSE_CLIENT_SECRET":
                sec = v.strip()
    if not cid or not sec:
        raise SystemExit("CDSE: defina CDSE_CLIENT_ID e CDSE_CLIENT_SECRET (variáveis de ambiente ou science/.env)")
    return cid, sec


def token() -> str:
    if _tok["value"] and time.time() < _tok["exp"] - 60:
        return _tok["value"]
    cid, sec = _creds()
    r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials", "client_id": cid, "client_secret": sec}, timeout=60)
    r.raise_for_status()
    j = r.json()
    _tok.update(value=j["access_token"], exp=time.time() + j.get("expires_in", 600))
    return _tok["value"]


def screen_dates(grid, start: str, end: str, max_cc: int = 60, res: float = 60.0) -> list[dict]:
    """Triagem de TODAS as datas da janela numa chamada: [{date, valid, haze}] sobre o AOI exato (UTM).
    Datas sem dado no AOI são descartadas."""
    l, b, r, t = grid.bounds
    body = {
        "input": {
            "bounds": {"bbox": [l, b, r, t], "properties": {"crs": f"http://www.opengis.net/def/crs/EPSG/0/{grid.epsg}"}},
            "data": [{"type": "sentinel-2-l2a",
                      "dataFilter": {"timeRange": {"from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"},
                                     "maxCloudCoverage": max_cc, "mosaickingOrder": "leastCC"}}],
        },
        "aggregation": {
            "timeRange": {"from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"},
            "aggregationInterval": {"of": "P1D"},
            "evalscript": EVAL_SCREEN,
            "resx": res, "resy": res,
        },
    }
    rq = requests.post(f"{SH}/api/v1/statistics", json=body, timeout=180,
                       headers={"Authorization": f"Bearer {token()}"})
    rq.raise_for_status()
    out = []
    for iv in rq.json().get("data", []):
        o = iv.get("outputs", {})
        try:
            v = o["valid"]["bands"]["B0"]["stats"]; h = o["haze"]["bands"]["B0"]["stats"]
        except KeyError:
            continue
        if not v.get("sampleCount") or v.get("noDataCount", 0) >= v["sampleCount"]:
            continue
        valid = float(v["mean"])
        # haze medido só onde válido: mean(haze)/mean(valid)
        out.append({"date": iv["interval"]["from"][:10], "valid": valid,
                    "haze": float(h["mean"]) / valid if valid > 0 else 1.0,
                    "coverage": 1 - v.get("noDataCount", 0) / v["sampleCount"],
                    "ndvi": (float(o["ndvi"]["bands"]["B0"]["stats"]["mean"]) / valid
                             if valid > 0 and "ndvi" in o else None),
                    "clm": (float(o["clm"]["bands"]["B0"]["stats"]["mean"]) / valid
                            if valid > 0 and "clm" in o else None)})
    return out
