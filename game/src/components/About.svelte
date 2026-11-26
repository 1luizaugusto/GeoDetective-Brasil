<script lang="ts">
  import type { Dataset } from "../lib/types";
  import { i18n, locale, COVER } from "../lib/i18n.svelte";
  let { data }: { data: Dataset } = $props();
  const m = $derived(data.model);
  const en = $derived(i18n.lang === "en");
  const n = (v: number, d = 1) => v.toLocaleString(locale(), { maximumFractionDigits: d });
  const lim = $derived(en && data.limitations_en ? data.limitations_en : data.limitations);
  const nat = Object.entries(COVER).filter(([k, v]) => v.native && k !== "tidalflat");
  const non = Object.entries(COVER).filter(([k, v]) => !v.native && ["pasture", "crop", "silviculture", "mosaic", "urban", "mining"].includes(k));
</script>

<article class="manual">
  <h1 class="gold-t">{en ? "DETECTIVE'S MANUAL" : "MANUAL DO DETETIVE"}</h1>

  <section class="win">
    <span class="win-title">{en ? "1 · THE MISSION" : "1 · A MISSÃO"}</span>
    {#if en}
      <p>The game shows how much of the <b>whole</b> tile was <b class="gold-t">native vegetation</b> in the first year (MapBiomas):
        that is the fixed starting point. You estimate the second year. If it was 60% and you think it became 35%, the change is
        <b class="neg">−25 pp</b> (percentage points: the difference between the two percentages). The change is what scores.</p>
    {:else}
      <p>O jogo mostra quanto do recorte <b>inteiro</b> era <b class="gold-t">vegetação nativa</b> no primeiro ano (MapBiomas):
        esse é o ponto de partida, fixo. Você estima quanto é no segundo ano. Se era 60% e você acha que ficou 35%, a variação é
        <b class="neg">−25 pp</b> (pontos percentuais: a diferença entre as duas porcentagens). É a variação que vale ponto.</p>
    {/if}
  </section>

  <section class="win">
    <span class="win-title">{en ? "2 · WHAT COUNTS AS NATIVE" : "2 · O QUE CONTA COMO NATIVA"}</span>
    <p>{en ? "Native vegetation follows the MapBiomas legend: forest and non-forest formations. Open formations with few trees are native too."
      : "Vegetação nativa segue a legenda do MapBiomas: formações florestais e não florestais. Formações abertas, com poucas árvores, também são nativas."}</p>
    <ul class="gl">
      {#each nat as [k, v]}<li><i style={`background:${v.color}`}></i><b>{en ? v.en : v.pt}</b></li>{/each}
    </ul>
    <p class="dim">{en ? "Not native, even when green:" : "Não conta como nativa, mesmo quando verde:"}</p>
    <ul class="gl">
      {#each non as [k, v]}<li><i style={`background:${v.color}`}></i>{en ? v.en : v.pt} ✕</li>{/each}
    </ul>
    <dl class="terms">
      {#if en}
        <dt>OPEN PHYSIOGNOMY</dt><dd>Vegetation with low tree cover by nature (grassland, savanna, lavrado). Not a sign of degradation.</dd>
        <dt>ROCK OUTCROP</dt><dd>Exposed rock with plants growing between the stones; MapBiomas groups it with native herbaceous and shrub vegetation.</dd>
        <dt>CLEARING / CONVERSION</dt><dd>Native vegetation removed and replaced by another use (pasture, cropland, mining, city).</dd>
        <dt>BURNED AREA</dt><dd>Fire changes the color; the vegetation stays native unless it is replaced.</dd>
        <dt>TREE PLANTATION</dt><dd>Commercial forestry (eucalyptus, pine). It is a crop, not native vegetation.</dd>
      {:else}
        <dt>FISIONOMIA ABERTA</dt><dd>Vegetação com poucas árvores por natureza (campo, savana, lavrado). Não é sinal de degradação.</dd>
        <dt>AFLORAMENTO ROCHOSO</dt><dd>Rocha exposta, com plantas entre as pedras; o MapBiomas o agrupa com a vegetação herbácea e arbustiva nativa.</dd>
        <dt>SUPRESSÃO / CONVERSÃO</dt><dd>Retirada da vegetação nativa e troca por outro uso (pasto, lavoura, mineração, cidade).</dd>
        <dt>ÁREA QUEIMADA</dt><dd>O fogo muda a cor; a vegetação continua nativa se não for substituída.</dd>
        <dt>SILVICULTURA</dt><dd>Plantio comercial de árvores (eucalipto, pinus). É cultivo, não vegetação nativa.</dd>
      {/if}
    </dl>
  </section>

  <section class="win">
    <span class="win-title">{en ? "3 · THE IMAGES" : "3 · AS IMAGENS"}</span>
    <ul>
      {#if en}
        <li><b>Sentinel-2</b> satellites (Copernicus, ESA/European Union), L2A product, 10 m per pixel.</li>
        <li>Both dates share the <b>same grid</b>: same place, pixel by pixel, and the same time of year.</li>
        <li><b>SEASON 2</b> shows a second pair of dates, at least 45 days away, so dry-season and leaf-off effects can be checked.</li>
        <li>Scenes with clouds or smoke are filtered automatically and reviewed by eye.</li>
        <li>Upscaled 3× by interpolation, <b>no super-resolution</b>: no detail is invented.</li>
      {:else}
        <li>Satélites <b>Sentinel-2</b> (Copernicus, ESA/União Europeia), produto L2A, 10 m por pixel.</li>
        <li>As duas datas estão na <b>mesma grade</b>: mesmo lugar, pixel a pixel, e mesma época do ano.</li>
        <li>A <b>ÉPOCA 2</b> mostra um segundo par de datas, a pelo menos 45 dias, para conferir efeitos da seca e da queda de folhas.</li>
        <li>Cenas com nuvem ou fumaça são filtradas automaticamente e revisadas a olho.</li>
        <li>Ampliadas 3× por interpolação, <b>sem super-resolução</b>: nenhum detalhe é inventado.</li>
      {/if}
    </ul>
  </section>

  <section class="win">
    <span class="win-title">{en ? "4 · THE ANSWER KEY" : "4 · O GABARITO"}</span>
    {#if en}
      <p>A <b>Random Forest</b> model classified each 10 m pixel as native or not, using the 10 Sentinel-2 bands of both seasons,
        indices such as NDVI, and the biome. It learned from <b>MapBiomas</b> labels in other tiles, and each case was answered by a
        model that <b>never trained on that place</b> (spatial cross-validation by case, out of sample).</p>
    {:else}
      <p>Um modelo <b>Random Forest</b> classificou cada pixel de 10 m como nativo ou não, usando as 10 bandas do Sentinel-2 das
        duas épocas, índices como o NDVI e o bioma. Ele aprendeu com rótulos do <b>MapBiomas</b> em outros recortes, e cada caso foi
        respondido por um modelo que <b>não treinou com aquele lugar</b> (validação cruzada espacial por caso, fora da amostra).</p>
    {/if}
    <dl>
      <dt>{en ? "PIXEL ACCURACY" : "ACERTO POR PIXEL"}</dt><dd>{n(m.pixel.overall_accuracy * 100)}%</dd>
      <dt>{en ? "MEAN Δ ERROR" : "ERRO MÉDIO DO Δ"}</dt><dd>{n(m.delta_vs_mapbiomas10m.MAE_pp, 2)} pp</dd>
      <dt>{en ? "MEAN BIAS" : "VIÉS MÉDIO"}</dt><dd>{n(m.delta_vs_mapbiomas10m.bias_pp, 2)} pp</dd>
      <dt>RMSE</dt><dd>{n(m.delta_vs_mapbiomas10m.RMSE_pp, 2)} pp</dd>
    </dl>
    <p class="dim">{en ? "Everything is computed in advance: the game does not run AI." : "Tudo é calculado antes: o jogo não roda inteligência artificial."}</p>
  </section>

  <section class="win">
    <span class="win-title">{en ? "5 · SCORING" : "5 · PONTUAÇÃO"}</span>
    {#if en}
      <p>Each case has a <b class="pos">100-point band</b> (green on the result scale): from the model's value to MapBiomas', with
        {data.scoring.margin_pp ?? 3} pp of margin on each side. Both are acceptable measurements, so matching either earns 100.</p>
      <p class="dim">Outside the band, points drop gradually: 40 pp beyond it, 0. <b>Admission rule</b> (separate from scoring): a case only
        enters the game if the model and MapBiomas differ by at most {data.scoring.tolerance_pp} pp. That limit is the model's mean error
        ({n(m.delta_vs_mapbiomas10m.MAE_pp, 2)} pp) capped at 10 pp.</p>
    {:else}
      <p>Cada caso tem uma <b class="pos">faixa de 100 pontos</b> (verde na régua do resultado): vai do valor do modelo ao do
        MapBiomas, com {data.scoring.margin_pp ?? 3} pp de margem para cada lado. Os dois são medições aceitáveis, então quem acerta
        qualquer um deles leva 100.</p>
      <p class="dim">Fora da faixa, os pontos caem aos poucos: 40 pp além dela, 0. <b>Regra de entrada</b> (separada da pontuação): só entram
        no jogo casos em que o modelo e o MapBiomas diferem no máximo {data.scoring.tolerance_pp} pp. Esse limite é o erro médio do
        modelo ({n(m.delta_vs_mapbiomas10m.MAE_pp, 2)} pp) limitado a 10 pp.</p>
    {/if}
    <p class="ranks"><b class="gold-t">S</b> 95+ · <b class="pos">A</b> 80+ · <b style="color:var(--cyan)">B</b> 60+ · <b>C</b> 35+ · <b class="neg">D</b> {en ? "below" : "abaixo"}</p>
  </section>

  <section class="win">
    <span class="win-title">{en ? "6 · LIMITATIONS" : "6 · LIMITAÇÕES"}</span>
    <ul>{#each lim as l}<li>{l}</li>{/each}</ul>
  </section>

  <p class="more"><a href="#/creditos">{en ? "CREDITS ▶" : "CRÉDITOS ▶"}</a></p>
</article>

<style>
  .manual { max-width: 860px; margin: 0 auto; display: grid; gap: 34px; }
  h1 { text-align: center; text-shadow: 4px 4px 0 var(--red-dk); margin-top: 8px; }
  .win { padding-top: 26px; }
  ul { padding-left: 22px; margin: 0; }
  li { margin-bottom: 6px; }
  li::marker { content: "■ "; color: var(--gold); }
  .gl { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 14px; margin: 6px 0 10px; }
  .gl li { margin: 0; display: flex; align-items: center; gap: 6px; }
  .gl li::marker { content: ""; }
  .gl i { width: 12px; height: 12px; border: 2px solid var(--shadow); flex: none; }
  dl { display: grid; grid-template-columns: 1fr auto; margin: 10px 0 14px; }
  dt, dd { margin: 0; padding: 6px 0; border-bottom: 2px dashed var(--line-lo); }
  dt { font-family: var(--px); font-size: 9px; display: flex; align-items: center; color: var(--dim); }
  dd { text-align: right; font-family: var(--px); font-size: 12px; color: var(--gold); }
  .terms { grid-template-columns: 1fr; }
  .terms dt { color: var(--gold); border-bottom: 0; padding-bottom: 0; font-size: 8px; }
  .terms dd { text-align: left; font-family: var(--txt); font-size: 19px; color: var(--ink); }
  .more { text-align: center; margin: 0; font-family: var(--px); font-size: 10px; }
  .ranks b { font-family: var(--px); font-weight: 400; }
</style>
