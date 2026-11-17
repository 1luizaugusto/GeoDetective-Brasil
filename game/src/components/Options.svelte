<script lang="ts">
  import { sound, toggleSound, sfx } from "../lib/sfx.svelte";
  import { settings, saveSettings } from "../lib/settings.svelte";
  import { resetProgress, progress } from "../lib/progress.svelte";
  import { clearRuns } from "../lib/run.svelte";

  const MODES = [["curtain", "CORTINA"], ["side", "LADO A LADO"], ["blink", "PISCA"]] as const;
  let confirmReset = $state(false);
  let done = $state("");

  function cycleMode(d: number) {
    const i = MODES.findIndex((m) => m[0] === settings.compareMode);
    settings.compareMode = MODES[(i + d + MODES.length) % MODES.length][0];
    saveSettings(); sfx("move");
  }
  function flip(k: "crt" | "typewriter") { settings[k] = !settings[k]; saveSettings(); sfx("move"); }

  type Row = { label: string; value: string; act: (d: number) => void };
  const rows = $derived<Row[]>([
    { label: "SOM", value: sound.on ? "ON" : "OFF", act: () => toggleSound() },
    { label: "COMPARAÇÃO INICIAL", value: MODES.find((m) => m[0] === settings.compareMode)![1], act: cycleMode },
    { label: "EFEITO TV (SCANLINES)", value: settings.crt ? "ON" : "OFF", act: () => flip("crt") },
    { label: "TEXTO DATILOGRAFADO", value: settings.typewriter ? "ON" : "OFF", act: () => flip("typewriter") },
  ]);
  let sel = $state(0);
  function onkey(e: KeyboardEvent) {
    if (confirmReset) return;
    if (e.key === "ArrowDown") { sel = (sel + 1) % rows.length; sfx("move"); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = (sel - 1 + rows.length) % rows.length; sfx("move"); e.preventDefault(); }
    else if (e.key === "ArrowRight" || e.key === "Enter") { rows[sel].act(1); e.preventDefault(); }
    else if (e.key === "ArrowLeft") { rows[sel].act(-1); e.preventDefault(); }
  }
  const nPlayed = $derived(Object.keys(progress.attempts).length);
</script>

<svelte:window onkeydown={onkey} />

<h1 class="gold-t">OPÇÕES</h1>
<section class="win opts">
  <span class="win-title">CONFIGURAÇÃO</span>
  {#each rows as r, i}
    <button class="row" class:sel={i === sel} onmouseenter={() => (sel = i)} onclick={() => { sel = i; r.act(1); }}>
      <span class="cur">{i === sel ? "▶" : ""}</span><span>{r.label}</span><b>◀ {r.value} ▶</b>
    </button>
  {/each}
  <p class="lbl hint">SETAS ESCOLHEM · ◀ ▶ MUDAM · ESC VOLTA AO MENU</p>
</section>

<section class="win opts">
  <span class="win-title">DADOS SALVOS</span>
  <p>O progresso fica só neste navegador. Nada é enviado para servidor nenhum.</p>
  {#if !confirmReset}
    <button class="pbtn" onclick={() => { confirmReset = true; sfx("move"); }}>APAGAR PROGRESSO E RECORDES</button>
  {:else}
    <p class="gold-t">Apagar {nPlayed} casos jogados e os recordes de partida? Não dá para desfazer.</p>
    <div class="row2">
      <button class="pbtn gold" onclick={() => { resetProgress(); clearRuns(); confirmReset = false; done = "PROGRESSO APAGADO."; sfx("bad"); }}>SIM, APAGAR</button>
      <button class="pbtn" onclick={() => { confirmReset = false; sfx("move"); }}>NÃO</button>
    </div>
  {/if}
  {#if done}<p class="lbl">{done}</p>{/if}
</section>
<p><a class="pbtn" href="#/">◀ MENU</a></p>

<style>
  h1 { font-size: clamp(16px, 3vw, 24px); margin: 6px 0 22px; }
  .opts { max-width: 720px; margin-bottom: 24px; }
  .row { display: flex; align-items: center; gap: 10px; width: 100%; background: none; border: 0; border-bottom: 2px dashed var(--line-lo); padding: 12px 4px; font-family: var(--px); font-size: 11px; color: var(--dim); text-align: left; }
  .row.sel { color: var(--ink); }
  .row b { margin-left: auto; font-weight: 400; color: var(--cyan); white-space: nowrap; }
  .cur { width: 22px; color: var(--gold); }
  .hint { margin: 14px 0 0; }
  .row2 { display: flex; gap: 12px; flex-wrap: wrap; }
  @media (max-width: 520px) { .row { flex-wrap: wrap; } .row b { margin-left: 32px; } }
</style>
