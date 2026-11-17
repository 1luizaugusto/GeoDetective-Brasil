# Configurar o Google Earth Engine (GEE) para o GeoDetective

O GEE é necessário porque o download direto dos mapas do MapBiomas está suspenso. Com ele obtemos:
- **rótulos de treino** (vegetação nativa) para o Random Forest;
- a **referência MapBiomas** (Δ de vegetação nativa) exatamente no recorte de cada par;
- **candidatos a ganho de vegetação nativa** (regeneração), que ainda não encontramos.

## Passo a passo (feito por você, com a sua conta Google)

1. **Criar um projeto no Google Cloud:** https://console.cloud.google.com/projectcreate
   - Sugestão de nome: `geodetective-brasil`. Anote o **ID do projeto**, que pode receber um sufixo numérico.
2. **Registrar o projeto no Earth Engine para uso não comercial:** https://console.cloud.google.com/earth-engine
   - Escolha **uso não comercial** (pesquisa/educação: Spate Tech Bootcamp 2026) e responda ao questionário.
   - Alternativa direta: `https://code.earthengine.google.com/register?project=<ID-do-projeto>`
3. **Ativar a API do Earth Engine** com o projeto selecionado: https://console.cloud.google.com/apis/library/earthengine.googleapis.com
4. **Autenticar este computador.** O navegador vai abrir para você fazer login e autorizar:

```bash
%USERPROFILE%\.venvs\geodet\Scripts\earthengine.exe authenticate
```

5. Depois, me envie só o **ID do projeto**. Não envie senhas nem tokens.

> Observações:
> - Projetos não comerciais passam por reverificação periódica.
> - O login e a autorização ficam com você. Eu só executo os scripts depois que as credenciais existirem nesta máquina.

## O que eu rodo em seguida (já escrito e com sintaxe verificada, ainda NÃO executado)

| Ordem | Script | Faz |
|---|---|---|
| 1 | `science/scripts/gee_inspect_assets.py --project <ID>` | Confere se os assets abrem, lista bandas e anos e mostra o histograma de classes nos 3 pilotos |
| 2 | `science/scripts/gee_reference_pairs.py --project <ID>` | Calcula a % de vegetação nativa em 2020 e 2024 e o Δ (pp) no recorte de cada par, nos mapas de 30 m (Col. 11) e 10 m (Col. 4) |
| 3 | `science/scripts/gee_find_native_gain.py --project <ID> --bbox W S E N --label <região> --exclude-fire` | Lista células de 2,4 km com regeneração nativa persistente (não nativo em 2019–20 → nativo em 2024–25, sem silvicultura) |

## Assets usados

IDs copiados da página oficial em 2026-11-12: https://brasil.mapbiomas.org/downloads/assets-no-google-earth-engine/

| Uso | Asset |
|---|---|
| Cobertura 30 m, Col. 11 (1985–2025) | `projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_coverage_v3` |
| Cobertura 10 m (Sentinel-2), Col. 4 | `projects/mapbiomas-public/assets/brazil/lulc_10m/collection4/mapbiomas_10m_collection4_coverage_v1` |
| Desmatamento e vegetação secundária, Col. 11 | `projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_deforestation_secondary_vegetation_v5` |
| Fogo, Col. 5.1 (área queimada anual) | `projects/mapbiomas-public/assets/brazil/fire/collection5_1/mapbiomas_fire_collection51_annual_burned_v1` |

Classes de **vegetação nativa** (legenda oficial da Col. 11, publicada em 13/08/2026; texto extraído em `data/external/mapbiomas/legenda_col11.txt`):

| Grupo | Códigos |
|---|---|
| Floresta | 3 Formação Florestal · 6 Floresta Alagável · 4 Formação Savânica · 7 Savana Alagada (beta) · 5 Mangue · 49 Restinga Arbórea |
| Vegetação Herbácea e Arbustiva | 12 Formação Campestre · 77 Formação Herbáceo Arbustiva · 11 Campo Alagado e Área Pantanosa · 84 Marisma (beta) · 50 Restinga Herbácea/Arbustiva · 32 Apicum · 29 Afloramento Rochoso |
| **Não-alvo** (exemplos) | 9 Silvicultura · 15 Pastagem · 18–48 Agricultura · 21 Mosaico de Usos |

**Ainda não verificado:**
- os anos disponíveis no mapa de 10 m (Col. 4);
- os nomes de banda e a legenda dos assets de vegetação secundária e de fogo.

O script 1 verifica esses pontos antes de qualquer cálculo.
