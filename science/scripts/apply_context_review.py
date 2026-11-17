"""Revisão das afirmações de CONTEXTO (nomes, história, eventos) — 2026-11-13.
Cada afirmação traz o veredito, o porquê e fontes verificadas (HTTP 200 conferido).
Grava data/catalog/context_claims.json e corrige nomes/textos em qa_decisions.json
(name_override / explanation). Afirmações sem fonte saíram do texto do jogo e ficam
registradas como "corrigido"/"removido" para o jogador ver o que mudou e por quê."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WDPA = lambda sid, n: {"nome": f"Protected Planet / WDPA — {n}", "url": f"https://www.protectedplanet.net/{sid}"}
S = {
    "cemaden": {"nome": "Cemaden — Nota Técnica nº 679/2024: Análise das Secas no Brasil",
                "url": "https://www.semadesc.ms.gov.br/wp-content/uploads/2024/12/NotaTcnicaHistricodeSecasnoBrasileProjecoes_2024_CEMADEN_202411.pdf"},
    "brumadinho": {"nome": "Governo de Minas Gerais — Histórico do rompimento das barragens da Vale na Mina Córrego do Feijão",
                   "url": "https://www.mg.gov.br/pro-brumadinho/pagina/historico-do-rompimento-das-barragens-da-vale-na-mina-corrego-do-feijao"},
    "brumadinho_wiki": {"nome": "Wikipedia — Brumadinho dam disaster (coordenadas da mina)", "url": "https://en.wikipedia.org/wiki/Brumadinho_dam_disaster"},
    "samarco": {"nome": "Ministério Público Federal — Caso Samarco: o desastre", "url": "https://www.mpf.mp.br/grandes-casos/caso-samarco/o-desastre"},
    "bento_wiki": {"nome": "Wikipedia — Bento Rodrigues (coordenadas)", "url": "https://pt.wikipedia.org/wiki/Bento_Rodrigues"},
    "fapesp_pantanal": {"nome": "Agência FAPESP (29/08/2023) — Em 2020, grandes incêndios queimaram 30% do Pantanal",
                        "url": "https://agencia.fapesp.br/em-2020-grandes-incendios-queimaram-30-do-pantanal/44693"},
    "matopiba": {"nome": "Embrapa — Proposta de Delimitação Territorial do MATOPIBA (Nota Técnica GITE 1, lista de municípios p. 18)",
                 "url": "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1037313/1/NT1DelimitacaoMatopiba.pdf"},
    "serido": {"nome": "Embrapa — trabalho sobre o Núcleo de Desertificação do Seridó (cita Carnaúba dos Dantas)",
               "url": "https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1015492/1/V2P41.pdf"},
    "caatinga": {"nome": "Embrapa Semiárido — fenologia de espécies da Caatinga (caducifólias)",
                 "url": "https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1083575/1/Magna7.pdf"},
    "lavrado": {"nome": "Embrapa Roraima — sistemas de produção (áreas de lavrado)",
                "url": "https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/68108/1/RoraimaSistemasProducao-19728.pdf"},
    "qf": {"nome": "Revista Gestão & Regionalidade (USCS) — O Quadrilátero Ferrífero de Minas Gerais (cita Nova Lima)",
           "url": "https://seer.uscs.edu.br/index.php/revista_gestao/article/download/8476/4329?inline=1"},
    "trincheira_wiki": {"nome": "Wikipedia — Trincheira/Bacajá Indigenous Territory",
                        "url": "https://en.wikipedia.org/wiki/Trincheira/Bacaj%C3%A1_Indigenous_Territory"},
    "ducke": {"nome": "INPA/PPBio — Reserva Florestal Adolpho Ducke (e-book)", "url": "https://ppbio.inpa.gov.br/sites/default/files/RFAD_ebook.pdf"},
    "pituacu": {"nome": "INEMA/Governo da Bahia — Parque Metropolitano de Pituaçu",
                "url": "https://www.ba.gov.br/inema/2024/10/obras-de-requalificacao-do-parque-metropolitano-de-pituacu-comecam-em-dezembro"},
    "osm": lambda t, i, n: {"nome": f"OpenStreetMap — {n}", "url": f"https://www.openstreetmap.org/{t}/{i}"},
}
C = lambda a, v, p, f: {"afirmacao": a, "veredito": v, "porque": p, "fontes": f}
osm = S["osm"]

CLAIMS = {
 "AMZ-01": [C("Versão anterior: 'desmatamento ao longo da BR-163'.", "corrigido",
              "O centro do recorte fica a cerca de 19 km a oeste da sede de Novo Progresso; não conferimos que o recorte esteja no eixo da rodovia, então o nome da estrada saiu. O que é certo: 96% da floresta perdida virou pastagem (mapa 10 m).", [])],
 "AMZ-03": [C("A Amazônia teve uma seca severa em 2023–24.", "comprovado",
              "O Cemaden lista 2023–24 entre as secas mais severas da Amazônia e a seca mais extensa da série histórica no Brasil. A imagem 'depois' é de julho de 2024. A cor mais amarelada do pasto combina com isso, mas a imagem sozinha não prova a causa.", [S["cemaden"]])],
 "CAA-02": [C("Versão anterior: o nome dizia 'Parque Nacional da Serra da Capivara'.", "corrigido",
              "Pela base WDPA, o parque fica a menos de 1 km, mas fora do recorte (0% de área em comum). O nome agora diz 'entorno'.", [WDPA(64, "PARNA Serra da Capivara")])],
 "CAA-03": [C("Carnaúba dos Dantas faz parte do Núcleo de Desertificação do Seridó.", "comprovado",
              "Trabalho publicado pela Embrapa lista Carnaúba dos Dantas entre os municípios do núcleo.", [S["serido"]]),
            C("Na seca a Caatinga perde as folhas, mas continua nativa.", "comprovado",
              "A Embrapa Semiárido descreve as espécies estudadas como caducifólias: perdem as folhas no período seco.", [S["caatinga"]])],
 "CAP-AM": [C("O recorte fica na borda da Reserva Florestal Adolpho Ducke.", "comprovado",
              "A reserva é do INPA e não aparece na base WDPA. Pelo OpenStreetMap, o centro do recorte cai dentro do retângulo da reserva.",
              [S["ducke"], osm("way", 161393396, "Reserva Florestal Adolpho Ducke")])],
 "CAP-AP": [C("Versão anterior: 'obras viárias e loteamentos sobre áreas de ressaca'.", "corrigido",
              "Não conferimos 'obras viárias' nem 'loteamentos'. O que os mapas mostram é que 93% da vegetação perdida virou área urbanizada.", [])],
 "CAP-BA": [C("O recorte fica no Parque Metropolitano de Pituaçu.", "comprovado",
              "O parque é gerido pelo INEMA e não aparece na base WDPA. Pelo OpenStreetMap, o centro do recorte cai dentro dos limites do parque (a 1,2 km do ponto central dele).",
              [S["pituacu"], osm("way", 29204845, "Parque Metropolitano de Pituaçu")])],
 "CAP-ES": [C("Versão anterior: 'a maré muda a cor da água'.", "corrigido",
              "Não conferimos a maré na hora de cada imagem. O texto agora diz só que a cor da água mudou.", [])],
 "CAP-MA": [C("O recorte fica perto do Porto do Itaqui.", "comprovado",
              "Pelo OpenStreetMap, o porto fica a cerca de 2,8 km do centro do recorte.",
              [osm("relation", 10189309, "Porto do Itaqui")])],
 "CAP-MG": [C("Versão anterior: o nome dizia 'Serra do Curral'.", "corrigido",
              "O centro do recorte fica em Nova Lima (IBGE). Não conferimos se ele está na própria Serra do Curral, então o nome agora traz só o município.", [])],
 "CAP-MS": [C("O recorte fica no Parque dos Poderes, que inclui o Parque Estadual do Prosa.", "comprovado",
              "Pelo OpenStreetMap, o centro está a 0,4 km do Parque dos Poderes. Pela base WDPA, o Parque Estadual do Prosa (2002) cobre 22% do recorte.",
              [osm("relation", 6196851, "Parque dos Poderes")])],
 "CAP-PA": [C("Versão anterior: 'os lagos mudam de cor com as algas'.", "removido",
              "Não temos medida de algas, então a explicação saiu. O texto diz só que a cor da água muda.", [])],
 "CAP-PB": [C("Versão anterior: 'uma das maiores florestas urbanas do país'.", "removido",
              "Não achamos fonte oficial para esse ranking, então ele saiu. Pela base WDPA, o Refúgio de Vida Silvestre Mata do Buraquinho cobre 41% do recorte.", [])],
 "CAP-PI": [C("Versão anterior: 'loteamentos e terraplanagem'.", "corrigido",
              "Agora o texto usa só o que os mapas mostram: 77% da vegetação perdida virou área urbanizada e 13% virou solo exposto.", [])],
 "CAP-RO": [C("A perda de floresta aconteceu dentro da Terra Indígena Karipuna.", "comprovado",
              "Pela base WDPA, a TI Karipuna cobre 60% do recorte. Os dois mapas MapBiomas mostram perda de floresta para pastagem.", [])],
 "CAP-RR": [C("Lavrado é o nome regional das savanas naturais de Roraima.", "comprovado",
              "A Embrapa Roraima chama de 'lavrado' as áreas de pastagem natural (savana) do estado. O aeroporto fica a 0,6 km do centro do recorte (OpenStreetMap).",
              [S["lavrado"], osm("way", 321933284, "Aeroporto Internacional de Boa Vista")])],
 "CAP-RS": [C("Versão anterior: 'o rio muda de cor com o sedimento'.", "corrigido",
              "Não medimos sedimento. O texto agora diz só que a cor da água muda.", [])],
 "CAP-SC": [C("Versão anterior: o nome dizia 'Parque Estadual do Rio Vermelho'.", "corrigido",
              "Pela base WDPA, quem cobre o recorte é o Refúgio de Vida Silvestre Municipal Meiembipe (40%). O Parque Estadual do Rio Vermelho fica a menos de 1 km, mas fora do recorte.", [])],
 "CAP-SP": [C("Versão anterior: 'terraplanagem para ocupação perto da Billings'.", "corrigido",
              "Agora o texto usa os mapas: a vegetação perdida virou mosaico de usos (69%) e solo exposto (21%). Pela base WDPA, a APA Bororé-Colônia cobre 95% do recorte.", [])],
 "CAP-TO": [C("Versão anterior: o nome dizia 'expansão de Taquaralto'.", "corrigido",
              "Não confirmamos que o recorte fica no bairro Taquaralto, então o nome mudou.", [])],
 "CER-02": [C("Formosa do Rio Preto (BA) faz parte do MATOPIBA.", "comprovado",
              "O município está na lista de municípios da delimitação oficial da Embrapa (p. 18).", [S["matopiba"]]),
            C("Versão anterior: 'convertido em lavoura mecanizada em grande escala'.", "corrigido",
              "O mapa 10 m classifica a área aberta como mosaico de usos. O mapa 30 m mostra soja (18%) e outras lavouras temporárias (13%) em parte dela. O texto agora diz exatamente isso.", [])],
 "CMP-01": [C("Barragens da mina Córrego do Feijão (Vale) se romperam em 25/01/2019.", "comprovado",
              "Pelo Governo de Minas Gerais, a barragem B-I rompeu às 12h28 e levou junto a B-IV e a B-IV-A. A lama desceu pelo Ribeirão Ferro-Carvão até o rio Paraopeba.", [S["brumadinho"]]),
            C("Este recorte fica no entorno da mina, fora do caminho da lama.", "comprovado",
              "O centro do recorte fica a cerca de 3,4 km a leste-sudeste do ponto da mina. A lama desceu para oeste, rumo ao rio Paraopeba.",
              [S["brumadinho_wiki"], S["brumadinho"]])],
 "CMP-02": [C("O recorte fica dentro da Terra Indígena Trincheira/Bacajá.", "comprovado",
              "Pela base WDPA, a TI cobre 100% do recorte. Ela se estende por São Félix do Xingu, Altamira, Anapu e Senador José Porfírio.",
              [S["trincheira_wiki"]])],
 "CMP-04": [C("A barragem de Fundão (Samarco) rompeu em 05/11/2015 e soterrou Bento Rodrigues.", "comprovado",
              "Pelo MPF, a onda de rejeitos soterrou boa parte de Bento Rodrigues e desceu pelo rio Gualaxo do Norte. O centro do recorte fica a cerca de 0,5 km das coordenadas do distrito.",
              [S["samarco"], S["bento_wiki"]])],
 "CMP-05": [C("A mancha clara de 2024 é área queimada.", "comprovado",
              "O MapBiomas Fogo marca 40% do recorte como queimado em 2024. Pela base WDPA, o recorte fica no Parque Nacional do Araguaia e na TI Inawebohona (Ilha do Bananal).", [])],
 "GAN-05": [C("Versão anterior: o nome dizia 'Cerrado (GO/DF)'.", "corrigido",
              "O centro do recorte fica em Vila Boa (GO), pela malha do IBGE.", [])],
 "GAN-10": [C("Versão anterior: o nome dizia 'Vale do Paraíba (SP/RJ)'.", "corrigido",
              "O centro do recorte fica em Mangaratiba (RJ), pela malha do IBGE, que não é Vale do Paraíba. O ganho de vegetação também foi pequeno demais para chamar o caso de 'ganho nativo'.", [])],
 "MAT-01": [C("Versão anterior: o nome dizia 'regeneração em pastagens'.", "corrigido",
              "Os mapas mostram só um ganho pequeno; o caso é praticamente estável. O nome foi ajustado.", [])],
 "MAT-02": [C("Nova Lima é município minerador do Quadrilátero Ferrífero.", "comprovado",
              "Um estudo acadêmico sobre o Quadrilátero Ferrífero lista Nova Lima entre os municípios com minas de ferro. Os dois mapas MapBiomas mostram a vegetação perdida virando mineração (56%) e solo exposto.", [S["qf"]])],
 "PAM-02": [C("Versão anterior: o nome dizia 'silvicultura'.", "corrigido",
              "A silvicultura no recorte é pequena (9→11% no mapa 10 m) e quase não mudou. O nome agora não destaca o plantio.", [])],
 "PAN-01": [C("Em 2020 grandes incêndios queimaram o Pantanal.", "comprovado",
              "Estudo do INPE divulgado pela FAPESP: os incêndios de 2020 queimaram cerca de 30% do Pantanal brasileiro. O MapBiomas Fogo marca 88% deste recorte queimado em 2020 (a imagem 'antes' é de 23/09/2020).", [S["fapesp_pantanal"]]),
            C("Versão anterior: o nome dizia 'Parque Estadual Encontro das Águas'.", "corrigido",
              "Pela base WDPA, o parque fica a 17 km do recorte, então o nome agora traz só o município (Poconé).", [WDPA(555576191, "PE Encontro das Águas")])],
 "PAN-03": [C("Versão anterior: o nome dizia 'fogo de 2024'.", "corrigido",
              "O MapBiomas Fogo marca 0% queimado em 2024 e 96% em 2020, então o nome do ano estava errado. Pela base WDPA, a RPPN Acurizal e Penha cobre 73% do recorte.", [])],
 "XTR-T04": [C("Versão anterior: 'virou um eucaliptal'.", "corrigido",
               "Os mapas dizem 'silvicultura' (árvores plantadas), sem dizer qual espécie. 'Eucalipto' saiu do texto.", [])],
}

NAMES = {
 "AMZ-01": "Novo Progresso – floresta e pasto",
 "CAA-02": "Entorno do Parque Nacional da Serra da Capivara",
 "CAP-AP": "Macapá – expansão urbana",
 "CAP-MA": "São Luís – arredores do Porto do Itaqui",
 "CAP-MG": "Nova Lima – franja urbana",
 "CAP-RO": "Porto Velho – Terra Indígena Karipuna",
 "CAP-SC": "Florianópolis – Refúgio Meiembipe / Rio Vermelho",
 "CAP-TO": "Palmas – periferia sul",
 "CMP-01": "Brumadinho – entorno da mina Córrego do Feijão",
 "CMP-02": "Terra Indígena Trincheira/Bacajá",
 "GAN-05": "Vila Boa – cerrado em regeneração",
 "GAN-10": "Mangaratiba – matas e pastos de morro",
 "MAT-01": "São Luiz do Paraitinga – matas e pastos de morro",
 "PAM-02": "Encruzilhada do Sul – lavouras, pastos e matas",
 "PAN-01": "Poconé – Pantanal depois do fogo de 2020",
 "PAN-03": "Serra do Amolar – RPPN Acurizal",
}

TEXTS = {
 "AMZ-01": "Novo Progresso (PA): a floresta contínua de 2020 foi aberta em clareiras até 2024. Os dois mapas MapBiomas mostram que quase toda a floresta perdida virou pastagem.",
 "AMZ-03": "Armadilha da seca: em 2024 o pasto aparece mais amarelado (2023–24 teve seca severa na Amazônia, segundo o Cemaden), mas a floresta nativa não mudou de tamanho.",
 "CAP-AP": "Macapá: a cidade avançou sobre vegetação nativa da periferia. Os dois mapas MapBiomas mostram a perda, quase toda para área urbanizada.",
 "CAP-ES": "Manguezal da Ilha do Lameirão, em Vitória: a cor da água muda entre as datas, mas o mangue ficou estável.",
 "CAP-MA": "Perto do Porto do Itaqui, em São Luís: a ocupação já estava lá em 2020. A mata em volta perdeu só pequenos trechos até 2024 — quase tudo o que você vê ficou igual.",
 "CAP-PA": "Parque Estadual do Utinga, em Belém: a cor dos lagos muda entre as datas, mas a floresta ao redor se manteve.",
 "CAP-PB": "Mata do Buraquinho, floresta protegida no meio de João Pessoa. Entre 2020 e 2025 a borda com os bairros praticamente não se moveu.",
 "CAP-PI": "Teresina: a cidade avançou sobre a vegetação nativa; os mapas mostram a perda virando área urbanizada e solo exposto.",
 "CAP-RO": "Dentro da Terra Indígena Karipuna, grandes áreas de floresta amazônica viraram pastagem entre 2020 e 2024: os dois mapas MapBiomas concordam em cerca de 45 pontos percentuais de perda.",
 "CAP-RR": "Perto do aeroporto de Boa Vista, áreas de lavrado foram abertas — o lavrado é a savana nativa de Roraima, que parece capim e não floresta. Nem toda vegetação nativa é mata!",
 "CAP-RS": "Delta do Jacuí, em Porto Alegre: a cor do rio muda entre as datas, mas as matas e banhados ficaram estáveis.",
 "CAP-SP": "Parelheiros, extremo sul de São Paulo, dentro da APA Bororé-Colônia: trechos de mata viraram mosaico de usos e solo exposto.",
 "CER-02": "MATOPIBA, oeste da Bahia: o cerrado nativo foi aberto para uso agropecuário. O mapa de 30 m já reconhece soja e outras lavouras em parte da área.",
 "CMP-01": "Brumadinho, perto da mina Córrego do Feijão, onde barragens da Vale se romperam em 2019. A lama desceu para o outro lado (oeste); neste recorte a vegetação nativa quase não mudou entre 2020 e 2024.",
 "CMP-02": "Terra Indígena Trincheira/Bacajá (São Félix do Xingu/PA): uma clareira nova foi aberta na floresta e virou pasto.",
 "CMP-05": "Ilha do Bananal: a mancha clara de 2024 é área queimada (MapBiomas Fogo). Fogo e seca mudam a cor, mas a vegetação continua nativa.",
 "XTR-T04": "ARMADILHA! O pasto de 2020 virou um plantio fechado de árvores (silvicultura) em 2025. Ficou muito mais verde, mas árvore plantada não é vegetação nativa: a mudança de nativa aqui é praticamente zero.",
}


def main():
    (ROOT / "data/catalog/context_claims.json").write_text(json.dumps(CLAIMS, indent=1, ensure_ascii=False), encoding="utf-8")
    qp = ROOT / "data/catalog/qa_decisions.json"
    qa = json.loads(qp.read_text(encoding="utf-8"))
    for cid, n in NAMES.items():
        qa.setdefault(cid, {})["name_override"] = n
    for cid, t in TEXTS.items():
        qa.setdefault(cid, {})["explanation"] = t
    qp.write_text(json.dumps(qa, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(CLAIMS), "casos com afirmações de contexto;", len(NAMES), "nomes e", len(TEXTS), "textos corrigidos")


if __name__ == "__main__":
    main()
