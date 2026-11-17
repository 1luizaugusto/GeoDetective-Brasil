<script lang="ts">
  import { untrack } from "svelte";
  import Compare from "./Compare.svelte";
  import type { Challenge, Dataset } from "../lib/types";
  import { score, band, fmtPP, fmtHa, fmtDate, rank, pad } from "../lib/score";
  import { progress, record } from "../lib/progress.svelte";
  import { sfx } from "../lib/sfx.svelte";
  import { run, recordRun } from "../lib/run.svelte";
  import { settings } from "../lib/settings.svelte";

  let { data, challenge: c, runIdx }: { data: Dataset; challenge: Challenge; runIdx?: number } = $props();
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
  // 3 etapas no MESMO painel de altura fixa: palpite → resultado → explicação (texto, fontes, arquivos)
  let step = $state<"guess" | "result" | "info">(prev ? "result" : "guess");
  const submitted = $derived(step !== "guess");
  let showContext = $state(false);
  let otherSeason = $state(false); // OUTRA ÉPOCA: mesma área, outra época do ano, nos dois anos
  const hasS2 = $derived(!!(c.images.before2 && c.images.after2 && c.dates2));
  const MES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];
  const lbl = (iso: string) => `${MES[Number(iso.slice(5, 7)) - 1]} ${iso.slice(0, 4)}`;
  const curDates = $derived(otherSeason && c.dates2 ? c.dates2 : c.dates);
  const imgs = $derived.by(() => {
    const I = c.images, o = otherSeason && hasS2;
    if (showContext) return o ? [I.context_before2!, I.context_after2!] : [I.context_before, I.context_after];
    return o ? [I.before2!, I.after2!] : [I.before, I.after];
  });
  let shown = $state(prev?.points ?? 0); // contador animado
  let typed = $state("");

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

  const defaultText: Record<Challenge["kind"], string> = {
    loss: "Vegetação nativa foi convertida — em geral em pasto, lavoura, mineração ou cidade. Procure manchas de mata ou cerrado que viraram solo exposto ou campo uniforme.",
    gain: "Parte da área voltou a ser vegetação nativa. Ganhos reais são lentos e discretos a 10 m por pixel.",
    stable_edge: "A fronteira entre vegetação nativa e uso humano ficou no mesmo lugar. Diferenças de cor por estação, chuva ou luz não contam.",
    trap: "ARMADILHA! Ficou muito mais verde, mas o verde é de árvores plantadas ou lavoura — não de vegetação nativa. A mudança esperada é perto de zero.",
  };
  const explanation = $derived(c.explanation || defaultText[c.kind]);
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let typing: ReturnType<typeof setInterval> | undefined;
  function openInfo() {
    step = "info"; sfx("select");
    if (typed === explanation) return; // já foi escrito uma vez
    clearInterval(typing);
    if (reduced || !settings.typewriter) { typed = explanation; return; }
    let i = 0; typed = "";
    typing = setInterval(() => { typed = explanation.slice(0, (i += 2)); if (i >= explanation.length) clearInterval(typing); }, 18);
  }
  function reveal(points: number) {
    shown = 0;
    if (reduced) { shown = points; return; }
    const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / 900);
      const v = Math.round(points * k);
      if (v !== shown && v % 4 === 0) sfx("tick");
      shown = v;
      if (k < 1) requestAnimationFrame(step);
      else {
        sfx(points >= 80 ? "good" : points >= 35 ? "ok" : "bad");
      }
    };
    requestAnimationFrame(step);
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

<!-- Layout fixo dentro do palco: cabeçalho do caso · imagem (todo o espaço que sobra) · painel de ALTURA FIXA -->
<div class="cv">
  <div class="casebar">
    <h1>
      {#if inRun}<a class="back" href="#/" aria-label="Menu">◀</a><span class="gold-t">{runIdx! + 1}/{runLen}</span>
      {:else}<a class="back" href={c.uf ? `#/mapa/${c.uf}` : "#/mapa"} aria-label="Mapa">◀</a><span class="gold-t">#{caseNo}</span>{/if}
      <span class="nm">{c.name}</span>
    </h1>
    <p class="meta dim">{c.biome}{c.municipality ? ` · ${c.municipality}` : ""}{c.uf ? `/${c.uf}` : ""} · {c.size_km.toLocaleString("pt-BR")} km · {fmtDate(c.dates[0])} → {fmtDate(c.dates[1])}</p>
  </div>

  <div class="view">
    <Compare
      before={imgs[0]} after={imgs[1]}
      labelBefore={`${lbl(curDates[0])}
NATIVA ${base}%`} labelAfter={`${lbl(curDates[1])}
NATIVA ${submitted ? `${refAfter}%` : "?"}`}
      alt={showContext ? `${c.name}, área ampla` : c.name}
      caption={showContext ? "Área ao redor · quadrado amarelo = recorte"
        : c.season_hint && !otherSeason && !submitted ? "Mata sem folhas pode parecer pasto · veja ÉPOCA 2"
        : otherSeason ? "ÉPOCA 2: época mais verde do ano" : ""}>
      {#snippet tools()}
        {#if hasS2}
          <button class="radar season" class:on={otherSeason} title="Mesma área em outra época do ano, nos dois anos"
            onclick={() => { otherSeason = !otherSeason; sfx("move"); }}>{otherSeason ? "◀ ÉPOCA 1" : "ÉPOCA 2"}</button>
        {/if}
        <button class="radar" class:on={showContext} onclick={() => { showContext = !showContext; sfx("move"); }}>
          {showContext ? "◀ RECORTE" : "RADAR"}
        </button>
      {/snippet}
    </Compare>
  </div>

  <section class="win panel">
    {#if !submitted}
      <p class="q">Em {y0}, <b class="gold-t">{base}%</b> do recorte era <b>vegetação nativa</b>. E em {y1}?</p>
      <div class="readout">
        <output class="digits">{after}%</output>
        <span class="ha"><b class:pos={guess > 0} class:neg={guess < 0}>{fmtPP(guess)}</b><br /><span class="dim">{fmtHa(guess, c.size_km)}</span></span>
      </div>
      <div class="gauge" bind:this={gauge} role="slider" tabindex="0"
        aria-label={`Vegetação nativa em ${y1}, em % do recorte; em ${y0} era ${base}%`}
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
      <div class="ticks abs lbl"><span>0%</span><span class="bt" style={`left:${base}%`}>{y0}</span><span>100%</span></div>
      <div class="controls">
        <button class="pbtn small" onclick={() => nudge(-10)}>-10</button>
        <button class="pbtn small" onclick={() => nudge(-1)}>-1</button>
        <button class="pbtn small" onclick={() => nudge(1)}>+1</button>
        <button class="pbtn small" onclick={() => nudge(10)}>+10</button>
        <button class="pbtn gold go" onclick={submit}>OK</button>
      </div>
    {:else if step === "result"}
      <div class="reshead">
        <div class={`rank r${rk}`} aria-label={`Nota ${rk}`}>{rk}</div>
        <div class="pts"><p class="lbl">PONTOS</p><p class="big">{pad(shown, 3)}</p></div>
        <button class="pbtn gold nx" onclick={openInfo}>ENTENDA ▶</button>
      </div>
      <div class="scroll">
        <div class="track" aria-hidden="true">
          <div class="tol" style={`left:${at(bd[0])}; width:${Math.max(0, Math.min(100, base + bd[1]) - Math.max(0, base + bd[0]))}%`}></div>
          <i class="mk ref" style={`left:${at(c.reference_pp.mapbiomas_10m)}`}></i>
          <i class="mk model" style={`left:${at(c.model_estimate_pp)}`}></i>
          <i class="mk you" style={`left:${at(guess)}`}></i>
          <b class="base" style={`left:${base}%`}></b>
        </div>
        <div class="ticks abs lbl"><span>0%</span><span class="bt" style={`left:${base}%`}>{y0}</span><span>100%</span></div>
        <dl>
          <dt><i class="sw you"></i>VOCÊ</dt><dd>{base}→{after}% <span class="dim">{fmtPP(guess)}</span></dd>
          <dt><i class="sw model"></i>MODELO</dt><dd>{fmtPP(c.model_estimate_pp, 1)}</dd>
          <dt><i class="sw ref"></i>MAPBIOMAS</dt><dd>{base}→{refAfter}% <span class="dim">{fmtPP(c.reference_pp.mapbiomas_10m, 1)}</span></dd>
        </dl>
        {#if !inRun}<button class="pbtn small" onclick={() => { step = "guess"; sfx("move"); }}>TENTAR DE NOVO</button>{/if}
      </div>
    {:else}
      <div class="reshead nav">
        <button class="pbtn bk" onclick={() => { step = "result"; sfx("move"); }}>◀ VOLTAR</button>
        <span class="lbl ttl">ENTENDA O CASO</span>
        {#if nextHref}<a class="pbtn gold nx" href={nextHref} onclick={() => sfx("select")}>{inRun && runIdx! + 1 >= runLen ? "FIM ▶" : "PRÓXIMO ▶"}</a>
        {:else}<a class="pbtn gold nx" href="#/mapa">MAPA ▶</a>{/if}
      </div>
      <div class="scroll">
        <div class="dialog"><p>{typed}<span class="blink">▌</span></p></div>
        {#if c.qa_note}<p class="dim small">Nota: {c.qa_note}</p>{/if}
        {#if c.dossier?.length}
          <details class="small dossie">
            <summary class="lbl">FONTES</summary>
            <ol>
              {#each c.dossier as d}
                <li>
                  <b>{d.afirmacao}</b>
                  <p>{d.porque}</p>
                  {#if d.fontes.length}
                    <p class="src">Fontes:
                      {#each d.fontes as f, i}{#if i}{"; "}{/if}<a href={f.url} target="_blank" rel="noopener">{f.nome}</a>{/each}
                    </p>
                  {/if}
                </li>
              {/each}
            </ol>
          </details>
        {/if}
        <details class="small">
          <summary class="lbl">ARQUIVOS DO CASO</summary>
          <ul>
            <li>Sentinel-2 · 10 m por pixel · ampliado 3× sem inventar detalhes.</li>
            {#if hasS2}<li>ÉPOCA 2 = a data mais verde que os dois anos têm na mesma época (até 30 dias de diferença), sem nuvem no recorte. O modelo usa as duas épocas.</li>{/if}
            {#each c.products as p, i}
              <li>{lbl(i < 2 ? c.dates[i] : c.dates2![i - 2])}: <code>{p.id}</code>{#if p.browser_url} · <a href={p.browser_url} target="_blank" rel="noopener">abrir no Copernicus Browser</a>{/if}</li>
            {/each}
            <li>Ponto de partida fixo: em {y0}, {c.native_pct.mapbiomas_10m[0].toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% do recorte era vegetação nativa no MapBiomas 10 m (mostrado arredondado). Você estima {y1}; o que vale ponto é a variação, depois − antes, em pp (pontos percentuais).</li>
            <li>Faixa de 100 pontos (verde na régua): de {fmtPP(bd[0], 1)} a {fmtPP(bd[1], 1)}, ou seja, do valor do modelo ao do MapBiomas, com 3 pp de margem. Fora dela, os pontos caem até zero em 40 pp.</li>
            <li>{c.attribution}</li>
          </ul>
        </details>
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
  .season { border-color: var(--green); color: var(--green); margin-right: 5px; }
  .season.on { background: var(--green); color: var(--night); }
  /* painel de ALTURA FIXA: palpite e resultado ocupam exatamente o mesmo lugar */
  .panel { flex: 0 0 236px; height: 236px; padding: 14px 14px 12px; display: flex; flex-direction: column; min-height: 0; }
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
  .controls { display: grid; grid-template-columns: repeat(4, 1fr) 1.3fr; gap: 6px; margin-top: auto; }
  .controls .pbtn { justify-content: center; padding: 11px 4px 9px; } .controls .pbtn::before { display: none; }
  .go { font-size: 12px; }
  .reshead { display: flex; align-items: center; gap: 12px; flex: none; padding-bottom: 8px; border-bottom: 2px dashed var(--line-lo); }
  .pts .lbl { margin: 0; font-size: 7px; }
  .big { font-family: var(--px); font-size: 26px; margin: 4px 0 0; color: var(--gold); text-shadow: 3px 3px 0 var(--red-dk); }
  .nav { min-height: 54px; }
  .bk { font-size: 9px; padding: 11px 9px 9px; } .bk::before { display: none; }
  .ttl { font-size: 7px; flex: 1; text-align: center; }
  .nx { margin-left: auto; font-size: 10px; padding: 12px 12px 10px; } .nx::before { display: none; }
  .rank { font-family: var(--px); font-size: 30px; width: 54px; height: 54px; flex: none; display: grid; place-items: center; border: 3px solid var(--ink); background: var(--shadow); text-shadow: 3px 3px 0 var(--night); animation: pop 0.4s steps(4); }
  @keyframes pop { from { transform: scale(0.3); } }
  .rS { color: var(--gold); } .rA { color: var(--green); } .rB { color: var(--cyan); } .rC { color: var(--ink); } .rD { color: var(--red); }
  .scroll { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 10px 4px 0 0; scrollbar-width: thin; scrollbar-color: var(--line-lo) transparent; }
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
  .dialog { background: var(--shadow); border: 3px solid var(--ink); padding: 8px 10px; margin-bottom: 10px; }
  .dialog p { margin: 0; font-size: 19px; }
  .small { font-size: 17px; }
  details { margin-top: 10px; }
  details ul { padding-left: 18px; margin: 8px 0 0; }
  summary { cursor: pointer; }
  .dossie ol { padding-left: 20px; margin: 8px 0 0; }
  .dossie li { margin-bottom: 10px; }
  .dossie li p { margin: 3px 0 0; }
  .dossie .src { font-size: 15px; color: var(--dim); overflow-wrap: anywhere; }
  code { font-size: 14px; word-break: break-all; color: var(--cyan); }
</style>
