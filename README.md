# GeoDetective Brasil

**Projeto final — Space Tech Bootcamp 2026 / Future Tech Leaders Brasil**

**Autor:** Luiz Augusto de Oliveira Almeida  
**Contato:** 1st.luizaugusto@gmail.com

## Objetivo

Jogo educativo de interpretação de imagens gratuitas de satélite. Cada desafio apresenta **duas imagens da mesma área**, em datas distintas. O jogador estima a **variação líquida na proporção da área coberta por vegetação**, numa escala de **−100 a +100 pontos percentuais**. A resposta é comparada a uma referência geoespacial independente e a uma estimativa produzida por Machine Learning.

**Escopo planejado:** até **100 imagens individuais**, agrupadas em até **50 pares/desafios**, cobrindo os **6 biomas brasileiros** e as **27 capitais**. Sem promessa de 50 desafios prontos nesta versão inicial.

## Fontes e tecnologia planejadas

- **Copernicus Sentinel-2 L2A:** bandas multiespectrais para as duas datas.
- **MapBiomas:** rótulos auxiliares para preparação do treinamento e aferição, sujeitos a revisão independente.
- **IBGE:** limites geográficos dos biomas e municípios.
- **Python:** rasterio, numpy, pandas e scikit-learn (`RandomForestClassifier`).
- **Web:** HTML, CSS e JavaScript; hospedagem via GitHub Pages.

## Metodologia em resumo

1. Definir áreas de interesse (AOIs), delimitações e período comparável do ano.
2. Obter pares de imagens Sentinel-2, com correção/máscara de nuvens e alinhamento de grade.
3. Construir amostras rotuladas de cobertura vegetal, distinguindo vegetação nativa de cultivos quando a pergunta exigir.
4. Treinar Random Forest em atributos espectrais e índices; separar treino/teste **geograficamente**.
5. Avaliar F1, precisão, recall e matriz de confusão; comparar estimativas percentuais com referência não usada no treinamento (MAE em pontos percentuais).
6. Exportar desafios reais com imagens RGB, metadados, estimativa do modelo e referência.
7. Publicar a interface gamificada com pontuação por erro absoluto.

**Definição matemática:** `delta_pp = 100 * (vegetated_area_after - vegetated_area_before) / valid_area`. O denominador deve representar a mesma área válida nos dois anos; um saldo igual a zero pode ocultar perdas e ganhos locais compensatórios. É incorreto chamar toda variação sazonal de degradação/recuperação ambiental.

## Estado atual

**Protótipo inicial:** interface local demonstrativa usando um cenário abstrato. **Não contém imagens de satélite reais, modelo treinado ou resultados científicos.** Esses componentes serão inseridos nas próximas etapas.

## Executar demonstração local

Abra `game/index.html` no navegador. Para publicar como GitHub Pages, configure Pages para servir a pasta `/game` via GitHub Actions, ou copie os arquivos do jogo para a raiz ou `/docs` (configuração *Deploy from a branch*).

## Organização

- `game/`: protótipo estático do jogo.
- `scripts/`: processamento, treinamento e exportação dos desafios (a implementar).
- `data/`: apenas orientações e metadados; GeoTIFFs grandes não devem ser enviados ao Git.
- `models/`: modelos treinados e documentação (a implementar).
- `docs/`: metodologia e referências (a implementar).

## Referências iniciais a revisar na redação final

- Copernicus Sentinel-2: https://dataspace.copernicus.eu/
- MapBiomas: https://brasil.mapbiomas.org/
- IBGE: https://www.ibge.gov.br/
- scikit-learn Random Forest: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html

## Licença

Código-fonte sob licença MIT (consulte `LICENSE`). Dados e imagens de terceiros permanecem sujeitos às respectivas condições e atribuições.
