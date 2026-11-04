"""
Enriquecedor de Bases de Dados Fiscais, Tributarias e Contabeis da AURA.
scripts/enrich_fiscal_databases.py

Ingere no banco SQLite local (data/webposto_knowledge.db) o catalogo expandido de:
1. Rejeicoes SEFAZ de Varejo de Postos (Meios de Pagamento TEF/PIX, Grupo comb, Encerrantes e Contingencia)
2. Matriz de ICMS Monofasico de Combustiveis (LC 192/2022, Convenios CONFAZ 199/2022 e 15/2023, CST 61 vs 60)
3. Tabela 4.3.10 SPED EFD-Contribuicoes (PIS/COFINS Monofasico de Pista e Bebidas Frias da Conveniencia)
4. Guia Contabil SPED Fiscal (Registros 1300/1310/1320, LMC, CFOP 5927 para Perdas de Tanque alem de 0.6%)
5. Reforma Tributaria de Combustiveis (LC 214/2025, NT Conjunta 2024.002 / 2025.002 - IBS/CBS)

Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura.enrich_fiscal")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "webposto_knowledge.db"


def obter_catalogo_rejeicoes_expandido() -> List[Dict[str, Any]]:
    """Gera o lote estruturado de rejeicoes operacionais criticas de postos e conveniencia."""
    regras: List[Dict[str, Any]] = []

    # 1. Rejeicao 391: Dados do cartao/PIX obrigatorios
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-391",
        "modulo": "Faturamento Pista / TEF e Cartoes",
        "titulo": "Rejeicao 391: Nao informados os dados do cartao de credito / debito nas Formas de Pagamento",
        "subtitulo": "Regra YA04-10 / MOC 7.0 e NT 2023.004",
        "resumo_executivo": (
            "Rejeicao 391: Quando o pagamento for por cartao (credito tPag=03, debito tPag=04 ou PIX dinâmico tPag=17), "
            "e obrigatorio informar o grupo card com o tipo de integracao (tpIntegra). Ocorre frequentemente quando a "
            "configuracao de TEF ou POS no webPosto esta incompleta."
        ),
        "conteudo_completo": (
            "# Rejeicao 391: Nao informados os dados do cartao de credito / debito\n"
            "**Codigo SEFAZ:** 391\n"
            "**Modulo Operacional:** Faturamento de Pista / Formas de Pagamento\n"
            "**Impacto Financeiro:** Travamento no fechamento da venda na pista e bloqueio da emissao de NFC-e.\n\n"
            "## Diagnostico Tecnico\n"
            "Se informada forma de pagamento 03 (Cartao de Credito) ou 04 (Cartao de Debito), o grupo `card` deve ser\n"
            "preenchido obrigatoriamente com o campo `tpIntegra` (1=TEF Integrado ou 2=POS Nao Integrado).\n\n"
            "## Como Corrigir no webPosto\n"
            "1. No cadastro de Formas de Pagamento da retaguarda, edite as modalidades de Cartao e PIX.\n"
            "2. Certifique-se de que a flag 'Tipo de Integracao TEF' esteja preenchida como Integrado (TEF) ou POS Manual.\n"
            "3. Se for TEF dedicado, vincule a credenciadora correspondente (Rede, Cielo, Stone, Getnet, PagBank).\n"
        ),
        "tabelas_banco": "formas_pagamento, nfce, pedido",
        "impacto_financeiro": "Venda de pista travada no momento de emitir cupom para cliente no cartao.",
        "acao_recomendada": "Vincular o tipo de integracao (tpIntegra=1 ou 2) na forma de pagamento no webPosto.",
        "tags_busca": "rejeicao 391 cartao debito credito tpintegra tef pos pix pagamentos nfce",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-391", "tag": "pag/card/tpIntegra"}, ensure_ascii=False),
    })

    # 2. Rejeicao 392: Falta CNPJ da credenciadora em pagamento integrado
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-392",
        "modulo": "Faturamento Pista / TEF Integrado",
        "titulo": "Rejeicao 392: Nao informados os dados da operacao de pagamento integrado (tpIntegra=1)",
        "subtitulo": "Regra YA05-10 / NT 2023.004 e NT 2024.002",
        "resumo_executivo": (
            "Rejeicao 392: Pagamento declarado como TEF Integrado (tpIntegra=1), mas a credenciadora de cartao ou banco "
            "nao foi identificada no XML (falta CNPJ da adquirente ou bandeira tBand). Exigencia fiscal para combater evadimento de TEF."
        ),
        "conteudo_completo": (
            "# Rejeicao 392: Nao informados os dados da operacao de pagamento integrado\n"
            "**Codigo SEFAZ:** 392\n"
            "**Modulo Operacional:** Integracao TEF / Conciliacao de Cartoes\n"
            "**Impacto Financeiro:** Emissao de NFC-e bloqueada no TEF da pista.\n\n"
            "## Diagnostico Tecnico\n"
            "Quando `tpIntegra = 1`, o preenchimento de `card/CNPJ` (CNPJ da credenciadora) e `card/tBand` (Bandeira do cartao) "
            "e mandatorio pela SEFAZ. Se a DLL de TEF nao repassar os metadados ao webPosto, a nota e rejeitada.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. Acesse Configuracoes de PDV > Modulo TEF.\n"
            "2. Atualize o Driver de TEF (Sitef, D-TEF ou Linx TEF) para a versao homologada.\n"
            "3. No cadastro de Administradoras de Cartao, preencha o CNPJ exato da credenciadora (ex: Cielo 01.027.058/0001-91).\n"
        ),
        "tabelas_banco": "formas_pagamento, config_tef, nfce",
        "impacto_financeiro": "Travamento no fluxo de caixa da pista em transacoes TEF.",
        "acao_recomendada": "Preencher o CNPJ da adquirente e bandeira na configuracao de TEF do webPosto.",
        "tags_busca": "rejeicao 392 tef integrado tpintegra cnpj credenciadora adquirente bandeira tband",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-392", "tag": "card/CNPJ"}, ensure_ascii=False),
    })

    # 3. Rejeicao 462: Grupo comb obrigatorio para combustiveis
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-462",
        "modulo": "Cadastro de Combustiveis / Bicos",
        "titulo": "Rejeicao 462: Nao informado o grupo de combustivel para produto com codigo ANP regulado",
        "subtitulo": "Regra LA01-10 / MOC 7.0 e NT 2018.005",
        "resumo_executivo": (
            "Rejeicao 462: O produto vendido possui codigo de combustivel ou lubrificante, mas o XML foi gerado sem a tag comb. "
            "A SEFAZ exige que Gasolina, Etanol, Diesel, GNV, GLP e Biodiesel contenham o grupo comb com cProdANP e descANP."
        ),
        "conteudo_completo": (
            "# Rejeicao 462: Grupo de combustivel obrigatorio no XML\n"
            "**Codigo SEFAZ:** 462\n"
            "**Modulo Operacional:** Cadastro de Produtos / Pista\n"
            "**Impacto Financeiro:** Paralisacao do bico de abastecimento por rejeicao sistematica na emissao fiscal.\n\n"
            "## Diagnostico Tecnico\n"
            "Regra LA01-10: Para produtos cujo codigo ANP esteja regulamentado (ex: Gasolina 320102001, Diesel 820101034), "
            "e obrigatorio informar o no `<comb>` dentro do grupo `<prod>`.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. Acesse Cadastros > Produtos > Combustiveis.\n"
            "2. Localize o combustivel rejeitado e va na aba Fiscal / ANP.\n"
            "3. Verifique se o campo 'Classificacao ANP' esta preenchido e marcado como 'Produto Sujeito a Controle de Combustivel'.\n"
            "4. Salve e retransmita a venda da pista.\n"
        ),
        "tabelas_banco": "produto, combustivel, bico, nfce",
        "impacto_financeiro": "Bico de abastecimento rejeitando todos os cupons na pista.",
        "acao_recomendada": "Marcar o combustivel com controle ANP ativo no cadastro de produtos do webPosto.",
        "tags_busca": "rejeicao 462 grupo comb anp cprodanp descanp combustivel bico pista",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-462", "tag": "prod/comb"}, ensure_ascii=False),
    })

    # 4. Rejeicao 463: Codigo ANP inexistente
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-463",
        "modulo": "Cadastro de Combustiveis / ANP",
        "titulo": "Rejeicao 463: Codigo ANP informado inexistente na tabela oficial de produtos da ANP",
        "subtitulo": "Regra LA02-10 / MOC 7.0 e Tabelas ANP",
        "resumo_executivo": (
            "Rejeicao 463: O codigo ANP preenchido no cadastro do combustivel foi descontinuado ou digitado incorretamente. "
            "A SEFAZ confronta o campo cProdANP com a tabela publica oficial da Agencia Nacional do Petroleo."
        ),
        "conteudo_completo": (
            "# Rejeicao 463: Codigo ANP inexistente\n"
            "**Codigo SEFAZ:** 463\n"
            "**Modulo Operacional:** Cadastro Fiscal de Pista\n"
            "**Impacto Financeiro:** Bloqueio imediato na venda do combustivel.\n\n"
            "## Diagnostico Tecnico\n"
            "A SEFAZ valida o codigo `cProdANP` contra a relacao oficial da ANP. Codigos com zeros a esquerda ausentes "
            "ou codigos antigos de diesel revogados geram rejeicao imediata.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. No cadastro de produtos do webPosto, confira o codigo ANP com 9 digitos:\n"
            "   * Gasolina C Comum: 320102001\n"
            "   * Gasolina C Aditivada: 320102002\n"
            "   * Etanol Hidratado Comum: 810101001\n"
            "   * Oleo Diesel B S10 Comum: 820101034\n"
            "   * Oleo Diesel B S500 Comum: 820101033\n"
            "   * GLP (Botijao P13): 210203001\n"
            "2. Ajuste o codigo no webPosto e retransmita as notas pendentes.\n"
        ),
        "tabelas_banco": "combustivel, produto, nfce",
        "impacto_financeiro": "Travamento da emissao do produto na pista.",
        "acao_recomendada": "Corrigir o codigo ANP de 9 digitos no cadastro do produto no webPosto.",
        "tags_busca": "rejeicao 463 codigo anp inexistente cprodanp tabela anp gasolina diesel etanol",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-463", "tabela": "ANP_9_DIGITOS"}, ensure_ascii=False),
    })

    # 5. Rejeicao 760: Informado grupo de encerrante para operacao indevida
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-760",
        "modulo": "Automacao de Bicos / Encerrantes",
        "titulo": "Rejeicao 760: Informado grupo de encerrante para operacao que nao e NFC-e ou produto sem bico",
        "subtitulo": "Regra LA11-10 / MOC 7.0 e NT 2016.002",
        "resumo_executivo": (
            "Rejeicao 760: O grupo de encerrantes (nBico, nBomba, vEncIni, vEncFin) e exclusivo para operacoes de abastecimento "
            "em NFC-e na pista. Se for gerada uma NF-e de remessa ou venda de conveniencia com tag de encerrante, a SEFAZ rejeita."
        ),
        "conteudo_completo": (
            "# Rejeicao 760: Grupo de encerrante informado indevidamente\n"
            "**Codigo SEFAZ:** 760\n"
            "**Modulo Operacional:** Integracao Automacao de Bombas e Concentrador\n"
            "**Impacto Financeiro:** Erro de faturamento na retaguarda do posto.\n\n"
            "## Diagnostico Tecnico\n"
            "A tag `<encerrante>` so pode constar em NFC-e modelo 65 de abastecimento de combustivel liquido. Se o ERP tentar "
            "incluir encerrantes em NF-e modelo 55 de agrupamento de frota ou em produtos de conveniencia, ocorre a rejeicao.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. No Módulo de Automacao de Pista, certifique-se de que o concentrador (Companytec, EzTech, Horustec) "
            "vincule encerrantes exclusivamente a cupons de abastecimento de bicos fisicos.\n"
            "2. Ao emitir NF-e mod 55 de frota com CFOP 5929, o webPosto deve expurgar a tag encerrante do XML.\n"
        ),
        "tabelas_banco": "bico, concentrador, encerrante, nfce, nfe",
        "impacto_financeiro": "Rejeicao em faturamentos de notas consolidadas de frota.",
        "acao_recomendada": "Remover o grupo de encerrante em notas modelo 55 de faturamento agrupado.",
        "tags_busca": "rejeicao 760 encerrante nbico nbomba vencini vencfin concentrador automacao",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-760", "tag": "prod/comb/encerrante"}, ensure_ascii=False),
    })

    # 6. Rejeicao 855: Encerrante final menor que o inicial (Virada de Bico)
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-855",
        "modulo": "Automacao de Bicos / Concentrador",
        "titulo": "Rejeicao 855: Encerrante final menor que encerrante inicial (Virada de Relogio / Bico)",
        "subtitulo": "Regra LA11-30 / MOC 7.0 e NT 2016.002",
        "resumo_executivo": (
            "Rejeicao 855: A leitura do encerrante final do bico e numericamente inferior a leitura inicial. "
            "Ocorre quando o medidor da bomba zera (virada de milhao de 999.999,99 para 0,00) ou apos manutencao tecnica de bomba/bloco."
        ),
        "conteudo_completo": (
            "# Rejeicao 855: Encerrante final menor que encerrante inicial\n"
            "**Codigo SEFAZ:** 855\n"
            "**Modulo Operacional:** Automacao de Pista e Bombas\n"
            "**Impacto Financeiro:** Bico de abastecimento travado no concentrador, impedindo emissao de cupom na pista.\n\n"
            "## Diagnostico Tecnico\n"
            "A SEFAZ exige que `vEncFin >= vEncIni`. Quando a bomba estoura o limite fisico do totalizador e vira para zero, "
            "o envio simples dos numeros brutos gera Rejeicao 855 imediata.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. Acesse Pista > Automacao > Bicos de Abastecimento.\n"
            "2. Selecione o bico afetado e utilize a funcao 'Registrar Virada de Encerrante / Intervencao Tecnica'.\n"
            "3. O webPosto registrara o evento formal no LMC e ajustara a esteira de transmissao com o offset correto.\n"
        ),
        "tabelas_banco": "bico, bomba, encerrante, lmc_movimentacao",
        "impacto_financeiro": "Bico paralisado gerando fila de carros na pista sem conseguir emitir nota.",
        "acao_recomendada": "Registrar virada de relogio ou intervencao tecnica no cadastro do bico no webPosto.",
        "tags_busca": "rejeicao 855 encerrante virada bico relogio bomba concentrador manutencao",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-855", "condicao": "vEncFin < vEncIni"}, ensure_ascii=False),
    })

    # 7. Rejeicao 958: CFOP incompativel com ICMS Monofasico
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-958",
        "modulo": "Tributacao Monofasica / Combustiveis",
        "titulo": "Rejeicao 958: CFOP incompativel com tributacao monofasica sobre combustiveis",
        "subtitulo": "Regra N12-90 / NT 2023.001 v1.50 (LC 192/2022)",
        "resumo_executivo": (
            "Rejeicao 958: Uso de CFOP generico (como 5102) em operacao com combustivel monofasico (Diesel, Gasolina, GLP). "
            "A legislacao da LC 192/2022 exige a utilizacao de CFOPs especificos de combustiveis (ex: 5656, 5655 ou 5929)."
        ),
        "conteudo_completo": (
            "# Rejeicao 958: CFOP incompativel com tributacao monofasica de combustiveis\n"
            "**Codigo SEFAZ:** 958\n"
            "**Modulo Operacional:** Faturamento de Pista e Retaguarda\n"
            "**Impacto Financeiro:** Todas as notas de Diesel e Gasolina bloqueadas no faturamento.\n\n"
            "## Diagnostico Tecnico\n"
            "Com a entrada do ICMS Monofasico (CST 02, 15, 53, 61), a SEFAZ bloqueou a combinacao de combustiveis sujeitos "
            "ao regime monofasico com CFOPs genericos de revenda (ex: CFOP 5102 / 6102).\n\n"
            "## Como Corrigir no webPosto\n"
            "1. No cadastro do combustivel, aba Fiscal, altere o CFOP padrao de venda para 5.656 (Venda a consumidor final) "
            "ou 5.655 (Venda para frotistas/industrializacao).\n"
            "2. Para fechamento de notas de frota agrupadas com cupons, utilize o CFOP 5.929.\n"
        ),
        "tabelas_banco": "combustivel, produto, nfe, nfce",
        "impacto_financeiro": "Bloqueio em lote na transmissao de notas fiscais de combustivel.",
        "acao_recomendada": "Alterar o CFOP de venda de combustivel para 5656 ou 5655 no cadastro do webPosto.",
        "tags_busca": "rejeicao 958 cfop combustivel monofasico 5656 5655 5102 nt 2023001 lc 192",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-958", "cfop_correto": "5656, 5655, 5929"}, ensure_ascii=False),
    })

    # 8. Rejeicao 960: Nao informada tag de ICMS Monofasico para CST 61
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-960",
        "modulo": "Tributacao Monofasica / CST 61",
        "titulo": "Rejeicao 960: Obrigatoria a informacao do ICMS Monofasico retido anteriormente (CST 61)",
        "subtitulo": "Regra N12-110 / NT 2023.001 v1.50 (Convenios 199/2022 e 15/2023)",
        "resumo_executivo": (
            "Rejeicao 960: Nota emitida com CST 61 (Monofasico Cobrado Anteriormente), mas as tags obrigatorias "
            "qBCMonoRet, adRemICMSRet e vICMSMonoRet nao foram geradas no grupo ICMS61 do XML."
        ),
        "conteudo_completo": (
            "# Rejeicao 960: Falta de tags do ICMS Monofasico retido anteriormente (CST 61)\n"
            "**Codigo SEFAZ:** 960\n"
            "**Modulo Operacional:** Motor Fiscal de Combustiveis / Retaguarda\n"
            "**Impacto Financeiro:** Bloqueio em todas as vendas de Gasolina e Diesel no faturamento.\n\n"
            "## Diagnostico Tecnico\n"
            "O CST 61 exige o preenchimento da quantidade base em litros (`qBCMonoRet`), a aliquota ad rem vigente (`adRemICMSRet`) "
            "e o valor retido calculado (`vICMSMonoRet`). Se o ERP gerar apenas o CST sem essas tags, a SEFAZ rejeita.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. No webPosto versao 26.9+, certifique-se de que a tabela de Aliquotas Ad Rem COTEPE esteja atualizada no modulo fiscal.\n"
            "2. O sistema calculara automaticamente: vICMSMonoRet = qBCMonoRet * adRemICMSRet.\n"
            "3. Caso o cadastro esteja como CST 60 indevidamente, mude para CST 61 em Gasolina e Diesel.\n"
        ),
        "tabelas_banco": "combustivel, aliquotas_adrem, nfe, nfce",
        "impacto_financeiro": "Impossibilidade de emitir NF-e ou NFC-e de Gasolina e Diesel.",
        "acao_recomendada": "Atualizar tabela de aliquotas ad rem e preencher tags de ICMS61 no webPosto.",
        "tags_busca": "rejeicao 960 cst 61 qbcmonoret adremicmsret vicmsmonoret icms monofasico",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-960", "cst": "61"}, ensure_ascii=False),
    })

    # 9. Rejeicao 778: Informado NCM inexistente na TIPI
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-778",
        "modulo": "Cadastro de Produtos / Conveniencia",
        "titulo": "Rejeicao 778: Informado codigo NCM inexistente na tabela oficial da Receita Federal (TIPI)",
        "subtitulo": "Regra I05-20 / MOC 7.0 e Tabela NCM Siscomex",
        "resumo_executivo": (
            "Rejeicao 778: O produto cadastrado na conveniencia ou na pista possui um NCM que foi extinto ou digitado errado. "
            "A SEFAZ valida em tempo real se o NCM com 8 digitos existe na tabela da Receita Federal."
        ),
        "conteudo_completo": (
            "# Rejeicao 778: NCM inexistente na tabela oficial\n"
            "**Codigo SEFAZ:** 778\n"
            "**Modulo Operacional:** Loja de Conveniencia e Pista\n"
            "**Impacto Financeiro:** Caixa da conveniencia travado ao tentar registrar a compra de cliente.\n\n"
            "## Diagnostico Tecnico\n"
            "A Receita Federal altera periodicamente a Nomenclatura Comum do Mercosul (NCM) extinguindo codigos antigos e "
            "desdobrando em novos subitens. Produtos antigos mantidos no cadastro geram Rejeicao 778 imediata.\n\n"
            "## Como Corrigir no webPosto\n"
            "1. Localize o produto rejeitado em Cadastros > Produtos.\n"
            "2. Consulte a tabela NCM vigente ou verifique o XML da nota de compra do fornecedor.\n"
            "3. Altere o campo NCM com o codigo valido de 8 digitos e retransmita a venda.\n"
        ),
        "tabelas_banco": "produto, ncm, nfce",
        "impacto_financeiro": "Fila no caixa da loja de conveniencia e venda bloqueada.",
        "acao_recomendada": "Atualizar o NCM com 8 digitos vigente na Receita Federal no cadastro do webPosto.",
        "tags_busca": "rejeicao 778 ncm inexistente tipi siscomex conveniencia cadastro produto",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-778", "tamanho_ncm": 8}, ensure_ascii=False),
    })

    # 10. Rejeicao 806: Falta do codigo CEST para produto com ST
    regras.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SEFAZ-REJ-806",
        "modulo": "Cadastro Fiscal / ICMS-ST e CEST",
        "titulo": "Rejeicao 806: Operacao com ICMS-ST sem informacao do CEST correspondente",
        "subtitulo": "Regra N28-10 / Convenio ICMS 142/2018",
        "resumo_executivo": (
            "Rejeicao 806: O produto utiliza CST de Substituicao Tributaria (CST 10, 30, 60, 70 ou CSOSN 201, 202, 500), "
            "mas o Codigo Especificador da Substituicao Tributaria (CEST) nao foi informado no cadastro."
        ),
        "conteudo_completo": (
            "# Rejeicao 806: CEST obrigatorio nao informado\n"
            "**Codigo SEFAZ:** 806\n"
            "**Modulo Operacional:** Cadastro Fiscal de Conveniencia e Pista\n"
            "**Impacto Financeiro:** Venda bloqueada em produtos de alta rotatividade (bebidas, lubrificantes, filtros).\n\n"
            "## Diagnostico Tecnico\n"
            "O Convenio ICMS 142/2018 exige a informacao do campo `<CEST>` com 7 digitos para qualquer item cujo CST/CSOSN "
            "possua cobranca de ICMS-ST (anterior ou concomitante).\n\n"
            "## Como Corrigir no webPosto\n"
            "1. No cadastro de produtos do webPosto, informe o codigo CEST de 7 digitos de acordo com o segmento:\n"
            "   * Etanol Hidratado: CEST 06.004.00\n"
            "   * Oleos Lubrificantes: CEST 06.007.00\n"
            "   * Cervejas e Chopes: CEST 03.021.00\n"
            "   * Refrigerantes e Aguas: CEST 03.010.00 / 03.001.00\n"
            "2. Salve o cadastro e libere a nota retida.\n"
        ),
        "tabelas_banco": "produto, cest, nfce, nfe",
        "impacto_financeiro": "Travamento no PDV na venda de itens com Substituicao Tributaria.",
        "acao_recomendada": "Preencher o codigo CEST de 7 digitos no cadastro do produto no webPosto.",
        "tags_busca": "rejeicao 806 cest icms st convenio 1422018 substituicao tributaria conveniencia",
        "metadados_json": json.dumps({"regra": "SEFAZ-REJ-806", "tamanho_cest": 7}, ensure_ascii=False),
    })

    return regras


def obter_catalogo_tributario_contabil() -> List[Dict[str, Any]]:
    """Gera artigos aprofundados sobre SPED Fiscal, PIS/COFINS Monofasico e Reforma Tributaria."""
    artigos: List[Dict[str, Any]] = []

    # A. PIS/COFINS Monofasico na Loja de Conveniencia (Tabela 4.3.10)
    artigos.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SPED-CONTRIB-4.3.10-BEBIDAS",
        "modulo": "Auditoria de Impostos Federais / Conveniencia",
        "titulo": "PIS/COFINS Monofasico na Loja de Conveniencia: Bebidas Frias e Produtos com Aliquota Zero (CST 04)",
        "subtitulo": "Tabela 4.3.10 da EFD-Contribuicoes e Lei 13.097/2015",
        "resumo_executivo": (
            "Auditoria de Risco Tributario: Postos e Lojas de Conveniencia (mesmo no Simples Nacional) nao devem pagar PIS/COFINS "
            "sobre Bebidas Frias (cervejas, refrigerantes, aguas, energeticos) e cigarros. Se cadastrados com CST 01 ou nao "
            "segregados no PGDAS, o dono do posto paga tributo em duplicidade."
        ),
        "conteudo_completo": (
            "# PIS/COFINS Monofasico na Loja de Conveniencia (Tabela 4.3.10 SPED)\n"
            "**Modulo Operacional:** Cadastro Fiscal de Conveniencia e Fechamento Mensal\n"
            "**Impacto Financeiro:** Pagamento indevido de 3,65% a 9,25% de PIS/COFINS sobre o faturamento de bebidas.\n\n"
            "## Base Normativa\n"
            "Pela Lei 13.097/2015 e Lei 10.833/2003, a cobranca de PIS e COFINS sobre bebidas frias e concentrada no fabricante "
            "ou importador (regime monofasico). No varejo (conveniencia), a saida e desonerada com Aliquota Zero (CST 04).\n\n"
            "## NCMs Monofasicos Criticos na Conveniencia\n"
            "- 2201.10.00: Aguas minerais naturais ou gaseificadas (CEST 03.001.00)\n"
            "- 2202.10.00: Aguas com sabor, refrigerantes e chas prontos (CEST 03.010.00)\n"
            "- 2202.99.00: Energeticos e bebidas hidroeletroliticas / isotonicos (CEST 03.014.00)\n"
            "- 2203.00.00: Cervejas de malte e chopes (CEST 03.021.00)\n\n"
            "## Como Configurar no webPosto\n"
            "1. No cadastro dos itens de conveniencia, altere o CST de PIS e COFINS na saida para '04 - Operacao Tributavel Monofasica'.\n"
            "2. No fechamento fiscal, o relatorio de vendas segregara as receitas monofasicas para o contador abater no Simples ou EFD.\n"
        ),
        "tabelas_banco": "produto, ncm, tributacao_pis_cofins, vendas",
        "impacto_financeiro": "Economia tributaria direta de ate 5% do faturamento da loja de conveniencia.",
        "acao_recomendada": "Garantir CST 04 de PIS/COFINS em bebidas frias no cadastro de produtos do webPosto.",
        "tags_busca": "pis cofins monofasico conveniencia bebidas frias cerveja refrigerante agua cst 04 tabela 4310",
        "metadados_json": json.dumps({"regra": "SPED-4.3.10", "cst_saida": "04"}, ensure_ascii=False),
    })

    # B. SPED Fiscal Registros 1300, 1310 e 1320 (Movimentacao de Combustiveis / LMC)
    artigos.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SPED-FISCAL-REG-1300-LMC",
        "modulo": "SPED Fiscal EFD ICMS/IPI / Bloco 1",
        "titulo": "SPED Fiscal Bloco 1: Registros 1300, 1310 e 1320 (Movimentacao Diaria de Combustiveis e Bicos)",
        "subtitulo": "Guia Pratico da EFD ICMS/IPI e Portaria DNC 26/1992",
        "resumo_executivo": (
            "Escrituracao Oficial de Combustiveis: Os Registros 1300, 1310 e 1320 do SPED Fiscal constituem a versao digital do LMC. "
            "Divergencias entre os encerrantes faturados na NFC-e e a medicao de tanques no Registro 1310 geram malha fiscal imediata na SEFAZ."
        ),
        "conteudo_completo": (
            "# Registros 1300, 1310 e 1320 do SPED Fiscal (LMC Digital)\n"
            "**Modulo Operacional:** Fechamento Mensal / Geracao de Arquivo SPED EFD ICMS/IPI\n"
            "**Impacto Financeiro:** Multa de 1% a 5% do valor do estoque por omissao ou divergencia de escrituracao de tanques.\n\n"
            "## Anatomia dos Registros\n"
            "- **Registro 1300:** Consolidado diario por combustivel (Estoque de Abertura, Entradas, Vendas, Perdas, Estoque de Fechamento).\n"
            "- **Registro 1310:** Movimentacao fisica por Tanque (volume medido com regua ou telemetria vs volume escriturado).\n"
            "- **Registro 1320:** Movimentacao fisica por Bico de Abastecimento (bico, encerrante inicial, encerrante final, afericoes).\n\n"
            "## Regra de Conciliacao no webPosto\n"
            "1. O volume de vendas do Registro 1300 deve bater rigorosamente com a soma dos encerrantes liquidos do Registro 1320:\n"
            "   `Vendas Liquidas = (Encerrante Final - Encerrante Inicial) - Volume de Afericoes`\n"
            "2. O webPosto gera o arquivo SPED pronto com o confronto automatico entre a medicao de tanques e os cupons emitidos.\n"
        ),
        "tabelas_banco": "lmc_movimentacao, lmc_tanque, lmc_bico, sped_fiscal",
        "impacto_financeiro": "Bloqueio de inscricao estadual e autuacao por inconsistencia no LMC digital.",
        "acao_recomendada": "Conciliar encerrantes fisicos e medicao de tanques antes de exportar o SPED no webPosto.",
        "tags_busca": "sped fiscal registros 1300 1310 1320 lmc digital bloco 1 encerrantes bicos tanques",
        "metadados_json": json.dumps({"regra": "SPED-REG-1300", "bloco": "1"}, ensure_ascii=False),
    })

    # C. Tratamento Fiscal de Perdas e Evaporacao (CFOP 5927 e Limite ANP +-0.6%)
    artigos.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "SPED-FISCAL-CFOP-5927-PERDAS",
        "modulo": "Perdas Volumetricas / Baixa de Estoque",
        "titulo": "Tratamento Tributario de Perdas e Evaporacao de Combustiveis: Limite ANP 0.6% e Emissao com CFOP 5927",
        "subtitulo": "Resolucao ANP 884/2022 e Regulamentos de ICMS Estaduais",
        "resumo_executivo": (
            "Diretriz Fiscal de Perdas: Variacao volumetrica de ate +-0,6% e considerada perda natural fisica (evaporacao/temperatura). "
            "Perdas anormais que excedem -0,6% exigem emissao de NF-e de Baixa de Estoque com CFOP 5.927 e estorno do credito de ICMS correspondente."
        ),
        "conteudo_completo": (
            "# Tratamento Fiscal de Perdas e Evaporacao de Combustiveis\n"
            "**Modulo Operacional:** Controle de Tanques / Estoque Fiscal\n"
            "**Impacto Financeiro:** Risco de autuacao por omissao de saida ou aproveitamento indevido de credito fiscal.\n\n"
            "## O Limite Regulatorio da ANP\n"
            "A Portaria DNC 26/1992 e Resolucao ANP 884/2022 toleram variacao fisica de ate 0,6% sobre o volume movimentado.\n"
            "- **Perda Normal (ate 0.6%):** Apenas escriturada no LMC e no Registro 1300 do SPED. Nao exige nota fiscal.\n"
            "- **Perda Anormal (acima de 0.6%):** Exige apuracao de causa (vazamento, rompimento de valvula ou furto). Contabilmente,\n"
            "  deve ser emitida NF-e modelo 55 de baixa com **CFOP 5.927** (Lancamento efetuado a titulo de baixa de estoque).\n\n"
            "## Estorno de Credito de ICMS\n"
            "Para combustiveis sob regime que gerem credito ou em estados com previsao expressa, o ICMS relativo a parcela que exceder\n"
            "o limite natural deve ser estornado na apuracao do imposto.\n"
        ),
        "tabelas_banco": "tanque, lmc_movimentacao, nfe, estoque_ajuste",
        "impacto_financeiro": "Evita penalidade fiscal e regulariza o estoque escriturado do posto.",
        "acao_recomendada": "Emitir NF-e com CFOP 5927 para perdas superiores ao teto de 0.6% da ANP.",
        "tags_busca": "perdas tanque evaporacao anp limite 06 cfop 5927 baixa estoque lmc icms estorno",
        "metadados_json": json.dumps({"regra": "CFOP-5927", "limite_anp_pct": 0.6}, ensure_ascii=False),
    })

    # D. Reforma Tributaria (LC 214/2025 e NT Conjunta 2024.002 - IBS/CBS de Combustiveis)
    artigos.append({
        "pilar": "fiscal_tributario_sefaz",
        "codigo_ref": "REFORMA-TRIB-LC214-COMBUSTIVEIS",
        "modulo": "Reforma Tributaria / IBS e CBS 2026",
        "titulo": "Reforma Tributaria no Setor de Combustiveis: Regime Especifico Monofasico de IBS/CBS (LC 214/2025)",
        "subtitulo": "Emenda Constitucional 132/2023, LC 214/2025 e NT 2024.002 / 2025.002",
        "resumo_executivo": (
            "Reforma Tributaria 2026: Combustiveis (Gasolina, Etanol, Diesel, GLP, GNV) operarao sob Regime Especifico Monofasico "
            "com aliquotas ad rem (em reais por litro) uniformes nacionalmente. O posto na ponta nao pagara IBS/CBS sobre a venda de combustivel."
        ),
        "conteudo_completo": (
            "# Reforma Tributaria e o Regime Especifico de Combustiveis (IBS e CBS)\n"
            "**Modulo Operacional:** Planejamento Tributario e Transicao Fiscal 2026+\n"
            "**Impacto Financeiro:** Simplificacao da apuracao de combustiveis na pista e mudanca radical na conveniencia.\n\n"
            "## Como Funcionara para Combustiveis (Pista)\n"
            "A Lei Complementar 214/2025 (antigo PLP 68/2024) consolidou que a tributacao de combustiveis pelo IBS e CBS sera monofasica:\n"
            "1. Recolhimento concentrado no produtor (refinaria/usina) ou importador com valor fixo por litro (ad rem).\n"
            "2. O posto revendedor nao recolhe nem gera credito de IBS/CBS sobre as saidas de combustiveis ao consumidor final.\n"
            "3. O XML da NF-e/NFC-e adotara novos grupos de tributacao (`<IBSCBS>`) com codigo de classificacao tributaria `cClassTrib`.\n\n"
            "## Como Funcionara para a Loja de Conveniencia\n"
            "Produtos de conveniencia (alimentos, acessorios) seguirao a regra geral do IVA Dual:\n"
            "- Credito integral sobre compras e debito na venda ao consumidor.\n"
            "- Substituicao gradual do PIS/COFINS (a partir de 2027) e do ICMS/ISS (de 2029 a 2033).\n"
        ),
        "tabelas_banco": "tributacao_reforma, ibs_cbs, nfe, nfce",
        "impacto_financeiro": "Adequacao previa aos novos leiautes de nota fiscal e regimes da Reforma Tributaria.",
        "acao_recomendada": "Acompanhar homologacao dos grupos de IBS/CBS nas atualizacoes do webPosto versao 27+.",
        "tags_busca": "reforma tributaria lc 214 plp 68 ibs cbs monofasico combustiveis iva dual cclasstrib",
        "metadados_json": json.dumps({"regra": "REFORMA-LC214", "ano_inicio": 2026}, ensure_ascii=False),
    })

    return artigos


def executar_enriquecimento() -> int:
    """Executa a gravacao de todos os novos registros no banco local."""
    logger.info("Iniciando enriquecimento de bases fiscais no banco local: %s", DB_PATH)
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Banco nao localizado em: {DB_PATH}")

    registros = obter_catalogo_rejeicoes_expandido()
    registros.extend(obter_catalogo_tributario_contabil())

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode = WAL;")

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

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tabela_conhecimento WHERE pilar = 'fiscal_tributario_sefaz'")
    total_fiscal = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tabela_conhecimento")
    total_geral = cur.fetchone()[0]
    conn.close()

    logger.info("Enriquecimento concluido com sucesso!")
    logger.info("Novos registros adicionados/atualizados: %d", len(registros))
    logger.info("Total de regras fiscais no banco: %d. Total geral no banco: %d", total_fiscal, total_geral)
    return len(registros)


if __name__ == "__main__":
    executar_enriquecimento()
