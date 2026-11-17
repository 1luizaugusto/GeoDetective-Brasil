"""Gera data/catalog/pairs_catalog.csv (uma linha por imagem) a partir dos metadata.json dos pares."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows = []
for m in sorted((ROOT / "data" / "pairs").glob("*/metadata.json")):
    d = json.loads(m.read_text(encoding="utf-8"))
    v = d.get("verification", {}); loc = v.get("ibge_location_of_center") or {}
    for k, im in zip("AB", d["images"]):
        rows.append({
            "challenge_id": d["challenge_id"], "imagem": k, "nome": d["name"],
            "municipio": loc.get("municipio"), "uf": loc.get("uf"), "cod_ibge": loc.get("ibge_municipio_codigo"),
            "lon_centro": d["center_lonlat"][0], "lat_centro": d["center_lonlat"][1],
            "bbox_lonlat": " ".join(map(str, d["aoi"]["bbox_lonlat"])), "crs": d["aoi"]["crs"],
            "bounds_utm": " ".join(map(str, d["aoi"]["bounds_utm"])), "tamanho_m": d["aoi"]["size_m"],
            "data": im["datetime_utc"][:10], "hora_utc": im["datetime_utc"][11:19], "plataforma": im["platform"],
            "tile_mgrs": im["mgrs_tile"], "orbita_relativa": im["relative_orbit"],
            "baseline": im["processing_baseline"], "nuvem_tile_pct": round(im["tile_cloud_cover_pct"], 2),
            "fracao_valida_recorte_scl": im["crop_valid_fraction_scl"], "elev_solar_graus": round(im["sun_elevation_deg"] or 0, 1),
            "id_earth_search": im["earth_search_id"], "id_produto_esa_cdse": im["cdse_product_id"],
            "url_stac_earth_search": im["stac_item_url"], "url_stac_cdse": im.get("cdse_stac_item_url"),
            "url_copernicus_browser": im["copernicus_browser_url"], "resolucao_m": d["aoi"]["pixel_size_m"],
            "alinhamento_identico": v.get("aligned_identical_grid"),
            "zoom_jogo": d["display"]["zoom_factor"], "px_imagem_jogo": d["display"]["game_image_px"],
            "triagem_delta_pp_dossel_proxy": d["triage"]["delta_pp_tree_proxy"],
            "alvo": d["target_definition"],
            "hipotese": d["selection_hypothesis"], "status": d["status"], "notas": d["notes"],
            "licenca": "Copernicus Sentinel Data Legal Notice (uso livre com atribuição)",
        })
out = ROOT / "data" / "catalog" / "pairs_catalog.csv"
with out.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r["challenge_id"], r["imagem"], r["data"], r["tile_mgrs"], r["orbita_relativa"], r["baseline"],
          r["nuvem_tile_pct"], r["fracao_valida_recorte_scl"], r["lon_centro"], r["lat_centro"], r["bbox_lonlat"])
print("->", out)
