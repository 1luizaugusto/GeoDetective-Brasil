<script lang="ts">
  import { untrack } from "svelte";
  import Compare from "./Compare.svelte";
  import type { Challenge, Dataset } from "../lib/types";
  import { score, band, fmtPP, fmtHa, fmtDate, rank, pad } from "../lib/score";
  import { progress, record } from "../lib/progress.svelte";
  import { sfx } from "../lib/sfx.svelte";
  import { run, recordRun } from "../lib/run.svelte";
  import { settings } from "../lib/settings.svelte";
  import { L, i18n, locale, biomeName, COVER } from "../lib/i18n.svelte";

  let { data, challenge: c, runIdx }: { data: Dataset; challenge: Challenge; runIdx?: number } = $props();
  const T = $derived(L());
  const en = $derived(i18n.lang === "en");
  // runIdx definido = caso de uma PARTIDA RÁPIDA (jogado do zero, sem reaproveitar o palpite da campanha)
  const inRun = untrack(() => runIdx !== undefined); // componente é recriado por caso ({#key})

  // App.svelte recria este componente a cada caso ({#key c.id}): ler o valor inicial é intencional
  const prev = untrack(() => {
    if (!inRun) return progress.attempts[c.id];
    const p = run.cur?.points[runIdx!], g = run.cur?.guesses[runIdx!];
    return p != null && g != null ? { guess: g, points: p, at: "" } : undefined;
  });
  // PONTO DE PARTIDA FIXO: % de vegetação nativa no 1º ano (MapBiomas 10 m). O jogador estima o 2º ano;
  // o palpite guardado/pontuado continua sendo a VARIAÇÃO (depois − antes), em pp.
  const y0 = untrack(() => c.dates[0].slice(0, 4)), y1 = untrack(() => c.dates[1].slice(0, 4));
  const base = untrack(() => Math.round(c.native_pct.mapbiomas_10m[0]));
  const clampG = (g: number) => Math.max(-base, Math.min(100 - base, g));
  let guess = $state(clampG(prev?.guess ?? 0));
  const after = $derived(base + guess);
  // 3 etapas: palpite → resultado → explicação. Palpite e resultado têm o painel de ALTURA FIXA;
  // a explicação ganha mais espaço (a imagem encolhe, mas continua visível para o botão MAPA).
  let step = $state<"guess" | "result" | "info">(prev ? "result" : "guess");
  const submitted = $derived(step !== "guess");
  let showContext = $state(false);
  let otherSeason = $state(false); // ÉPOCA 2: mesma área, outra época do ano, nos dois anos
  let showMap = $state(false); // MAPA: onde o MapBiomas marca nativa (só depois do palpite: senão entrega a resposta)
  const hasS2 = $derived(!!(c.images.before2 && c.images.after2 && c.dates2));
  const hasMap = $derived(!!(c.images.native_a && c.images.native_b));
  const mapOn = $derived(submitted && showMap && hasMap && !showContext);
  const lbl = (iso: string) => `${T.months[Number(iso.slice(5, 7)) - 1]} ${iso.slice(0, 4)}`;
  const curDates = $derived(otherSeason && c.dates2 ? c.dates2 : c.dates);
  const imgs = $derived.by(() => {
    const I = c.images, o = otherSeason && hasS2;
    if (showContext) return o ? [I.context_before2!, I.context_after2!] : [I.context_before, I.context_after];
    return o ? [I.before2!, I.after2!] : [I.before, I.after];
  });
  let shown = $state(prev?.points ?? 0); // contador animado
  let typed = $state("");

  const name = $derived(en && c.name_en ? c.name_en : c.name);
  const bd = $derived(band(c));
  const pts = $derived(score(guess, bd));
  const rk = $derived(rank(pts));
  const caseNo = $derived(String(data.challenges.findIndex((x) => x.id === c.id) + 1).padStart(2, "0"));
  const idx = $derived(data.challenges.findIndex((x) => x.id === c.id));
  const runLen = $derived(run.cur?.ids.length ?? 0);
  const next = $derived(
    data.challenges.slice(idx + 1).find((x) => !progress.attempts[x.id]) ??
      data.challenges.find((x) => x.id !== c.id && !progress.attempts[x.id]),
  );
  const nextHref = $derived(
    inRun ? (runIdx! + 1 < runLen ? `#/partida/${runIdx! + 2}` : "#/resultado") : next ? `#/desafio/${next.id}` : "",
  );

  const explanation = $derived((en ? c.explanation_en : c.explanation) || T.defaultText[c.kind]);
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- ENTENDA O CASO: tudo calculado dos dados do caso (data/explain + MapBiomas), nada inventado
  const num = (v: number, d = 0) => v.toLocaleString(locale(), { maximumFractionDigits: d });
  const comp = $derived(c.composition ?? {});
  const compYears = $derived([y0, y1].filter((y) => comp[y]));
  const order = Object.keys(COVER); // nativos primeiro (ordem do dicionário)
  const segsOf = (y: string) => order.filter((k) => (comp[y]?.[k] ?? 0) > 0).map((k) => ({ k, v: comp[y][k] }));
  const natOf = (y: string) => segsOf(y).filter((s) => COVER[s.k].native).reduce((a, s) => a + s.v, 0);
  const legendRows = $derived(order.filter((k) => compYears.some((y) => (comp[y]?.[k] ?? 0) >= 2)));
  const tags = $derived(c.tags ?? []);
  const fireList = $derived(
    Object.entries(c.fire_pct ?? {}).filter(([, v]) => v >= 5).sort((a, b) => +a[0] - +b[0])
      .map(([y, v]) => T.burnedItem(+y, num(v))).join(", "),
  );
  const openPct = $derived(["grassland", "wetland", "rock", "savanna", "tidalflat"].reduce((a, k) => a + (comp[y0]?.[k] ?? 0), 0));
  const share = (k: string, y: string) => num(comp[y]?.[k] ?? 0);
  const clues = $derived(
    tags.flatMap((t) => {
      if (t === "fire" && fireList) return [T.clue.fire(fireList)];
      if (t === "open") return [T.clue.open(num(openPct))];
      if (t === "plantation") return [T.clue.plantation(share("silviculture", y0), share("silviculture", y1))];
      if (t === "crop") return [T.clue.crop(share("crop", y0), share("crop", y1))];
      if (t === "season") return [T.clue.season];
      if (t === "water") return [T.clue.water];
      return [];
    }),
  );
  const PRIORITY: Record<Challenge["kind"], string[]> = {
    loss: ["openLoss", "conversion"],
    stable_edge: ["plantation", "crop", "open", "fire", "season", "water"],
    gain: ["crop", "regrowth"],
    trap: ["plantation"],
  };
  const lesson = $derived.by(() => {
    const has = (k: string) => (k === "openLoss" ? tags.includes("open") : tags.includes(k));
    const k = PRIORITY[c.kind].find(has) ?? c.kind;
    return T.lessons[k] ?? T.lessons[c.kind];
  });
  const proofs = $derived.by(() => {
    const m = c.native_pct.mapbiomas_10m;
    const out = [
      T.proof.maps(num(m[0], 1), num(m[1], 1), fmtPP(c.reference_pp.mapbiomas_10m, 1), fmtPP(c.reference_pp.mapbiomas_30m, 1)),
      T.proof.model(fmtPP(c.model_estimate_pp, 1)),
    ];
    const pa = c.protected?.[0];
    if (pa && pa.pct >= 10) out.push(T.proof.protected(pa.pct, pa.name));
    return out;
  });

  let typing: ReturnType<typeof setInterval> | undefined;
  function openInfo() {
    step = "info"; sfx("select");
    if (typed === explanation) return; // já foi escrito uma vez
    clearInterval(typing);
    if (reduced || !settings.typewriter) { typed = explanation; return; }
    let i = 0; typed = "";
    typing = setInterval(() => { typed = explanation.slice(0, (i += 2)); if (i >= explanation.length) clearInterval(typing); }, 18);
  }
  $effect(() => { // troca de idioma com a explicação aberta: reescreve sem animação
    const e = explanation;
    untrack(() => { if (typed && !e.startsWith(typed)) { clearInterval(typing); typed = e; } });
  });
  function reveal(points: number) {
    shown = 0;
    if (reduced) { shown = points; return; }
    const t0 = performance.now();
    const stepFn = (t: number) => {
      const k = Math.min(1, (t - t0) / 900);
      const v = Math.round(points * k);
      if (v !== shown && v % 4 === 0) sfx("tick");
      shown = v;
      if (k < 1) requestAnimationFrame(stepFn);
      else sfx(points >= 80 ? "good" : points >= 35 ? "ok" : "bad");
    };
    requestAnimationFrame(stepFn);
  }
  if (prev) untrack(() => { shown = prev.points; });

  function submit() {
    if (submitted) return;
    step = "result";
    const p = score(guess, bd);
    if (inRun) recordRun(runIdx!, guess, p);
    const old = progress.attempts[c.id];
    if (!inRun || !old || p > old.points) record(c.id, { guess, points: p, at: new Date().toISOString() });
    sfx("select");
    reveal(p);
  }
  function retry() { step = "guess"; showMap = false; sfx("move"); }
  function nudge(d: number) {
    const g = clampG(guess + d);
    if (g !== guess) { guess = g; sfx("move"); }
  }
  function onkey(e: KeyboardEvent) {
    if ((e.target as HTMLElement)?.getAttribute("role") === "slider") return; // cortina usa as setas
    if (step === "result") { if (e.key === "Enter") openInfo(); return; }
    if (step === "info") {
      if (e.key === "Enter" && nextHref) location.hash = nextHref;
      if (e.key === "Backspace") { step = "result"; sfx("move"); e.preventDefault(); }
      return;
    }
    if (e.key === "ArrowLeft" || e.key === "ArrowDown") { nudge(e.shiftKey ? -10 : -1); e.preventDefault(); }
    else if (e.key === "ArrowRight" || e.key === "ArrowUp") { nudge(e.shiftKey ? 10 : 1); e.preventDefault(); }
    else if (e.key === "Enter") submit();
  }

  // Área rolável SEM barra visível: um "▼ MAIS" piscando avisa que há conteúdo abaixo e some no fim.
  function moreHint(node: HTMLElement) {
    const wrap = node.parentElement!;
    const upd = () => wrap.classList.toggle("hasmore", node.scrollHeight - node.scrollTop - node.clientHeight > 6);
    const ro = new ResizeObserver(upd); ro.observe(node);
    const mo = new MutationObserver(upd); mo.observe(node, { childList: true, subtree: true, characterData: true, attributes: true });
    node.addEventListener("scroll", upd, { passive: true });
    upd();
    return { destroy() { ro.disconnect(); mo.disconnect(); node.removeEventListener("scroll", upd); } };
  }
  function scrollMore(e: Event) {
    const sc = (e.currentTarget as HTMLElement).parentElement!.querySelector(".scroll") as HTMLElement;
    sc.scrollBy({ top: sc.clientHeight * 0.8, behavior: reduced ? "auto" : "smooth" });
    sfx("move");
  }

  // medidor = o RECORTE INTEIRO (0…100% de vegetação nativa), 50 segmentos de 2%.
  // verde-escuro = nativa que já havia e continua · verde = ganho · vermelho = perda · marca branca = ANTES (fixo)
  const segs = Array.from({ length: 50 }, (_, i) => i * 2 + 1);
  const segKind = (s: number) =>
    s < Math.min(base, after) ? "keep" : s >= base && s < after ? "gain" : s >= after && s < base ? "loss" : "";
  let gauge: HTMLDivElement | undefined = $state();
  let drag = false;
  function fromPointer(e: PointerEvent) {
    if (!gauge || submitted) return;
    const r = gauge.getBoundingClientRect();
    const g = clampG(Math.round(((e.clientX - r.left) / r.width) * 100) - base);
    if (g !== guess) { guess = g; sfx("tick"); }
  }
  // régua do resultado na mesma escala: % de nativa no 2º ano = ANTES + variação
  const at = (v: number) => `${Math.max(0, Math.min(100, base + v))}%`;
  const refAfter = $derived(Math.round(c.native_pct.mapbiomas_10m[1]));
</script>

<svelte:window onkeydown={onkey} />

<!-- Layout fixo dentro do palco: cabeçalho do caso · imagem (todo o espaço que sobra) · painel -->
<div class="cv" class:info={step === "info"}>
  <div class="casebar">
    <h1>
      {#if inRun}<a class="back" href="#/" aria-label={T.menu}>◀</a><span class="gold-t">{runIdx! + 1}/{runLen}</span>
      {:else}<a class="back" href={c.uf ? `#/mapa/${c.uf}` : "#/mapa"} aria-label={T.backMap}>◀</a><span class="gold-t">#{caseNo}</span>{/if}
      <span class="nm">{name}</span>
    </h1>
    <p class="meta dim">{biomeName(c.biome)}{c.municipality ? ` · ${c.municipality}` : ""}{c.uf ? `/${c.uf}` : ""} · {c.size_km.toLocaleString(locale())} km · {fmtDate(c.dates[0])} → {fmtDate(c.dates[1])}</p>
  </div>

  <div class="view">
    <Compare
      before={imgs[0]} after={imgs[1]}
      labelBefore={`${lbl(curDates[0])} · ${T.native} ${base}%`}
      labelAfter={`${lbl(curDates[1])} · ${T.native} ${submitted ? `${refAfter}%` : "?"}`}
      overlayBefore={mapOn ? c.images.native_a : ""} overlayAfter={mapOn ? c.images.native_b : ""}
      alt={showContext ? `${name}, ${T.wideArea}` : name}
      legend={mapOn ? mapLegend : undefined}
      caption={showContext ? T.capContext
        : c.hint && !submitted ? (i18n.lang === "en" && c.hint_en ? c.hint_en : c.hint)
        : c.season_hint && !otherSeason && !submitted ? T.capSeason
        : otherSeason ? T.capSeason2 : ""}>
      {#snippet tools()}
        {#if submitted && hasMap && !showContext}
          <button class="radar maptg" class:on={showMap} title={T.mapTitle}
            onclick={() => { showMap = !showMap; sfx("move"); }}>{showMap ? T.mapLayerOff : T.mapLayer}</button>
        {/if}
        {#if hasS2}
          <button class="radar season" class:on={otherSeason} title={T.season2Title}
            onclick={() => { otherSeason = !otherSeason; sfx("move"); }}>{otherSeason ? T.season1 : T.season2}</button>
        {/if}
        <button class="radar" class:on={showContext} onclick={() => { showContext = !showContext; sfx("move"); }}>
          {showContext ? T.crop : T.radar}
        </button>
      {/snippet}
    </Compare>
  </div>

  {#snippet mapLegend()}
    <span class="mleg"><i style="background:rgb(69 224 124 / .7)"></i>{T.legNative}<i style="background:#ff3b3b"></i>{T.legLost}<i style="background:#ffd23f"></i>{T.legGained}<span class="dim"> · {T.legSrc}</span></span>
  {/snippet}

  <section class="win panel">
    {#if !submitted}
      {@const q = T.question(y0, base, y1)}
      <p class="q">{q[0]}<b class="gold-t">{q[1]}</b>{q[2]}<b>{q[3]}</b>{q[4]}</p>
      <div class="readout">
        <output class="digits">{after}%</output>
        <span class="ha"><b class:pos={guess > 0} class:neg={guess < 0}>{fmtPP(guess)}</b><br /><span class="dim">{fmtHa(guess, c.size_km)}</span></span>
      </div>
      <div class="gauge" bind:this={gauge} role="slider" tabindex="0"
        aria-label={T.sliderLabel(y1, y0, base)}
        aria-valuemin={0} aria-valuemax={100} aria-valuenow={after} aria-valuetext={`${after}% (${fmtPP(guess)})`}
        onpointerdown={(e) => { drag = true; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); fromPointer(e); }}
        onpointermove={(e) => drag && fromPointer(e)}
        onpointerup={() => (drag = false)}
        onkeydown={(e) => {
          if (e.key === "ArrowLeft" || e.key === "ArrowDown") { nudge(e.shiftKey ? -10 : -1); e.preventDefault(); e.stopPropagation(); }
          if (e.key === "ArrowRight" || e.key === "ArrowUp") { nudge(e.shiftKey ? 10 : 1); e.preventDefault(); e.stopPropagation(); }
        }}>
        {#each segs as s}<i class={segKind(s)}></i>{/each}
        <b class="base" style={`left:${base}%`}></b>
      </div>
      <div class="ticks abs lbl"><span class:hide={base < 20}>0%</span><span class="bt" class:start={base < 6} class:end={base > 94} style={`left:${base}%`}>{y0}</span><span class:hide={base > 80}>100%</span></div>
      <div class="controls">
        <button class="pbtn small" onclick={() => nudge(-10)}>-10</button>
        <button class="pbtn small" onclick={() => nudge(-1)}>-1</button>
        <button class="pbtn small" onclick={() => nudge(1)}>+1</button>
        <button class="pbtn small" onclick={() => nudge(10)}>+10</button>
        <button class="pbtn gold go" onclick={submit}>OK</button>
      </div>
    {:else if step === "result"}
      <div class="reshead">
        <div class={`rank r${rk}`} aria-label={T.rankLabel(rk)}>{rk}</div>
        <div class="pts"><p class="lbl">{T.points}</p><p class="big">{pad(shown, 3)}</p></div>
        <!-- TENTAR DE NOVO no cabeçalho do resultado: sempre visível, sem precisar rolar -->
        {#if !inRun}<button class="pbtn again" onclick={retry} title={T.tryAgainFull} aria-label={T.tryAgainFull}>↺ {T.tryAgain}</button>{/if}
        <button class="pbtn gold nx" onclick={openInfo}>{T.understand}</button>
      </div>
      <div class="scrollwrap">
        <div class="scroll" use:moreHint>
          <div class="track" aria-hidden="true">
            <div class="tol" style={`left:${at(bd[0])}; width:${Math.max(0, Math.min(100, base + bd[1]) - Math.max(0, base + bd[0]))}%`}></div>
            <i class="mk ref" style={`left:${at(c.reference_pp.mapbiomas_10m)}`}></i>
            <i class="mk model" style={`left:${at(c.model_estimate_pp)}`}></i>
            <i class="mk you" style={`left:${at(guess)}`}></i>
            <b class="base" style={`left:${base}%`}></b>
          </div>
          <div class="ticks abs lbl"><span class:hide={base < 20}>0%</span><span class="bt" class:start={base < 6} class:end={base > 94} style={`left:${base}%`}>{y0}</span><span class:hide={base > 80}>100%</span></div>
          <dl>
            <dt><i class="sw you"></i>{T.you}</dt><dd>{base}→{after}% <span class="dim">{fmtPP(guess)}</span></dd>
            <dt><i class="sw model"></i>{T.model}</dt><dd>{fmtPP(c.model_estimate_pp, 1)}</dd>
            <dt><i class="sw ref"></i>{T.mapbiomas}</dt><dd>{base}→{refAfter}% <span class="dim">{fmtPP(c.reference_pp.mapbiomas_10m, 1)}</span></dd>
          </dl>
        </div>
        <button class="moretag lbl" onclick={scrollMore} aria-hidden="true" tabindex="-1">{T.more}</button>
      </div>
    {:else}
      <div class="reshead nav">
        <button class="pbtn bk" onclick={() => { step = "result"; sfx("move"); }}>{T.back}</button>
        <span class="lbl ttl">{T.understandTitle}</span>
        {#if nextHref}<a class="pbtn gold nx" href={nextHref} onclick={() => sfx("select")}>{inRun && runIdx! + 1 >= runLen ? T.end : T.next}</a>
        {:else}<a class="pbtn gold nx" href="#/mapa">{T.mapBtn}</a>{/if}
      </div>
      <div class="scrollwrap">
        <div class="scroll" use:moreHint>
          <h2 class="lbl sec">{T.whatHappened}</h2>
          <div class="dialog"><p>{typed}<span class="blink">▌</span></p></div>
          {#if c.qa_note && !en}<p class="dim small">Nota: {c.qa_note}</p>{/if}

          {#if compYears.length}
            <h2 class="lbl sec">{T.landscape}</h2>
            {#each compYears as y}
              <div class="cbar">
                <span class="cy lbl">{y}</span>
                <div class="bars">
                  <div class="stack">{#each segsOf(y) as s}<i style={`width:${s.v}%;background:${COVER[s.k].color}`} title={`${en ? COVER[s.k].en : COVER[s.k].pt} ${num(s.v)}%`}></i>{/each}</div>
                  <div class="nat" style={`width:${natOf(y)}%`}></div>
                </div>
              </div>
            {/each}
            <p class="natline small"><b class="pos">▬</b> {T.nativeShare(num(natOf(compYears[0])), num(natOf(compYears[compYears.length - 1])))}</p>
            <ul class="cleg">
              {#each legendRows as k}
                <li><i style={`background:${COVER[k].color}`}></i>{en ? COVER[k].en : COVER[k].pt}{COVER[k].native ? "" : " ✕"}
                  <span class="dim">{compYears.map((y) => `${num(comp[y]?.[k] ?? 0)}%`).join(" → ")}</span></li>
              {/each}
            </ul>
            <p class="dim tiny">{T.landscapeNote}</p>
          {/if}

          {#if clues.length}
            <h2 class="lbl sec">{T.falseClues}</h2>
            <ul class="clues">{#each clues as cl}<li>{cl}</li>{/each}</ul>
          {/if}

          <h2 class="lbl sec">{T.evidence}</h2>
          <ul class="proofs">{#each proofs as p}<li>{p}</li>{/each}</ul>

          <div class="lesson"><span class="lbl">{T.lesson}</span><p>{lesson}</p></div>

          {#if c.dossier?.length}
            <details class="small dossie">
              <summary class="lbl">{T.fullDossier}</summary>
              {#if T.dossierNote}<p class="dim">{T.dossierNote}</p>{/if}
              <ol lang="pt-BR">
                {#each c.dossier as d}
                  <li>
                    <b>{d.afirmacao}</b>
                    <p>{d.porque}</p>
                    {#if d.fontes.length}
                      <p class="src">{en ? "Sources" : "Fontes"}:
                        {#each d.fontes as f, i}{#if i}{"; "}{/if}<a href={f.url} target="_blank" rel="noopener">{f.nome}</a>{/each}
                      </p>
                    {/if}
                  </li>
                {/each}
              </ol>
            </details>
          {/if}
          <details class="small">
            <summary class="lbl">{T.files}</summary>
            <ul>
              <li>{T.filesS2}</li>
              {#if hasS2}<li>{T.filesSeason}</li>{/if}
              {#each c.products as p, i}
                <li>{lbl(i < 2 ? c.dates[i] : c.dates2![i - 2])}: <code>{p.id}</code>{#if p.browser_url} · <a href={p.browser_url} target="_blank" rel="noopener">{T.openBrowser}</a>{/if}</li>
              {/each}
              <li>{T.filesBase(y0, c.native_pct.mapbiomas_10m[0].toLocaleString(locale(), { maximumFractionDigits: 1 }), y1)}</li>
              <li>{T.filesBand(fmtPP(bd[0], 1), fmtPP(bd[1], 1))}</li>
              <li>{c.attribution}</li>
            </ul>
          </details>
        </div>
        <button class="moretag lbl" onclick={scrollMore} aria-hidden="true" tabindex="-1">{T.more}</button>
      </div>
    {/if}
  </section>
</div>

<style>
  .cv { display: flex; flex-direction: column; height: 100%; min-height: 0; gap: 8px; }
  .casebar { flex: none; }
  h1 { display: flex; align-items: baseline; gap: 8px; font-size: 11px; margin: 0; line-height: 1.5; min-width: 0; }
  .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .back { text-decoration: none; color: var(--cyan); }
  .meta { font-size: 16px; margin: 2px 0 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .view { flex: 1 1 auto; min-height: 0; }
  .radar { font-family: var(--px); font-size: 8px; background: var(--navy); border: 2px solid var(--gold); color: var(--gold); padding: 7px 7px 6px; white-space: nowrap; }
  .radar.on { background: var(--gold); color: var(--night); }
  @container (max-width: 400px) { .radar { padding: 7px 4px 6px; } }
  .season { border-color: var(--green); color: var(--green); }
  .season.on { background: var(--green); color: var(--night); }
  .maptg { border-color: var(--magenta); color: var(--magenta); }
  .maptg.on { background: var(--magenta); color: var(--night); }
  .mleg { font-size: 15px; color: var(--ink); }
  .mleg i { display: inline-block; width: 10px; height: 10px; margin: 0 4px 0 8px; border: 1px solid var(--shadow); vertical-align: -1px; }
  .mleg i:first-child { margin-left: 0; }
  /* painel de ALTURA FIXA: palpite e resultado ocupam exatamente o mesmo lugar */
  .panel { flex: 0 0 236px; height: 236px; padding: 14px 14px 12px; display: flex; flex-direction: column; min-height: 0; }
  /* na explicação o painel cresce; a imagem fica menor, mas visível (botão MAPA) */
  .cv.info .view { flex: 0 1 40%; }
  .cv.info .panel { flex: 1 1 60%; height: auto; }
  .q { font-size: 19px; margin: 0; }
  .readout { display: flex; align-items: center; justify-content: center; gap: 14px; margin: 4px 0 8px; }
  .digits { font-family: var(--px); font-size: 28px; text-shadow: 3px 3px 0 var(--shadow); }
  .ha { font-size: 15px; line-height: 1.1; }
  .gauge { position: relative; display: grid; grid-template-columns: repeat(50, 1fr); gap: 1px; height: 34px; padding: 4px 0; background: var(--shadow); cursor: pointer; touch-action: none; flex: none; }
  .gauge i { background: #1a1f4a; }
  .gauge i.keep { background: #1f7a45; } .gauge i.gain { background: var(--green); } .gauge i.loss { background: var(--red); }
  .base { position: absolute; top: -3px; bottom: -3px; width: 3px; transform: translateX(-50%); background: var(--ink); box-shadow: 0 0 0 1px var(--shadow); pointer-events: none; }
  .ha b { font-family: var(--px); font-size: 11px; font-weight: 400; }
  .pos { color: var(--green); } .neg { color: var(--red); }
  .ticks { display: flex; justify-content: space-between; margin: 4px 0 8px; font-size: 7px; }
  .ticks.abs { position: relative; }
  .ticks .bt { position: absolute; top: 0; transform: translateX(-50%); color: var(--ink); white-space: nowrap; }
  .ticks .bt.start { transform: none; } .ticks .bt.end { transform: translateX(-100%); } .ticks .hide { visibility: hidden; }
  .controls { display: grid; grid-template-columns: repeat(4, 1fr) 1.3fr; gap: 6px; margin-top: auto; }
  .controls .pbtn { justify-content: center; padding: 11px 4px 9px; } .controls .pbtn::before { display: none; }
  .go { font-size: 12px; }
  .reshead { display: flex; align-items: center; gap: 10px; flex: none; padding-bottom: 8px; border-bottom: 2px dashed var(--line-lo); }
  .pts .lbl { margin: 0; font-size: 7px; }
  .big { font-family: var(--px); font-size: 26px; margin: 4px 0 0; color: var(--gold); text-shadow: 3px 3px 0 var(--red-dk); }
  .again { margin-left: auto; font-size: 8px; padding: 10px 7px 8px; white-space: nowrap; } .again::before { display: none; }
  .nav { min-height: 54px; }
  .bk { font-size: 9px; padding: 11px 9px 9px; } .bk::before { display: none; }
  .ttl { font-size: 7px; flex: 1; text-align: center; }
  .nx { margin-left: auto; font-size: 10px; padding: 12px 12px 10px; white-space: nowrap; } .nx::before { display: none; }
  .again + .nx { margin-left: 0; }
  @container (max-width: 400px) { .big { font-size: 22px; } .nx { font-size: 9px; padding: 11px 8px 9px; } .reshead { gap: 8px; }
    .reshead .rank { width: 44px; height: 44px; font-size: 24px; } .reshead .big { font-size: 20px; }
    .again { padding: 10px 5px 8px; } .again + .nx { padding: 11px 6px 9px; } }
  .rank { font-family: var(--px); font-size: 30px; width: 54px; height: 54px; flex: none; display: grid; place-items: center; border: 3px solid var(--ink); background: var(--shadow); text-shadow: 3px 3px 0 var(--night); animation: pop 0.4s steps(4); }
  @keyframes pop { from { transform: scale(0.3); } }
  .rS { color: var(--gold); } .rA { color: var(--green); } .rB { color: var(--cyan); } .rC { color: var(--ink); } .rD { color: var(--red); }
  /* rolagem sem barra visível + aviso "▼ MAIS" quando há conteúdo abaixo */
  .scrollwrap { position: relative; flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }
  .scroll { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 10px 4px 0 0; scrollbar-width: none; }
  .scroll::-webkit-scrollbar { display: none; }
  .moretag { display: none; position: absolute; left: 50%; bottom: 0; transform: translateX(-50%); font-size: 8px; color: var(--night); background: var(--cyan); border: 2px solid var(--ink); padding: 5px 8px 4px; animation: blink 1s steps(1) infinite; }
  .scrollwrap:global(.hasmore) > .moretag { display: block; }
  .scrollwrap:global(.hasmore) > .scroll { mask-image: linear-gradient(to bottom, #000 calc(100% - 30px), transparent); }
  @media (prefers-reduced-motion: reduce) { .moretag { animation: none; } }
  .track { position: relative; height: 22px; background: var(--shadow); }
  .tol { position: absolute; top: 4px; bottom: 4px; background: rgb(69 224 124 / 0.25); }
  .mk { position: absolute; top: 50%; width: 12px; height: 12px; transform: translate(-50%, -50%); border: 2px solid var(--shadow); }
  .mk.you, .sw.you { background: var(--gold); } .mk.model, .sw.model { background: var(--green); } .mk.ref, .sw.ref { background: var(--magenta); }
  dl { display: grid; grid-template-columns: auto 1fr; margin: 0 0 10px; }
  dt, dd { margin: 0; padding: 4px 0; border-bottom: 2px dashed var(--line-lo); }
  dt { font-family: var(--px); font-size: 8px; display: flex; align-items: center; }
  dd { text-align: right; font-size: 19px; }
  dd .dim { font-size: 15px; }
  .sw { display: inline-block; width: 10px; height: 10px; margin-right: 6px; border: 2px solid var(--shadow); }
  .sec { font-size: 8px; color: var(--gold); margin: 14px 0 6px; font-weight: 400; }
  .sec:first-child { margin-top: 2px; }
  .dialog { background: var(--shadow); border: 3px solid var(--ink); padding: 8px 10px; }
  .dialog p { margin: 0; font-size: 19px; }
  .small { font-size: 17px; }
  .tiny { font-size: 14px; margin: 4px 0 0; }
  .cbar { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
  .cy { font-size: 7px; width: 34px; flex: none; }
  .bars { flex: 1; }
  .stack { display: flex; height: 16px; background: var(--shadow); border: 2px solid var(--shadow); }
  .stack i { display: block; height: 100%; }
  .nat { height: 4px; margin-top: 2px; background: var(--green); }
  .natline { margin: 2px 0 6px 42px; }
  .cleg { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 2px 10px; font-size: 16px; }
  .cleg li { display: flex; align-items: baseline; gap: 5px; min-width: 0; }
  .cleg i { width: 10px; height: 10px; flex: none; border: 1px solid var(--shadow); align-self: center; }
  .cleg .dim { margin-left: auto; white-space: nowrap; }
  @container (max-width: 400px) { .cleg { grid-template-columns: 1fr; } }
  .clues, .proofs { margin: 0; padding-left: 18px; font-size: 17px; }
  .clues li, .proofs li { margin-bottom: 4px; }
  .clues li::marker { content: "! "; color: var(--magenta); }
  .proofs li::marker { content: "■ "; color: var(--cyan); }
  .lesson { margin: 14px 0 4px; border: 3px solid var(--gold); background: var(--shadow); padding: 8px 10px; }
  .lesson .lbl { font-size: 7px; color: var(--gold); }
  .lesson p { margin: 4px 0 0; font-size: 19px; color: var(--ink); }
  details { margin-top: 10px; }
  details ul { padding-left: 18px; margin: 8px 0 0; }
  summary { cursor: pointer; }
  .dossie ol { padding-left: 20px; margin: 8px 0 0; }
  .dossie li { margin-bottom: 10px; }
  .dossie li p { margin: 3px 0 0; }
  .dossie .src { font-size: 15px; color: var(--dim); overflow-wrap: anywhere; }
  code { font-size: 14px; word-break: break-all; color: var(--cyan); }
</style>
