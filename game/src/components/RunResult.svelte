<script lang="ts">
  import type { Dataset } from "../lib/types";
  import { run, startRun } from "../lib/run.svelte";
  import { rank, pad, fmtPP, zeroScore } from "../lib/score";
  import { sfx } from "../lib/sfx.svelte";
  import { L, i18n } from "../lib/i18n.svelte";
  const T = $derived(L());

  let { data }: { data: Dataset } = $props();
  const r = $derived(run.cur);
  const total = $derived(r ? r.points.reduce<number>((s, p) => s + (p ?? 0), 0) : 0);
  const max = $derived(r ? r.ids.length * 100 : 0);
  const rk = $derived(rank(max ? (100 * total) / max : 0));
  const isBest = $derived(!!r && run.best.length > 0 && run.best[0].total === total && run.best[0].max === max);
  const byId = (id: string) => data.challenges.find((c) => c.id === id)!;
  const zero = $derived(r ? r.ids.reduce((s, id) => s + zeroScore(byId(id)), 0) : 0);
</script>

{#if !r}
  <div class="win"><p>{T.noRun} <a href="#/">{T.backMenu}</a></p></div>
{:else}
  <section class="win res">
    <span class="win-title">{T.runOver}</span>
    {#if isBest}<p class="new blink">{T.newRecord}</p>{/if}
    <div class="top">
      <div><p class="lbl">{T.total}</p><p class="big">{pad(total, 3)}<span class="dim">/{max}</span></p></div>
      <div class={`rank r${rk}`}>{rk}</div>
    </div>
    <p class={`vs ${total > zero ? "win-t" : "lose-t"}`}>
      {T.vsZero(pad(total, 3), pad(zero, 3))}
      {total > zero ? T.won(total - zero) : total === zero ? T.tie : T.lost(zero - total)}
    </p>
    <p class="dim small">{T.zeroNote}</p>
    <table>
      <thead><tr><th>#</th><th>{T.thCase}</th><th>{T.thYou}</th><th>{T.thModel}</th><th>{T.thPts}</th><th>{T.thZero}</th></tr></thead>
      <tbody>
        {#each r.ids as id, i}
          {@const c = byId(id)}
          <tr>
            <td>{i + 1}</td>
            <td><a href={`#/partida/${i + 1}`}>{i18n.lang === "en" && c.name_en ? c.name_en : c.name}</a></td>
            <td>{r.guesses[i] === null ? "—" : fmtPP(r.guesses[i]!)}</td>
            <td>{fmtPP(c.model_estimate_pp)}</td>
            <td class="gold-t">{r.points[i] ?? "—"}</td>
            <td class="dim">{zeroScore(c)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
    <div class="actions">
      <button class="pbtn gold" onclick={() => { sfx("select"); location.hash = startRun(data.challenges, 5); }}>{T.playAgain}</button>
      <a class="pbtn" href="#/recordes">{T.records}</a>
      <a class="pbtn" href="#/">{T.menu}</a>
    </div>
  </section>
{/if}

<style>
  .res { max-width: 760px; margin: 10px auto; }
  .new { font-family: var(--px); color: var(--gold); text-align: center; }
  .top { display: flex; align-items: center; justify-content: space-between; margin: 6px 0 16px; }
  .big { font-family: var(--px); font-size: 40px; margin: 6px 0 0; color: var(--gold); text-shadow: 4px 4px 0 var(--red-dk); }
  .big .dim { font-size: 18px; text-shadow: none; }
  .rank { font-family: var(--px); font-size: 64px; width: 100px; height: 100px; display: grid; place-items: center; border: 4px solid var(--ink); background: var(--shadow); }
  .rS { color: var(--gold); } .rA { color: var(--green); } .rB { color: var(--cyan); } .rC { color: var(--ink); } .rD { color: var(--red); }
  table { width: 100%; border-collapse: collapse; font-size: 21px; }
  th { font-family: var(--px); font-size: 9px; text-align: left; color: var(--dim); padding: 6px 4px; }
  td { padding: 6px 4px; border-top: 2px dashed var(--line-lo); }
  .vs { font-family: var(--px); font-size: 11px; line-height: 1.8; margin: 0 0 4px; }
  .win-t { color: var(--green); } .lose-t { color: var(--red); }
  .small { font-size: 18px; margin: 0 0 12px; }
  .actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 18px; }
</style>
