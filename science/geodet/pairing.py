"""Escolha do par de cenas (ano A x ano B) para uma mesma grade, com QA de nuvem e fumaça."""
from __future__ import annotations

import numpy as np

from . import s2

HAZE_DEFAULT = HAZE_MAX = 0.03  # fração máx. de pixels "azulados e claros" (calibrado em diagnostics/calib_haze.py)


def haze_fraction(item, grid) -> float:
    """Fumaça/névoa: pixels com azul > 0,06 e azul >= 0,95·vermelho (60 m).
    Calibração: cenas limpas <= 0,006; cenas com fumaça 0,21–0,96."""
    g60 = grid.at(60.0)
    r = s2.read_reflectance(item, g60, ("blue", "red"))
    b, rd = r["blue"], r["red"]
    # só pixels que o SCL considera limpos: nuvem branca também é "azul ≥ vermelho" e não é fumaça
    ok = np.isfinite(b) & np.isfinite(rd) & np.isin(s2.read_scl(item, g60), s2.SCL_VALID)
    return float(((b > 0.06) & (b >= 0.95 * rd))[ok].mean()) if ok.any() else 1.0


def _window(year, season):
    s0, s1 = season
    return f"{year}-{s0}", f"{year + 1 if s1 < s0 else year}-{s1}"


USE_CDSE = True  # triagem no servidor do Copernicus (geodet.cdse); cai no método local se indisponível


def _best_scenes_cdse(grid, start, end, min_valid, exclude):
    """Uma chamada à Statistical API do CDSE dá SCL válido e névoa de TODAS as datas;
    só as datas aprovadas viram itens Earth Search (mesmo produto, leitura dos COGs depois)."""
    from . import cdse
    stats = {r["date"]: r for r in cdse.screen_dates(grid, start, end)}
    ok_dates = {d for d, r in stats.items() if r["coverage"] >= 0.999 and r["valid"] >= min_valid and r["haze"] <= HAZE_MAX}
    scored = []
    for it in s2.search(grid, start, end, max_tile_cloud=100):
        d = it.datetime.date().isoformat()
        if it.id in set(exclude) or d not in ok_dates:
            continue
        scored.append((stats[d]["valid"], it, stats[d]["haze"]))
    scored.sort(key=lambda t: -t[0])
    return scored


def best_scenes(grid, year: int, season, max_eval: int = 10, min_valid=0.9, exclude=()):
    start, end = _window(year, season)
    if USE_CDSE:
        try:
            return _best_scenes_cdse(grid, start, end, min_valid, exclude)
        except SystemExit:
            pass  # sem credenciais: método local
        except Exception as e:  # noqa: BLE001
            print("   CDSE indisponível, usando método local:", repr(e)[:120])
    items = [it for it in s2.search(grid, start, end) if it.id not in set(exclude)][:max_eval]
    scored = []
    for it in items:
        try:
            frac, _ = s2.scl_valid_fraction(it, grid)
            if frac < min_valid:
                continue
            hz = haze_fraction(it, grid)
        except Exception as e:  # noqa: BLE001
            print("   falha QA", it.id, repr(e)[:120]); continue
        if hz <= HAZE_MAX:
            scored.append((frac, it, hz))
    scored.sort(key=lambda t: -t[0])
    return scored


def choose_pair(grid, year_a: int, year_b: int, season, valid_threshold=0.97, min_valid=0.9, max_eval=10, exclude=()):
    """Par sazonalmente mais próximo entre cenas válidas e sem fumaça; prefere mesmo tile.
    min_valid < 0,9 serve a regiões muito nubladas: o recorte final ainda exige >= 99% válido."""
    A = best_scenes(grid, year_a, season, max_eval, min_valid, exclude)
    B = best_scenes(grid, year_b, season, max_eval, min_valid, exclude)
    if not A or not B:
        return None, A, B

    def tile(it):
        p = it.properties
        return (p.get("mgrs:utm_zone"), p.get("mgrs:latitude_band"), p.get("mgrs:grid_square"))

    def ok(lst):
        good = [x for x in lst if x[0] >= valid_threshold]
        return good or lst[:1]

    best = None
    for fa, ia, ha in ok(A):
        for fb, ib, hb in ok(B):
            dd = abs(s2.doy(ia) - s2.doy(ib)); dd = min(dd, 365 - dd)
            score = dd + (0 if tile(ia) == tile(ib) else 30) - 100 * min(fa, fb)
            if best is None or score < best[0]:
                best = (score, (fa, ia, ha), (fb, ib, hb))
    return (best[1], best[2]), A, B
