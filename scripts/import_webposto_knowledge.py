"""
Curador e Ingestor de Conhecimento Estruturado do webPosto para o RAG Local da AURA.
Extrai diretamente dos arquivos locais do Sentinel / RAG WP (sem Docker, sem nuvem, sem conexoes externas):
1. 911 paginas oficiais do Confluence e Hubs de Modulos (Manuais e Procedimentos do webPosto)
2. Dicionario Semantico de Regras e Flags do Banco (Zero Alucinacao SQL)
3. Traducao de Incidentes de Pista para Dinheiro Travado (Diagnosticos Executivos)
4. Catalogo de Endpoints OpenAPI para Expansao Multi-Posto (153 rotas)

Armazena em SQLite local com indice FTS5 (data/webposto_knowledge.db) para busca instantanea sub-milissegundo.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Caminhos do projeto
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "webposto_knowledge.db"

# Diretorios padrao de origem do RAG WP
SOURCE_ROOT_CANDIDATES = [
    Path(r"C:\Users\Marlon\Documents\RAG WP"),
    Path(r"G:\Projetos\RAG WP"),
    Path(r"C:\Users\Marlon\Desktop\RAG WP"),
]


def localizar_raiz_rag_wp() -> Path:
    for cand in SOURCE_ROOT_CANDIDATES:
        if cand.exists() and (cand / "quality-rag").exists():
            return cand
    raise FileNotFoundError("Diretorio de origem do RAG WP nao localizado nos caminhos padrao.")


def inicializar_banco_dados(db_file: Path) -> sqlite3.Connection:
    """Cria tabela relacional e tabela virtual FTS5 para busca em portugues."""
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tabela_conhecimento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pilar TEXT NOT NULL,
                codigo_ref TEXT NOT NULL UNIQUE,
                modulo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                subtitulo TEXT,
                resumo_executivo TEXT NOT NULL,
                conteudo_completo TEXT NOT NULL,
                tabelas_banco TEXT,
                impacto_financeiro TEXT,
                acao_recomendada TEXT,
                tags_busca TEXT,
                metadados_json TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conhecimento_pilar_modulo 
            ON tabela_conhecimento (pilar, modulo);
        """)

        # Tabela FTS5 para busca full-text com ranking BM25
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS conhecimento_fts USING fts5(
                codigo_ref,
                pilar,
                modulo,
                titulo,
                subtitulo,
                resumo_executivo,
                conteudo_completo,
                tabelas_banco,
                impacto_financeiro,
                tags_busca,
                content='tabela_conhecimento',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            );
        """)

        # Triggers de sincronizacao automatica com FTS5
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_conhecimento_ai AFTER INSERT ON tabela_conhecimento BEGIN
                INSERT INTO conhecimento_fts(
                    rowid, codigo_ref, pilar, modulo, titulo, subtitulo,
                    resumo_executivo, conteudo_completo, tabelas_banco,
                    impacto_financeiro, tags_busca
                ) VALUES (
                    new.id, new.codigo_ref, new.pilar, new.modulo, new.titulo, new.subtitulo,
                    new.resumo_executivo, new.conteudo_completo, new.tabelas_banco,
                    new.impacto_financeiro, new.tags_busca
                );
            END;
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_conhecimento_ad AFTER DELETE ON tabela_conhecimento BEGIN
                INSERT INTO conhecimento_fts(conhecimento_fts, rowid, codigo_ref, pilar, modulo, titulo, subtitulo, resumo_executivo, conteudo_completo, tabelas_banco, impacto_financeiro, tags_busca)
                VALUES ('delete', old.id, old.codigo_ref, old.pilar, old.modulo, old.titulo, old.subtitulo, old.resumo_executivo, old.conteudo_completo, old.tabelas_banco, old.impacto_financeiro, old.tags_busca);
            END;
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_conhecimento_au AFTER UPDATE ON tabela_conhecimento BEGIN
                INSERT INTO conhecimento_fts(conhecimento_fts, rowid, codigo_ref, pilar, modulo, titulo, subtitulo, resumo_executivo, conteudo_completo, tabelas_banco, impacto_financeiro, tags_busca)
                VALUES ('delete', old.id, old.codigo_ref, old.pilar, old.modulo, old.titulo, old.subtitulo, old.resumo_executivo, old.conteudo_completo, old.tabelas_banco, old.impacto_financeiro, old.tags_busca);
                INSERT INTO conhecimento_fts(
                    rowid, codigo_ref, pilar, modulo, titulo, subtitulo,
                    resumo_executivo, conteudo_completo, tabelas_banco,
                    impacto_financeiro, tags_busca
                ) VALUES (
                    new.id, new.codigo_ref, new.pilar, new.modulo, new.titulo, new.subtitulo,
                    new.resumo_executivo, new.conteudo_completo, new.tabelas_banco,
                    new.impacto_financeiro, new.tags_busca
                );
            END;
        """)

    return conn


def limpar_markdown(texto: str) -> str:
    """Remove macros Confluence, links quebrados e espacos duplicados."""
    texto = re.sub(r"> \*\*LIVESEARCH:\*\*.*", "", texto)
    texto = re.sub(r"> \*\*CHILDREN:\*\*.*", "", texto)
    texto = re.sub(r"> \*\*INCLUDE:\*\*.*", "", texto)
    texto = re.sub(r"\*\(imagem:.*?\)\*", "", texto)
    texto = re.sub(r"!\[.*?\]\(.*?\)", "", texto)
    texto = re.sub(r"\[\[(.*?)\]\]", r"\1", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_resumo(texto: str, max_chars: int = 400) -> str:
    """Extrai primeiro paragrafo descritivo significativo."""
    linhas = [l.strip() for l in texto.split("\n") if l.strip() and not l.strip().startswith("#")]
    for linha in linhas:
        if len(linha) > 40:
            return linha[:max_chars].strip()
    return texto[:max_chars].strip()


def importar_confluence_e_hubs(source_root: Path, conn: sqlite3.Connection) -> int:
    """Processa as 911 paginas do Confluence e os Hubs de Modulos."""
    confluence_dir = source_root / "quality-rag" / "sources" / "confluence"
    hubs_dir = source_root / "quality-rag" / "sources" / "hubs" / "modulos"

    conf_files = list(confluence_dir.rglob("*.md"))
    hub_files = list(hubs_dir.glob("*.md")) if hubs_dir.exists() else []

    print(f"[*] Ingestao Pilar 1: {len(conf_files)} docs Confluence e {len(hub_files)} Hubs...")
    total_inseridos = 0

    with conn:
        for fpath in conf_files:
            try:
                raw = fpath.read_text(encoding="utf-8", errors="ignore")
                if not raw.startswith("---"):
                    continue
                partes = raw.split("---", 2)
                if len(partes) < 3:
                    continue

                meta = yaml.safe_load(partes[1]) or {}
                corpo = limpar_markdown(partes[2])

                page_id = str(meta.get("page_id") or fpath.stem)
                titulo = str(meta.get("titulo") or fpath.stem.replace("-", " ").title())
                slug = str(meta.get("slug") or fpath.stem)
                hierarquia = str(meta.get("path_hierarquia") or "webPosto")
                labels = meta.get("labels") or []
                if isinstance(labels, list):
                    labels_str = ", ".join(str(l) for l in labels)
                else:
                    labels_str = str(labels)

                modulo = "Geral"
                if ">" in hierarquia:
                    partes_h = [p.strip() for p in hierarquia.split(">")]
                    if len(partes_h) > 1:
                        modulo = partes_h[1]

                resumo = extrair_resumo(corpo)
                if not resumo:
                    resumo = f"Documentacao e rotinas operacionais do modulo {modulo}: {titulo}."

                codigo_ref = f"CONF-{page_id}"
                tags = f"{slug}, {modulo}, {labels_str}, webposto, procedimento, tela, manual".lower()

                conn.execute("""
                    INSERT INTO tabela_conhecimento (
                        pilar, codigo_ref, modulo, titulo, subtitulo,
                        resumo_executivo, conteudo_completo, tabelas_banco,
                        impacto_financeiro, acao_recomendada, tags_busca, metadados_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(codigo_ref) DO UPDATE SET
                        titulo = excluded.titulo,
                        subtitulo = excluded.subtitulo,
                        resumo_executivo = excluded.resumo_executivo,
                        conteudo_completo = excluded.conteudo_completo,
                        tags_busca = excluded.tags_busca,
                        metadados_json = excluded.metadados_json;
                """, (
                    "confluence_procedimentos",
                    codigo_ref,
                    modulo,
                    titulo,
                    hierarquia,
                    resumo,
                    corpo,
                    "",
                    "",
                    f"Acessar menu '{modulo}' no retaguarda ou PDV do webPosto conforme orientacao oficial.",
                    tags,
                    json.dumps(meta, ensure_ascii=False)
                ))
                total_inseridos += 1
            except Exception as e:
                pass

        # Ingestao dos Hubs funcionais de modulos
        for hpath in hub_files:
            try:
                raw = hpath.read_text(encoding="utf-8", errors="ignore")
                if not raw.startswith("---"):
                    continue
                partes = raw.split("---", 2)
                if len(partes) < 3:
                    continue

                meta = yaml.safe_load(partes[1]) or {}
                corpo = limpar_markdown(partes[2])
                nome_modulo = str(meta.get("nome") or hpath.stem.replace("-", " ").title())
                slug = str(meta.get("slug") or hpath.stem)
                codigo_ref = f"HUB-MODULO-{slug.upper()}"

                resumo = f"Indice e mapeamento funcional do modulo '{nome_modulo}' do sistema webPosto."
                tags = f"{slug}, {nome_modulo}, modulo, catalogo, regras, webposto".lower()

                conn.execute("""
                    INSERT INTO tabela_conhecimento (
                        pilar, codigo_ref, modulo, titulo, subtitulo,
                        resumo_executivo, conteudo_completo, tabelas_banco,
                        impacto_financeiro, acao_recomendada, tags_busca, metadados_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(codigo_ref) DO UPDATE SET
                        titulo = excluded.titulo,
                        resumo_executivo = excluded.resumo_executivo,
                        conteudo_completo = excluded.conteudo_completo,
                        tags_busca = excluded.tags_busca;
                """, (
                    "confluence_procedimentos",
                    codigo_ref,
                    nome_modulo,
                    f"Modulo {nome_modulo}",
                    "Catalogo estruturado de modulos do webPosto",
                    resumo,
                    corpo,
                    "",
                    "",
                    f"Consultar procedimentos e telas associadas ao modulo {nome_modulo}.",
                    tags,
                    json.dumps(meta, ensure_ascii=False)
                ))
                total_inseridos += 1
            except Exception:
                pass

    return total_inseridos


def importar_dicionario_sql_e_incidentes(source_root: Path, conn: sqlite3.Connection) -> Tuple[int, int]:
    """
    Processa todos os runbooks extraindo:
    1. Dicionario Semantico de Regras e Flags do Banco (Zero Alucinacao SQL)
    2. Traducao de Incidentes de Pista para Dinheiro Travado (Diagnosticos Executivos)
    """
    runbooks_dir = source_root / "knowledge_base" / "runbooks"
    rb_files = list(runbooks_dir.rglob("*.md"))

    print(f"[*] Ingestao Pilares 2 e 3: {len(rb_files)} runbooks de regras, banco e contingencias...")
    count_sql = 0
    count_incidentes = 0

    # Dicionario canônico de tabelas e flags nucleares do webPosto
    REGRAS_SEMANTICAS_NUCLEARES = [
        {
            "codigo_ref": "SCHEMA_ABASTECIMENTOS",
            "modulo": "PISTA_CONCENTRADOR",
            "titulo": "Tabela abastecimentos (Bicos, Encerrantes e Pista)",
            "subtitulo": "Campos criticos: imprimiu, docu, controle, integraweb, bico, litro, total",
            "resumo": "Armazena eventos brutos emitidos pelo concentrador (Companytec/EzTech). 'imprimiu=S' indica faturado ou cupom em processamento. Se a venda for cancelada (situ=X), imprimiu deve voltar para F para desocupar o bico.",
            "conteudo": (
                "Regras de Integridade para Consultas SQL no webPosto:\n"
                "1. Status 'imprimiu': 'S' indica que o abastecimento ja foi associado a um cupom fiscal ou faturado. 'F' indica pendente na pista.\n"
                "2. Relacionamento: 'docu' contem o identificador da venda (pedido.codi ou nfce.nfc_cd_pedido).\n"
                "3. Bico preso: Ocorre quando imprimiu='S' mas o cupom associado foi cancelado ou rejeitado pela SEFAZ.\n"
                "4. Nunca efetuar DELETE em abastecimentos, pois violara a integridade dos encerrantes do LMC da ANP."
            ),
            "tabelas": "abastecimentos, nfce, pedido",
            "tags": "abastecimentos, imprimiu, bico preso, concentrador, encerrante, pista, lmc",
        },
        {
            "codigo_ref": "SCHEMA_PEDIDO_NFCE",
            "modulo": "FISCAL_VENDAS",
            "titulo": "Tabelas pedido e nfce (Vendas e Documentos Fiscais)",
            "subtitulo": "Relacionamento: pedido.codi = nfce.nfc_cd_pedido e pedido.cupom = nfce.nfc_cd_nota",
            "resumo": "Tabela pedido centraliza as vendas do PDV e retaguarda (situ=X para cancelado, situ=F para finalizado, ven_ds_modelo='65' para NFC-e e '55' para NF-e). Tabela nfce gerencia o status SEFAZ (nfc_fl_status: A=Autorizada, C=Cancelada, I=Inutilizada, O/N=Pendente).",
            "conteudo": (
                "Regras Cruciais de Text-to-SQL para o webPosto:\n"
                "1. Faturamento real: SELECT SUM(ven_vl_total) FROM pedido WHERE situ <> 'X' AND dtem = CURRENT_DATE;\n"
                "2. Modelos de Documentos: ven_ds_modelo = '65' (Consumidor / NFC-e) e '55' (Nota Fiscal Eletronica / NF-e).\n"
                "3. Join obrigatorio: pedido p JOIN nfce n ON p.codi = n.nfc_cd_pedido.\n"
                "4. Notas em contingencia: nfc_fl_status IN ('O', 'N') indicam cupons pendentes de sincronismo com a SEFAZ que geram risco de autuacao se ultrapassarem 24h."
            ),
            "tabelas": "pedido, nfce, itemped",
            "tags": "pedido, nfce, faturamento, vendas, situ, nfc_fl_status, fiscal, cupom, contingencia, modelo 65, modelo 55",
        },
        {
            "codigo_ref": "SCHEMA_PRODUTOS_PRECOS",
            "modulo": "CADASTRO_PRECOS",
            "titulo": "Tabela produtos e produto_integracao",
            "subtitulo": "Classificacao: tpprod ('COMBUSTIVEL', 'LUBRIFICANTE', 'CONVENIENCIA'), situacao='A'",
            "resumo": "Cadastros de mercadorias e precos de venda. Em postos, tpprod='COMBUSTIVEL' define itens regulados pela ANP com aliquotas ad rem monofasicas. produto_integracao sincroniza precos com apps e gateways de terceiros.",
            "conteudo": (
                "Diretrizes de Auditoria SQL:\n"
                "1. Itens de combustiveis validos: SELECT * FROM produtos WHERE tpprod = 'COMBUSTIVEL' AND situacao = 'A';\n"
                "2. Preco vigente: precovista e o preco de bomba. Descontos de aplicativos sao aplicados em alteracao_preco_cartao_app ou produto_integracao.\n"
                "3. Tributacao Monofasica: Combustiveis possuem CST 61 (ad rem), diferindo dos produtos de conveniencia que usam ICMS normal ou ST."
            ),
            "tabelas": "produtos, produto_integracao, alteracao_preco_cartao_app",
            "tags": "produtos, precovista, combustivel, lubrificante, conveniencia, tpprod, produto_integracao, precos, anp",
        },
        {
            "codigo_ref": "SCHEMA_TANQUES_BICOS_LMC",
            "modulo": "METROLOGIA_LMC",
            "titulo": "Tabelas tanque, bico e encerrante (Livro de Movimentacao de Combustiveis)",
            "subtitulo": "Controle volumetrico de tanques e encerrantes fisicos para conformidade ANP",
            "resumo": "Armazena a capacidade nominal dos tanques, o volume medido por regua/sonda e a correlacao dos bicos. A diferenca diaria entre o volume vendido nos encerrantes e a variacao dos tanques nao pode ultrapassar 0.60% (Resolucao ANP).",
            "conteudo": (
                "Regras Metrologicas no Banco:\n"
                "1. Auditoria de Fechamento de Tanques: Cruzar volume inicial + descargas de combustivel - vendas de encerrante = volume final escriturado.\n"
                "2. Tolerancia Maxima Regulamentar: Variacao percentual LMC deve estar entre -0.60% e +0.60%.\n"
                "3. Afericoes de Bico: Afericoes de bomba (balde de 20 litros) devem ser baixadas com motivo proprio para nao computar como venda e nao gerar faturamento indevido."
            ),
            "tabelas": "tanque, bico, encerrante, medicao_tanque",
            "tags": "tanque, bico, encerrante, lmc, volumetrico, anp, calibracao, bomba, diferenca de estoque",
        }
    ]

    with conn:
        for regra in REGRAS_SEMANTICAS_NUCLEARES:
            conn.execute("""
                INSERT INTO tabela_conhecimento (
                    pilar, codigo_ref, modulo, titulo, subtitulo,
                    resumo_executivo, conteudo_completo, tabelas_banco,
                    impacto_financeiro, acao_recomendada, tags_busca, metadados_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo_ref) DO UPDATE SET
                    titulo = excluded.titulo,
                    resumo_executivo = excluded.resumo_executivo,
                    conteudo_completo = excluded.conteudo_completo,
                    tabelas_banco = excluded.tabelas_banco,
                    tags_busca = excluded.tags_busca;
            """, (
                "dicionario_sql",
                regra["codigo_ref"],
                regra["modulo"],
                regra["titulo"],
                regra["subtitulo"],
                regra["resumo"],
                regra["conteudo"],
                regra["tabelas"],
                "Previne consultas SQL incorretas que geram metricas contabeis ou de faturamento distorcidas.",
                "Utilizar estes relacionamentos e condicoes exatas nas consultas Text-to-SQL da AURA.",
                regra["tags"].lower(),
                json.dumps({"tipo": "regra_semantica_sql", "criticidade": "alta"}, ensure_ascii=False)
            ))
            count_sql += 1

        # Processar os 366 runbooks para Incidentes de Pista -> Dinheiro Travado
        for rb_file in rb_files:
            try:
                raw = rb_file.read_text(encoding="utf-8", errors="ignore")
                
                # Extrair ID e Categoria
                m_id = re.search(r"\*\*ID do Runbook:\*\*\s*`?([A-Za-z0-9_\-]+)`?", raw)
                m_cat = re.search(r"\*\*Categoria:\*\*\s*`?([A-Za-z0-9_\-]+)`?", raw)
                m_title = re.search(r"^#\s*Runbook(?:\s+N3|\s+PDV)?:\s*(.+)$", raw, re.MULTILINE)

                rb_id = m_id.group(1).strip() if m_id else f"WP_RB_{rb_file.stem.upper()}"
                categoria = m_cat.group(1).strip() if m_cat else "PISTA_OPERACIONAL"
                titulo = m_title.group(1).strip() if m_title else rb_file.stem.replace("_", " ").title()

                # Extrair Sintomas e Diagnostico
                m_sintomas = re.search(r"##\s*Diagn[oó]stico\s*(?:de Causa Raiz|& Sintomas)?\s*\n(.*?)(?=\n##|\Z)", raw, re.DOTALL | re.IGNORECASE)
                sintomas_texto = m_sintomas.group(1).strip() if m_sintomas else ""

                # Identificar tabelas SQL mencionadas
                tabelas_mencionadas = set(re.findall(r"\b(abastecimentos|nfce|pedido|itemped|produtos|tanque|bico|empresa|produto_integracao|cliente|fechamento_caixa)\b", raw.lower()))
                tabelas_str = ", ".join(sorted(tabelas_mencionadas))

                # Gerar Traducao Executiva para Dinheiro Travado
                impacto = "Risco de retencao de vendas na pista, bico inoperante ou rejeicao fiscal temporaria."
                acao_executiva = "Verificar pendencias operacionais na tela do PDV ou solicitar realinhamento de sincronismo de lote."

                if "abastecimento" in raw.lower() or "preso" in raw.lower() or "imprimiu" in raw.lower():
                    impacto = "Dinheiro Travado na Pista: Abastecimento concluido fisicamente mas retido no bico, gerando fila e impedindo novos abastecimentos no concentrador."
                    acao_executiva = "Orientar o operador do PDV a liberar o abastecimento pendente pelo Controle de Pista ou emitir cupom correspondente."
                elif "nfce" in raw.lower() or "rejei" in raw.lower() or "sefaz" in raw.lower():
                    impacto = "Risco Fiscal e Bloqueio de Caixa: Notas fiscais em contingencia ou rejeitadas por diferenca cadastral, gerando risco de autuacao tributaria."
                    acao_executiva = "Acessar Gerenciador Fiscal no webPosto, revisar o cadastro do produto com rejeicao e retransmitir o lote SEFAZ."
                elif "tef" in raw.lower() or "cart" in raw.lower() or "pay" in raw.lower():
                    impacto = "Perda de Recebiveis e Atrito no Checkout: Transacao de cartao ou aplicativo retida ou duplicada no fechamento do operador."
                    acao_executiva = "Conferir o comprovante TEF impresso com o extrato da adquirente no modulo Conciliacao de Cartao do retaguarda."
                elif "desconto" in raw.lower() or "preco" in raw.lower():
                    impacto = "Erosao de Margem de Lucro: Divergencia entre tabela de precos do sistema e precos de aplicativos de frotas ou desconto indevido de caixa."
                    acao_executiva = "Conferir vigencia da Tabela de Precos e alinhar o percentual maximo de desconto por operador de caixa."

                codigo_ref = f"INCIDENTE-{rb_id}"
                resumo = f"Incidente Operacional ({categoria}): {titulo}. {impacto}"
                tags = f"{rb_id}, {categoria}, {tabelas_str}, incidente, pista, dinheiro travado, causa raiz, contingencia".lower()

                conn.execute("""
                    INSERT INTO tabela_conhecimento (
                        pilar, codigo_ref, modulo, titulo, subtitulo,
                        resumo_executivo, conteudo_completo, tabelas_banco,
                        impacto_financeiro, acao_recomendada, tags_busca, metadados_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(codigo_ref) DO UPDATE SET
                        titulo = excluded.titulo,
                        resumo_executivo = excluded.resumo_executivo,
                        conteudo_completo = excluded.conteudo_completo,
                        impacto_financeiro = excluded.impacto_financeiro,
                        acao_recomendada = excluded.acao_recomendada,
                        tags_busca = excluded.tags_busca;
                """, (
                    "incidentes_pista_perdas",
                    codigo_ref,
                    categoria,
                    titulo,
                    f"Diagnostico Operacional e Causa Raiz N3 ({categoria})",
                    resumo,
                    limpar_markdown(raw),
                    tabelas_str,
                    impacto,
                    acao_executiva,
                    tags,
                    json.dumps({"runbook_id": rb_id, "categoria": categoria}, ensure_ascii=False)
                ))
                count_incidentes += 1

            except Exception:
                pass

    return count_sql, count_incidentes


def importar_catalogo_openapi(source_root: Path, conn: sqlite3.Connection) -> int:
    """Processa o OpenAPI do webPosto com 153 rotas para expansao Multi-Posto."""
    openapi_file = source_root / "knowledge_base" / "webposto_openapi_integracao.json"
    if not openapi_file.exists():
        print("[!] Arquivo OpenAPI webposto_openapi_integracao.json nao encontrado.")
        return 0

    with open(openapi_file, "r", encoding="utf-8") as fp:
        spec = json.load(fp)

    paths = spec.get("paths", {})
    print(f"[*] Ingestao Pilar 4: {len(paths)} rotas de API para expansao multi-posto...")
    total_endpoints = 0

    with conn:
        for path_url, path_data in paths.items():
            for method, op_data in path_data.items():
                if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    continue

                summary = op_data.get("summary") or op_data.get("description") or f"Operacao {method.upper()} em {path_url}"
                tags_list = op_data.get("tags") or ["INTEGRACAO"]
                tag_modulo = tags_list[0] if tags_list else "API_WEBPOSTO"
                op_id = op_data.get("operationId") or f"{method}_{path_url.replace('/', '_').strip('_')}"

                # Traducao de uso analitico executivo para gestor de rede
                uso_analitico = f"Conexao com filial para leitura e integracao de {tag_modulo} via nuvem webPosto."
                if "ABASTECIMENTO" in path_url.upper():
                    uso_analitico = "Consolidacao em tempo real de litros abastecidos em rede para comparativo de vazao entre postos."
                elif "PRECO" in path_url.upper() or "APRIX" in path_url.upper():
                    uso_analitico = "Auditoria de alinhamento de precos entre postos da rede e sincronismo com painel do proprietario."
                elif "SANGRIA" in path_url.upper() or "CAIXA" in path_url.upper():
                    uso_analitico = "Monitoramento remoto de sangrias de dinheiro e conferencias de caixa sem depender de ligacao telefonica para a pista."
                elif "TANQUE" in path_url.upper():
                    uso_analitico = "Leitura centralizada de estoques de tanques para roteamento otimizado de carretas de combustiveis."

                codigo_ref = f"API-{method.upper()}-{path_url.strip('/')}"
                conteudo = (
                    f"Endpoint Oficial webPosto API: {method.upper()} {path_url}\n"
                    f"Modulo / Tag: {tag_modulo}\n"
                    f"Resumo da Operacao: {summary}\n"
                    f"Finalidade Multi-Posto: {uso_analitico}\n"
                    f"Parametros Aceitos: {json.dumps(op_data.get('parameters', []), ensure_ascii=False)}"
                )

                tags = f"{path_url}, {method}, {tag_modulo}, api, integracao, multi posto, matriz filial, webposto".lower()

                conn.execute("""
                    INSERT INTO tabela_conhecimento (
                        pilar, codigo_ref, modulo, titulo, subtitulo,
                        resumo_executivo, conteudo_completo, tabelas_banco,
                        impacto_financeiro, acao_recomendada, tags_busca, metadados_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(codigo_ref) DO UPDATE SET
                        titulo = excluded.titulo,
                        resumo_executivo = excluded.resumo_executivo,
                        conteudo_completo = excluded.conteudo_completo,
                        impacto_financeiro = excluded.impacto_financeiro,
                        tags_busca = excluded.tags_busca;
                """, (
                    "catalogo_api",
                    codigo_ref,
                    tag_modulo,
                    f"{method.upper()} {path_url}",
                    f"Catalogo API Integracao webPosto ({tag_modulo})",
                    f"Rota de integracao para gestao multi-posto: {summary}. {uso_analitico}",
                    conteudo,
                    tag_modulo.lower(),
                    "Permite visao consolidada de filiais evitando atrasos na conciliacao financeira da rede.",
                    f"Acionar este endpoint para consultar dados de filiais remotas do webPosto.",
                    tags,
                    json.dumps(op_data, ensure_ascii=False)
                ))
                total_endpoints += 1

    return total_endpoints


def executar_curadoria_completa():
    print("=" * 70)
    print("  CURADORIA E INGESTAO DE CONHECIMENTO WEBPOSTO -> RAG LOCAL AURA")
    print("=" * 70)

    raiz_rag = localizar_raiz_rag_wp()
    print(f"[*] Raiz RAG WP localizada em: {raiz_rag}")

    conn = inicializar_banco_dados(DB_PATH)
    print(f"[*] Banco SQLite FTS5 inicializado em: {DB_PATH}")

    t_conf = importar_confluence_e_hubs(raiz_rag, conn)
    t_sql, t_inc = importar_dicionario_sql_e_incidentes(raiz_rag, conn)
    t_api = importar_catalogo_openapi(raiz_rag, conn)

    # Contagem final por pilar
    with conn:
        res = conn.execute("""
            SELECT pilar, count(*) 
            FROM tabela_conhecimento 
            GROUP BY pilar;
        """).fetchall()

        total_geral = conn.execute("SELECT count(*) FROM tabela_conhecimento;").fetchone()[0]

    conn.close()

    print("\n" + "=" * 70)
    print(f"  RESULTADO DA INGESTAO E CURADORIA:")
    print(f"  • Total de Registros Curados no RAG Local: {total_geral}")
    for pilar, cnt in res:
        print(f"    - {pilar}: {cnt} registros")
    print("=" * 70)
    print(f"[OK] Banco SQLite FTS5 pronto para uso sub-milissegundo pela AURA!")


if __name__ == "__main__":
    executar_curadoria_completa()
