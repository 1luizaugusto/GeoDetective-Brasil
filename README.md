# GeoDetective Brasil

**Projeto final — Space Tech Bootcamp 2026 / Future Tech Leaders Brasil** · Autor: Luiz Augusto de Oliveira Almeida

### ▶ [Jogar agora](https://1luizaugusto.github.io/GeoDetective-Brasil/)

Jogo web educativo (ODS 4 e 15). O jogador compara dois recortes reais de Sentinel-2 da mesma área (2020 × 2024/2025; nos casos de regeneração longa, 2018 × 2025) e estima a variação líquida da **vegetação nativa**, de −100 a +100 pp.
O resultado de referência é calculado **antes da publicação** por um modelo Random Forest. O jogo não executa ML.

**Estado atual (2026-11-17):**
- **44 desafios jogáveis**: 22 desmatamento, 15 estáveis, 5 regeneração e 2 armadilhas. Quatro dos casos de regeneração comparam **2018 × 2025** (mata que voltou em 7 anos); os demais, 2020 × 2024/2025. Para entrar no jogo, cada um passou por:
  - QA visual;
  - **auditoria de evidências** (dois mapas MapBiomas + NDVI + MapBiomas Fogo);
  - **regra de justiça**: o modelo e o MapBiomas concordam dentro da tolerância, então chutar o valor do MapBiomas sempre rende 100;
  - imagens de **duas épocas por ano**, as mesmas para o jogador e para o modelo.
- Random Forest de duas épocas (`rf_native_v2`), com validação espacial out-of-fold:
  - acurácia por pixel 0,85;
  - MAE do Δ de 13,56 pp contra o MapBiomas 10 m, em 109 desafios. O acervo inclui muitas perdas totais, em que o modelo erra mais; no jogo só entram os casos em que ele concorda com o MapBiomas.
- O jogo (estética de videogame dos anos 90) está pronto e é gerado como site estático (`npm run build`).

Documentação: [docs/01-primeira-entrega.md](docs/01-primeira-entrega.md) · [docs/03-pipeline-modelo-e-jogo.md](docs/03-pipeline-modelo-e-jogo.md).

## Estrutura
- `science/`: aquisição (Earth Search + triagem no Copernicus Data Space), máscaras MapBiomas via Google Earth Engine, QA, Random Forest e export — em Python.
- `data/`: catálogos, decisões de QA, pares e metadados de proveniência.
- `game/`: Vite + Svelte 5 + TypeScript, publicado pelo GitHub Pages (`.github/workflows/pages.yml`).

## Rodar o jogo
```bash
cd game && npm ci --legacy-peer-deps && npm run dev
```

## Regerar os dados
Python em `%USERPROFILE%\.venvs\geodet` (`science/requirements.txt`).
Credenciais do CDSE ficam em `science/.env`, que **não é versionado** (`CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`). O Google Earth Engine usa a autenticação local (`earthengine authenticate`). Nenhuma chave fica no repositório.

Rasters e imagens intermediárias (`data/pairs/**/*.tif`, `*.png`) não são versionados: são reproduzíveis pelos scripts. O jogo usa só `game/public/data`.
```bash
python science/scripts/build_from_catalog.py data/catalog/challenges_v1.json --skip-done
python science/scripts/export_labels.py
python science/scripts/build_season2.py
python science/scripts/train_rf2.py
python science/scripts/audit_challenges.py
python science/scripts/build_dossier.py
python science/scripts/export_game.py
```
Detalhes do pipeline, das regras de justiça e do QA: [docs/03-pipeline-modelo-e-jogo.md](docs/03-pipeline-modelo-e-jogo.md).

## Créditos e licenças
- Código: licença MIT ([LICENSE](LICENSE)).
- Imagens: *Contains modified Copernicus Sentinel data 2018, 2020, 2024, 2025* (Copernicus Sentinel Data Legal Notice).
- Referência: MapBiomas Brasil (CC-BY 4.0). Limites: IBGE.
