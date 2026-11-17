<script lang="ts">
  // Grades idênticas (mesmo CRS/origem/pixel): a cortina compara pixel a pixel.
  // Ocupa TODO o espaço que o pai der (altura fixa do palco): a imagem é o maior quadrado que cabe.
  import type { Snippet } from "svelte";
  import { sfx } from "../lib/sfx.svelte";
  import { settings } from "../lib/settings.svelte";
  let { before, after, labelBefore, labelAfter, alt, caption = "", tools }:
    { before: string; after: string; labelBefore: string; labelAfter: string; alt: string; caption?: string; tools?: Snippet } = $props();

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

  // Fade nos RÓTULOS DE ANO (as imagens ficam sempre com brilho total):
  // ao puxar a cortina em direção a um ano, o rótulo do OUTRO ano vai apagando — até 25%, nunca some.
  const MIN_OPACITY = 0.25;
  const opBefore = $derived(pos < 50 ? 1 - (1 - MIN_OPACITY) * ((50 - pos) / 50) : 1);
  const opAfter = $derived(pos > 50 ? 1 - (1 - MIN_OPACITY) * ((pos - 50) / 50) : 1);
</script>

<div class="cmp">
  <div class="modes" role="tablist" aria-label="Modo de comparação">
    <button role="tab" aria-selected={mode === "curtain"} class:on={mode === "curtain"} onclick={() => setMode("curtain")}>CORTINA</button>
    <button role="tab" aria-selected={mode === "side"} class:on={mode === "side"} onclick={() => setMode("side")}>LADO</button>
    <button role="tab" aria-selected={mode === "blink"} class:on={mode === "blink"} onclick={() => setMode("blink")}>PISCA</button>
    {#if tools}<span class="tools">{@render tools()}</span>{/if}
  </div>

  <div class="area">
    {#if mode === "curtain"}
      <div class="screen sq curtain" bind:this={box} role="slider" tabindex="0" aria-label="Posição da cortina"
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
        <img src={before} alt={`${alt} — ${labelBefore}`} draggable="false" class="layer" style={`clip-path: inset(0 ${100 - pos}% 0 0)`} />
        <div class="handle" style={`left:${pos}%`}><span>◀▶</span></div>
        <span class="yr l fade" style={`opacity:${opBefore}`}>{labelBefore}</span><span class="yr r fade" style={`opacity:${opAfter}`}>{labelAfter}</span>
        {#if caption}<span class="cap">{caption}</span>{/if}
      </div>
    {:else if mode === "side"}
      <div class="side">
        <div class="screen half"><img class="layer" src={before} alt={`${alt} — ${labelBefore}`} /><span class="yr l">{labelBefore}</span></div>
        <div class="screen half"><img class="layer" src={after} alt={`${alt} — ${labelAfter}`} /><span class="yr r">{labelAfter}</span></div>
      </div>
    {:else}
      <button class="screen sq blinkbox" onclick={() => { showAfter = !showAfter; sfx("tick"); }} aria-label="Alternar entre antes e depois">
        <img class="layer" src={showAfter ? after : before} alt={`${alt} — ${showAfter ? labelAfter : labelBefore}`} />
        <span class={`yr ${showAfter ? "r" : "l"}`}>{showAfter ? labelAfter : labelBefore}</span>
        <span class="cap">{caption || "TOQUE PARA TROCAR"}</span>
      </button>
    {/if}
  </div>
</div>

<style>
  .cmp { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .modes { flex: none; display: flex; gap: 5px; margin-bottom: 10px; align-items: center; }
  .modes button { font-family: var(--px); font-size: 8px; background: var(--navy); border: 2px solid var(--line-lo); padding: 7px 7px 6px; color: var(--dim); white-space: nowrap; }
  .modes button.on { background: var(--cyan); color: var(--night); border-color: var(--ink); }
  .tools { margin-left: auto; display: flex; }
  /* a área vira um "container" de tamanho: o quadrado usa min(largura, altura) disponível */
  .area { flex: 1 1 auto; min-height: 0; container-type: size; display: grid; place-items: center; padding: 8px; }
  .sq { width: min(100cqw - 16px, 100cqh - 16px); aspect-ratio: 1; }
  .side { display: flex; gap: 10px; }
  .half { width: min(50cqw - 18px, 100cqh - 16px); aspect-ratio: 1; }
  .layer { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; user-select: none; }
  .curtain { touch-action: none; cursor: ew-resize; overflow: hidden; background: #000; }
  .yr.fade { transition: opacity 90ms linear; }
  @media (prefers-reduced-motion: reduce) { .yr.fade { transition: none; } }
  .handle { position: absolute; top: 0; bottom: 0; width: 4px; background: var(--gold); transform: translateX(-2px); pointer-events: none; box-shadow: 0 0 0 2px var(--shadow); }
  .handle span { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--gold); color: var(--night); font-size: 12px; padding: 6px 4px; border: 2px solid var(--shadow); white-space: nowrap; }
  .yr { position: absolute; top: 6px; font-family: var(--px); font-size: 10px; line-height: 1.5; white-space: pre-line; background: var(--shadow); padding: 5px 6px 4px; pointer-events: none; }
  .yr.l { left: 6px; color: var(--gold); } .yr.r { right: 6px; color: var(--cyan); text-align: right; }
  .blinkbox { padding: 0; display: block; }
  .cap { position: absolute; bottom: 6px; left: 6px; right: 6px; width: fit-content; background: var(--shadow); padding: 4px 6px; font-size: 15px; color: var(--ink); pointer-events: none; }
</style>
