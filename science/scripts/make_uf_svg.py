"""Gera o mapa das UFs para o jogo (sem servidor de tiles): game/src/lib/ufs.json
Fonte: API de malhas v3 do IBGE (qualidade mínima), simplificada com shapely e projetada
em equiretangular com correção de cos(lat média). Cada UF: sigla, nome, path SVG, centróide."""
import json
import math
from pathlib import Path

import requests
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
       "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF")
gj = requests.get(URL, timeout=60).json()
meta = {str(u["id"]): (u["sigla"], u["nome"]) for u in
        requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/estados", timeout=60).json()}

K = math.cos(math.radians(-14.0))  # latitude média do Brasil
W = 1000.0
geoms = [(f["properties"]["codarea"], shape(f["geometry"]).simplify(0.03, preserve_topology=True)) for f in gj["features"]]
minx = min(g.bounds[0] for _, g in geoms); maxx = max(g.bounds[2] for _, g in geoms)
miny = min(g.bounds[1] for _, g in geoms); maxy = max(g.bounds[3] for _, g in geoms)
s = W / ((maxx - minx) * K)
H = (maxy - miny) * s


def xy(lon, lat):
    return round((lon - minx) * K * s, 1), round((maxy - lat) * s, 1)


def ring(coords):
    pts = [xy(*c[:2]) for c in coords]
    return "M" + "L".join(f"{x},{y}" for x, y in pts) + "Z"


out = []
for code, g in geoms:
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    d = "".join(ring(p.exterior.coords) for p in polys)
    c = g.representative_point()
    sigla, nome = meta[str(code)]
    out.append({"uf": sigla, "name": nome, "d": d, "label": xy(c.x, c.y)})
doc = {"source": "IBGE — API de malhas v3 (qualidade mínima), simplificada", "width": W, "height": round(H, 1),
       "projection": {"type": "equirectangular", "minLon": minx, "maxLat": maxy, "k": K, "scale": s},
       "ufs": sorted(out, key=lambda u: u["uf"])}
p = ROOT / "game" / "src" / "lib" / "ufs.json"; p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
print(p, len(out), "UFs", f"{p.stat().st_size/1024:.0f} KB")
