<script lang="ts">
  import type { Dataset } from "../lib/types";
  import { L, i18n, locale } from "../lib/i18n.svelte";
  let { data }: { data: Dataset } = $props();
  const T = $derived(L());
  const en = $derived(i18n.lang === "en");
</script>

<article class="credits">
  <h1 class="gold-t">{T.credits}</h1>

  <section class="win">
    <span class="win-title">{T.authorship}</span>
    {#if en}
      <p>Developed by <b class="gold-t">Luiz Augusto de Almeida</b> as part of <b>Future Tech Leaders Brasil 2026 – Space Tech Bootcamp</b>.</p>
      <p>The project is part of the activities carried out during the program, which is supported by the
        <b>United Nations Development Programme (UNDP)</b>, the <b>SDG AI Lab</b>, the <b>Brazilian Space Agency (AEB)</b>
        and <b>UNDP Brazil</b>.</p>
      <p><b>The institutions mentioned are partners of Future Tech Leaders Brasil 2026 and do not constitute direct partnerships with, or institutional endorsement of, this project.</b></p>
    {:else}
      <p>Desenvolvido por <b class="gold-t">Luiz Augusto de Almeida</b>, no âmbito do <b>Future Tech Leaders Brasil 2026 – Space Tech Bootcamp</b>.</p>
      <p>O projeto integra as atividades desenvolvidas durante o programa, que conta com a parceria do
        <b>Programa das Nações Unidas para o Desenvolvimento (PNUD/UNDP)</b>, do <b>SDG AI Lab</b>, da
        <b>Agência Espacial Brasileira (AEB)</b> e do <b>PNUD Brasil</b>.</p>
      <p><b>As instituições mencionadas são parceiras do Future Tech Leaders Brasil 2026, não constituindo parcerias diretas ou endosso institucional a este projeto.</b></p>
    {/if}
  </section>

  <section class="win">
    <span class="win-title">{T.dataLicenses}</span>
    <p>{T.openSource} <a href="https://github.com/1luizaugusto/GeoDetective-Brasil" target="_blank" rel="noopener">github.com/1luizaugusto/GeoDetective-Brasil</a></p>
    <p>{data.licenses}. {T.statesMesh}</p>
    <p class="dim">{T.generated(new Date(data.generated_utc).toLocaleDateString(locale()), data.schema_version)}</p>
  </section>
</article>

<style>
  .credits { max-width: 860px; margin: 0 auto; display: grid; gap: 34px; }
  h1 { text-align: center; text-shadow: 4px 4px 0 var(--red-dk); margin-top: 8px; }
  .win { padding-top: 26px; }
  a { overflow-wrap: anywhere; }
</style>
