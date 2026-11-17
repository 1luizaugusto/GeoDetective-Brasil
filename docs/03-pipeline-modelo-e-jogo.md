# GeoDetective Brasil — 2ª entrega: pipeline em lote, modelo e jogo

Data: 2026-11-12. Continua [01-primeira-entrega.md](01-primeira-entrega.md) e [02-earth-engine-setup.md](02-earth-engine-setup.md).

## 1. Mudança de escopo (aprovada)

> **Proposta original:** 50 desafios (18 por bioma, 27 capitais, até 5 complementares), no máximo 100 imagens.
>
> **Mudança:** os **50 desafios continuam sendo o núcleo acadêmico** avaliado. Acima deles, o pipeline pode gerar um
> **acervo extra** (meta máxima de 500) de desafios produzidos e checados pelo mesmo método.
>
> **Justificativa:**
> - o processo agora é automático e reprodutível: escolha do par, filtro de nuvem e fumaça, posicionamento pelo MapBiomas e referência;
> - mais casos melhoram o treino e a validação do modelo, que sofre com poucos exemplos por bioma (ver seção 4);
> - o limite de 100 imagens vale para o núcleo; o acervo extra é opcional e fica separado (`group` diferente no catálogo).
>
> **Não muda:** alvo (vegetação nativa), fontes gratuitas, separação ciência × jogo, nenhuma IA rodando no jogo.

Status: **aprovada pelo responsável do projeto em 2026-11-13.**
Primeira prioridade do acervo extra: locais de silvicultura e de formações nativas abertas (campos, savanas), as duas fraquezas do modelo (seção 4).

## 2. Pipeline científico (science/)

| Etapa | Script | O que faz |
|---|---|---|
| Catálogo | `make_challenge_catalog.py`, `make_gain_catalog.py` | Lista de locais → JSON (modo do recorte a partir da hipótese) |
| Par de cenas | `geodet/pairing.py` | Mesma estação, SCL ≥ 90% válido, **filtro de fumaça** (ver 2.1), mesmo tile MGRS preferido |
| Recorte | `build_pair.py` | Máscaras MapBiomas (10 m Col. 4 + 30 m Col. 11) baixadas via GEE **na mesma grade UTM** do par; recorte de 2,4 km posicionado por modo |
| Rótulos | `export_labels.py` | GeoTIFF nativa/não-nativa por pixel (10 m) para treino |
| Verificação | `verify_pairs.py` | Grades idênticas, município/UF do centro (IBGE), ID oficial no CDSE |
| QA visual | `make_contact_sheet.py` + `data/catalog/qa_decisions.json` | Folhas lado a lado; decisão aprovado/rejeitado/refazer com motivo |
| Modelo | `train_rf.py` | Random Forest por pixel + validação espacial |
| Export | `export_game.py` | `game/public/data/challenges.json` + WebP |
| Mapa | `make_uf_svg.py` | Contornos das UFs (IBGE) simplificados em SVG |

Lotes: `build_from_catalog.py <catalogo.json> [--skip-done]`, com log por desafio em `data/catalog/build_log.jsonl`.
Falhas são reprocessadas por `make_retry_catalog.py`; as correções pedidas no QA visual, por `make_fix_catalog.py`.

### 2.1 Filtro de fumaça e névoa
O SCL (máscara de nuvem do L2A) marca fumaça como "válida". Por isso foi criado um indicador próprio:

`haze_frac` = fração de pixels limpos pelo SCL com B02 > 0,06 e B02 ≥ 0,95·B04, a 60 m.

Calibração em `diagnostics/calib_haze.py`, com cenas classificadas a olho:

| Caso | haze_frac |
|---|---|
| Cenas limpas | ≤ 0,006 |
| Cenas com fumaça | 0,21 a 0,96 |

- Limiar adotado: 0,03.
- O AOT (espessura óptica do aerossol) **não** separou os casos e foi descartado.
- Correção posterior: nuvem branca também satisfaz a regra; por isso o indicador passou a ser medido só nos pixels limpos pelo SCL.

### 2.1.1 Nuvens pequenas (cúmulos): sem detector automático confiável
Em capitais litorâneas (João Pessoa, Aracaju, São Luís) e em Boa Vista, cúmulos pequenos e suas sombras passaram
pelo SCL. Foram testados, nos recortes já classificados a olho:

| Indicador | Resultado |
|---|---|
| CLD (probabilidade de nuvem do Sen2Cor) | ≤ 3% sobre nuvens visíveis |
| Brancura + banda costeira B01 | Areia, dunas e pista de aeroporto pontuam mais que as nuvens |
| Brilho transitório entre as duas datas | Obras e solo exposto pontuam mais que as nuvens |

Nenhum separou nuvem de superfície clara. Decisão: o **QA visual é obrigatório**.
Cena reprovada é excluída (`exclude`, cumulativo) e o pipeline escolhe a próxima.
O CDSE gratuito usa as mesmas máscaras do Sen2Cor (SCL/CLD), então não resolve isso.

### 2.2 Posicionamento do recorte (modos)

| Modo | Critério sobre as máscaras MapBiomas |
|---|---|
| `loss` | maior perda média (10 m e 30 m) |
| `gain` | maior ganho médio |
| `stable_edge` | Δ ≈ 0 nos dois mapas, borda nativa × não-nativa visível (mistura ≥ 15%), sem mudança visual de NDVI |
| `trap` | maior expansão de silvicultura com Δ nativa ≈ 0 |

Todos os modos penalizam recortes com mais de 20% de água e exigem pelo menos 99% de pixels válidos nas duas datas.

### 2.3 Lições do QA visual (lote 1)

| Problema | Casos | Correção |
|---|---|---|
| Imagens pretas: um pixel nodata gerava NaN no cálculo do tom | CAP-MA, CAP-SE, CMP-01, GAN-01, GAN-03 | Pixels sem dado ficam fora do cálculo |
| Floresta uniforme virando "neon" | CAP-AM, CMP-02 | Faixa mínima de contraste de 0,15 de reflectância |
| Recorte "estável" sem nada para ver | CAP-AM, CER-03 | Exige borda visível |
| Nuvens pequenas que o SCL não marcou | CAP-PB, CAP-RS, PAM-03 | Cena excluída (`--exclude`), escolhida a próxima |
| Fumaça | CAP-RR | Cena excluída (`--exclude`), escolhida a próxima |
| Recorte dominado por rio | PAN-03 | Penalidade de água |
| **Ganho nativo do MapBiomas sem regeneração visível** | GAN-01..04 | **Rejeitados**: no Pantanal o "ganho" é a secagem de área alagada; no Cerrado (GAN-04), provável reclassificação de pasto em campo nativo |

### 2.4 Triagem pelo Copernicus Data Space (CDSE) e rodadas finais
- `geodet/cdse.py` usa a Statistical API do Sentinel Hub (conta gratuita CDSE) para medir, numa única chamada, a fração SCL válida e o `haze_frac` de **todas** as datas da janela sobre o AOI exato.
- As datas aprovadas viram itens do Earth Search (mesmo produto L2A), lidos depois como COG.
- A escolha do par caiu de minutos para cerca de 15 s. Sem credenciais, o pipeline volta ao método local.
- **Ano preferido:** 2020 × 2025, porque 2025 é o último ano com MapBiomas. Se não houver par, o pipeline cai para 2024.
- `preview_dates.py <ID>`: prévia RGB das melhores datas para o **recorte de 2,4 km**, para escolher a olho entre cenas que o SCL diz serem 100% limpas (cúmulos pequenos).

| Caso | Problema | Correção |
|---|---|---|
| CAP-RN (Natal) | Dunas brancas disparam o filtro de névoa em cenas limpas (0,1–0,4) | `haze_max` 0,4 só para este caso; fumaça conferida no QA visual |
| CAP-RR (Boa Vista) | Janela dez→mar fazia o "2020" virar imagem de 2021 | Janela jan–mar, no mesmo ano civil do rótulo |
| CER-03 (Emas) | Centro no meio do parque; a borda com lavoura ficava a mais de 12 km | Recentrado na borda encontrada nas máscaras MapBiomas 30 m (IBGE: Mineiros/GO) |
| CAP-MA (São Luís) | Recorte onde só o mapa de 30 m mudava (−23 pp × −1 pp) | Nova penalidade 2·\|Δ10m − Δ30m\| na escolha do recorte, em todos os modos |
| CAP-PB, CAP-MA | Cúmulos pequenos em várias datas | Cenas escolhidas com `preview_dates.py` |
| CAP-MG, CAP-GO, MAT-02 | Nome do local ≠ município do centro no IBGE | Nomes corrigidos para o município do IBGE |

**Situação:** os 50 desafios do núcleo e 2 de ganho estão aprovados no QA visual. Destes, 48 entram no jogo após a regra de justiça.

### 2.5 Acervo extra e fechamento em 50 (2026-11-13)
- `find_sites.py` acha locais **direto nas máscaras MapBiomas 30 m**, sem coordenadas escritas à mão:
  - o Brasil é varrido em blocos de 4° com células de cerca de 2,4 km, em cache em `data/external/mb_cells/`;
  - município vem do IBGE (malhas) e bioma do IBGE 1:250 mil (`geodet/biomes.py`);
  - foco: silvicultura (armadilha) e formações nativas abertas (borda estável e perda);
  - a perda de campo no Pantanal foi excluída (cheia e seca, como em GAN-01..03).
- `predict_new.py` aplica o modelo final a desafios **novos**, que nunca entraram no treino: estimativa fora da amostra.
- Teste com o modelo atual em 10 extras: só 3 passaram na regra dos 15 pp, porque o modelo erra formações abertas e silvicultura. Isso confirma a fraqueza da seção 4.
- Entraram no jogo 2 extras, fechando **50 desafios jogáveis**:

| ID | Local (IBGE) | Tipo | Modelo | MapBiomas 10 m |
|---|---|---|---|---|
| XTR-E05 | Boa Viagem/CE (Caatinga) | borda estável | −7,4 pp | +0,2 pp |
| XTR-T04 | Selvíria/MS (Cerrado) | armadilha | −10,5 pp | +0,1 pp |

- **Regra nova para armadilhas:** o plantio precisa ser confirmado por três evidências independentes.
  - MapBiomas 30 m e 10 m concordando em silvicultura;
  - NDVI de dossel fechado na estação seca.
- XTR-T04 passou: 30 m 0 → 99,3% silvicultura; 10 m pastagem 99,4% → silvicultura 98,4%; NDVI 0,50 → 0,90 no fim de maio.
- XTR-T02 foi reprovado: 30 m diz 100% silvicultura, mas 10 m diz 22,6% silvicultura e 77,4% mosaico de usos.
- Notas técnicas do QA (`note`) não vão mais ao jogo; só `player_note`, opcional.

### 2.6 Auditoria de evidências (2026-11-13) — trava do export
`audit_challenges.py` confere, para cada desafio, **o que mudou de fato**, com fontes independentes:
- **Transições de classe** no MapBiomas 30 m (Col. 11, Landsat) e 10 m (Col. 4, Sentinel-2), na grade exata do recorte. Mostra, por exemplo, que a perda virou pastagem 96%.
- **NDVI das próprias imagens** do jogo nos pixels que mudaram: precisa cair onde houve perda e subir onde houve ganho ou plantio.
- **Veredito:** desmatamento, regeneração, armadilha de plantio ou estável, só quando os **dois mapas** concordam. O veredito precisa bater com o tipo do desafio.
- Afirmações sobre fogo são conferidas no **MapBiomas Fogo** (Col. 5.1, área queimada anual).
- `change_overlay.py` pinta, sobre a imagem, os pixels em que os dois mapas concordam (perda em vermelho, ganho em verde, plantio em amarelo), para conferência visual.

O `export_game.py` só publica casos com auditoria OK ou revisados à mão (`audit_override`, com motivo registrado).
O tipo comprovado vai ao jogo por `kind_override`.

**Resultado na primeira rodada:** 37 de 50 OK direto; 13 revisados à mão.

| Decisão | Casos | Motivo |
|---|---|---|
| Saíram do jogo | CAP-SE | Sem desmatamento comprovado: o 10 m não vê mudança, o "perda" do 30 m é maré/mangue virando água e o NDVI subiu |
| | PAN-02 | Mapas contraditórios (−3,9 × +3,6 pp, cheia e seca) |
| | CAP-AL | Regeneração não comprovada (NDVI não sobe nos pixels de "ganho") |
| Aceitos com motivo | CAP-AC, CAP-GO, CAP-RR | Perda real nos dois mapas, só de tamanho diferente; NDVI cai −0,07 a −0,21 |
| | CAP-MS | Estável na imagem; ruído de borda no 10 m |
| | CMP-04 | Regeneração pequena, mas comprovada (NDVI +0,12, manchas verdes visíveis) |
| Tipo corrigido | PAM-02 | Armadilha → estável (silvicultura só +1 a +2 pp) |
| | PAN-01 | Armadilha do fogo: MapBiomas Fogo, 88% queimado em 2020 |
| | PAN-03 | Estável. A explicação antiga dizia "queimada em 2024", mas o MapBiomas Fogo dá **0%**: texto falso, reescrito |
| | GAN-10, MAT-01 | Ganho em < 1% dos pixels e invisível: passam a estáveis, texto reescrito |
| Texto reescrito (afirmação não verificada) | CAP-AC (queimada: só 1%), CAP-RO ("seca"), CAP-MT ("empreendimentos"), CAP-TO ("loteamento"), CMP-02 | Só o que os mapas mostram |

**Reposição para 50:** casos de floresta, onde o modelo acerta, com `find_sites.py --kinds forest_loss forest_edge`.
De 12 candidatos, 7 passaram na regra dos 15 pp e na auditoria. Entraram:
- XTR-F02, Altamira/PA: desmatamento, 100% de perda nos dois mapas;
- XTR-B05, Barra do Garças/MT: borda estável;
- XTR-B04, Vera Cruz/RS: borda estável.

**Composição final (50):** 18 desmatamento, 28 estáveis, 2 regeneração nativa (GAN-05, CMP-04) e 2 armadilhas (eucalipto XTR-T04, fogo PAN-01).

### 2.7 Jogo: escala e cortina
- A escala −100…+100 pp é um **limite físico**: é a fatia do recorte cuja cobertura nativa mudou (100% → 0% = −100 pp). Para dar noção de tamanho, o jogo mostra a área equivalente em hectares; o recorte tem 576 ha, então 1 pp ≈ 5,8 ha.
- Na cortina, o fade é só no **rótulo do ano**: o número do ano que vai saindo da tela apaga até 25%, sem sumir. As imagens ficam sempre com brilho total. Era assim que a usuária queria; escurecer a imagem atrapalhava a comparação.
- **Menu de jogo** (2026-11-13): Continuar, Novo jogo (pede confirmação), Partida rápida (5 casos sorteados, com placar e recordes), Escolher fase, Recordes, Opções (som, modo de comparação inicial, efeito de TV, texto datilografado, apagar progresso) e Manual. O ESC volta ao menu.
- **Chute zero:**
  - O problema: como só 7 dos 50 casos têm |Δ do modelo| ≥ 10 pp, quem sempre chuta 0 fazia 91% dos pontos na campanha.
  - A partida rápida agora sorteia 3 mudanças claras, 1 armadilha ou ganho e 1 caso estável. Com isso, o chute zero cai para cerca de 60% em média (nota B; 20 mil sorteios simulados).
  - O resultado e a tela de recordes mostram "VOCÊ × CHUTE ZERO".
  - A fórmula de pontos não mudou: a tolerância continua sendo a incerteza do modelo.
  - Para a campanha ficar desafiadora, o acervo precisa de mais casos com mudança clara.
- **Troca no acervo (2026-11-13):**
  - `find_sites.py` ganhou o tipo `forest_partial`: perda de 25–70 pp de floresta, com preferência por cerca de 45 pp. O modelo erra perdas totais (XTR-F01/F03/F05), e uma perda parcial deixa borda dos dois lados.
  - De 12 locais (`challenges_extra_v3.json`), 3 passaram na justiça, na auditoria e no QA visual: XTR-D06 (Santa Carmem/MT), XTR-D07 (Bela Vista/MS; as listras são curvas de nível no pasto, com 0% de silvicultura nos mapas) e XTR-D11 (Cascavel/CE). O XTR-F04 (Passagem Franca/MA) também saiu da reserva.
  - Foram para a reserva 4 estáveis: GAN-10, MAT-01, XTR-B04 e XTR-B05.
  - Resultado: 22 desmatamento, 24 estáveis, 2 regeneração e 2 armadilhas. Casos com |Δ| ≥ 10 pp passaram de 7 para 11. O chute zero na campanha caiu de 91% para 83%.
- **Tela de desafio para celular:** uma coluna só, com a imagem e, logo abaixo, o palpite.
- **Palco fixo (2026-11-16):** o jogo é um "console" em retrato. A área útil tem sempre o mesmo tamanho, em qualquer tela e em qualquer estado.
  - Largura `min(100vw, 100dvh × 9/16, 620px)` e altura `100dvh`, centralizado no computador.
  - Faixas de altura fixa: HUD de 44 px no topo e créditos de 22 px embaixo. O meio é a "tela".
  - No desafio, nada rola. A imagem é o maior quadrado que cabe (container query `min(100cqw, 100cqh)`), e o painel de avaliação tem altura fixa de 236 px, tanto no palpite quanto no resultado. O que não cabe no resultado (fontes, arquivos) rola dentro do painel.
  - As outras telas (menu, mapa, recordes, opções, manual) rolam por dentro do palco, sem mudar o tamanho dele.
  - O HUD responde à largura do palco, não à da janela: abaixo de 460 px, os rótulos PTS/CASOS somem.

### 2.8 Dossiê de provas e fontes por desafio (2026-11-13)
Cada desafio agora mostra, depois do palpite, a seção **"FONTES"**. Cada afirmação vem com o porquê, com os números, e links para as fontes. O jogo mostra **só afirmações comprovadas**, sem selos: a pedido da usuária, a versão ainda não foi lançada, então o histórico de correções fica só em `context_claims.json` (vereditos "corrigido" e "removido") e não aparece na tela.
- **Afirmações automáticas** (`science/scripts/build_dossier.py` → `data/dossie/<ID>.json`):
  - o tipo de mudança, pelos dois mapas MapBiomas (10 m Col. 4 e 30 m Col. 11) e pelo NDVI das duas imagens Sentinel-2, com link para cada produto no Copernicus Browser;
  - para onde foi a vegetação perdida e de onde veio a ganha (legenda oficial MapBiomas);
  - silvicultura (plantio comercial ≠ nativa);
  - fogo: MapBiomas Fogo Col. 5.1, área queimada por ano;
  - áreas protegidas e Terras Indígenas: WDPA/Protected Planet via GEE `WCMC/WDPA/current/polygons`, com a % do recorte;
  - município e bioma: IBGE.
- **Afirmações de contexto** (`science/scripts/apply_context_review.py` → `data/catalog/context_claims.json`):
  - história e eventos, escritos à mão **só com fonte conferida** (HTTP 200): Cemaden, Governo de MG, MPF, FAPESP/INPE, Embrapa, INPA, INEMA, OpenStreetMap;
  - o que não tinha fonte saiu do texto e ficou registrado como "corrigido" ou "removido".
- O `export_game.py` não exporta um desafio sem dossiê, e usa `name_override` para os nomes corrigidos.
- **Erros achados e corrigidos nesta revisão:**
  - CMP-02 ficava na TI Trincheira/Bacajá (100% do recorte, pela WDPA), não na Apyterewa;
  - PAN-01 fica a 17 km do PE Encontro das Águas, não dentro dele;
  - PAN-03 não queimou em 2024 (Fogo 0%) e sim em 2020 (96%);
  - GAN-10 fica em Mangaratiba, não no Vale do Paraíba;
  - CMP-01 não está no caminho da lama de 2019, que desceu para oeste;
  - CER-02: os mapas dizem "mosaico de usos" e soja em parte da área, não "lavoura mecanizada" em tudo;
  - CAA-02 e CAP-SC: o parque do nome fica fora do recorte;
  - XTR-T04: "eucalipto" saiu, porque os mapas dizem só "silvicultura";
  - saíram também afirmações sem fonte: algas, sedimento, maré, "uma das maiores florestas urbanas", BR-163, "loteamentos", "terraplanagem", "pátios de minério".
- **Fato novo comprovado:** a perda do CAP-RO acontece dentro da TI Karipuna (60% do recorte).

**Achado relevante:** ganho de vegetação nativa visível a 10 m em 4 anos é raro. A maior parte do "ganho" nos mapas
é dinâmica hidrológica, reclassificação ou silvicultura. Por isso o jogo tem mais desafios de perda e de estabilidade,
e trata o ganho como caso especial.

## 3. Regra de justiça do jogo (revista em 2026-11-16)
O jogador é pontuado contra a **estimativa do modelo**, como pede a proposta. Desde 2026-11-16, valem três regras:

1. **O modelo vê o mesmo que o jogador.**
   - O gabarito vem do modelo de duas épocas, `rf_native_v2` (§4.1).
   - Ele usa exatamente as imagens que o jogo mostra: a época 1 e a ÉPOCA 2, nos dois anos.
2. **O gabarito concorda com a referência.**
   - Só entra no jogo o caso com |Δ modelo − Δ MapBiomas 10 m| ≤ tolerância de pontuação (hoje 10 pp). Antes, o limite era 15 pp.
   - Assim, quem chuta exatamente o valor do MapBiomas leva **100 pontos em todos os casos** (conferido nos 33).
3. **Toda imagem tem par da mesma época.**
   - As duas fotos de cada época são do mesmo período do calendário (época 1: mediana de 1 dia de diferença; ÉPOCA 2: até 30 dias).
   - O caso que não tem ÉPOCA 2 limpa sai do jogo.

O caso que motivou a revisão foi o CAA-03 (Seridó):
- O v1, que via uma foto por ano, dava −16,7 pp, contra −2,5 pp do MapBiomas. Ele lia a Caatinga sem folhas de setembro como pasto.
- Quem chutava "estável" levava só 78 pontos.
- Com o v2, o modelo dá −7,1 pp, e −3 leva 100 pontos.

**Fora do jogo, com motivo listado pelo `export_game.py`:**
- 13 casos sem ÉPOCA 2 limpa. Neles, a chuva sempre veio com nuvem: AMZ-01, CAP-AP, CAP-BA, CAP-CE, CAP-ES, CAP-MA, CAP-PA, CAP-PB, CAP-PE, CAP-PI, CMP-03, CMP-04 e XTR-F02.
- 4 casos em que o modelo e o MapBiomas divergem mais que a tolerância: CAP-MT, CER-03, PAM-03 e XTR-E05.
**Faixa de 100 pontos por caso** (2026-11-16):
- A tolerância única (±10 pp em volta do modelo) foi trocada por uma faixa própria de cada caso.
- A faixa vai de min(modelo, MapBiomas) − 3 a max(modelo, MapBiomas) + 3. O campo é `score_band`, e os 3 pp são o piso da regra de tolerância.
- Fora da faixa, os pontos caem até zero em 40 pp: `round(100 × max(0, 1 − distância até a faixa / 40))`.
- Os 10 pp (erro médio do modelo) continuam valendo só como trava de entrada: modelo e MapBiomas não podem diferir mais que isso.

| Simulação nos 33 casos | ±10 em volta do modelo | Faixa por caso |
|---|---|---|
| Chutar o valor do MapBiomas / do modelo | 100 / 100 | 100 / 100 |
| Chutar sempre 0 (campanha) | 81% | 79% |
| Chutar 0 nos 7 casos com \|Δ\| ≥ 10 pp | 10% | 5% |

- O chute zero quase não muda porque 17 dos 33 casos são estáveis ou armadilhas, e neles 0 é a resposta certa.
- O que torna o jogo mais exigente são mais casos com mudança clara.

- Resultado: o jogo tem **33 casos** (15 desmatamento, 15 estáveis, 1 regeneração, 2 armadilhas).
- Chutar sempre 0 rende 81% dos pontos na campanha. A partida rápida continua sorteando mudanças claras.

### 3.1 Mais casos de mudança clara (2026-11-16)
- `find_sites.py` ganhou `--id-start` e `--per-kind-map`. Foram buscados 20 locais novos de perda (`challenges_extra_v4.json`, IDs a partir de 21): 8 `forest_partial`, 6 `forest_loss` e 6 `open_loss`.
- Os 20 foram baixados, ganharam rótulos e ÉPOCA 2. Dois não têm ÉPOCA 2 limpa: XTR-D23 e XTR-F21.
- O `rf_native_v2` foi treinado de novo com todos: 102 desafios, MAE 15,31 pp.
  - O MAE subiu porque entraram muitas perdas totais (−100 pp), em que o modelo subestima.
  - A tolerância continua em 10 pp (o teto da regra).
- **Funil dos 24 candidatos** (os 20 novos mais XTR-D01, D02, D03 e L01 do acervo):
  - 2 sem ÉPOCA 2 limpa e 2 reprovados na auditoria (XTR-D28 e L26: NDVI não caiu onde os mapas dizem perda).
  - Dos que restaram, 10 passaram na regra de justiça.
  - No QA visual de 4 imagens por caso, 4 foram reprovados: XTR-D22, F25 e L22 por nuvem com sombra na ÉPOCA 2, e XTR-D24 por fumaça na foto de 2020.
  - **Entraram 6:** XTR-D01, D03, D21, D25, L23 e L25. Os reprovados ficaram como `reserva` em `qa_decisions.json`, com o motivo.
- Com o treino novo, CAP-RO e PAN-01 passaram a divergir do MapBiomas e saíram do jogo. O PAM-03 voltou.
- **Jogo:** 38 casos (21 desmatamento, 15 estáveis, 1 regeneração, 1 armadilha), 12 com |Δ| ≥ 10 pp.
  - Chute zero na campanha: **68%**, contra 79% antes.
  - Chutar o valor do MapBiomas continua rendendo 100 em todos os casos.

### 3.2 Regeneração a partir de restaurações documentadas (2026-11-16)
- **Ideia:** em vez de procurar "ganho" nos mapas, que é quase sempre cheia, seca ou reclassificação (GAN-01..12), partir de projetos de restauração com fonte pública.
- **Pesquisa na web** (Agência Brasil, novamata.org, ISA, Iniciativa Verde, IBÁ):
  - Os projetos com data e local publicados são pequenos perto do recorte de 576 ha. Exemplos: Rede de Sementes do Xingu, de 1 a 35 ha por fazenda; Guapiaçu, 60 ha em 2019.
  - Os grandes (Symbiosis, cerca de 2 mil ha; Nova Tamoios, cerca de 430 ha) não informam datas ou são áreas espalhadas.
- **Teste no melhor candidato:** GAN-21, REGUA/Projeto Guapiaçu, com local pela sede no OSM.
  - MapBiomas: +1,7 pp (10 m) e +1,9 pp (30 m) no melhor recorte, sem diferença visível nas imagens. Rejeitado.
- **Conclusão:** com recortes de 2,4 km e intervalo de 5 anos, restauração documentada não gera mudança visível e mensurável. O jogo segue com 1 caso de regeneração (GAN-05).

### 3.3 Regeneração com intervalo longo: 2018 × 2025 (2026-11-17)
- **Web primeiro, de novo:** os projetos grandes com fonte são recentes demais (Mombak/Fazenda Turmalina, Mãe do Rio/PA: plantio a partir de 14/04/2023; re.green e Biomas: 2023–2025) ou pequenos/espalhados (corredores do IPÊ no Pontal; muvuca no Xingu, dezenas de ha). Conferidos no MapBiomas 2017→2025: sem ganho claro nas regiões. A reabilitação de mina da Hydro (Paragominas) tem os dois mapas em contradição (10 m: mata; 30 m: mineração).
- **Varredura do Brasil** com o novo tipo `regrowth` em `find_sites.py` (2017→2025, 66 blocos; ganho de nativa ≥ 20 pp na célula, fora de formação aberta, sem silvicultura, água < 5%, fora do Pantanal). Cada candidato foi conferido nos **dois** mapas (ganho ≥ 15 pp em cada um, diferença ≤ 20 pp). Os reprovados ficaram em `data/catalog/regrowth_2017_rejeitados_mapas.json` (ex.: pasto → campo alagado em Vila Bela/MT; mapas contraditórios em Porto Velho/RO).
- **2017 não existe na coleção usada:** o Sentinel-2 L2A c1 do Earth Search começa em 2018 nesses locais (a coleção antiga `sentinel-2-l2a` tem 2017, mas com processamento diferente do de 2025 — cor diferente sem mudança real). Os pares ficaram **2018 × 2025**; o ganho foi reconferido com 2018.
- **Funil de 21 candidatos** (`challenges_regrowth_2018.json`):
  - 14 sem ÉPOCA 2 limpa (2018 tem poucas cenas limpas) → `reserva`;
  - R56 reprovado na auditoria (NDVI não subiu: só a textura muda);
  - R45 (−20,4 pp) e R17 (+10,2 pp) fora pela regra de justiça → `reserva`;
  - QA visual: duas datas de ÉPOCA 2 com nuvem pequena trocadas no R45 (`season2_exclude.json`).
  - **Entraram 4:** XTR-R07 Oriximiná/PA (mina de bauxita reflorestada na Flona Saracá-Taquera; MRN informa reflorestar as áreas lavradas — fonte IBRAM/Info MRN), XTR-R23 Juara/MT (40% queimado em 2017, MapBiomas Fogo), XTR-R49 Senador La Rocque/MA e XTR-R03 Gaúcha do Norte/MT (ganho pequeno, +5 pp: a área que fica verde é uso agropecuário — "verde não é mata").
- **Modelo retreinado** com todos: 109 desafios, MAE 13,56 pp; tolerância segue 10 pp. Com o treino novo, CAP-RO voltou a concordar com o MapBiomas e entrou.
- **Jogo:** 44 casos (22 desmatamento, 15 estáveis, 5 regeneração, 2 armadilhas), 17 com |Δ| ≥ 10 pp. Chute zero na campanha: **66%**. Todos os dossiês foram refeitos com as estimativas novas.

### 3.5 Ordem da campanha misturada (2026-11-17)
- Antes, a campanha seguia a ordem dos IDs, e os casos do mesmo tipo vinham em sequência (todas as regenerações juntas no fim).
- Agora `export_game.py` (`campaign_order`, sorteio fixo, reprodutível) intercala perdas com os demais tipos e espalha estáveis, regenerações e armadilhas ao longo da lista. Nenhum par de casos seguidos é do mesmo tipo. O 1º caso é uma perda clara (|Δ| ≥ 20 pp).
- Com o acervo atual: regenerações nos casos 6, 12, 22, 32 e 42; armadilhas em 16 e 36. O progresso é guardado por ID, então só a numeração dos casos muda.

### 3.4 Palpite com ponto de partida fixo (2026-11-17)
- **Problema:** a régua −100…+100 pp dava a impressão de avaliar "a área que mudou", e não o recorte inteiro. Ex.: em Oriximiná a grade de mina inteira fica verde, mas boa parte já era floresta em 2018; a variação líquida é +32 pp.
- **Agora:** o jogo mostra a % de vegetação nativa do 1º ano (MapBiomas 10 m, arredondada), fixa, na pergunta, na imagem ("JUN 2018 · NATIVA 46%") e como marca branca na régua. A régua é o recorte inteiro, de 0 a 100%: o jogador ajusta quanto é no 2º ano. Verde-escuro = nativa que continuou; verde = ganho; vermelho = perda. O número em pp aparece como consequência (depois − antes).
- **Pontuação inalterada:** o palpite guardado continua sendo a variação em pp, então recordes e progresso antigos valem. A faixa de 100 pontos é a mesma, só desenhada na nova escala. Mostrar o ponto de partida não entrega a resposta: ele vem do mesmo mapa de referência, e o que vale ponto é a variação.

## 4. Modelo (Random Forest)
Treino final em 2026-11-13 (`data/model/cv_report.json`): 65 desafios com rótulo, 62 áreas independentes, 5 dobras, 300 árvores.

| Métrica (out-of-fold) | Valor |
|---|---|
| Acurácia por pixel | 0,841 |
| F1 da classe nativa | 0,839 |
| Δ vs MapBiomas 10 m: MAE / viés / RMSE | 7,86 / +3,46 / 18,0 pp |
| Δ vs MapBiomas 10 m: correlação de Pearson | 0,70 |
| Δ vs MapBiomas 30 m: MAE / viés / RMSE | 9,08 / +2,00 / 18,5 pp |

Tolerância usada na pontuação: MAE = 7,9 pp.
Treino provisório anterior (15 desafios, sem bioma): OA 0,79, MAE 8,9 pp, r 0,60.

**Erros grandes (RMSE ≫ MAE):**

| Caso | Modelo | MapBiomas 10 m | Leitura |
|---|---|---|---|
| CER-01 (armadilha do eucalipto) | +92 pp | 0 pp | O modelo caiu na armadilha: é o único local com silvicultura, então na dobra de teste ele nunca viu eucalipto |
| AMZ-02 (borda do Xingu) | −32 pp | 0 pp | Hipótese, não verificada: fase da lavoura confundida com floresta |
| PAM-01 | +17 pp | 0 pp | Hipótese: campo nativo × pastagem |
| CAA-01 | +12 pp | −4 pp | Hipótese: sazonalidade da Caatinga |

Os quatro ficam fora do jogo pela regra de justiça (seção 3).

**Formações abertas:** em 8 desafios exportados, o nível de nativa do modelo fica mais de 20 pp abaixo do MapBiomas
(ex.: lavrado de Boa Vista, 2% contra 44%). São campos, savanas, caatinga e restinga, que espectralmente parecem pasto.
A mudança (Δ) continua dentro da regra de justiça, mas o nível não é confiável.
Por isso o jogo mostra só os níveis do MapBiomas e explica essa limitação no manual.

**Melhoria prevista:** novos locais de silvicultura (MS, ES, sul da BA) e de formações campestres no conjunto extra, para o modelo aprender esses casos.

- **Entradas por pixel:** 10 bandas L2A; NDVI, NDMI, NBR, NDWI e razão de red-edge; média e desvio do NDVI em janela 5×5; bioma (one-hot, IBGE).
- **Rótulo:** nativa / não-nativa, do MapBiomas 10 m (Col. 4) no ano de cada imagem.
- **Validação:**
  - GroupKFold por desafio (5 dobras): pixels do desafio avaliado nunca entram no treino;
  - os pilotos ficam no mesmo grupo dos desafios de mesma área (sem vazamento);
  - a estimativa exibida no jogo é a out-of-fold.
- **Métricas:**
  - MAE, viés, RMSE e correlação do Δ em pp, contra o MapBiomas 10 m e, de forma independente, contra o 30 m;
  - acurácia e F1 por pixel.
  - Substituem o MAPE da proposta, que é indefinido ou instável quando Δ ≈ 0.
- **Limitação:** a referência é o MapBiomas, não uma amostra de campo. Uma avaliação no estilo Olofsson et al. (2014) fica como trabalho futuro.

### 4.1 Modelo de duas épocas (`rf_native_v2`, 2026-11-16)
**ÉPOCA 2** (`science/scripts/build_season2.py`, saída em `data/pairs/<ID>/season2/`):
- Para cada ano, escolhe a data mais verde que **os dois anos têm na mesma época**: ≤ 30 dias de diferença no calendário, mesmo ano civil (o rótulo MapBiomas é anual) e ≥ 45 dias da data principal. Entre esses pares, maximiza o NDVI médio do ano menos verde.
- Casar pelo verde em comum, e não só pelo calendário, evita mostrar um ano chuvoso contra um ano seco.
- **Limpeza:**
  - Triagem pela Statistical API do CDSE: SCL válido, névoa e máscara s2cloudless (CLM), com limite relativo ao próprio recorte. A data tem de ser tão limpa quanto os dias mais limpos daquele lugar, porque há recortes com artefato permanente, como solo claro que conta como "névoa".
  - Depois, QA visual das 66 imagens. Três datas com nuvem pequena e sombra passaram pelos filtros e foram excluídas (`data/catalog/season2_exclude.json`): CAP-DF 2024-04-26 e 2024-05-11, PAM-02 2024-06-25.

**Modelo** (`science/scripts/train_rf2.py`):
- Para cada pixel e ano, usa 17 atributos da época 1, 17 da ÉPOCA 2, ΔNDVI e ΔNDMI entre épocas e o bioma: 42 no total.
- Mesmo Random Forest e mesma validação espacial do v1.
- Relatório em `data/model/cv_report_v2.json`.

| Out-of-fold, 84 desafios com 2 épocas | v1 (1 foto/ano) | v2 (2 épocas) |
|---|---|---|
| Δ vs MapBiomas 10 m: MAE | 15,2 pp | **11,6 pp** |
| Casos com \|Δ modelo − Δ MapBiomas\| > 7,9 pp | 37 | **29** |
| Acurácia por pixel | — | 0,847 (F1 nativa 0,848) |

- O MAE do v1 aqui (15,2) é maior que o 7,9 da tabela acima porque o conjunto é outro: inclui os desafios extras, mais difíceis.
- A comparação vale porque v1 e v2 foram medidos nos **mesmos** 84 desafios.
- A tolerância de pontuação segue a regra de sempre, MAE limitado a [3, 10] pp, e por isso agora é **10 pp**.

**No jogo:**
- Cada imagem mostra mês e ano (ex.: SET 2020 × SET 2024), e o botão ÉPOCA 2 troca as duas pela outra época.
- Em 13 casos, a época 1 é bem menos verde que a ÉPOCA 2 nos dois anos (ΔNDVI > 0,10, campo `season_hint`). Neles, aparece o aviso "Mata sem folhas pode parecer pasto · veja ÉPOCA 2".
- No ENTENDA, o dossiê ganhou duas afirmações:
  - as datas e o NDVI das duas épocas (com aviso quando um ano está mais verde que o outro);
  - a concordância entre o modelo e o MapBiomas.

## 5. Jogo (game/)
- **Stack:** Vite + Svelte 5 + TypeScript.
- **Hospedagem:** site estático, com deploy pelo GitHub Pages (`.github/workflows/pages.yml`).
- **Estética:** videogame dos anos 90, original.
  - Fontes pixel (Press Start 2P, VT323; licença OFL, servidas localmente).
  - Scanlines e janelas com borda dupla.
  - Bipes 8-bit gerados com WebAudio, desligáveis.
  - As imagens de satélite **não** são pixeladas, porque são o dado.
- **Telas:**
  - título com menu (teclado/mouse) e demonstração;
  - mapa de fases por UF;
  - caso, com cortina, lado a lado e pisca, e radar da área ao redor;
  - palpite em medidor segmentado de −100 a +100;
  - resultado com contagem, nota S–D, trilha você × modelo × MapBiomas e explicação;
  - manual com método, métricas e limitações.
- **Progresso:** salvo só no `localStorage` do navegador (sem cadastro e sem servidor).
- **Acessibilidade:** controles por teclado, `aria-*` nos sliders, respeito a `prefers-reduced-motion`.
