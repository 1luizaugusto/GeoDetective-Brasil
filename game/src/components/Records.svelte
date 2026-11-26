<script lang="ts">
  import type { Dataset } from "../lib/types";
  import { progress } from "../lib/progress.svelte";
  import { run } from "../lib/run.svelte";
  import { rank, pad, fmtDate, zeroScore } from "../lib/score";
  import { L, biomeName } from "../lib/i18n.svelte";
  const T = $derived(L());

  let { data }: { data: Dataset } = $props();

  const played = $derived(data.challenges.filter((c) => progress.attempts[c.id]));
  const total = $derived(played.reduce((s, c) => s + progress.attempts[c.id].points, 0));
  const avg = $derived(played.length ? total / played.length : 0);
  const ranks = $derived(
    (["S", "A", "B", "C", "D"] as const).map((r) => [r, played.filter((c) => rank(progress.attempts[c.id].points) === r).length] as const),
  );
  const byBiome = $derived.by(() => {
    const m = new Map<string, { n: number; pts: number; all: number }>();
    for (const c of data.challenges) {
      const b = m.get(c.biome) ?? { n: 0, pts: 0, all: 0 };
      b.all++;
      const a = progress.attempts[c.id];
      if (a) { b.n++; b.pts += a.points; }
      m.set(c.biome, b);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  });
  const zero = $derived(played.reduce((s, c) => s + zeroScore(c), 0));
  const clear = $derived(played.filter((c) => Math.abs(c.model_estimate_pp) >= 10));
  const clearAvg = $derived(clear.length ? clear.reduce((s, c) => s + progress.attempts[c.id].points, 0) / clear.length : 0);
  const traps = $derived(data.challenges.filter((c) => c.kind === "trap"));
</script>

<h1 class="gold-t">{T.records}</h1>

<div class="cols">
  <section class="win">
    <span class="win-title">{T.campaign}</span>
    <dl>
      <dt>{T.points}</dt><dd class="gold-t">{pad(total)}</dd>
      <dt>{T.cases}</dt><dd>{played.length}/{data.challenges.length}</dd>
      <dt>{T.average}</dt><dd>{avg.toFixed(0)} <span class="dim">({rank(avg)})</span></dd>
      <dt>{T.vsZeroShort}</dt><dd class={total - zero > 0 ? "up" : total - zero < 0 ? "down" : ""}>{total - zero > 0 ? "+" : ""}{total - zero}</dd>
      <dt>{T.clearChanges}</dt><dd>{clear.length ? `${clearAvg.toFixed(0)} (${rank(clearAvg)})` : "—"} <span class="dim">{clear.length} {T.casesWord}</span></dd>
      <dt>{T.traps}</dt><dd>{traps.filter((c) => progress.attempts[c.id]?.points >= 80).length}/{traps.length} <span class="dim">{T.disarmed}</span></dd>
    </dl>
    <div class="ranks">
      {#each ranks as [r, n]}<div class={`rk r${r}`}><b>{r}</b><span>{n}</span></div>{/each}
    </div>
  </section>

  <section class="win">
    <span class="win-title">{T.top5}</span>
    {#if run.best.length}
      <ol>
        {#each run.best as b}
          <li><b class="gold-t">{pad(b.total, 3)}</b>/{b.max} · {rank((100 * b.total) / b.max)} <span class="dim">· {fmtDate(b.at.slice(0, 10))}</span></li>
        {/each}
      </ol>
    {:else}
      <p class="dim">{T.noRuns}</p>
    {/if}
  </section>
</div>

<section class="win">
  <span class="win-title">{T.byBiome}</span>
  <table>
    <thead><tr><th>{T.biome}</th><th>{T.cases}</th><th>{T.average}</th></tr></thead>
    <tbody>
      {#each byBiome as [b, v]}
        <tr><td>{biomeName(b)}</td><td>{v.n}/{v.all}</td><td>{v.n ? `${(v.pts / v.n).toFixed(0)} (${rank(v.pts / v.n)})` : "—"}</td></tr>
      {/each}
    </tbody>
  </table>
</section>
<p><a class="pbtn" href="#/">{T.menuBack}</a></p>

<style>
  h1 { font-size: clamp(16px, 3vw, 24px); margin: 6px 0 22px; }
  .cols { display: grid; grid-template-columns: 1fr; gap: 24px; margin-bottom: 24px; }
  dl { display: grid; grid-template-columns: 1fr auto; margin: 6px 0 14px; }
  dt, dd { margin: 0; padding: 6px 0; border-bottom: 2px dashed var(--line-lo); }
  dt { font-family: var(--px); font-size: 10px; display: flex; align-items: center; }
  dd { text-align: right; font-size: 24px; }
  .up { color: var(--green); } .down { color: var(--red); }
  .ranks { display: flex; gap: 8px; }
  .rk { flex: 1; text-align: center; background: var(--shadow); padding: 8px 0; }
  .rk b { display: block; font-family: var(--px); font-size: 20px; font-weight: 400; }
  .rS b { color: var(--gold); } .rA b { color: var(--green); } .rB b { color: var(--cyan); } .rD b { color: var(--red); }
  ol { margin: 8px 0 0; padding-left: 26px; font-size: 22px; }
  table { width: 100%; border-collapse: collapse; font-size: 21px; margin-top: 6px; }
  th { font-family: var(--px); font-size: 9px; text-align: left; color: var(--dim); padding: 6px 4px; }
  td { padding: 6px 4px; border-top: 2px dashed var(--line-lo); }
  @media (max-width: 700px) { .cols { grid-template-columns: 1fr; } }
</style>
