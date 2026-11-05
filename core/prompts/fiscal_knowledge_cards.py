"""
Catalogo Canonico de Fichas Tecnicas Fiscais (Micro-SOPs de Verdade Minima).
Fornece grounding deterministico e regras fiscais inquestionaveis para modelos SLM/Flash.
Cobre CST 61 (ICMS Monofasico), CST 04 (PIS/COFINS Monofasico na Conveniencia),
Rejeicoes SEFAZ criticas e regras de postos de combustiveis.
Regra inegociavel: ZERO travessoes em todo o modulo.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Biblioteca Canonica de Fichas Fiscais (Micro-SOPs)
FISCAL_KNOWLEDGE_CARDS: Dict[str, Dict[str, Any]] = {
    "cst_61_icms_monofasico": {
        "id": "cst_61_icms_monofasico",
        "titulo": "ICMS Monofasico sobre Combustiveis (CST 61)",
        "base_legal": "Lei Complementar 192/2022 e Convenios ICMS 15/2023 (Gasolina/Etanol) e 199/2022 (Diesel/GLP)",
        "aplicabilidade": "Gasolina Comum/Aditivada, Diesel S10/S500, Biodiesel B100 e GLP/GLGN",
        "regra_revenda_posto": (
            "Aliquota ad rem fixa por litro recolhida na refinaria ou importador (substituto tributario). "
            "Na revenda varejista no posto para o consumidor final, a aliquota própria de ICMS e ZERO. "
            "O XML deve conter o grupo ICMS61 com qBCMonoRet, adRemICMSRet e vICMSMonoRet devidamente preenchidos."
        ),
        "cfop_padrao": "5656 (venda de combustivel para consumidor final) ou 5655 (venda para frota/industrializacao)",
        "cfops_proibidos": "5102 e 6102 (provocam Rejeicao 958 imediata da SEFAZ)",
        "pontos_criticos": [
            "Rejeicao 960 SEFAZ: Falta das tags obrigatorias qBCMonoRet (litros), adRemICMSRet (aliquota COTEPE) ou vICMSMonoRet no grupo ICMS61.",
            "Rejeicao 958 SEFAZ: Uso de CFOP generico de revenda (ex: 5102) em combustivel monofasico, exigindo alteracao para CFOP 5656 ou 5655.",
            "Rejeicao 959 SEFAZ: Divergencia matematica no calculo (vICMSMonoRet != qBCMonoRet * adRemICMSRet com tolerancia ABNT NBR 5891).",
            "Escrituracao SPED Fiscal: Campos de ICMS Monofasico nos registros 1300 e 1310 (LMC) e C113 para cupons vinculados a NF-e 55.",
        ],
        "acao_recomendada_erp": (
            "1. No cadastro de combustiveis, aba Fiscal, definir CST 61 e CFOP 5656. "
            "2. No modulo fiscal, certificar-se de que a tabela de aliquotas ad rem COTEPE esteja preenchida."
        ),
        "tags_busca": [
            "cst 61",
            "icms monofasico",
            "combustivel monofasico",
            "gasolina monofasica",
            "diesel monofasico",
            "lc 192",
            "rejeicao 960",
            "rejeicao 958",
            "rejeicao 959",
            "qbcmonoret",
            "adremicmsret",
            "vicmsmonoret",
        ],
    },
    "cst_04_pis_cofins_conveniencia": {
        "id": "cst_04_pis_cofins_conveniencia",
        "titulo": "PIS/COFINS Monofasico na Loja de Conveniencia (CST 04)",
        "base_legal": "Lei 13.097/2015 (art. 14 a 36), Lei 10.833/2003 e Tabela 4.3.10 da EFD-Contribuicoes",
        "aplicabilidade": (
            "Bebidas Frias (cervejas NCM 2203, refrigerantes NCM 2202.10, aguas minerais NCM 2201.10, "
            "energeticos e isotonicos NCM 2202.99) e Cigarros (NCM 2402)"
        ),
        "regra_revenda_posto": (
            "Tributacao de PIS e COFINS concentrada no fabricante ou importador. "
            "Na revenda varejista na loja de conveniencia, a saida e desonerada com Aliquota Zero "
            "(CST 04 de PIS e CST 04 de COFINS na saida)."
        ),
        "cfop_padrao": "5102 (venda de mercadoria adquirida de terceiros dentro do estado)",
        "pontos_criticos": [
            "Risco de Bitributacao no Simples Nacional (PGDAS): Se cadastrados com CST 01 ou nao segregados no PGDAS, o posto paga de 3,65% a 9,25% de tributos federais em duplicidade sobre as bebidas vendidas.",
            "Rejeicao 806 SEFAZ: Falta do codigo CEST obrigatorio para NCMs monofasicos de bebidas frias (ex: CEST 03.001.00 para agua, 03.010.00 para refrigerante, 03.021.00 para cerveja).",
            "Lucro Presumido e Lucro Real: Na EFD-Contribuicoes, saidas com CST 04 devem ser segregadas no Bloco M (M200/M600), garantindo exclusao da base de calculo de PIS e COFINS.",
        ],
        "acao_recomendada_erp": (
            "1. No cadastro de itens da conveniencia, alterar CST de PIS e COFINS para 04 em todas as bebidas frias. "
            "2. Preencher o CEST obrigatorio em cada NCM. "
            "3. Configurar relatorio de vendas com segregacao de receitas monofasicas para envio mensal a contabilidade."
        ),
        "tags_busca": [
            "cst 04",
            "pis cofins monofasico",
            "conveniencia monofasico",
            "bebidas frias",
            "cerveja",
            "refrigerante",
            "agua mineral",
            "tabela 4.3.10",
            "tabela 4310",
            "lei 13097",
            "bitributacao",
            "pgdas",
            "rejeicao 806",
            "cest",
        ],
    },
    "rejeicoes_sefaz_criticas_posto": {
        "id": "rejeicoes_sefaz_criticas_posto",
        "titulo": "Catalogo de Rejeicoes SEFAZ Criticas em Postos de Combustiveis",
        "base_legal": "Manual de Orientacao do Contribuinte (MOC 7.0) e Notas Tecnicas SEFAZ (NT 2023.001, NT 2020.005)",
        "aplicabilidade": "Emissao de NF-e (Modelo 55) e NFC-e (Modelo 65) no PDV e Retaguarda",
        "rejeicoes": [
            {
                "codigo": "960",
                "motivo": "Obrigatoria a informacao do ICMS Monofasico retido anteriormente (CST 61).",
                "causa": "Tags qBCMonoRet, adRemICMSRet ou vICMSMonoRet ausentes no XML de combustivel.",
                "solucao": "Atualizar tabela de aliquotas ad rem no ERP e emitir com grupo ICMS61 completo.",
            },
            {
                "codigo": "958",
                "motivo": "CFOP incompativel com tributacao monofasica de combustiveis.",
                "causa": "Uso de CFOP generico 5102 ou 6102 em produto sujeito a LC 192.",
                "solucao": "Alterar CFOP para 5656 (consumidor final) ou 5655 (frotista).",
            },
            {
                "codigo": "806",
                "motivo": "Operacao com combustivel ou mercadoria sem preenchimento do CEST obrigatorio.",
                "causa": "Tag CEST vazia em produto sujeito a substituicao tributaria ou monofasia.",
                "solucao": "Cadastrar codigo CEST correspondente ao NCM do produto no seu ERP.",
            },
            {
                "codigo": "375",
                "motivo": "NF-e com cupom fiscal referenciado com modelo incorreto.",
                "causa": "Chave de NFC-e (modelo 65) referenciada no campo refNFe em vez de refNFC.",
                "solucao": "No fechamento de fatura de frota, referenciar cupom na aba correta (refNFC).",
            },
            {
                "codigo": "805",
                "motivo": "Destinatario com informacao de IE incompativel.",
                "causa": "indIEDest = 2 (isento) em UF que veda isencao para pessoa fisica.",
                "solucao": "Alterar indIEDest para 9 (nao contribuinte) no cadastro do cliente.",
            },
            {
                "codigo": "508",
                "motivo": "CST incompativel na operacao com nao contribuinte.",
                "causa": "Combinacao inadequada de CST e modalidade de faturamento.",
                "solucao": "Ajustar CST e regime de tributacao no modulo de vendas.",
            },
        ],
        "pontos_criticos": [
            "Rejeicao em lote bloqueia faturamento na pista e trava fechamento de notas de frotistas.",
            "Rejeicao 375 e 958 sao as causas mais frequentes de bloqueio de notas agrupadas (CFOP 5929).",
        ],
        "acao_recomendada_erp": "Identificar o codigo de 3 digitos no log da SEFAZ e ajustar o cadastro do produto ou do cliente.",
        "tags_busca": [
            "rejeicao sefaz",
            "erro sefaz",
            "rejeicao 960",
            "rejeicao 958",
            "rejeicao 806",
            "rejeicao 375",
            "rejeicao 805",
            "rejeicao 508",
            "nota travada",
            "nota bloqueada",
        ],
    },
    "difal_combustiveis": {
        "id": "difal_combustiveis",
        "titulo": "DIFAL (Diferencial de Aliquotas) em Operacoes com Combustiveis",
        "base_legal": "Art. 155, § 2º, inciso X, alinea 'b' da CF/88 e Lei Complementar 190/2022",
        "aplicabilidade": "Vendas interestaduais de combustiveis e suprimento de frotas",
        "regra_revenda_posto": (
            "Nas operacoes interestaduais com derivados de petroleo (gasolina e diesel), NAO ha cobranca de ICMS "
            "na origem e NAO se aplica o DIFAL convencional da EC 87/2015. O imposto pertence 100% ao estado onde "
            "ocorrer o consumo. Com o regime monofasico da LC 192/2022, a partilha ad rem e recolhida na refinaria."
        ),
        "pontos_criticos": [
            "Nao calcular DIFAL de consumo em notas de saida de gasolina ou diesel para frotistas de outros estados.",
            "Para lubrificantes derivados de petroleo, aplicar a regra especifica de substituicao tributaria interestadual.",
        ],
        "acao_recomendada_erp": "Desmarcar aplicacao automatica de DIFAL para NCMs de combustiveis derivados de petroleo.",
        "tags_busca": [
            "difal",
            "diferencial de aliquota",
            "venda interestadual",
            "frota interestadual",
            "partilha icms",
            "imposto interestadual",
        ],
    },
    "reforma_tributaria_combustiveis": {
        "id": "reforma_tributaria_combustiveis",
        "titulo": "Reforma Tributaria e Regime Monofasico de Combustiveis (LC 214)",
        "base_legal": "Lei Complementar 214/2025 e Emenda Constitucional 132/2023",
        "aplicabilidade": "Transicao tributaria para IBS (estados/municipios) e CBS (Uniao)",
        "regra_revenda_posto": (
            "Os combustiveis continuarao sob regime monofasico no novo sistema tributario: "
            "IBS e CBS serao cobrados uma unica vez na producao ou importacao com aliquotas ad rem (fixas por litro). "
            "Na revenda no posto de combustivel, a aliquota de IBS e CBS sera ZERO, com proibicao de apropriacao de creditos "
            "na entrada e desoneracao na saida ao consumidor."
        ),
        "pontos_criticos": [
            "Periodo de transicao a partir de 2026 com teste de aliquotas de CBS (0,9%) e IBS (0,1%).",
            "Manutencao da simplificacao monofasica para o varejo de combustiveis.",
        ],
        "acao_recomendada_erp": "Manter modulo fiscal atualizado para novas regras de validacao de IBS e CBS no XML.",
        "tags_busca": [
            "reforma tributaria",
            "lc 214",
            "ibs",
            "cbs",
            "transicao tributaria",
            "iva dual",
        ],
    },
}


def obter_card_fiscal(chave_ou_termo: str) -> Optional[Dict[str, Any]]:
    """Recupera um cartao fiscal diretamente pela chave identificadora."""
    chave_norm = (chave_ou_termo or "").strip().lower()
    return FISCAL_KNOWLEDGE_CARDS.get(chave_norm)


def obter_todos_cards_relevantes(query: str) -> List[Dict[str, Any]]:
    """
    Identifica todos os cartoes fiscais relevantes para uma pergunta livre do usuario.
    Retorna lista de cartoes ordenados pela quantidade e peso dos termos correspondentes.
    """
    q_norm = (query or "").lower().strip()
    if not q_norm:
        return []

    scores: List[Tuple[int, Dict[str, Any]]] = []

    for card_id, card in FISCAL_KNOWLEDGE_CARDS.items():
        score = 0
        tags = card.get("tags_busca") or []
        for tag in tags:
            tag_clean = tag.lower().strip()
            if tag_clean in q_norm:
                # Termos especificos como 'cst 61', 'cst 04', 'rejeicao 960' recebem peso 3
                if re.search(r"\b(cst\s*\d+|rejei[cç][aã]o\s*\d+|lc\s*\d+|tabela\s*[\d.]+)\b", tag_clean):
                    score += 3
                else:
                    score += 1

        if score > 0:
            scores.append((score, card))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scores]


def formatar_fichas_para_prompt(query: str, max_cards: int = 3) -> str:
    """
    Formata os cartoes fiscais relevantes em bloco compacto de Grounding (Micro-SOP)
    para injecao direta no prompt da LLM (Gemini Flash ou SLM local).
    """
    cards = obter_todos_cards_relevantes(query)
    if not cards:
        # Fallback para os 2 cartoes mais fundamentais de postos
        cards = [
            FISCAL_KNOWLEDGE_CARDS["cst_61_icms_monofasico"],
            FISCAL_KNOWLEDGE_CARDS["cst_04_pis_cofins_conveniencia"],
        ]

    cards_selecionados = cards[:max_cards]

    linhas = [
        "### [GROUNDING FISCAL DETERMINISTICO - VERDADE MINIMA GARANTIDA]",
        "Abaixo estao as regras tributarias canonicas inegociaveis para fundamentar a resposta ao operador:",
        "",
    ]

    for c in cards_selecionados:
        linhas.append(f"#### Ficha: {c.get('titulo')}")
        linhas.append(f"- **Base Legal:** {c.get('base_legal')}")
        linhas.append(f"- **Aplicabilidade:** {c.get('aplicabilidade')}")
        linhas.append(f"- **Regra de Varejo no Posto:** {c.get('regra_revenda_posto')}")
        if c.get("cfop_padrao"):
            linhas.append(f"- **CFOP Padrao:** {c.get('cfop_padrao')}")
        if c.get("cfops_proibidos"):
            linhas.append(f"- **CFOPs Proibidos:** {c.get('cfops_proibidos')}")

        pontos = c.get("pontos_criticos") or []
        if pontos:
            linhas.append("- **Pontos Criticos & Rejeicoes:**")
            for p in pontos:
                linhas.append(f"  * {p}")

        if c.get("rejeicoes"):
            linhas.append("- **Rejeicoes SEFAZ Relacionadas:**")
            for r in c.get("rejeicoes", []):
                linhas.append(f"  * Rej {r.get('codigo')}: {r.get('motivo')} -> Solucao: {r.get('solucao')}")

        if c.get("acao_recomendada_erp"):
            linhas.append(f"- **Acao Corretiva no seu ERP:** {c.get('acao_recomendada_erp')}")
        linhas.append("")

    linhas.append("Diretiva: Responda diretamente com base nestas fichas tecnicas. NUNCA mencione tanques de combustivel ou estoque de pista quando a duvida for fiscal/tributaria.")
    return "\n".join(linhas)
