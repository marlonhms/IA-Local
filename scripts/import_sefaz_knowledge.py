"""
Importador de Conhecimento Fiscal e Rejeicoes SEFAZ para o RAG Local da AURA.
Extrai diretamente do projeto Agent Sefaz (knowledge_base/rejeicoes/rejeicoes_sefaz.json)
e injeta no banco SQLite local (data/webposto_knowledge.db) como o 5o Pilar:
'fiscal_tributario_sefaz'.

Inclui regras criticas para postos de combustiveis e webPosto:
- Rejeicao 375 vs 701: CFOP 5929/6929 e referenciamento de NFC-e (mod 65) vs SPED C113
- Rejeicao 629: Multiplicacao qCom * vUnCom em bicos e combustiveis fracionados (ABNT NBR 5891)
- Rejeicao 531: Total de produtos difere do somatorio dos itens (Regra W07-10)
- Rejeicao 535: Total da NF-e difere do somatorio das parcelas (Regra W16-10)
- Rejeicoes 694, 695, 697, 698: DIFAL interestadual e excecoes de codigos ANP
- Rejeicoes 508, 529, 600, 805: Cadastro B2B/Frota, indIEDest e UFs que vedam Isento
- Rejeicoes 760, 381, 385: CST e CSOSN com ICMS-ST indevido na NFC-e de pista
- Regra SEFAZ-VAL-NEG: Bloqueio de valores negativos de cupons de apps no ACBr

Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura.import_sefaz")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "webposto_knowledge.db"

AGENT_SEFAZ_DIR = PROJECT_ROOT.parent / "Ferramentas" / "Agent Sefaz"
REJEICOES_JSON_PATH = AGENT_SEFAZ_DIR / "knowledge_base" / "rejeicoes" / "rejeicoes_sefaz.json"


def carregar_catalogo_rejeicoes() -> Dict[str, Any]:
    """Carrega o catalogo de rejeicoes estruturado do Agent Sefaz."""
    if not REJEICOES_JSON_PATH.exists():
        raise FileNotFoundError(f"Catalogo de rejeicoes nao encontrado em: {REJEICOES_JSON_PATH}")

    with open(REJEICOES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def enriquecer_contexto_posto(codigo: str, rej_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriquece a rejeicao com contexto operacional de postos de combustiveis e webPosto.
    Garante foco executivo: impacto financeiro, tela do webPosto e acao corretiva.
    """
    titulo = rej_data.get("titulo", "")
    descricao = rej_data.get("descricao", "")
    na_pratica = rej_data.get("na_pratica", "")
    como_corrigir = rej_data.get("como_corrigir", "")
    embasamento = rej_data.get("embasamento_legal", [])
    campos = rej_data.get("campos_afetados", [])
    excecoes = rej_data.get("excecoes", [])

    modulo = "Fiscal / SEFAZ"
    tabelas_banco = "nfce, nfe, pedido"
    impacto_financeiro = "Nota fiscal rejeitada na SEFAZ. Faturamento travado ou risco de penalidade tributaria."
    acao_recomendada = como_corrigir or "Revisar dados cadastrais e fiscais no webPosto."

    if codigo == "375":
        modulo = "Faturamento Frota / NF-e 55"
        titulo = "Rejeicao 375: NF-e com lancamento relativo a Cupom Fiscal referencia uma NFC-e (Regra I08-180)"
        impacto_financeiro = "Faturamento de frota e fechamento de clientes mensalistas bloqueados na transmissao a SEFAZ."
        acao_recomendada = (
            "No webPosto versao 26.9+, a referencia formal a NFC-e (mod 65) em NFref foi removida do XML "
            "e transferida para as Informacoes Complementares (infCpl). Se o seu posto emite em estados onde a "
            "regra entrou em vigor, certifique-se de que as chaves estejam em infCpl ou emita NF-e original própria."
        )
        tabelas_banco = "nfe, nfce, pedido, cliente"

    elif codigo == "701":
        modulo = "Faturamento Frota / SPED Fiscal"
        titulo = "Alerta Fiscal 701: Nao informado documento fiscal referenciado em CFOP 5929/6929 (Regra BA02)"
        impacto_financeiro = "Risco de rejeicao em UFs com validacao ativa (MG, RS, MT, BA) e divergencia no SPED Fiscal (Registro C113)."
        acao_recomendada = (
            "Em estados que exigem amarração de cupons na NF-e de faturamento, a ausencia de NFref gera rejeicao 701. "
            "Alinhar com a contabilidade a escrituracao do Registro C113 no SPED quando as chaves constarem apenas em infCpl."
        )
        tabelas_banco = "nfe, nfce, sped_c113"

    elif codigo == "805":
        modulo = "Cadastro de Clientes / Frota"
        titulo = "Rejeicao 805: A SEFAZ do destinatario nao permite Contribuinte Isento de IE"
        impacto_financeiro = "Faturamento para cliente B2B rejeitado. Venda a prazo ou faturamento bloqueado."
        acao_recomendada = (
            "UFs como SP, MG, BA, CE, GO, MS, MT, PA, PE, RN, SE nao aceitam indIEDest=2 (Isento) a menos que "
            "haja destaque de ICMS-ST. No cadastro de clientes do webPosto, altere o indicador para 1 (com IE informada) "
            "ou 9 (Nao Contribuinte)."
        )
        tabelas_banco = "cliente, nfe"

    elif codigo == "508":
        modulo = "Cadastro e Tributacao / ICMS"
        titulo = "Rejeicao 508: CST incompativel na operacao com Nao Contribuinte (indIEDest=9)"
        impacto_financeiro = "Rejeicao imediata ao tentar emitir nota para cliente cadastrado como Nao Contribuinte."
        acao_recomendada = (
            "Em vendas para Nao Contribuinte (indIEDest=9), a SEFAZ aceita apenas CSTs 00, 20, 40, 41 ou 60. "
            "Verificar a regra de tributacao do produto no webPosto e o cadastro do destinatario."
        )
        tabelas_banco = "produtos, cliente, nfe"

    elif codigo == "600":
        modulo = "Simples Nacional / Tributacao"
        titulo = "Rejeicao 600: CSOSN incompativel na operacao com Nao Contribuinte (indIEDest=9)"
        impacto_financeiro = "Postos ou conveniencias no Simples Nacional com emissao travada."
        acao_recomendada = (
            "Para emitente do Simples Nacional vendendo para Nao Contribuinte, sao permitidos apenas CSOSN "
            "102, 103, 300, 400 ou 500. Ajustar a tributacao da classe de produtos no webPosto."
        )
        tabelas_banco = "produtos, cliente, nfce"

    elif codigo in ("694", "695", "697", "698"):
        modulo = "DIFAL / Combustivel Interestadual"
        titulo = f"Rejeicao {codigo}: Regras de ICMS Interestadual e Partilha DIFAL (EC 87/2015)"
        impacto_financeiro = "Venda interestadual de combustiveis ou produtos de conveniencia travada por erro de aliquota ou partilha."
        acao_recomendada = (
            "Atencao para a excecao de combustiveis: derivados de petroleo nao entram no grupo ICMSUFDest "
            "pois possuem tributacao monofasica e regime proprio. Etanol (ANP 810101001), biodiesel e lubrificantes "
            "devem seguir a regra especifica de aliquotas interestaduais (4% importados, 7% ou 12% por regiao)."
        )
        tabelas_banco = "produtos, nfe, combustiveis"

    elif codigo == "760":
        modulo = "NFC-e Pista / CST Proibido"
        titulo = "Rejeicao 760: Item com CST indevido na NFC-e (Modelo 65)"
        impacto_financeiro = "Bomba ou PDV travado ao tentar emitir cupom fiscal na pista."
        acao_recomendada = (
            "NFC-e de pista aceita exclusivamente CSTs 00, 20, 40, 41 e 60 (90 a criterio da UF). "
            "Se o produto estiver com CST 10, 30 ou 70 no webPosto, altere o cadastro fiscal para CST 60 (ST cobrado anteriormente)."
        )
        tabelas_banco = "produtos, bicos, nfce"

    elif codigo == "778":
        modulo = "Cadastro de Produtos / NCM"
        titulo = "Rejeicao 778: Informado NCM inexistente na tabela oficial MDIC/Receita Federal"
        impacto_financeiro = "Item bloqueia o fechamento do caixa no PDV ate que o NCM seja corrigido."
        acao_recomendada = (
            "Consultar a tabela NCM vigente e atualizar o cadastro do item no webPosto antes de reenviar a nota."
        )
        tabelas_banco = "produtos, nfce"

    resumo_executivo = (
        f"{titulo}. "
        f"Impacto: {impacto_financeiro} "
        f"Acao no webPosto: {acao_recomendada}"
    )

    linhas_conteudo = [
        f"# {titulo}",
        f"**Codigo SEFAZ:** {codigo}",
        f"**Modulo Operacional:** {modulo}",
        f"**Impacto Financeiro:** {impacto_financeiro}",
        "",
        "## Diagnostico Tecnico",
        descricao,
        "",
        "## Regra na Pratica",
        na_pratica if na_pratica else "Validacao deterministica conforme especificacao tecnica SEFAZ MOC 7.0.",
        "",
        "## Como Corrigir no webPosto",
        acao_recomendada,
        "",
        "## Embasamento Legal e Normativo",
    ]
    for b in embasamento:
        linhas_conteudo.append(f"- {b}")

    if campos:
        linhas_conteudo.append("")
        linhas_conteudo.append("## Campos e Tags XML Afetados")
        for c in campos:
            linhas_conteudo.append(f"- `{c}`")

    if excecoes:
        linhas_conteudo.append("")
        linhas_conteudo.append("## Excecoes Legais Previstas")
        for e in excecoes:
            linhas_conteudo.append(f"- {e}")

    conteudo_completo = "\n".join(linhas_conteudo)

    tags_lista = [
        f"rejeicao {codigo}",
        f"sefaz {codigo}",
        f"erro {codigo}",
        modulo.lower(),
        "nfe",
        "nfce",
        "fiscal",
        "tributario",
    ]
    for p in titulo.lower().split():
        if len(p) >= 4 and p not in tags_lista:
            tags_lista.append(p)

    return {
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": f"SEFAZ-REJ-{codigo}",
        "modulo": modulo,
        "titulo": titulo,
        "subtitulo": f"Regra SEFAZ Rejeicao {codigo} - MOC 7.0 / NTs",
        "resumo_executivo": resumo_executivo,
        "conteudo_completo": conteudo_completo,
        "tabelas_banco": tabelas_banco,
        "impacto_financeiro": impacto_financeiro,
        "acao_recomendada": acao_recomendada,
        "tags_busca": " ".join(tags_lista),
        "metadados_json": json.dumps(rej_data, ensure_ascii=False),
    }


def obter_regras_matematicas_adicionais() -> List[Dict[str, Any]]:
    """Gera regras estruturadas para Rejeicoes 629, 531, 535 e Schema ACBr."""
    regras = []

    # Rejeicao 629
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-629",
        "modulo": "Pista e Bombas / Arredondamento ABNT",
        "titulo": "Rejeicao 629: Valor do Produto difere de Quantidade vezes Valor Unitario (Regra I08-10)",
        "subtitulo": "MOC 7.0 Anexo I - Regra I08-10 / ABNT NBR 5891:2014",
        "resumo_executivo": (
            "No bico de abastecimento ou item vendido, a quantidade multiplicada pelo preco unitario "
            "diverge do total do item informado em vProd por mais de R$ 0,01. Ocorre frequentemente "
            "em abastecimentos fracionados de bomba com 3 casas decimais de litros. A SEFAZ exige estrita "
            "obediencia a norma ABNT NBR 5891:2014 (ROUND_HALF_UP)."
        ),
        "conteudo_completo": (
            "# Rejeicao 629: Valor do Produto difere de Quantidade vezes Valor Unitario\n"
            "**Codigo da Regra:** SEFAZ-REJ-629 (Regra I08-10)\n"
            "**Modulo Operacional:** Automacao de Pista, Bicos e PDV\n"
            "**Impacto Financeiro:** Bloqueio imediato na autorizacao da NFC-e/NF-e de abastecimento.\n\n"
            "## Diagnostico Tecnico\n"
            "A multiplicacao qCom * vUnCom deve ser igual ao valor informado na tag <vProd>, tolerando diferenca "
            "maxima de R$ 0,01 decorrente de arredondamento conforme a norma ABNT NBR 5891:2014.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. Ajustar a tag <vProd> para coincidir com qCom * vUnCom arredondado com ROUND_HALF_UP.\n"
            "2. Verificar se o preco por litro configurado no bico possui mais de 3 casas decimais.\n"
            "3. Recalcular os totalizadores do cabecalho (vProd e vNF) para evitar rejeicao em cascata (531 e 535).\n\n"
            "## Embasamento Legal\n"
            "- Manual de Orientacao do Contribuinte (MOC) 7.0 - Anexo I - Regra I08-10\n"
            "- ABNT NBR 5891:2014 - Regras de Arredondamento na Numeracao Decimal\n"
        ),
        "tabelas_banco": "abastecimentos, nfce, bicos, produtos",
        "impacto_financeiro": "Bloqueio na autorizacao do cupom ou nota de abastecimento na pista.",
        "acao_recomendada": "Ajustar vProd para coincidir com qCom * vUnCom conforme ABNT NBR 5891:2014 com tolerancia de R$ 0,01.",
        "tags_busca": "rejeicao 629 multiplicacao quantidade valor unitario abnt nbr 5891 arredondamento bicos fracionado",
        "metadados_json": json.dumps({"regra_id": "SEFAZ-I08-10", "codigo": "629"}, ensure_ascii=False),
    })

    # Rejeicao 531
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-531",
        "modulo": "Totais da Nota / Cabecalho",
        "titulo": "Rejeicao 531: Total do Valor dos Produtos difere do somatorio dos itens (Regra W07-10)",
        "subtitulo": "MOC 7.0 Anexo I - Regra W07-10",
        "resumo_executivo": (
            "O somatorio dos campos vProd dos itens da nota nao coincide com o total informado no cabecalho "
            "<total><ICMSTot><vProd>. Ocorre frequentemente quando um item e corrigido ou sofre desconto e os "
            "totalizadores da nota nao sao recalculados (efeito cascata)."
        ),
        "conteudo_completo": (
            "# Rejeicao 531: Total do Valor dos Produtos difere do somatorio dos itens\n"
            "**Codigo da Regra:** SEFAZ-REJ-531 (Regra W07-10)\n"
            "**Modulo Operacional:** Fechamento e Totais de Documento Fiscal\n"
            "**Impacto Financeiro:** Rejeicao impeditiva da NF-e/NFC-e na SEFAZ.\n\n"
            "## Diagnostico Tecnico\n"
            "O campo totalizador <vProd> deve ser exatamente a soma de todos os <vProd> dos itens onde indTot=1.\n\n"
            "## Como Corrigir no webPosto\n"
            "Recalcular o totalizador <vProd> no grupo ICMSTot do XML para igualar a soma exata dos itens.\n"
        ),
        "tabelas_banco": "nfce, nfe, pedido",
        "impacto_financeiro": "Rejeicao da nota por divergencia nos totalizadores de produtos.",
        "acao_recomendada": "Ajustar a tag total/ICMSTot/vProd para coincidir com a soma exata dos itens.",
        "tags_busca": "rejeicao 531 total produtos somatorio itens w07-10 totalizadores icmstot",
        "metadados_json": json.dumps({"regra_id": "SEFAZ-W07-10", "codigo": "531"}, ensure_ascii=False),
    })

    # Rejeicao 535
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-535",
        "modulo": "Totais da Nota / Valor Total vNF",
        "titulo": "Rejeicao 535: Total da NF-e difere do somatorio dos valores que compoem o total (Regra W16-10)",
        "subtitulo": "MOC 7.0 Anexo I - Regra W16-10",
        "resumo_executivo": (
            "O valor total da nota fiscal (<vNF>) nao confere com a soma dos produtos menos descontos "
            "mais adicionais (frete, seguro, outras despesas, ICMS-ST). Causa bloqueio no faturamento."
        ),
        "conteudo_completo": (
            "# Rejeicao 535: Total da NF-e difere do somatorio das parcelas\n"
            "**Codigo da Regra:** SEFAZ-REJ-535 (Regra W16-10)\n"
            "**Modulo Operacional:** Totais Gerais de NF-e\n"
            "**Impacto Financeiro:** Bloqueio na emissao de notas de faturamento.\n\n"
            "## Diagnostico Tecnico\n"
            "A composicao oficial do vNF exige: vProd - vDesc - vICMSDeson + vST + vFrete + vSeg + vOutro + ... == vNF.\n\n"
            "## Como Corrigir no webPosto\n"
            "Ajustar a tag <vNF> no cabecalho para refletir com exatidao a composicao das parcelas financeiras.\n"
        ),
        "tabelas_banco": "nfe, nfce, pedido",
        "impacto_financeiro": "Nota rejeitada por incoerencia no valor total a pagar.",
        "acao_recomendada": "Ajustar o total <vNF> para coincidir com a soma exata das parcelas.",
        "tags_busca": "rejeicao 535 total nfe vnf composicao soma parcelas frete seguro desconto",
        "metadados_json": json.dumps({"regra_id": "SEFAZ-W16-10", "codigo": "535"}, ensure_ascii=False),
    })

    # Falha de Schema / Valor Negativo
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-VAL-NEG",
        "modulo": "Validacao de Schema / ACBr",
        "titulo": "Falha de Schema (XSD): Valor Monetario Negativo Proibido no XML (ACBr / TDec_1302)",
        "subtitulo": "MOC 7.0 Tipos Basicos / Schemas PL_009",
        "resumo_executivo": (
            "Valores monetarios negativos sao estritamente proibidos em qualquer tag da NF-e/NFC-e. "
            "Descontos e abatimentos de vouchers de aplicativos devem ser somados no campo de Desconto (vDesc), "
            "nunca como despesa ou acrescimo negativo (vOutro). Causa travamento no ACBr."
        ),
        "conteudo_completo": (
            "# Falha de Schema (XSD): Valor Monetario Negativo Proibido no XML\n"
            "**Codigo da Regra:** SEFAZ-VAL-NEG\n"
            "**Modulo Operacional:** Integracao PDV e Componente Fiscal ACBr\n"
            "**Impacto Financeiro:** Bloqueio local imediato no PDV do posto ('Falha na validacao dos dados da nota').\n\n"
            "## Diagnostico Tecnico\n"
            "No padrao SEFAZ, campos monetarios pertencem ao tipo TDec_1302 com pattern sem sinal de menos (-).\n"
            "Se o sistema de PDV gerar `<vOutro>-5.00</vOutro>` para registrar um voucher ou cashback, o componente\n"
            "ACBr rejeita o XML antes do envio para a SEFAZ.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. Zerar o campo vOutro.\n"
            "2. Ratear o desconto do aplicativo proporcionalmente entre os itens no campo vDesc.\n"
        ),
        "tabelas_banco": "nfce, pedido, formas_pagamento",
        "impacto_financeiro": "Travamento no PDV no momento do pagamento de abastecimento com app.",
        "acao_recomendada": "Lancar cupons e abatimentos no campo vDesc (Desconto), nunca em vOutro negativo.",
        "tags_busca": "valor negativo schema xsd acbr voutro vdesc cupom voucher app abastecimento",
        "metadados_json": json.dumps({"regra": "SEFAZ-VAL-NEG", "tipo": "TDec_1302"}, ensure_ascii=False),
    })

    return regras


def registrar_rejeicoes_no_banco(conn: sqlite3.Connection, registros: List[Dict[str, Any]]) -> int:
    """Insere ou atualiza os registros fiscais na tabela_conhecimento."""
    query = """
        INSERT INTO tabela_conhecimento (
            pilar, codigo_ref, modulo, titulo, subtitulo,
            resumo_executivo, conteudo_completo, tabelas_banco,
            impacto_financeiro, acao_recomendada, tags_busca, metadados_json
        ) VALUES (
            :pilar, :codigo_ref, :modulo, :titulo, :subtitulo,
            :resumo_executivo, :conteudo_completo, :tabelas_banco,
            :impacto_financeiro, :acao_recomendada, :tags_busca, :metadados_json
        )
        ON CONFLICT(codigo_ref) DO UPDATE SET
            pilar = excluded.pilar,
            modulo = excluded.modulo,
            titulo = excluded.titulo,
            subtitulo = excluded.subtitulo,
            resumo_executivo = excluded.resumo_executivo,
            conteudo_completo = excluded.conteudo_completo,
            tabelas_banco = excluded.tabelas_banco,
            impacto_financeiro = excluded.impacto_financeiro,
            acao_recomendada = excluded.acao_recomendada,
            tags_busca = excluded.tags_busca,
            metadados_json = excluded.metadados_json;
    """

    with conn:
        cursor = conn.cursor()
        for r in registros:
            cursor.execute(query, r)
        count = len(registros)

    return count


def executar_ingestao_sefaz() -> int:
    """Executa o pipeline completo de ingestao do conhecimento fiscal SEFAZ."""
    logger.info("Iniciando ingestao de conhecimento fiscal do Agent Sefaz...")
    cat = carregar_catalogo_rejeicoes()
    rejeicoes = cat.get("rejeicoes", {})
    logger.info("Catalogo lido com sucesso: %d rejeicoes encontradas.", len(rejeicoes))

    registros: List[Dict[str, Any]] = []
    for codigo, r_data in rejeicoes.items():
        reg = enriquecer_contexto_posto(codigo, r_data)
        registros.append(reg)

    # Injetar regras matematicas e de schema adicionais (629, 531, 535, VAL-NEG)
    regras_adicionais = obter_regras_matematicas_adicionais()
    registros.extend(regras_adicionais)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode = WAL;")
    total_gravados = registrar_rejeicoes_no_banco(conn, registros)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tabela_conhecimento")
    total_banco = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tabela_conhecimento WHERE pilar = 'fiscal_tributario_sefaz'")
    total_sefaz = cur.fetchone()[0]
    conn.close()

    logger.info("Ingestao concluida: %d regras SEFAZ gravadas.", total_gravados)
    logger.info("Total de regras fiscais no banco: %d. Total geral no banco: %d registros.", total_sefaz, total_banco)
    return total_gravados


if __name__ == "__main__":
    executar_ingestao_sefaz()
