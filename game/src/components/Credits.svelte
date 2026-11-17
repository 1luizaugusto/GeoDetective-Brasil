<script lang="ts">
  import type { Dataset } from "../lib/types";
  let { data }: { data: Dataset } = $props();
</script>

<article class="credits">
  <h1 class="gold-t">CRÉDITOS</h1>

  <section class="win">
    <span class="win-title">AUTORIA</span>
    <p>Desenvolvido por <b class="gold-t">Luiz Augusto de Almeida</b>, no âmbito do <b>Future Tech Leaders Brasil 2026 – Space Tech Bootcamp</b>.</p>
    <p>O projeto integra as atividades desenvolvidas durante o programa, que conta com a parceria do
      <b>Programa das Nações Unidas para o Desenvolvimento (PNUD/UNDP)</b>, do <b>SDG AI Lab</b>, da
      <b>Agência Espacial Brasileira (AEB)</b> e do <b>PNUD Brasil</b>.</p>
    <p><b>As instituições mencionadas são parceiras do Future Tech Leaders Brasil 2026, não constituindo parcerias diretas ou endosso institucional a este projeto.</b></p>
  </section>

  <section class="win">
    <span class="win-title">DADOS E LICENÇAS</span>
    <p>Código aberto (licença MIT): <a href="https://github.com/1luizaugusto/GeoDetective-Brasil" target="_blank" rel="noopener">github.com/1luizaugusto/GeoDetective-Brasil</a></p>
    <p>{data.licenses}. Malha dos estados: IBGE.</p>
    <p class="dim">Dados gerados em {new Date(data.generated_utc).toLocaleDateString("pt-BR")} · esquema {data.schema_version}.</p>
  </section>
</article>

<style>
  .credits { max-width: 860px; margin: 0 auto; display: grid; gap: 34px; }
  h1 { text-align: center; text-shadow: 4px 4px 0 var(--red-dk); margin-top: 8px; }
  .win { padding-top: 26px; }
  a { overflow-wrap: anywhere; }
</style>
