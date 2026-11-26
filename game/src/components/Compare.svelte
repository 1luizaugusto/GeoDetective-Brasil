<script lang="ts">
  // Grades idênticas (mesmo CRS/origem/pixel): a cortina compara pixel a pixel.
  // Ocupa TODO o espaço que o pai der (altura fixa do palco): a imagem é o maior quadrado que cabe.
  // Os selos (mês/ano · % nativa) e a legenda ficam FORA da imagem, para não cobrir o mapa no celular.
  import type { Snippet } from "svelte";
  import { sfx } from "../lib/sfx.svelte";
  import { settings } from "../lib/settings.svelte";
  import { L } from "../lib/i18n.svelte";
  let { before, after, labelBefore, labelAfter, alt, caption = "", overlayBefore = "", overlayAfter = "", legend, tools }:
    { before: string; after: string; labelBefore: string; labelAfter: string; alt: string; caption?: string;
      overlayBefore?: string; overlayAfter?: string; legend?: Snippet; tools?: Snippet } = $props();
  const T = $derived(L());

  let mode = $state<"curtain" | "side" | "blink">(settings.compareMode);
  let pos = $state(50);
  let showAfter = $state(false);
  let box: HTMLDivElement | undefined = $state();
  let dragging = false;

  function setFromEvent(e: PointerEvent) {
    if (!box) return;
    const r = box.getBoundingClientRect();
    pos = Math.min(100, Math.max(0, ((e.clientX - r.left) / r.width) * 100));
  }
  function setMode(m: typeof mode) { mode = m; sfx("move"); }

  // Fade nos SELOS DE ANO (as imagens ficam sempre com brilho total):
  // ao puxar a cortina em direção a um ano, o selo do OUTRO ano vai apagando — até 25%, nunca some.
  const MIN_OPACITY = 0.25;
  const opBefore = $derived(mode === "blink" ? (showAfter ? MIN_OPACITY : 1) : pos < 50 && mode === "curtain" ? 1 - (1 - MIN_OPACITY) * ((50 - pos) / 50) : 1);
  const opAfter = $derived(mode === "blink" ? (showAfter ? 1 : MIN_OPACITY) : pos > 50 && mode === "curtain" ? 1 - (1 - MIN_OPACITY) * ((pos - 50) / 50) : 1);
</script>

<div class="cmp">
  <div class="modes" role="tablist" aria-label={T.compareMode}>
    <button role="tab" aria-selected={mode === "curtain"} class:on={mode === "curtain"} onclick={() => setMode("curtain")}>{T.curtain}</button>
    <button role="tab" aria-selected={mode === "side"} class:on={mode === "side"} onclick={() => setMode("side")}>{T.side}</button>
    <button role="tab" aria-selected={mode === "blink"} class:on={mode === "blink"} onclick={() => setMode("blink")}>{T.blink}</button>
    {#if tools}<span class="tools">{@render tools()}</span>{/if}
  </div>

  <div class="stamps" aria-hidden="true">
    <span class="yr l fade" style={`opacity:${opBefore}`}>{labelBefore}</span>
    <span class="yr r fade" style={`opacity:${opAfter}`}>{labelAfter}</span>
  </div>

  <div class="area">
    {#if mode === "curtain"}
      <div class="screen sq curtain" bind:this={box} role="slider" tabindex="0" aria-label={T.curtainPos}
        aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(pos)}
        onpointerdown={(e) => { dragging = true; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); setFromEvent(e); }}
        onpointermove={(e) => dragging && setFromEvent(e)}
        onpointerup={() => (dragging = false)}
        onkeydown={(e) => {
          if (e.key === "ArrowLeft") { pos = Math.max(0, pos - 5); e.preventDefault(); }
          if (e.key === "ArrowRight") { pos = Math.min(100, pos + 5); e.preventDefault(); }
          if (e.key === "Home") { pos = 0; e.preventDefault(); }
          if (e.key === "End") { pos = 100; e.preventDefault(); }
        }}>
        <img src={after} alt={`${alt} — ${labelAfter}`} draggable="false" class="layer" style={`clip-path: inset(0 0 0 ${pos}%)`} />
        {#if overlayAfter}<img src={overlayAfter} alt="" draggable="false" class="layer px" style={`clip-path: inset(0 0 0 ${pos}%)`} />{/if}
        <img src={before} alt={`${alt} — ${labelBefore}`} draggable="false" class="layer" style={`clip-path: inset(0 ${100 - pos}% 0 0)`} />
        {#if overlayBefore}<img src={overlayBefore} alt="" draggable="false" class="layer px" style={`clip-path: inset(0 ${100 - pos}% 0 0)`} />{/if}
        <div class="handle" style={`left:${pos}%`}><span>◀▶</span></div>
      </div>
    {:else if mode === "side"}
      <div class="side">
        <div class="screen half"><img class="layer" src={before} alt={`${alt} — ${labelBefore}`} />{#if overlayBefore}<img class="layer px" src={overlayBefore} alt="" />{/if}</div>
        <div class="screen half"><img class="layer" src={after} alt={`${alt} — ${labelAfter}`} />{#if overlayAfter}<img class="layer px" src={overlayAfter} alt="" />{/if}</div>
      </div>
    {:else}
      <button class="screen sq blinkbox" onclick={() => { showAfter = !showAfter; sfx("tick"); }} aria-label={T.swap}>
        <img class="layer" src={showAfter ? after : before} alt={`${alt} — ${showAfter ? labelAfter : labelBefore}`} />
        {#if showAfter ? overlayAfter : overlayBefore}<img class="layer px" src={showAfter ? overlayAfter : overlayBefore} alt="" />{/if}
      </button>
    {/if}
  </div>

  <p class="cap" class:empty={!legend && !caption && mode !== "blink"}>
    {#if legend}{@render legend()}{:else}{caption || (mode === "blink" ? T.tapSwap : "")}{/if}
  </p>
</div>

<style>
  .cmp { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .modes { flex: none; display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 6px; align-items: center; }
  .modes button { font-family: var(--px); font-size: 8px; background: var(--navy); border: 2px solid var(--line-lo); padding: 7px 7px 6px; color: var(--dim); white-space: nowrap; }
  .modes button.on { background: var(--cyan); color: var(--night); border-color: var(--ink); }
  .tools { margin-left: auto; display: flex; gap: 5px; }
  /* selos FORA da imagem: uma linha acima, antes à esquerda e depois à direita */
  .stamps { flex: none; display: flex; justify-content: space-between; gap: 8px; padding: 0 8px; }
  .yr { font-family: var(--px); font-size: 8px; line-height: 1.6; white-space: nowrap; }
  .yr.l { color: var(--gold); } .yr.r { color: var(--cyan); text-align: right; }
  @container (max-width: 400px) { .yr { font-size: 7px; } .stamps { padding: 0 4px; } .modes { gap: 3px; } .modes button { padding: 7px 4px 6px; } .tools { gap: 3px; } }
  .yr.fade { transition: opacity 90ms linear; }
  @media (prefers-reduced-motion: reduce) { .yr.fade { transition: none; } }
  /* a área vira um "container" de tamanho: o quadrado usa min(largura, altura) disponível */
  .area { flex: 1 1 auto; min-height: 0; container-type: size; display: grid; place-items: center; padding: 4px 8px; }
  .sq { width: min(100cqw - 16px, 100cqh - 8px); aspect-ratio: 1; }
  .side { display: flex; gap: 10px; }
  .half { width: min(50cqw - 18px, 100cqh - 8px); aspect-ratio: 1; }
  .layer { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; user-select: none; }
  .layer.px { image-rendering: pixelated; pointer-events: none; }
  .curtain { touch-action: none; cursor: ew-resize; overflow: hidden; background: #000; }
  .handle { position: absolute; top: 0; bottom: 0; width: 4px; background: var(--gold); transform: translateX(-2px); pointer-events: none; box-shadow: 0 0 0 2px var(--shadow); }
  .handle span { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--gold); color: var(--night); font-size: 12px; padding: 6px 4px; border: 2px solid var(--shadow); white-space: nowrap; }
  .blinkbox { padding: 0; display: block; }
  .cap { flex: none; margin: 0; min-height: 1.2em; padding: 0 8px; font-size: 15px; line-height: 1.2; color: var(--dim); text-align: center; overflow: hidden; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; }
  .cap.empty { min-height: 0; }
</style>
