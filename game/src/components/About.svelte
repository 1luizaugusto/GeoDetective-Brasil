<script lang="ts">
  import type { Dataset } from "../lib/types";
  let { data }: { data: Dataset } = $props();
  const m = $derived(data.model);
</script>

<article class="manual">
  <h1 class="gold-t">MANUAL DO DETETIVE</h1>

  <section class="win">
    <span class="win-title">1 · A MISSÃO</span>
    <p>O jogo mostra quanto do recorte <b>inteiro</b> era <b class="gold-t">vegetação nativa</b> no primeiro ano (MapBiomas) —
      esse é o ponto de partida, fixo. Você estima quanto é no segundo ano.
      Se era 60% e você acha que ficou 35%, a variação é <b class="neg">−25 pp</b> (pontos percentuais: a diferença entre as duas porcentagens).
      É a variação que vale ponto.</p>
    <p class="dim">Conta como nativa: florestas, savanas, campos, mangues e restingas (classes do MapBiomas).
      <b>Não conta</b>: eucalipto e pinus plantados, lavouras e pastagens — mesmo quando parecem verdes.</p>
  </section>

  <section class="win">
    <span class="win-title">2 · AS IMAGENS</span>
    <ul>
      <li>Satélites <b>Sentinel-2</b> (Copernicus, ESA/União Europeia), produto L2A, 10 m por pixel.</li>
      <li>As duas datas estão na <b>mesma grade</b>: mesmo lugar, pixel a pixel, e mesma estação do ano.</li>
      <li>Cenas com nuvem ou fumaça são filtradas automaticamente e revisadas a olho.</li>
      <li>Ampliadas 3× por interpolação, <b>sem super-resolução</b>: nenhum detalhe é inventado.</li>
    </ul>
  </section>

  <section class="win">
    <span class="win-title">3 · O GABARITO</span>
    <p>Um modelo <b>Random Forest</b> classificou cada pixel de 10 m como nativo ou não, usando as 10 bandas do
      Sentinel-2 e índices como NDVI. Ele aprendeu com rótulos do <b>MapBiomas</b>, e cada caso foi respondido por um
      modelo que <b>nunca viu aquele lugar</b> ({m.validation}).</p>
    <dl>
      <dt>ACERTO POR PIXEL</dt><dd>{(m.pixel.overall_accuracy * 100).toFixed(1)}%</dd>
      <dt>ERRO MÉDIO DO Δ</dt><dd>{m.delta_vs_mapbiomas10m.MAE_pp} pp</dd>
      <dt>VIÉS MÉDIO</dt><dd>{m.delta_vs_mapbiomas10m.bias_pp} pp</dd>
      <dt>CORRELAÇÃO</dt><dd>{m.delta_vs_mapbiomas10m.pearson_r}</dd>
    </dl>
    <p class="dim">Só entram no jogo casos em que o modelo e o MapBiomas concordam. Tudo é calculado antes: o jogo
      não roda inteligência artificial.</p>
  </section>

  <section class="win">
    <span class="win-title">4 · PONTUAÇÃO</span>
    <p>Cada caso tem uma <b class="pos">faixa de 100 pontos</b> (verde na régua do resultado): vai do valor do modelo ao do
      MapBiomas, com {data.scoring.margin_pp ?? 3} pp de margem para cada lado. Os dois são medições aceitáveis, então quem acerta
      qualquer um deles leva 100.</p>
    <p class="dim">Fora da faixa, os pontos caem aos poucos: 40 pp além dela, 0. Só entram no jogo casos em que o modelo e o
      MapBiomas diferem no máximo {data.scoring.tolerance_pp} pp (o erro médio do modelo em áreas que ele não viu no treino).</p>
    <p class="ranks"><b class="gold-t">S</b> 95+ · <b class="pos">A</b> 80+ · <b style="color:var(--cyan)">B</b> 60+ · <b>C</b> 35+ · <b class="neg">D</b> abaixo</p>
  </section>

  <section class="win">
    <span class="win-title">5 · LIMITAÇÕES</span>
    <ul>{#each data.limitations as l}<li>{l}</li>{/each}</ul>
  </section>

  <section class="win">
    <span class="win-title">CRÉDITOS</span>
    <p>Desenvolvido por <b class="gold-t">Luiz Augusto de Almeida</b>, no âmbito do <b>Future Tech Leaders Brasil 2026 – Space Tech Bootcamp</b>.</p>
    <p>O projeto integra as atividades desenvolvidas durante o programa, que conta com a parceria do
      <b>Programa das Nações Unidas para o Desenvolvimento (PNUD/UNDP)</b>, do <b>SDG AI Lab</b>, da
      <b>Agência Espacial Brasileira (AEB)</b> e do <b>PNUD Brasil</b>.</p>
    <p><b>As instituições mencionadas são parceiras do Future Tech Leaders Brasil 2026, não constituindo parcerias diretas ou endosso institucional a este projeto.</b></p>
    <p>Código aberto (licença MIT): <a href="https://github.com/1luizaugusto/GeoDetective-Brasil" target="_blank" rel="noopener">github.com/1luizaugusto/GeoDetective-Brasil</a></p>
    <p>{data.licenses}. Malha dos estados: IBGE.</p>
    <p class="dim">Dados gerados em {new Date(data.generated_utc).toLocaleDateString("pt-BR")} · esquema {data.schema_version}.</p>
  </section>
</article>

<style>
  .manual { max-width: 860px; margin: 0 auto; display: grid; gap: 34px; }
  h1 { text-align: center; text-shadow: 4px 4px 0 var(--red-dk); margin-top: 8px; }
  .win { padding-top: 26px; }
  ul { padding-left: 22px; margin: 0; }
  li { margin-bottom: 6px; }
  li::marker { content: "■ "; color: var(--gold); }
  dl { display: grid; grid-template-columns: 1fr auto; margin: 10px 0 14px; }
  dt, dd { margin: 0; padding: 6px 0; border-bottom: 2px dashed var(--line-lo); }
  dt { font-family: var(--px); font-size: 9px; display: flex; align-items: center; color: var(--dim); }
  dd { text-align: right; font-family: var(--px); font-size: 12px; color: var(--gold); }
  .ranks b { font-family: var(--px); font-weight: 400; }
</style>
