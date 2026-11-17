<script lang="ts">
  import type { Dataset } from "../lib/types";
  import { progress } from "../lib/progress.svelte";
  import { sfx } from "../lib/sfx.svelte";
  import { resetProgress } from "../lib/progress.svelte";
  import { run, startRun } from "../lib/run.svelte";
  import { pad } from "../lib/score";

  let { data, total, played }: { data: Dataset; total: number; played: number } = $props();

  const next = $derived(data.challenges.find((c) => !progress.attempts[c.id]) ?? data.challenges[0]);

  type Item = { label: string; go: () => void; hint?: string };
  // confirmação no estilo "TEM CERTEZA?" de jogo antigo: o menu troca por SIM / NÃO
  let ask = $state<{ text: string; yes: () => void } | null>(null);
  const runOpen = $derived(run.cur && run.cur.points.some((p) => p === null) ? run.cur : null);
  const runAt = $derived(runOpen ? runOpen.points.findIndex((p) => p === null) + 1 : 0);
  const allDone = $derived(played === data.challenges.length);

  function newGame() {
    const go = () => { resetProgress(); location.hash = `#/desafio/${data.challenges[0].id}`; };
    if (!played) return go();
    ask = { text: `APAGAR O PROGRESSO (${played} CASOS, ${pad(total)} PONTOS) E COMEÇAR DO ZERO?`, yes: go };
    sel = 1; // cursor em NÃO, como nos jogos
  }
  function quickRun() {
    const go = () => (location.hash = startRun(data.challenges, 5));
    if (!runOpen) return go();
    ask = { text: `JÁ HÁ UMA PARTIDA NO CASO ${runAt}/${runOpen.ids.length}. SORTEAR OUTRA?`, yes: go };
    sel = 1;
  }

  const menu = $derived<Item[]>([
    ...(played && !allDone ? [{ label: "CONTINUAR", hint: `${played}/${data.challenges.length} CASOS`, go: () => (location.hash = `#/desafio/${next.id}`) }] : []),
    { label: "NOVO JOGO", go: newGame },
    ...(runOpen ? [{ label: "RETOMAR PARTIDA", hint: `CASO ${runAt}/${runOpen.ids.length}`, go: () => (location.hash = `#/partida/${runAt}`) }] : []),
    { label: "PARTIDA RÁPIDA", hint: "5 CASOS SORTEADOS", go: quickRun },
    { label: "ESCOLHER FASE", hint: "MAPA DO BRASIL", go: () => (location.hash = "#/mapa") },
    { label: "RECORDES", go: () => (location.hash = "#/recordes") },
    { label: "OPÇÕES", go: () => (location.hash = "#/opcoes") },
    { label: "MANUAL", go: () => (location.hash = "#/sobre") },
    { label: "CRÉDITOS", go: () => (location.hash = "#/creditos") },
  ]);
  const confirmItems = $derived<Item[]>(ask ? [
    { label: "SIM", go: () => { const y = ask!.yes; ask = null; y(); } },
    { label: "NÃO", go: () => { ask = null; sel = 0; } },
  ] : []);
  const items = $derived(ask ? confirmItems : menu);
  let sel = $state(0);
  $effect(() => { if (sel >= items.length) sel = 0; });

  function onkey(e: KeyboardEvent) {
    if (e.key === "ArrowDown") { sel = (sel + 1) % items.length; sfx("move"); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = (sel - 1 + items.length) % items.length; sfx("move"); e.preventDefault(); }
    else if (e.key === "Enter") { sfx("select"); items[sel].go(); e.preventDefault(); }
    else if (e.key === "Escape" && ask) { ask = null; sel = 0; sfx("move"); }
  }
</script>

<svelte:window onkeydown={onkey} />

<section class="title">
  <!-- satélite em pixel art (desenho original) -->
  <svg class="sat" viewBox="0 0 32 16" aria-hidden="true" shape-rendering="crispEdges">
    <rect x="0" y="5" width="10" height="6" fill="#5ce1e6" /><rect x="1" y="6" width="2" height="4" fill="#26338a" /><rect x="4" y="6" width="2" height="4" fill="#26338a" /><rect x="7" y="6" width="2" height="4" fill="#26338a" />
    <rect x="22" y="5" width="10" height="6" fill="#5ce1e6" /><rect x="23" y="6" width="2" height="4" fill="#26338a" /><rect x="26" y="6" width="2" height="4" fill="#26338a" /><rect x="29" y="6" width="2" height="4" fill="#26338a" />
    <rect x="10" y="7" width="2" height="2" fill="#a7a9d6" /><rect x="20" y="7" width="2" height="2" fill="#a7a9d6" />
    <rect x="12" y="3" width="8" height="10" fill="#f4efd6" /><rect x="13" y="4" width="6" height="8" fill="#ffd23f" /><rect x="15" y="13" width="2" height="3" fill="#a7a9d6" />
  </svg>

  <h1 class="logo"><span class="a">GEO</span><span class="b">DETECTIVE</span></h1>
  <p class="sub">★ BRASIL ★</p>
  <p class="tag">Investigue imagens reais de satélite e descubra quanto da vegetação nativa mudou.</p>

  <div class="grid">

    <div class="win menu">
      <span class="win-title">{ask ? "TEM CERTEZA?" : "MENU"}</span>
      {#if ask}<p class="ask">{ask.text}</p>{/if}
      <ul role="menu">
        {#each items as it, i}
          <li role="none">
            <button role="menuitem" class:sel={i === sel}
              onmouseenter={() => { if (sel !== i) { sel = i; sfx("move"); } }}
              onclick={() => { sfx("select"); it.go(); }}>
              <span class="cur">{i === sel ? "▶" : ""}</span>{it.label}{#if it.hint}<span class="hint2">{it.hint}</span>{/if}
            </button>
          </li>
        {/each}
      </ul>
      <p class="hint lbl"><span class="blink">APERTE ENTER</span> · SETAS ESCOLHEM</p>
      {#if played}
        <p class="rec lbl">RECORDE <b class="gold-t">{pad(total)}</b> · {played}/{data.challenges.length} CASOS</p>
      {/if}
    </div>
  </div>

  <div class="rules">
    <div><b>1</b> COMPARE AS DUAS IMAGENS</div>
    <div><b>2</b> ESTIME A MUDANÇA DA VEGETAÇÃO NATIVA</div>
    <div><b>3</b> CUIDADO: VERDE PODE NÃO SER NATIVO!</div>
  </div>
</section>

<style>
  .title { text-align: center; padding: 4px 0 6px; }
  .sat { width: 96px; height: 48px; animation: float 3s steps(6) infinite; }
  @keyframes float { 50% { transform: translateY(-8px); } }
  .logo { font-size: clamp(22px, 8cqw, 40px); line-height: 1.1; margin: 10px 0 6px; letter-spacing: 0; }
  .logo .a { color: var(--gold); text-shadow: 4px 4px 0 var(--red-dk), 8px 8px 0 var(--shadow); }
  .logo .b { color: var(--ink); text-shadow: 4px 4px 0 var(--line-lo), 8px 8px 0 var(--shadow); }
  .sub { font-family: var(--px); font-size: 11px; color: var(--cyan); letter-spacing: 0.3em; margin: 10px 0; }
  .tag { font-size: 20px; color: var(--dim); margin: 0 auto 22px; }
  .grid { max-width: 420px; margin: 0 auto; text-align: left; }
  .menu ul { list-style: none; margin: 8px 0 14px; padding: 0; }
  .menu button { display: flex; align-items: center; gap: 8px; width: 100%; background: none; border: 0; padding: 8px 4px; font-family: var(--px); font-size: 13px; text-align: left; color: var(--dim); }
  .menu button.sel { color: var(--ink); }
  .cur { display: inline-block; width: 28px; color: var(--gold); animation: blink 0.8s steps(1) infinite; }
  .hint { margin: 0; }
  .hint2 { margin-left: auto; font-size: 8px; color: var(--line-lo); white-space: nowrap; }
  @container (max-width: 470px) { .hint2 { display: none; } .menu button { font-size: 12px; } }
  .menu button.sel .hint2 { color: var(--cyan); }
  .ask { font-family: var(--px); font-size: 10px; line-height: 1.8; color: var(--gold); margin: 10px 0 0; }
  .rec { margin-top: 10px; }
  .rules { display: flex; justify-content: center; gap: 26px; flex-wrap: wrap; margin-top: 22px; font-family: var(--px); font-size: 8px; color: var(--dim); }
  .rules b { color: var(--night); background: var(--gold); padding: 3px 6px 2px; margin-right: 6px; font-weight: 400; }
</style>
