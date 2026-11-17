<script lang="ts">
  import type { Challenge, Dataset } from "../lib/types";
  import { progress, resetProgress } from "../lib/progress.svelte";
  import { rank } from "../lib/score";
  import { sfx } from "../lib/sfx.svelte";
  import ufmap from "../lib/ufs.json";

  let { data, uf = "" }: { data: Dataset; uf?: string } = $props();
  let biome = $state("");

  const P = ufmap.projection;
  const xy = (lon: number, lat: number): [number, number] => [(lon - P.minLon) * P.k * P.scale, (P.maxLat - lat) * P.scale];

  const biomes = $derived([...new Set(data.challenges.map((c) => c.biome).filter(Boolean))].sort());
  const byUf = $derived.by(() => {
    const m: Record<string, Challenge[]> = {};
    for (const c of data.challenges) if (c.uf) (m[c.uf] ??= []).push(c);
    return m;
  });
  const list = $derived(data.challenges.filter((c) => (!uf || c.uf === uf) && (!biome || c.biome === biome)));
  const ufName = $derived(ufmap.ufs.find((u) => u.uf === uf)?.name ?? "");
  let hover = $state("");

  function ufState(sigla: string) {
    const cs = byUf[sigla] ?? [];
    if (!cs.length) return "none";
    const done = cs.filter((c) => progress.attempts[c.id]).length;
    return done === cs.length ? "done" : done ? "partial" : "todo";
  }
  function selectUf(sigla: string) {
    sfx("select");
    location.hash = sigla === uf ? "#/mapa" : `#/mapa/${sigla}`;
  }
</script>

<div class="layout">
  <section class="win mapwin">
    <span class="win-title">MAPA DE FASES</span>
    <p class="lbl status">{hover ? `▶ ${hover}` : uf ? `▶ ${ufName.toUpperCase()}` : "▶ ESCOLHA UM ESTADO"}</p>
    <svg viewBox={`-10 -10 ${ufmap.width + 20} ${ufmap.height + 20}`} role="group" aria-label="Mapa do Brasil por estado" shape-rendering="crispEdges">
      {#each ufmap.ufs as u (u.uf)}
        <path
          d={u.d}
          class={`uf ${ufState(u.uf)}`}
          class:sel={u.uf === uf}
          role="button"
          tabindex={byUf[u.uf] ? 0 : -1}
          aria-label={`${u.name}: ${byUf[u.uf]?.length ?? 0} casos`}
          onmouseenter={() => (hover = `${u.name.toUpperCase()} · ${byUf[u.uf]?.length ?? 0} CASO(S)`)}
          onmouseleave={() => (hover = "")}
          onclick={() => byUf[u.uf] && selectUf(u.uf)}
          onkeydown={(e) => (e.key === "Enter" || e.key === " ") && byUf[u.uf] && selectUf(u.uf)}
        />
      {/each}
      {#each data.challenges as c (c.id)}
        {@const p = xy(c.center_lonlat[0], c.center_lonlat[1])}
        <a href={`#/desafio/${c.id}`} aria-label={c.name} onclick={() => sfx("select")}>
          <rect x={p[0] - 7} y={p[1] - 7} width="14" height="14" class="dot" class:played={!!progress.attempts[c.id]} />
        </a>
      {/each}
      {#each ufmap.ufs as u (u.uf)}
        <text x={u.label[0]} y={u.label[1]} class="ufl">{u.uf}</text>
      {/each}
    </svg>
    <div class="legend lbl">
      <span><i class="sw todo"></i>NOVO</span><span><i class="sw partial"></i>EM CURSO</span>
      <span><i class="sw done"></i>COMPLETO</span><span><i class="sw none"></i>VAZIO</span>
    </div>
  </section>

  <section class="win side">
    <span class="win-title">{uf ? `CASOS · ${uf}` : "TODOS OS CASOS"}</span>
    <div class="chips">
      <button class:on={!biome} onclick={() => { biome = ""; sfx("move"); }}>TODOS</button>
      {#each biomes as b}
        <button class:on={biome === b} onclick={() => { biome = b; sfx("move"); }}>{b.toUpperCase()}</button>
      {/each}
    </div>
    {#if uf}<a class="lbl back" href="#/mapa">◀ TODOS OS ESTADOS</a>{/if}
    <ol class="list">
      {#each list as c (c.id)}
        {@const a = progress.attempts[c.id]}
        <li>
          <a class="row" href={`#/desafio/${c.id}`} onclick={() => sfx("select")}>
            <span class="no">{String(data.challenges.indexOf(c) + 1).padStart(2, "0")}</span>
            <img src={c.images.after} alt="" loading="lazy" />
            <span class="meta">
              <span class="nm">{c.name}</span>
              <span class="dim sm">{c.biome}{c.uf ? ` · ${c.uf}` : ""}</span>
            </span>
            {#if a}<span class={`rk r${rank(a.points)}`}>{rank(a.points)}</span>{:else}<span class="new blink">NEW</span>{/if}
          </a>
        </li>
      {:else}
        <li class="dim">Nenhum caso com esse filtro.</li>
      {/each}
    </ol>
    {#if Object.keys(progress.attempts).length}
      <button class="pbtn small" onclick={() => confirm("Apagar seu progresso neste navegador?") && resetProgress()}>APAGAR SAVE</button>
    {/if}
  </section>
</div>

<style>
  .layout { display: grid; grid-template-columns: 1fr; gap: 24px; align-items: start; }
  .status { min-height: 1.4em; color: var(--gold); margin: 4px 0 6px; }
  svg { width: 100%; height: auto; display: block; }
  .uf { stroke: var(--shadow); stroke-width: 3; fill: #232b63; }
  .uf.todo { fill: #2f6a9e; cursor: pointer; }
  .uf.partial { fill: #c79a1e; cursor: pointer; }
  .uf.done { fill: #1f9a52; cursor: pointer; }
  .uf.todo:hover, .uf.partial:hover, .uf.done:hover, .uf.sel { fill: var(--cyan); }
  .uf:focus-visible { outline: none; fill: var(--gold); }
  .dot { fill: var(--gold); stroke: var(--shadow); stroke-width: 3; animation: blink 1.2s steps(1) infinite; }
  .dot.played { fill: var(--ink); animation: none; }
  .ufl { font-family: var(--px); font-size: 14px; fill: var(--ink); text-anchor: middle; pointer-events: none; paint-order: stroke; stroke: var(--shadow); stroke-width: 4px; }
  .legend { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 10px; }
  .sw { display: inline-block; width: 12px; height: 12px; margin-right: 6px; vertical-align: -2px; border: 2px solid var(--shadow); }
  .sw.todo { background: #2f6a9e; } .sw.partial { background: #c79a1e; } .sw.done { background: #1f9a52; } .sw.none { background: #232b63; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 10px; }
  .chips button { font-family: var(--px); font-size: 8px; background: var(--navy); border: 2px solid var(--line-lo); padding: 6px 7px 5px; color: var(--dim); }
  .chips button.on { background: var(--gold); color: var(--night); border-color: var(--ink); }
  .back { display: inline-block; text-decoration: none; color: var(--cyan); margin-bottom: 8px; }
  .list { list-style: none; padding: 0; margin: 0 0 12px; max-height: none; }
  .row { display: grid; grid-template-columns: 30px 48px 1fr 36px; gap: 10px; align-items: center; padding: 6px; text-decoration: none; color: var(--ink); border-bottom: 2px dashed var(--line-lo); }
  .row:hover, .row:focus-visible { background: var(--panel-2); }
  .row:hover .no { color: var(--gold); }
  .no { font-family: var(--px); font-size: 10px; color: var(--dim); }
  .row img { width: 48px; height: 48px; object-fit: cover; border: 2px solid var(--shadow); }
  .meta { display: grid; min-width: 0; }
  .nm { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 21px; }
  .sm { font-size: 18px; }
  .rk { font-family: var(--px); font-size: 16px; text-align: center; text-shadow: 2px 2px 0 var(--shadow); }
  .rS { color: var(--gold); } .rA { color: var(--green); } .rB { color: var(--cyan); } .rC { color: var(--ink); } .rD { color: var(--red); }
  .new { font-family: var(--px); font-size: 8px; color: var(--magenta); text-align: center; }
</style>
