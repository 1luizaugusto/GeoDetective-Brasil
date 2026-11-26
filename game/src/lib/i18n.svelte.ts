// Idioma da interface (pt-BR / en). Fica só no navegador. Termos técnicos em inglês são os usados na
// literatura de sensoriamento remoto e ecologia (ex.: "rock outcrop", "tree plantation"), não tradução literal.
export type Lang = "pt" | "en";
const KEY = "geodetective-lang";

function load(): Lang {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "pt" || v === "en") return v;
  } catch { /* modo privado */ }
  return (navigator.language || "pt").toLowerCase().startsWith("pt") ? "pt" : "en";
}

export const i18n = $state<{ lang: Lang }>({ lang: load() });

export function setLang(l: Lang) {
  i18n.lang = l;
  try { localStorage.setItem(KEY, l); } catch { /* ignora */ }
  applyLang();
}
export function applyLang() {
  document.documentElement.lang = i18n.lang === "pt" ? "pt-BR" : "en";
}
export const locale = () => (i18n.lang === "pt" ? "pt-BR" : "en-US");

const BIOME_EN: Record<string, string> = { "Amazônia": "Amazon", "Mata Atlântica": "Atlantic Forest" };
export const biomeName = (b: string) => (i18n.lang === "en" ? BIOME_EN[b] ?? b : b);

// grupos de cobertura (science/scripts/build_explain.py) — cores da legenda oficial MapBiomas
export const COVER: Record<string, { native: boolean; color: string; pt: string; en: string }> = {
  forest: { native: true, color: "#1f8d49", pt: "Floresta", en: "Forest" },
  mangrove: { native: true, color: "#04381d", pt: "Mangue", en: "Mangrove" },
  savanna: { native: true, color: "#7dc975", pt: "Savana", en: "Savanna" },
  grassland: { native: true, color: "#d6bc74", pt: "Campo nativo", en: "Native grassland" },
  wetland: { native: true, color: "#519799", pt: "Campo alagado", en: "Wetland" },
  rock: { native: true, color: "#ad5100", pt: "Afloramento rochoso", en: "Rock outcrop" },
  tidalflat: { native: true, color: "#fc8114", pt: "Apicum", en: "Hypersaline tidal flat" },
  pasture: { native: false, color: "#edde8e", pt: "Pasto", en: "Pasture" },
  crop: { native: false, color: "#e974ed", pt: "Lavoura", en: "Cropland" },
  silviculture: { native: false, color: "#7a5900", pt: "Silvicultura", en: "Tree plantation" },
  mosaic: { native: false, color: "#ffefc3", pt: "Mosaico de usos", en: "Land-use mosaic" },
  water: { native: false, color: "#2532e4", pt: "Água", en: "Water" },
  urban: { native: false, color: "#d4271e", pt: "Área urbana", en: "Built-up area" },
  mining: { native: false, color: "#9c0027", pt: "Mineração", en: "Mining" },
  bare: { native: false, color: "#db4d4f", pt: "Solo exposto", en: "Bare ground" },
  other: { native: false, color: "#757272", pt: "Outros", en: "Other" },
};

const pt = {
  pts: "PTS", cases: "CASOS", menu: "MENU", ptsTitle: "pontos", casesTitle: "casos jogados",
  loadErr: "Não foi possível carregar os desafios.", loading: "CARREGANDO", error: "ERRO",
  caseNotFound: "Caso não encontrado.", backMap: "Voltar ao mapa", noRun: "Nenhuma partida em andamento.", backMenu: "Voltar ao menu",
  // menu
  tagline: "Investigue imagens reais de satélite e descubra quanto da vegetação nativa mudou.",
  continue: "CONTINUAR", newGame: "NOVO JOGO", resumeRun: "RETOMAR PARTIDA", quickRun: "PARTIDA RÁPIDA", pickStage: "ESCOLHER FASE",
  records: "RECORDES", options: "OPÇÕES", manual: "MANUAL", credits: "CRÉDITOS",
  hintCases: (a: number, b: number) => `${a}/${b} CASOS`, hintCase: (a: number, b: number) => `CASO ${a}/${b}`,
  hintRandom: "5 CASOS SORTEADOS", hintMap: "MAPA DO BRASIL",
  askWipe: (n: number, p: string) => `APAGAR O PROGRESSO (${n} CASOS, ${p} PONTOS) E COMEÇAR DO ZERO?`,
  askRun: (a: number, b: number) => `JÁ HÁ UMA PARTIDA NO CASO ${a}/${b}. SORTEAR OUTRA?`,
  sure: "TEM CERTEZA?", yes: "SIM", no: "NÃO", pressEnter: "APERTE ENTER", arrowsPick: "SETAS ESCOLHEM",
  record: "RECORDE", rule1: "COMPARE AS DUAS IMAGENS", rule2: "ESTIME A MUDANÇA DA VEGETAÇÃO NATIVA", rule3: "CUIDADO: VERDE PODE NÃO SER NATIVO!",
  // caso
  months: ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"],
  native: "NATIVA", question: (y0: string, b: number, y1: string) => [`Em ${y0}, `, `${b}%`, " do recorte era ", "vegetação nativa", `. E em ${y1}?`],
  sliderLabel: (y1: string, y0: string, b: number) => `Vegetação nativa em ${y1}, em % do recorte; em ${y0} era ${b}%`,
  points: "PONTOS", rankLabel: (r: string) => `Nota ${r}`, understand: "ENTENDA ▶", tryAgain: "DE NOVO", tryAgainFull: "Tentar este caso de novo",
  you: "VOCÊ", model: "MODELO", mapbiomas: "MAPBIOMAS", back: "◀ VOLTAR", understandTitle: "ENTENDA O CASO", next: "PRÓXIMO ▶", end: "FIM ▶", mapBtn: "MAPA ▶",
  more: "▼ MAIS",
  season2: "ÉPOCA 2", season1: "ÉPOCA 1", radar: "RADAR", crop: "◀ RECORTE", mapLayer: "MAPA", mapLayerOff: "FOTO",
  season2Title: "Mesma área em outra época do ano, nos dois anos", mapTitle: "Onde o MapBiomas marca vegetação nativa",
  capContext: "Área ao redor · quadrado amarelo = recorte", capSeason: "Mata sem folhas pode parecer pasto · veja ÉPOCA 2",
  capSeason2: "ÉPOCA 2: o mesmo lugar em outra data do ano", wideArea: "área ampla",
  legNative: "nativa", legLost: "perdida", legGained: "ganha", legSrc: "MapBiomas 10 m",
  defaultText: {
    loss: "A vegetação nativa foi suprimida e convertida, em geral, em pasto, lavoura, mineração ou cidade.",
    gain: "Parte da área voltou a ser vegetação nativa. A regeneração é lenta e discreta a 10 m por pixel.",
    stable_edge: "O limite entre vegetação nativa e uso humano ficou no mesmo lugar. Mudança de cor por estação, chuva ou luz não conta.",
    trap: "ARMADILHA! Ficou mais verde, mas o verde é de plantio ou lavoura, não de vegetação nativa.",
  },
  // ENTENDA O CASO
  whatHappened: "O QUE ACONTECEU", landscape: "A PAISAGEM", landscapeNote: "Classes do MapBiomas 10 m. A barra verde marca o que conta como nativo.",
  falseClues: "PISTAS FALSAS", evidence: "PROVAS", lesson: "LIÇÃO DO DETETIVE", fullDossier: "DOSSIÊ COMPLETO (FONTES)", files: "ARQUIVOS DO CASO",
  nativeShare: (a: string, b: string) => `nativa ${a}% → ${b}%`,
  clue: {
    fire: (list: string) => `FOGO: queimou ${list} (MapBiomas Fogo). A cor muda; a vegetação só deixa de ser nativa se for substituída.`,
    open: (p: string) => `FORMAÇÃO ABERTA: ${p}% do recorte é campo, savana ou afloramento rochoso. Tem poucas árvores, mas é nativo.`,
    plantation: (a: string, b: string) => `SILVICULTURA: plantio comercial de árvores (${a}% → ${b}% do recorte). Não conta como nativa.`,
    crop: (a: string, b: string) => `LAVOURA: ${a}% → ${b}% do recorte. O verde da safra não é vegetação nativa.`,
    season: "ESTAÇÃO: na época 1 a vegetação está bem mais seca nos dois anos. Compare com a ÉPOCA 2.",
    water: "ÁGUA: a extensão da água e do campo alagado varia entre as datas.",
  },
  proof: {
    maps: (a: string, b: string, d10: string, d30: string) => `MapBiomas 10 m: ${a}% → ${b}% de nativa (${d10}). O mapa de 30 m dá ${d30}.`,
    model: (d: string) => `Modelo (Random Forest, usa as 10 bandas do Sentinel-2 das duas épocas, índices como o NDVI e o bioma, e não treinou com este recorte): ${d}.`,
    protected: (p: number, n: string) => `${p}% do recorte fica em área protegida: ${n} (WDPA).`,
    burned: (list: string) => `Área queimada: ${list} (MapBiomas Fogo).`,
  },
  burnedItem: (y: number, p: string) => `${p}% em ${y}`,
  lessons: {
    plantation: "Verde não é sinônimo de nativo: silvicultura é plantio comercial, não vegetação nativa.",
    crop: "Lavoura verde não é vegetação nativa.",
    open: "Poucas árvores não é desmatamento: campo, savana e afloramento rochoso são formações nativas.",
    openLoss: "Campo e savana também são vegetação nativa: suprimi-los também conta como perda.",
    fire: "Área queimada muda de cor, mas continua nativa se a vegetação não for substituída.",
    season: "Compare a mesma época do ano: na seca, a vegetação nativa perde folhas e pode parecer pasto.",
    water: "Cheia e seca mudam a água e o campo alagado, não a vegetação nativa.",
    regrowth: "Regeneração é lenta e discreta: procure solo exposto que ficou coberto.",
    conversion: "Supressão deixa marcas retas: talhões, estradas e solo exposto onde havia vegetação nativa.",
    loss: "Procure a borda: onde a vegetação nativa terminava antes e onde termina agora.",
    stable_edge: "Mudança de cor não é mudança de cobertura: compare as bordas entre o nativo e o uso.",
    gain: "Regeneração é lenta e discreta: procure solo exposto que ficou coberto.",
    trap: "Verde não é sinônimo de nativo.",
  } as Record<string, string>,
  filesS2: "Sentinel-2 · 10 m por pixel · ampliado 3× sem inventar detalhes.",
  filesSeason: "ÉPOCA 2 = um segundo par de datas, a pelo menos 45 dias da época 1: entre as datas sem nuvem no recorte, o par mais verde que os dois anos têm com até 30 dias de diferença no calendário. O modelo usa as duas épocas.",
  openBrowser: "abrir no Copernicus Browser",
  filesBase: (y0: string, v: string, y1: string) => `Ponto de partida fixo: em ${y0}, ${v}% do recorte era vegetação nativa no MapBiomas 10 m (mostrado arredondado). Você estima ${y1}; o que vale ponto é a variação, depois − antes, em pp (pontos percentuais).`,
  filesBand: (a: string, b: string) => `Faixa de 100 pontos (verde na régua): de ${a} a ${b}, ou seja, do valor do modelo ao do MapBiomas, com 3 pp de margem. Fora dela, os pontos caem até zero em 40 pp.`,
  dossierNote: "",
  // comparação
  curtain: "CORTINA", side: "LADO", sideLong: "LADO A LADO", blink: "PISCA", compareMode: "Modo de comparação", curtainPos: "Posição da cortina",
  tapSwap: "TOQUE PARA TROCAR", swap: "Alternar entre antes e depois",
  // opções
  config: "CONFIGURAÇÃO", sound: "SOM", initialCompare: "COMPARAÇÃO INICIAL", crt: "EFEITO TV (SCANLINES)", typewriter: "TEXTO DATILOGRAFADO", language: "IDIOMA / LANGUAGE",
  optHint: "SETAS ESCOLHEM · ◀ ▶ MUDAM · ESC VOLTA AO MENU", saved: "DADOS SALVOS",
  savedText: "O progresso fica só neste navegador. Nada é enviado para servidor nenhum.", wipeBtn: "APAGAR PROGRESSO E RECORDES",
  wipeAsk: (n: number) => `Apagar ${n} casos jogados e os recordes de partida? Não dá para desfazer.`, wipeYes: "SIM, APAGAR", wiped: "PROGRESSO APAGADO.", menuBack: "◀ MENU",
  // fim de partida
  runOver: "FIM DA PARTIDA", newRecord: "★ NOVO RECORDE ★", total: "TOTAL",
  vsZero: (a: string, b: string) => `VOCÊ ${a} × ${b} CHUTE ZERO — `,
  won: (n: number) => `VENCEU POR ${n}!`, tie: "EMPATE. Arrisque mais!", lost: (n: number) => `PERDEU POR ${n}. Olhe melhor as imagens!`,
  zeroNote: "\"Chute zero\" é quem sempre diz que nada mudou. Vencê-lo prova que você viu a mudança.",
  thCase: "CASO", thYou: "VOCÊ", thModel: "MODELO", thPts: "PTS", thZero: "ZERO", playAgain: "JOGAR DE NOVO",
  // recordes
  campaign: "CAMPANHA", average: "MÉDIA", vsZeroShort: "× CHUTE ZERO", clearChanges: "MUDANÇAS CLARAS", casesWord: "casos", traps: "ARMADILHAS", disarmed: "desarmadas",
  top5: "PARTIDA RÁPIDA · TOP 5", noRuns: "Nenhuma partida completa ainda.", byBiome: "POR BIOMA", biome: "BIOMA",
  // mapa
  stageMap: "MAPA DE FASES", pickState: "▶ ESCOLHA UM ESTADO", stateCases: (n: string, k: number) => `${n.toUpperCase()} · ${k} CASO(S)`,
  mapAria: "Mapa do Brasil por estado", ufAria: (n: string, k: number) => `${n}: ${k} casos`,
  legNew: "NOVO", legPartial: "EM CURSO", legDone: "COMPLETO", legEmpty: "VAZIO", casesUf: (uf: string) => `CASOS · ${uf}`, allCases: "TODOS OS CASOS",
  all: "TODOS", allStates: "◀ TODOS OS ESTADOS", noFilter: "Nenhum caso com esse filtro.", wipeSave: "APAGAR SAVE", wipeSaveAsk: "Apagar seu progresso neste navegador?",
  // créditos
  authorship: "AUTORIA", dataLicenses: "DADOS E LICENÇAS", openSource: "Código aberto (licença MIT):", statesMesh: "Malha dos estados: IBGE.",
  generated: (d: string, v: string) => `Dados gerados em ${d} · esquema ${v}.`,
};

type Dict = typeof pt;

const en: Dict = {
  pts: "PTS", cases: "CASES", menu: "MENU", ptsTitle: "points", casesTitle: "cases played",
  loadErr: "Could not load the cases.", loading: "LOADING", error: "ERROR",
  caseNotFound: "Case not found.", backMap: "Back to the map", noRun: "No run in progress.", backMenu: "Back to the menu",
  tagline: "Investigate real satellite images and find out how much native vegetation has changed.",
  continue: "CONTINUE", newGame: "NEW GAME", resumeRun: "RESUME RUN", quickRun: "QUICK RUN", pickStage: "SELECT STAGE",
  records: "RECORDS", options: "OPTIONS", manual: "MANUAL", credits: "CREDITS",
  hintCases: (a, b) => `${a}/${b} CASES`, hintCase: (a, b) => `CASE ${a}/${b}`,
  hintRandom: "5 RANDOM CASES", hintMap: "MAP OF BRAZIL",
  askWipe: (n, p) => `ERASE PROGRESS (${n} CASES, ${p} POINTS) AND START OVER?`,
  askRun: (a, b) => `A RUN IS IN PROGRESS AT CASE ${a}/${b}. DRAW A NEW ONE?`,
  sure: "ARE YOU SURE?", yes: "YES", no: "NO", pressEnter: "PRESS ENTER", arrowsPick: "ARROWS SELECT",
  record: "RECORD", rule1: "COMPARE THE TWO IMAGES", rule2: "ESTIMATE THE CHANGE IN NATIVE VEGETATION", rule3: "CAREFUL: GREEN MAY NOT BE NATIVE!",
  months: ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
  native: "NATIVE", question: (y0, b, y1) => [`In ${y0}, `, `${b}%`, " of the tile was ", "native vegetation", `. What about ${y1}?`],
  sliderLabel: (y1, y0, b) => `Native vegetation in ${y1}, as % of the tile; in ${y0} it was ${b}%`,
  points: "POINTS", rankLabel: (r) => `Grade ${r}`, understand: "DEBRIEF ▶", tryAgain: "RETRY", tryAgainFull: "Try this case again",
  you: "YOU", model: "MODEL", mapbiomas: "MAPBIOMAS", back: "◀ BACK", understandTitle: "CASE DEBRIEF", next: "NEXT ▶", end: "END ▶", mapBtn: "MAP ▶",
  more: "▼ MORE",
  season2: "SEASON 2", season1: "SEASON 1", radar: "RADAR", crop: "◀ TILE", mapLayer: "MAP", mapLayerOff: "PHOTO",
  season2Title: "Same area in another season, in both years", mapTitle: "Where MapBiomas maps native vegetation",
  capContext: "Surroundings · yellow square = tile", capSeason: "Leafless forest can look like pasture · check SEASON 2",
  capSeason2: "SEASON 2: the same place on another date of the year", wideArea: "wide area",
  legNative: "native", legLost: "lost", legGained: "gained", legSrc: "MapBiomas 10 m",
  defaultText: {
    loss: "Native vegetation was cleared and converted, usually to pasture, cropland, mining or urban area.",
    gain: "Part of the area reverted to native vegetation. Regrowth is slow and subtle at 10 m per pixel.",
    stable_edge: "The boundary between native vegetation and land use stayed in place. Color changes from season, rain or light do not count.",
    trap: "TRAP! It got greener, but the green is a plantation or crop, not native vegetation.",
  },
  whatHappened: "WHAT HAPPENED", landscape: "THE LANDSCAPE", landscapeNote: "MapBiomas 10 m classes. The green bar marks what counts as native.",
  falseClues: "FALSE CLUES", evidence: "EVIDENCE", lesson: "DETECTIVE'S LESSON", fullDossier: "FULL EVIDENCE FILE (IN PORTUGUESE)", files: "CASE FILES",
  nativeShare: (a, b) => `native ${a}% → ${b}%`,
  clue: {
    fire: (list) => `FIRE: burned ${list} (MapBiomas Fire). Color changes; vegetation only stops being native if it is replaced.`,
    open: (p) => `OPEN FORMATION: ${p}% of the tile is grassland, savanna or rock outcrop. Few trees, but native.`,
    plantation: (a, b) => `TREE PLANTATION: commercial forestry (${a}% → ${b}% of the tile). Not counted as native.`,
    crop: (a, b) => `CROPLAND: ${a}% → ${b}% of the tile. Crop green is not native vegetation.`,
    season: "SEASON: season 1 is much drier in both years. Compare with SEASON 2.",
    water: "WATER: the extent of open water and wetland varies between dates.",
  },
  proof: {
    maps: (a, b, d10, d30) => `MapBiomas 10 m: ${a}% → ${b}% native (${d10}). The 30 m map gives ${d30}.`,
    model: (d) => `Model (Random Forest using all 10 Sentinel-2 bands from both seasons, indices such as NDVI and the biome; not trained on this tile): ${d}.`,
    protected: (p, n) => `${p}% of the tile lies in a protected area: ${n} (WDPA).`,
    burned: (list) => `Burned area: ${list} (MapBiomas Fire).`,
  },
  burnedItem: (y, p) => `${p}% in ${y}`,
  lessons: {
    plantation: "Green does not mean native: a tree plantation is a crop, not native vegetation.",
    crop: "A green crop field is not native vegetation.",
    open: "Few trees is not deforestation: grassland, savanna and rock outcrops are native formations.",
    openLoss: "Grassland and savanna are native vegetation too: clearing them also counts as loss.",
    fire: "Burned land changes color, but stays native unless the vegetation is replaced.",
    season: "Compare the same time of year: in the dry season, native vegetation sheds leaves and can look like pasture.",
    water: "Floods and droughts shift water and wetlands, not native vegetation.",
    regrowth: "Regrowth is slow and subtle: look for bare ground that became covered.",
    conversion: "Clearing leaves straight lines: fields, roads and bare soil where native vegetation used to be.",
    loss: "Find the edge: where native vegetation ended before, and where it ends now.",
    stable_edge: "A color change is not a land-cover change: compare the edges between native areas and land use.",
    gain: "Regrowth is slow and subtle: look for bare ground that became covered.",
    trap: "Green does not mean native.",
  },
  filesS2: "Sentinel-2 · 10 m per pixel · upscaled 3× without inventing detail.",
  filesSeason: "SEASON 2 = a second pair of dates, at least 45 days from season 1: among cloud-free dates over the tile, the greenest pair both years share within 30 calendar days. The model uses both seasons.",
  openBrowser: "open in Copernicus Browser",
  filesBase: (y0, v, y1) => `Fixed starting point: in ${y0}, ${v}% of the tile was native vegetation in MapBiomas 10 m (shown rounded). You estimate ${y1}; what scores is the change, after − before, in pp (percentage points).`,
  filesBand: (a, b) => `100-point band (green on the scale): from ${a} to ${b}, i.e. from the model's value to MapBiomas', with a 3 pp margin. Outside it, points drop to zero at 40 pp.`,
  dossierNote: "The full evidence file was compiled in Portuguese; the key evidence is summarized above.",
  curtain: "SLIDER", side: "SIDE", sideLong: "SIDE BY SIDE", blink: "BLINK", compareMode: "Comparison mode", curtainPos: "Slider position",
  tapSwap: "TAP TO SWAP", swap: "Toggle between before and after",
  config: "SETTINGS", sound: "SOUND", initialCompare: "DEFAULT COMPARISON", crt: "TV EFFECT (SCANLINES)", typewriter: "TYPEWRITER TEXT", language: "IDIOMA / LANGUAGE",
  optHint: "ARROWS SELECT · ◀ ▶ CHANGE · ESC BACK TO MENU", saved: "SAVED DATA",
  savedText: "Progress is stored only in this browser. Nothing is sent to any server.", wipeBtn: "ERASE PROGRESS AND RECORDS",
  wipeAsk: (n) => `Erase ${n} played cases and the run records? This cannot be undone.`, wipeYes: "YES, ERASE", wiped: "PROGRESS ERASED.", menuBack: "◀ MENU",
  runOver: "RUN OVER", newRecord: "★ NEW RECORD ★", total: "TOTAL",
  vsZero: (a, b) => `YOU ${a} × ${b} ZERO GUESS — `,
  won: (n) => `YOU WON BY ${n}!`, tie: "A TIE. Take more risks!", lost: (n) => `YOU LOST BY ${n}. Look closer at the images!`,
  zeroNote: "\"Zero guess\" always says nothing changed. Beating it proves you spotted the change.",
  thCase: "CASE", thYou: "YOU", thModel: "MODEL", thPts: "PTS", thZero: "ZERO", playAgain: "PLAY AGAIN",
  campaign: "CAMPAIGN", average: "AVERAGE", vsZeroShort: "× ZERO GUESS", clearChanges: "CLEAR CHANGES", casesWord: "cases", traps: "TRAPS", disarmed: "disarmed",
  top5: "QUICK RUN · TOP 5", noRuns: "No completed runs yet.", byBiome: "BY BIOME", biome: "BIOME",
  stageMap: "STAGE MAP", pickState: "▶ PICK A STATE", stateCases: (n, k) => `${n.toUpperCase()} · ${k} CASE(S)`,
  mapAria: "Map of Brazil by state", ufAria: (n, k) => `${n}: ${k} cases`,
  legNew: "NEW", legPartial: "IN PROGRESS", legDone: "COMPLETE", legEmpty: "EMPTY", casesUf: (uf) => `CASES · ${uf}`, allCases: "ALL CASES",
  all: "ALL", allStates: "◀ ALL STATES", noFilter: "No cases match this filter.", wipeSave: "ERASE SAVE", wipeSaveAsk: "Erase your progress in this browser?",
  authorship: "AUTHORSHIP", dataLicenses: "DATA AND LICENSES", openSource: "Open source (MIT license):", statesMesh: "State boundaries: IBGE.",
  generated: (d, v) => `Data generated on ${d} · schema ${v}.`,
};

const DICT: Record<Lang, Dict> = { pt, en };
/** Textos no idioma atual. Em componente: `const T = $derived(L())`. */
export const L = (): Dict => DICT[i18n.lang];
