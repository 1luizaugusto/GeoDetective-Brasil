<script lang="ts">
  import Home from "./components/Home.svelte";
  import MapView from "./components/MapView.svelte";
  import ChallengeView from "./components/ChallengeView.svelte";
  import About from "./components/About.svelte";
  import Credits from "./components/Credits.svelte";
  import Options from "./components/Options.svelte";
  import Records from "./components/Records.svelte";
  import RunResult from "./components/RunResult.svelte";
  import { run } from "./lib/run.svelte";
  import { applySettings } from "./lib/settings.svelte";
  import type { Dataset } from "./lib/types";
  import { progress } from "./lib/progress.svelte";
  import { pad } from "./lib/score";

  let data = $state<Dataset | null>(null);
  let error = $state("");
  let hash = $state(location.hash || "#/");

  fetch("data/challenges.json", { cache: "no-cache" }) // revalida: o acervo muda entre versões
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((d: Dataset) => (data = d))
    .catch((e) => (error = String(e)));

  applySettings();
  // ESC em qualquer tela volta ao menu principal (como "pausa" de jogo); no menu, ESC fecha a confirmação
  addEventListener("keydown", (e) => {
    if (e.key === "Escape" && route.page !== "home" && !(e.target as HTMLElement)?.closest?.("input,textarea")) location.hash = "#/";
  });
  addEventListener("hashchange", () => {
    hash = location.hash || "#/";
    scrollTo(0, 0);
  });

  const route = $derived.by(() => {
    const parts = hash.replace(/^#\/?/, "").split("/");
    return { page: parts[0] || "home", arg: parts[1] ? decodeURIComponent(parts[1]) : "" };
  });
  const total = $derived(
    data ? data.challenges.reduce((s, c) => s + (progress.attempts[c.id]?.points ?? 0), 0) : 0,
  );
  const played = $derived(data ? data.challenges.filter((c) => progress.attempts[c.id]).length : 0);
</script>

<!-- PALCO: a área de jogo tem sempre o mesmo tamanho (console portátil em retrato).
     HUD e créditos têm altura fixa; o meio é a "tela" do jogo. -->
<div class="stage">
  <header class="hud">
    <a class="logo" href="#/">GEO<span>DETECTIVE</span></a>
    {#if data}
      <div class="stats">
        <span title="pontos"><i class="lbl">PTS</i> <b class="gold-t">{pad(total)}</b></span>
        <span title="casos jogados"><i class="lbl">CASOS</i> <b>{String(played).padStart(2, "0")}/{data.challenges.length}</b></span>
      </div>
    {/if}
    {#if route.page !== "home"}<a class="menu-btn" href="#/">MENU</a>{/if}
  </header>

  <main class:fixed={route.page === "desafio" || route.page === "partida"}>
    {#if error}
      <div class="win"><span class="win-title">ERRO</span><p>Não foi possível carregar os desafios.</p><p class="dim">{error}</p></div>
    {:else if !data}
      <p class="loading lbl">CARREGANDO<span class="blink">_</span></p>
    {:else if route.page === "mapa"}
      <MapView {data} uf={route.arg} />
    {:else if route.page === "desafio"}
      {@const c = data.challenges.find((x) => x.id === route.arg)}
      {#if c}
        {#key c.id}<ChallengeView {data} challenge={c} />{/key}
      {:else}
        <div class="win"><p>Caso não encontrado. <a href="#/mapa">Voltar ao mapa</a></p></div>
      {/if}
    {:else if route.page === "partida"}
      {@const i = Number(route.arg) - 1}
      {@const c = run.cur && i >= 0 && i < run.cur.ids.length ? data.challenges.find((x) => x.id === run.cur!.ids[i]) : undefined}
      {#if c}
        {#key `${run.cur?.started}-${i}`}<ChallengeView {data} challenge={c} runIdx={i} />{/key}
      {:else}
        <div class="win"><p>Nenhuma partida em andamento. <a href="#/">Voltar ao menu</a></p></div>
      {/if}
    {:else if route.page === "resultado"}
      <RunResult {data} />
    {:else if route.page === "recordes"}
      <Records {data} />
    {:else if route.page === "opcoes"}
      <Options />
    {:else if route.page === "sobre"}
      <About {data} />
    {:else if route.page === "creditos"}
      <Credits {data} />
    {:else}
      <Home {data} {total} {played} />
    {/if}
  </main>

  <footer class="dim">Copernicus Sentinel-2 · MapBiomas (CC-BY 4.0) · IBGE</footer>
</div>

<style>
  /* largura = 9/16 da altura (retrato), nunca mais larga que a janela */
  .stage {
    --hud-h: 44px; --foot-h: 22px;
    height: 100vh; height: 100dvh;
    width: min(100vw, 100dvh * 0.5625, 620px);
    margin: 0 auto; display: flex; flex-direction: column; overflow: hidden; container-type: inline-size;
    background: rgb(10 13 36 / 0.92);
    box-shadow: 0 0 0 4px var(--line-lo), 0 0 0 8px var(--shadow), 0 0 60px rgb(0 0 0 / 0.6);
  }
  .hud { flex: 0 0 var(--hud-h); display: flex; align-items: center; gap: 12px; padding: 0 12px; background: var(--shadow); border-bottom: 4px solid var(--line-lo); }
  .logo { font-family: var(--px); font-size: 10px; color: var(--gold); text-decoration: none; text-shadow: 2px 2px 0 var(--red-dk); white-space: nowrap; }
  .logo span { color: var(--ink); text-shadow: 2px 2px 0 var(--line-lo); }
  .stats { display: flex; gap: 12px; margin-left: auto; white-space: nowrap; }
  .stats i { font-style: normal; font-size: 7px; }
  .stats b { font-family: var(--px); font-size: 10px; font-weight: 400; }
  .menu-btn { font-family: var(--px); font-size: 8px; color: var(--night); background: var(--cyan); padding: 6px 7px 5px; text-decoration: none; border: 2px solid var(--ink); }
  main { container-type: inline-size; flex: 1 1 auto; min-height: 0; overflow-y: auto; overflow-x: hidden; padding: 18px 12px 18px; scrollbar-width: thin; scrollbar-color: var(--line-lo) transparent; }
  main.fixed { overflow: hidden; padding: 10px 12px 12px; display: flex; flex-direction: column; }
  footer { flex: 0 0 var(--foot-h); display: flex; align-items: center; justify-content: center; font-size: 13px; border-top: 2px dashed var(--line-lo); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 8px; }
  .loading { padding: 60px 0; text-align: center; font-size: 12px; }
  @container (max-width: 460px) { .stats i { display: none; } .hud { gap: 10px; } }
</style>
