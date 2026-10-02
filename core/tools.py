"""
Ferramentas de Negócio e Integração da IA (Tools).
Conecta o Agente às bases relacionais (ERP na porta 5433) e vetoriais (pgvector na porta 5434).
"""

import re
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple, List

from config.settings import DB_ERP_CONFIG
from core.rag_engine import HybridRAGEngine
from core.sanitizer import sanitize_dict


class PostoTools:
    """Conjunto de ferramentas operacionais executáveis pelo Agente."""

    def __init__(self, rag_engine: HybridRAGEngine):
        self.rag = rag_engine

    def dados_cadastrais_filial(self) -> dict:
        """Retorna os dados cadastrais da empresa/filial do ERP ou fallback."""
        info = {
            "idempresa": "59050",
            "nome": "ANÁLISE TÉCNICA",
            "razao_social": "ANÁLISE TÉCNICA",
            "cnpj": "10.353.336/0001-91",
            "endereco": "Avenida ADALTO SANTOS, 100 - Praia da Costa - VILA VELHA/ES",
            "pdv": "007",
        }
        try:
            conn = psycopg2.connect(**DB_ERP_CONFIG)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT idempresa, nome, razao_social, cnpj, endereco, numero, bairro, cidade, estado 
                    FROM empresa LIMIT 1;
                """)
                row = cur.fetchone()
                if row:
                    info["idempresa"] = str(row[0] or "")
                    info["nome"] = str(row[1] or "").strip()
                    info["razao_social"] = str(row[2] or "").strip()
                    info["cnpj"] = str(row[3] or "").strip()
                    end = f"{row[4] or ''}, {row[5] or ''} - {row[6] or ''}, {row[7] or ''}/{row[8] or ''}".strip(" ,-/")
                    if end:
                        info["endereco"] = end
            conn.close()
        except Exception:
            pass
        return info

    def buscar_produtos_catalogo(self, termo: str, top_k: int = 5, query_vector: list = None, grupo_filter: str = None) -> dict:
        """Executa busca semântica e lexical híbrida no catálogo de produtos."""
        return self.rag.search_hybrid(termo, top_k=top_k, query_vector=query_vector, grupo_filter=grupo_filter)

    def consultar_analise_vendas_erp(self, tipo: str = "mais_vendidos") -> dict:
        """
        Consulta dados analíticos de vendas e abastecimentos no banco ERP (porta 5433).
        Retorna últimos produtos vendidos (conveniência e pista), faturamento geral,
        dados de hoje e ranking dos mais vendidos.
        """
        try:
            conn = psycopg2.connect(**DB_ERP_CONFIG)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Últimos produtos vendidos na loja de conveniência (pedido + itemped)
                cur.execute("""
                    SELECT 
                        TRIM(p.codi) AS pedido,
                        TRIM(p.cupom) AS cupom,
                        TRIM(p.pdv) AS pdv,
                        COALESCE(p.ven_ts_venda, (p.dtem + p.hsmov)::timestamp) AS data_hora_venda,
                        TRIM(i.codpec) AS codpro,
                        TRIM(pr.nompro) AS nompro,
                        ROUND(i.quant::numeric, 2) AS quantidade,
                        ROUND(i.valunit::numeric, 2) AS valor_unitario,
                        ROUND(i.valitem::numeric, 2) AS total_item,
                        ROUND(p.valortotal::numeric, 2) AS total_pedido
                    FROM pedido p
                    JOIN itemped i ON TRIM(i.pedido) = TRIM(p.codi)
                    LEFT JOIN produtos pr ON pr.codpro = i.codpec
                    ORDER BY COALESCE(p.ven_ts_venda, (p.dtem + p.hsmov)::timestamp) DESC NULLS LAST, p.codi DESC
                    LIMIT 10;
                """)
                ultimos_produtos_conveniencia = cur.fetchall()

                # 2. Últimos abastecimentos na pista (abastecimentos)
                cur.execute("""
                    SELECT 
                        a.controle, 
                        TRIM(a.bomba) AS bomba, 
                        a.data, 
                        a.hora, 
                        TRIM(a.codpro) AS codpro,
                        COALESCE(TRIM(pr.nompro), 'COMBUSTÍVEL ' || TRIM(a.codpro)) AS nompro,
                        ROUND(a.litros::numeric, 3) AS litros, 
                        ROUND(a.total::numeric, 2) AS total,
                        ROUND(a.pu::numeric, 3) AS preco_unitario
                    FROM abastecimentos a
                    LEFT JOIN produtos pr ON pr.codpro = a.codpro
                    ORDER BY a.data DESC, a.hora DESC
                    LIMIT 10;
                """)
                ultimos_abastecimentos = cur.fetchall()

                # 3. Destaque do ÚLTIMO produto vendido em todo o sistema
                ultimo_vendido_destaque = None
                if ultimos_produtos_conveniencia:
                    p_conv = ultimos_produtos_conveniencia[0]
                    ultimo_vendido_destaque = {
                        "origem": "Conveniência / PDV",
                        "pedido": p_conv.get("pedido"),
                        "produto": p_conv.get("nompro"),
                        "codigo_sku": p_conv.get("codpro"),
                        "data_hora": str(p_conv.get("data_hora_venda")),
                        "quantidade": float(p_conv.get("quantidade") or 1),
                        "valor_unitario": float(p_conv.get("valor_unitario") or 0),
                        "valor_total": float(p_conv.get("total_item") or 0),
                        "cupom": p_conv.get("cupom"),
                        "pdv": p_conv.get("pdv")
                    }

                # 4. Produtos mais vendidos na conveniência (itemped)
                cur.execute("""
                    SELECT 
                        TRIM(i.codpec) AS codpro,
                        COALESCE(TRIM(pr.nompro), 'PRODUTO ' || TRIM(i.codpec)) AS nompro,
                        COUNT(*) AS total_saidas,
                        ROUND(SUM(i.quant)::numeric, 2) AS qtd_total,
                        ROUND(SUM(i.valitem)::numeric, 2) AS receita_total
                    FROM itemped i
                    LEFT JOIN produtos pr ON pr.codpro = i.codpec
                    GROUP BY i.codpec, pr.nompro
                    ORDER BY qtd_total DESC
                    LIMIT 5;
                """)
                produtos_mais_vendidos = cur.fetchall()

                if not produtos_mais_vendidos:
                    cur.execute("""
                        SELECT 
                            TRIM(a.codpro) AS codpro,
                            COALESCE(TRIM(p.nompro), 'PRODUTO ' || TRIM(a.codpro)) AS nompro,
                            COUNT(*) AS total_saidas,
                            ROUND(SUM(a.litros)::numeric, 2) AS qtd_total,
                            ROUND(SUM(a.total)::numeric, 2) AS receita_total
                        FROM abastecimentos a
                        LEFT JOIN produtos p ON a.codpro = p.codpro
                        GROUP BY a.codpro, p.nompro
                        ORDER BY qtd_total DESC
                        LIMIT 5;
                    """)
                    produtos_mais_vendidos = cur.fetchall()

                # 5. Abastecimentos por bomba
                cur.execute("""
                    SELECT 
                        bomba,
                        COUNT(*) AS total_abastecimentos,
                        ROUND(SUM(litros)::numeric, 2) AS total_litros,
                        ROUND(SUM(total)::numeric, 2) AS faturamento_bomba
                    FROM abastecimentos
                    GROUP BY bomba
                    ORDER BY total_litros DESC;
                """)
                abastecimentos_bomba = cur.fetchall()

                # 6. Resumo de Hoje (Conveniência + Combustíveis)
                cur.execute("""
                    SELECT 
                        CURRENT_DATE AS data_consulta,
                        COUNT(*) AS total_abastecimentos_hoje,
                        ROUND(COALESCE(SUM(litros), 0)::numeric, 2) AS total_litros_hoje,
                        ROUND(COALESCE(SUM(total), 0)::numeric, 2) AS faturamento_combustivel_hoje
                    FROM abastecimentos
                    WHERE data = CURRENT_DATE;
                """)
                resumo_abast_hoje = cur.fetchone()

                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT codi) AS total_pedidos_hoje,
                        ROUND(COALESCE(SUM(valortotal), 0)::numeric, 2) AS faturamento_conveniencia_hoje
                    FROM pedido
                    WHERE dtem = CURRENT_DATE OR DATE(ven_ts_venda) = CURRENT_DATE;
                """)
                resumo_conv_hoje = cur.fetchone()

                # 7. Resumo Geral de Abastecimentos / Vendas de Combustíveis
                cur.execute("""
                    SELECT 
                        COUNT(*) AS total_abastecimentos,
                        ROUND(SUM(litros)::numeric, 2) AS total_litros,
                        ROUND(SUM(total)::numeric, 2) AS faturamento_total
                    FROM abastecimentos;
                """)
                resumo_geral = cur.fetchone()

                conn.close()
                resposta = {
                    "status": "ok",
                    "ultimo_produto_vendido_destaque": ultimo_vendido_destaque,
                    "ultimos_produtos_conveniencia": [dict(r) for r in ultimos_produtos_conveniencia],
                    "ultimos_abastecimentos_pista": [dict(r) for r in ultimos_abastecimentos],
                    "produtos_mais_vendidos": [dict(r) for r in produtos_mais_vendidos],
                    "abastecimentos_por_bomba": [dict(r) for r in abastecimentos_bomba],
                    "resumo_hoje": {
                        "data": str(resumo_abast_hoje.get("data_consulta") if resumo_abast_hoje else ""),
                        "abastecimentos_hoje": resumo_abast_hoje.get("total_abastecimentos_hoje") if resumo_abast_hoje else 0,
                        "litros_hoje": float(resumo_abast_hoje.get("total_litros_hoje") or 0) if resumo_abast_hoje else 0,
                        "faturamento_combustivel_hoje": float(resumo_abast_hoje.get("faturamento_combustivel_hoje") or 0) if resumo_abast_hoje else 0,
                        "pedidos_conveniencia_hoje": resumo_conv_hoje.get("total_pedidos_hoje") if resumo_conv_hoje else 0,
                        "faturamento_conveniencia_hoje": float(resumo_conv_hoje.get("faturamento_conveniencia_hoje") or 0) if resumo_conv_hoje else 0,
                    },
                    "resumo_geral": dict(resumo_geral) if resumo_geral else {},
                }
                resposta_limpa, _ = sanitize_dict(resposta)
                return resposta_limpa
        except Exception as e:
            return {
                "status": "indisponivel",
                "motivo": f"Falha na consulta ao ERP (porta 5433): {e}",
            }

    def consultar_estoque_erp(self, termo: str = "") -> dict:
        """
        Consulta dados de estoque em tempo real direto do ERP (tabelas produtos e tanques).
        Retorna maiores estoques, estoques críticos e saldo volumétrico de cada tanque.
        """
        try:
            conn = psycopg2.connect(**DB_ERP_CONFIG)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Top produtos com maior estoque cadastrado
                cur.execute("""
                    SELECT 
                        TRIM(p.codpro) as codpro,
                        TRIM(p.nompro) as nompro,
                        COALESCE(TRIM(g.grupo), 'GERAL') as grupo,
                        COALESCE(TRIM(p.uni), 'UN') as unidade,
                        ROUND(COALESCE(p.qtdeat, 0)::numeric, 3) as estoque_atual,
                        ROUND(COALESCE(p.valvenda, 0)::numeric, 2) as preco_venda
                    FROM produtos p
                    LEFT JOIN grupos g ON g.codi = p.codgru
                    WHERE p.qtdeat IS NOT NULL AND p.nompro IS NOT NULL
                    ORDER BY p.qtdeat DESC
                    LIMIT 10;
                """)
                maiores_estoques = cur.fetchall()

                # 2. Posição dos Tanques de Combustíveis (saldo em litros e ocupação)
                cur.execute("""
                    SELECT 
                        codtan,
                        COALESCE(prl_ds_produto_lmc, 'COMBUSTÍVEL') as combustivel,
                        ROUND(COALESCE(capacidade, 0)::numeric, 2) as capacidade_litros,
                        ROUND(COALESCE(qtdeat, 0)::numeric, 2) as saldo_atual_litros,
                        ROUND((COALESCE(qtdeat, 0) / NULLIF(capacidade, 0) * 100)::numeric, 1) as percentual_ocupacao
                    FROM tanques
                    ORDER BY codtan;
                """)
                tanques = cur.fetchall()

                conn.close()
                return {
                    "status": "ok",
                    "maiores_estoques": [dict(r) for r in maiores_estoques],
                    "tanques_combustivel": [dict(r) for r in tanques]
                }
        except Exception as e:
            return {
                "status": "indisponivel",
                "motivo": f"Falha na consulta de estoque no ERP (porta 5433): {e}",
            }

    def consultar_clientes_erp(self, termo: str = "") -> dict:
        """
        Consulta dados analíticos de clientes, histórico de compras e cadastro no ERP.
        Retorna clientes que mais compraram e busca específica com mascaramento LGPD.
        """
        try:
            conn = psycopg2.connect(**DB_ERP_CONFIG)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Ranking de compras por cliente na tabela pedido
                cur.execute("""
                    SELECT 
                        p.clie AS codigo_cliente,
                        COALESCE(c.cli_nome_a, 'CONSUMIDOR PADRÃO') AS nome_cliente,
                        COUNT(*) AS total_pedidos,
                        ROUND(SUM(p.valortotal)::numeric, 2) AS total_comprado
                    FROM pedido p
                    LEFT JOIN clientes c ON c.cli_cod_a = p.clie
                    GROUP BY p.clie, c.cli_nome_a
                    ORDER BY total_comprado DESC
                    LIMIT 5;
                """)
                ranking_compras = cur.fetchall()

                # 2. Total de clientes cadastrados na base
                cur.execute("SELECT COUNT(*) AS total_cadastrados FROM clientes;")
                total_clientes = cur.fetchone()['total_cadastrados']

                # 3. Busca por cliente específico se houver termo
                busca_especifica = []
                stopwords = {"quem", "e", "é", "o", "a", "os", "as", "de", "do", "da", "em", "um", "uma", "cliente", "clientes", "qual", "mais", "comprou", "comprador", "compradores", "cadastro", "dados", "sobre", "ranking"}
                palavras = [w for w in re.findall(r"[\w]+", termo.lower()) if w not in stopwords and len(w) > 2]
                if palavras:
                    termo_busca = "%" + "%".join(palavras) + "%"
                    cur.execute("""
                        SELECT 
                            TRIM(cli_cod_a) as cli_cod_a, 
                            TRIM(cli_nome_a) as cli_nome_a, 
                            COALESCE(TRIM(cidade), 'NÃO INFORMADA') as cidade,
                            CASE 
                                WHEN cpf IS NOT NULL AND length(cpf) >= 11 THEN left(cpf, 3) || '.***.***-' || right(cpf, 2)
                                WHEN cgc IS NOT NULL AND length(cgc) >= 14 THEN left(cgc, 6) || '.***/****-' || right(cgc, 2)
                                ELSE 'NÃO INFORMADO'
                            END AS documento_mascarado
                        FROM clientes
                        WHERE cli_nome_a ILIKE %s OR cli_cod_a = %s
                        LIMIT 5;
                    """, (termo_busca, palavras[0]))
                    busca_especifica = cur.fetchall()

                conn.close()
                resposta = {
                    "status": "ok",
                    "total_clientes_cadastrados": total_clientes,
                    "ranking_compras_pedidos": [dict(r) for r in ranking_compras],
                    "busca_especifica": [dict(r) for r in busca_especifica],
                    "observacao_pdv": "No PDV do posto, a maior parte dos cupons e abastecimentos rápidos são registrados sob o código 00001 (CONSUMIDOR FINAL) caso o cliente não solicite inclusão de CPF/CNPJ."
                }
                resposta_limpa, _ = sanitize_dict(resposta)
                return resposta_limpa
        except Exception as e:
            return {
                "status": "indisponivel",
                "motivo": f"Falha na consulta de clientes no ERP (porta 5433): {e}",
            }

    def obter_telemetria_sre(self) -> dict:
        """Retorna métricas de saúde do PostgreSQL 16 para observabilidade."""
        return self.rag.get_sre_metrics()

    @staticmethod
    def calcular_volume_encerrante(enc_ini: Decimal, enc_fim: Decimal, afericao: Decimal = Decimal("0.0")) -> Tuple[Decimal, Decimal, str]:
        """
        Calcula volume bruto e faturado do encerrante de bomba, com tratamento de
        virada de odômetro mecânico/digital (rollover) e validação de erros de digitação.
        Retorna: (volume_bruto_litros, volume_faturado_litros, status_calculo)
        """
        if enc_ini == Decimal("0.0") and enc_fim == Decimal("0.0"):
            return Decimal("0.0"), Decimal("0.0"), "SEM_LANCAMENTO"
        
        # Caso normal: encerrante final maior ou igual ao inicial
        if enc_fim >= enc_ini:
            vol_bruto = enc_fim - enc_ini
            vol_fat = max(Decimal("0.0"), vol_bruto - afericao)
            return vol_bruto, vol_fat, "NORMAL"
        
        # Caso: enc_fim < enc_ini (possível virada de relógio ou erro de digitação)
        limite = None
        if enc_ini > Decimal("9000000"):
            limite = Decimal("10000000")
        elif enc_ini > Decimal("900000"):
            limite = Decimal("1000000")
        elif enc_ini > Decimal("90000"):
            limite = Decimal("100000")
        
        # Se for virada plausível (volume resultante < 50.000 L)
        if limite and (limite - enc_ini + enc_fim) < Decimal("50000"):
            vol_bruto = (limite - enc_ini) + enc_fim
            vol_fat = max(Decimal("0.0"), vol_bruto - afericao)
            return vol_bruto, vol_fat, f"VIRADA_ODOMETRO ({int(limite):,})".replace(",", ".")
        
        # Se não for virada plausível, trata-se de inversão ou erro de leitura
        return Decimal("0.0"), Decimal("0.0"), "ERRO_DIGITACAO (Encerrante final menor que inicial)"

    @staticmethod
    def normalizar_turno(turno_input: Any) -> Tuple[Optional[str], Optional[int]]:
        """
        Normaliza a entrada de turno para busca no ERP ('1º TURNO', '2º TURNO', '3º TURNO').
        Suporta números, ordinais, texto em português ('manhã', 'tarde', 'noite', 'madrugada')
        e evita falso-positivo em dígitos soltos de datas.
        """
        if turno_input is None:
            return None, None
        s = str(turno_input).strip().lower()
        if not s or s in ["todos", "all", "geral", "none", "qualquer", "dia"]:
            return None, None

        # Turno 1 / Manhã
        if re.search(r"\b(1[º°ªo]|primeir[oa]|manh[aã]|turno\s*1|1\s*turno)\b", s) or s == "1":
            return "%1%TURNO%", 1
        # Turno 2 / Tarde
        if re.search(r"\b(2[º°ªo]|segund[oa]|tarde|turno\s*2|2\s*turno)\b", s) or s == "2":
            return "%2%TURNO%", 2
        # Turno 3 / Noite / Madrugada
        if re.search(r"\b(3[º°ªo]|terceir[oa]|noite|madrugada|turno\s*3|3\s*turno)\b", s) or s == "3":
            return "%3%TURNO%", 3

        return None, None

    @staticmethod
    def normalizar_data(data_input: Any) -> Optional[str]:
        """
        Normaliza formatos de data (ISO YYYY-MM-DD, BR DD/MM/YYYY, DD/MM, 'hoje', 'ontem', 'anteontem', extenso).
        Retorna string ISO segura 'YYYY-MM-DD' ou None se inválida (evitando SQL syntax error).
        """
        if not data_input:
            return None
        s = str(data_input).strip().lower()
        if s in ["hoje", "today"]:
            return "hoje"
        if s in ["ontem", "yesterday"]:
            return "ontem"
        if s in ["anteontem"]:
            return "anteontem"

        # 1. ISO YYYY-MM-DD
        m_iso = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", s)
        if m_iso:
            y, m, d = m_iso.groups()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

        # 2. BR DD/MM/YYYY
        m_br = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", s)
        if m_br:
            d, m, y = m_br.groups()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

        # 3. BR DD/MM (assume ano 2026 do ERP)
        m_dia_mes = re.search(r"\b(\d{1,2})[-/](\d{1,2})\b", s)
        if m_dia_mes:
            d, m = m_dia_mes.groups()
            return f"2026-{int(m):02d}-{int(d):02d}"

        # 4. Extenso em português: '2 de setembro', '02 de setembro de 2026'
        meses = {
            "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
            "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
        }
        m_ext = re.search(r"\b(\d{1,2})\s+de\s+([a-zçãõ]+)(?:\s+de\s+(\d{4}))?", s)
        if m_ext:
            d, mes_str, ano_str = m_ext.groups()
            mes_prefix = mes_str[:3]
            if mes_prefix in meses:
                ano = int(ano_str) if ano_str else 2026
                return f"{ano:04d}-{meses[mes_prefix]:02d}-{int(d):02d}"

        return None

    def auditar_fechamento_turno(self, data: Any = None, turno: Any = None) -> dict:
        """
        Motor de Conciliação de Turnos & Auditoria de Pista (Fase 2 - P0).
        Executa a triangulação matemática entre:
        1. Encerrantes físicos de pista (fechabomba): Volume = (enclts - encltsa) - qtdeaf
        2. Telemetria em tempo real Companytec CBC04 (abastecimentos)
        3. Fechamento financeiro dos caixas (fechacaixa + pedido)
        4. Balanço de tanques e tolerância volumétrica ANP (±0.6%)
        Calcula quebras, sobras, furos e divergências de pista/caixa com conformidade LGPD.
        """
        try:
            conn = psycopg2.connect(**DB_ERP_CONFIG)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Determinação da Data Alvo
                data_param = self.normalizar_data(data)
                aviso_data = None
                data_alvo = None

                cur.execute("SELECT CURRENT_DATE;")
                data_hoje = cur.fetchone()['current_date']

                if not data_param or data_param == "hoje":
                    cur.execute("SELECT COUNT(*) as c FROM fechabomba WHERE dtmov = %s;", (data_hoje,))
                    c_fb = cur.fetchone()['c']
                    cur.execute("SELECT COUNT(*) as c FROM abastecimentos WHERE data = %s;", (data_hoje,))
                    c_ab = cur.fetchone()['c']

                    if c_fb > 0 or c_ab > 0:
                        data_alvo = str(data_hoje)
                    else:
                        cur.execute("""
                            SELECT GREATEST(
                                (SELECT MAX(dtmov) FROM fechabomba),
                                (SELECT MAX(dtmov) FROM fechacaixa),
                                (SELECT MAX(data) FROM abastecimentos)
                            ) as max_d;
                        """)
                        max_d = cur.fetchone()['max_d']
                        if max_d:
                            data_alvo = str(max_d)
                            aviso_data = (
                                f"Nenhum fechamento registrado para hoje ({data_hoje}). "
                                f"Exibindo auditoria da data mais recente com movimentação: {data_alvo}."
                            )
                        else:
                            data_alvo = str(data_hoje)
                elif data_param == "ontem":
                    cur.execute("SELECT (CURRENT_DATE - INTERVAL '1 day')::date as ontem;")
                    data_alvo = str(cur.fetchone()['ontem'])
                elif data_param == "anteontem":
                    cur.execute("SELECT (CURRENT_DATE - INTERVAL '2 days')::date as anteontem;")
                    data_alvo = str(cur.fetchone()['anteontem'])
                else:
                    data_alvo = data_param

                # 2. Determinação do Turno
                filtro_turno_pattern, _ = self.normalizar_turno(turno)

                # 3. Consulta de Encerrantes de Pista (fechabomba)
                cur.execute("""
                    SELECT 
                        TRIM(fb.codbom) AS bico,
                        TRIM(fb.codtan) AS tanque,
                        TRIM(fb.codpro) AS codpro,
                        COALESCE(TRIM(p.nompro), 'COMBUSTÍVEL ' || TRIM(fb.codpro)) AS nompro,
                        COALESCE(fb.encltsa, 0)::numeric AS encerrante_inicial,
                        COALESCE(fb.enclts, 0)::numeric AS encerrante_final,
                        COALESCE(fb.qtdeaf, 0)::numeric AS afericao_litros,
                        fb.preco::numeric AS preco_fechamento,
                        p.valvenda::numeric AS preco_cadastro,
                        fb.enc_cd_caixa,
                        TRIM(fb.codpdv) AS pdv,
                        TRIM(fb.turno) AS turno
                    FROM fechabomba fb
                    LEFT JOIN produtos p ON p.codpro = fb.codpro
                    WHERE fb.dtmov = %s 
                      AND (%s::text IS NULL OR fb.turno ILIKE %s)
                    ORDER BY fb.codbom;
                """, (data_alvo, filtro_turno_pattern, filtro_turno_pattern))
                linhas_fechabomba = cur.fetchall()

                # 4. Consulta de Automação CBC04 (abastecimentos)
                cur.execute("""
                    SELECT 
                        TRIM(a.bomba) AS bico,
                        TRIM(a.tanque) AS tanque,
                        TRIM(a.codpro) AS codpro,
                        COALESCE(TRIM(p.nompro), 'COMBUSTÍVEL ' || TRIM(a.codpro)) AS nompro,
                        COUNT(*)::int AS qtd_abastecimentos,
                        ROUND(COALESCE(SUM(a.litros), 0)::numeric, 3) AS volume_automacao_litros,
                        ROUND(COALESCE(SUM(a.total), 0)::numeric, 2) AS total_automacao_reais,
                        ROUND(MIN(a.ei)::numeric, 3) AS encerrante_inicial_automacao,
                        ROUND(MAX(a.encerrante)::numeric, 3) AS encerrante_final_automacao,
                        TRIM(a.turno) AS turno
                    FROM abastecimentos a
                    LEFT JOIN produtos p ON p.codpro = a.codpro
                    WHERE a.data = %s 
                      AND (%s::text IS NULL OR a.turno ILIKE %s)
                      AND (a.abt_bl_venda_cancelada IS NOT TRUE)
                    GROUP BY a.bomba, a.tanque, a.codpro, p.nompro, a.turno
                    ORDER BY a.bomba;
                """, (data_alvo, filtro_turno_pattern, filtro_turno_pattern))
                linhas_automacao = cur.fetchall()

                # 5. Consulta de Fechamento de Caixa (fechacaixa + funcionarios)
                cur.execute("""
                    SELECT 
                        fc.cai_cd_caixa AS caixa_id,
                        TRIM(fc.codpdv) AS pdv,
                        TRIM(fc.turno) AS turno,
                        TRIM(fc.matricula) AS matricula,
                        COALESCE(TRIM(f.nome), 'OPERADOR NÃO INFORMADO') AS operador_nome,
                        COALESCE(fc.fechado, 'N') AS fechado,
                        fc.cai_ts_abertura,
                        CASE WHEN fc.cai_ts_fechamento > '1900-01-01' THEN fc.cai_ts_fechamento ELSE NULL END AS cai_ts_fechamento,
                        COALESCE(fc.valdinh, 0)::numeric AS dinheiro,
                        COALESCE(fc.valcart, 0)::numeric AS cartao,
                        COALESCE(fc.valnotpra, 0)::numeric AS prazo,
                        (COALESCE(fc.valcheconv, 0) + COALESCE(fc.valchevis, 0) + COALESCE(fc.valchepre, 0))::numeric AS convenio_cheque,
                        COALESCE(fc.valtot, (COALESCE(fc.valdinh, 0) + COALESCE(fc.valcart, 0) + COALESCE(fc.valnotpra, 0) + COALESCE(fc.valcheconv, 0) + COALESCE(fc.valchevis, 0) + COALESCE(fc.valchepre, 0)))::numeric AS total_declarado,
                        COALESCE(fc.venda_combustivel, 0)::numeric AS venda_combustivel,
                        COALESCE(fc.venda_produtos, 0)::numeric AS venda_produtos,
                        COALESCE(fc.litros, 0)::numeric AS litros_declarados
                    FROM fechacaixa fc
                    LEFT JOIN funcionarios f ON f.matr = fc.matricula
                    WHERE fc.dtmov = %s 
                      AND (%s::text IS NULL OR fc.turno ILIKE %s)
                    ORDER BY fc.cai_cd_caixa;
                """, (data_alvo, filtro_turno_pattern, filtro_turno_pattern))
                linhas_fechacaixa = cur.fetchall()

                # Se não houver movimentação em nenhuma das 3 fontes
                if not linhas_fechabomba and not linhas_automacao and not linhas_fechacaixa:
                    cur.execute("""
                        SELECT GREATEST(
                            (SELECT MAX(dtmov) FROM fechabomba),
                            (SELECT MAX(dtmov) FROM fechacaixa),
                            (SELECT MAX(data) FROM abastecimentos)
                        ) as max_d;
                    """)
                    max_disp = cur.fetchone()['max_d']
                    conn.close()
                    msg = f"Nenhum registro de fechamento de bomba, caixa ou abastecimento encontrado para a data {data_alvo}."
                    if max_disp:
                        msg += f" Última data com movimentação registrada: {max_disp}."
                    return {
                        "status": "sem_movimento",
                        "data_auditada": str(data_alvo),
                        "data_solicitada": data or "hoje",
                        "turno_solicitado": turno or "TODOS",
                        "ultima_data_disponivel": str(max_disp) if max_disp else None,
                        "mensagem": msg
                    }

                # 6. Consulta de Cupons / Pedidos do PDV (para caixas abertos ou faturamento PDV)
                cur.execute("""
                    SELECT 
                        TRIM(pdv) AS pdv,
                        COUNT(DISTINCT codi)::int AS total_pedidos,
                        ROUND(COALESCE(SUM(valortotal), 0)::numeric, 2) AS total_faturado_pedidos
                    FROM pedido
                    WHERE (dtem = %s OR DATE(ven_ts_venda) = %s)
                    GROUP BY pdv;
                """, (data_alvo, data_alvo))
                pedidos_pdv_rows = cur.fetchall()
                pedidos_por_pdv = {r['pdv']: float(r['total_faturado_pedidos']) for r in pedidos_pdv_rows}
                total_pedidos_pdv = sum(float(r['total_faturado_pedidos']) for r in pedidos_pdv_rows)

                # 7. Consulta de Tanques de Combustíveis (tanques)
                cur.execute("""
                    SELECT 
                        TRIM(t.codtan) AS codtan,
                        COALESCE(TRIM(t.prl_ds_produto_lmc), 'COMBUSTÍVEL ' || TRIM(t.codtan)) AS combustivel,
                        ROUND(COALESCE(t.capacidade, 0)::numeric, 2) AS capacidade_litros,
                        ROUND(COALESCE(t.qtdeinicioturno, t.qtdean, t.qtdeat, 0)::numeric, 2) AS saldo_inicial_litros,
                        ROUND(COALESCE(t.tan_vl_quantidade_fim, t.qtdeat, 0)::numeric, 2) AS saldo_final_litros,
                        ROUND(COALESCE(t.vendasturno, 0)::numeric, 2) AS vendas_registradas_tanque,
                        (t.qtdeinicioturno IS NOT NULL OR t.tan_vl_quantidade_fim IS NOT NULL) AS tem_medicao_fisica
                    FROM tanques t
                    ORDER BY t.codtan;
                """)
                linhas_tanques = cur.fetchall()

                conn.close()

            # ----------------------------------------------------
            # PROCESSAMENTO MATEMÁTICO E TRIANGULAÇÃO
            # ----------------------------------------------------

            # A. Triangulação de Pista: Mapear automação por bico
            aut_map = {r['bico']: r for r in linhas_automacao}

            bicos_auditados = []
            tot_litros_bruto_encerrante = Decimal("0.0")
            tot_litros_faturados_encerrante = Decimal("0.0")
            tot_afericao_litros = Decimal("0.0")
            tot_fat_encerrante = Decimal("0.0")
            tot_litros_automacao = Decimal("0.0")
            tot_fat_automacao = Decimal("0.0")
            total_abast_count = 0

            todos_bicos = sorted(list(set([r['bico'] for r in linhas_fechabomba] + list(aut_map.keys()))))
            fb_map = {r['bico']: r for r in linhas_fechabomba}

            for bico_id in todos_bicos:
                fb = fb_map.get(bico_id, {})
                aut = aut_map.get(bico_id, {})

                tanque = fb.get('tanque') or aut.get('tanque') or "N/D"
                codpro = fb.get('codpro') or aut.get('codpro') or "N/D"
                nompro = fb.get('nompro') or aut.get('nompro') or f"COMBUSTÍVEL {codpro}"
                enc_ini = Decimal(str(fb.get('encerrante_inicial') or 0))
                enc_fim = Decimal(str(fb.get('encerrante_final') or 0))
                af = Decimal(str(fb.get('afericao_litros') or 0))
                preco_un = Decimal(str(fb.get('preco_fechamento') or fb.get('preco_cadastro') or 0))

                vol_bruto, vol_fat, status_calculo = self.calcular_volume_encerrante(enc_ini, enc_fim, af)
                fat_enc = round(vol_fat * preco_un, 2)

                vol_aut = Decimal(str(aut.get('volume_automacao_litros') or 0))
                fat_aut = Decimal(str(aut.get('total_automacao_reais') or 0))
                qtd_abast = int(aut.get('qtd_abastecimentos') or 0)

                dif_litros = vol_aut - vol_fat

                # Diagnóstico preciso por bico
                if enc_ini == Decimal("0.0") and enc_fim == Decimal("0.0") and vol_aut == Decimal("0.0"):
                    status_bico = "SEM_MOVIMENTO (Sem lançamentos de encerrante ou automação no turno)"
                elif enc_ini == Decimal("0.0") and enc_fim == Decimal("0.0") and vol_aut > Decimal("0.0"):
                    status_bico = f"PENDENTE_ENCERRANTE (Automação registrou {float(vol_aut):.3f} L, encerrante não digitado)"
                elif "ERRO_DIGITACAO" in status_calculo:
                    status_bico = f"ERRO_LEITURA ({status_calculo})"
                elif abs(dif_litros) < Decimal("0.005"):
                    if "VIRADA_ODOMETRO" in status_calculo:
                        status_bico = f"CONCILIADO COM VIRADA DE ODÔMETRO ({status_calculo})"
                    else:
                        status_bico = "CONCILIADO"
                elif dif_litros > Decimal("0.0"):
                    status_bico = f"DIVERGÊNCIA (+{float(dif_litros):.3f} L na Automação)"
                else:
                    status_bico = f"DIVERGÊNCIA ({float(abs(dif_litros)):.3f} L no Encerrante)"

                bicos_auditados.append({
                    "bico": bico_id,
                    "tanque": tanque,
                    "codpro": codpro,
                    "combustivel": nompro,
                    "encerrante_inicial": float(enc_ini),
                    "encerrante_final": float(enc_fim),
                    "afericao_litros": float(af),
                    "volume_bruto_litros": float(vol_bruto),
                    "volume_faturado_encerrante": float(vol_fat),
                    "preco_unitario": float(preco_un),
                    "faturamento_encerrante": float(fat_enc),
                    "volume_automacao_litros": float(vol_aut),
                    "total_reais_automacao": float(fat_aut),
                    "qtd_abastecimentos": qtd_abast,
                    "diferenca_litros": float(dif_litros),
                    "status_calculo_encerrante": status_calculo,
                    "status_bico": status_bico,
                })

                tot_litros_bruto_encerrante += vol_bruto
                tot_litros_faturados_encerrante += vol_fat
                tot_afericao_litros += af
                tot_fat_encerrante += fat_enc
                tot_litros_automacao += vol_aut
                tot_fat_automacao += fat_aut
                total_abast_count += qtd_abast

            dif_pista_total_litros = tot_litros_automacao - tot_litros_faturados_encerrante

            # B. Triangulação de Caixa
            caixas_auditados = []
            tot_dinh = Decimal("0.0")
            tot_cart = Decimal("0.0")
            tot_prazo = Decimal("0.0")
            tot_conv = Decimal("0.0")
            tot_declarado = Decimal("0.0")
            todos_caixas_fechados = (len(linhas_fechacaixa) > 0) and all(fc['fechado'] == 'S' for fc in linhas_fechacaixa)

            for fc in linhas_fechacaixa:
                c_id = fc['caixa_id']
                pdv = fc['pdv']
                matricula = fc['matricula']
                operador = fc['operador_nome']
                fechado = (fc['fechado'] == 'S')

                dinh = Decimal(str(fc['dinheiro'] or 0))
                cart = Decimal(str(fc['cartao'] or 0))
                prazo = Decimal(str(fc['prazo'] or 0))
                conv = Decimal(str(fc['convenio_cheque'] or 0))
                declarado = Decimal(str(fc['total_declarado'] or 0))

                pedidos_pdv_val = pedidos_por_pdv.get(pdv, 0.0)

                caixas_auditados.append({
                    "caixa_id": c_id,
                    "pdv": pdv,
                    "matricula": matricula,
                    "operador": operador,
                    "status": "FECHADO" if fechado else "EM ABERTO",
                    "abertura": str(fc['cai_ts_abertura'] or ""),
                    "fechamento": str(fc['cai_ts_fechamento'] or "") if fc['cai_ts_fechamento'] else None,
                    "dinheiro": float(dinh),
                    "cartao": float(cart),
                    "prazo": float(prazo),
                    "convenio_cheque": float(conv),
                    "total_declarado": float(declarado),
                    "pedidos_faturados_pdv": pedidos_pdv_val,
                    "venda_combustivel": float(fc.get('venda_combustivel') or 0),
                    "venda_produtos": float(fc.get('venda_produtos') or 0),
                    "litros_declarados": float(fc['litros_declarados'] or 0),
                })

                tot_dinh += dinh
                tot_cart += cart
                tot_prazo += prazo
                tot_conv += conv
                tot_declarado += declarado

            # Origem e valor do Faturamento de Pista esperado
            if tot_fat_encerrante > Decimal("0.0"):
                faturamento_pista_esperado = tot_fat_encerrante
                origem_faturamento_pista = "Encerrantes Físicos (fechabomba)"
            elif tot_fat_automacao > Decimal("0.0"):
                faturamento_pista_esperado = tot_fat_automacao
                origem_faturamento_pista = "Automação Companytec CBC04 (tempo real)"
            else:
                faturamento_pista_esperado = Decimal("0.0")
                origem_faturamento_pista = "Sem movimentação de pista"

            # Origem e valor do Faturamento de Caixa apurado
            if tot_declarado > Decimal("0.0"):
                faturamento_caixa_apurado = tot_declarado
                origem_faturamento_caixa = "Fechamento de Caixa Declarado"
            elif total_pedidos_pdv > 0:
                faturamento_caixa_apurado = Decimal(str(total_pedidos_pdv))
                origem_faturamento_caixa = "Cupons / Pedidos PDV (Caixa em Aberto)"
            else:
                faturamento_caixa_apurado = Decimal("0.0")
                origem_faturamento_caixa = "Sem lançamentos de caixa ou cupons"

            diferenca_financeira = faturamento_caixa_apurado - faturamento_pista_esperado

            # C. Auditoria de Tanques & Regra ANP (±0.6%)
            saidas_bicos_por_tanque: Dict[str, Decimal] = {}
            for b in bicos_auditados:
                t_id = b['tanque']
                vol_util = Decimal(str(b['volume_automacao_litros'] if b['volume_automacao_litros'] > 0 else b['volume_faturado_encerrante']))
                saidas_bicos_por_tanque[t_id] = saidas_bicos_por_tanque.get(t_id, Decimal("0.0")) + vol_util

            tanques_auditados = []
            tanques_fora_tolerancia = 0

            for t in linhas_tanques:
                codtan = t['codtan']
                comb = t['combustivel']
                cap = Decimal(str(t['capacidade_litros'] or 0))
                s_ini = Decimal(str(t['saldo_inicial_litros'] or 0))
                s_fim = Decimal(str(t['saldo_final_litros'] or 0))
                tem_medicao = bool(t.get('tem_medicao_fisica'))

                saida_bicos = saidas_bicos_por_tanque.get(codtan, Decimal("0.0"))
                dif_estoque_fisico = s_ini - s_fim

                if tem_medicao and (s_ini != s_fim):
                    variacao_litros = dif_estoque_fisico - saida_bicos
                    base_calculo = saida_bicos if saida_bicos > 0 else (s_ini if s_ini > 0 else cap)
                    pct_variacao = round(float(abs(variacao_litros) / base_calculo * 100), 3) if base_calculo > 0 else 0.0
                    if pct_variacao <= 0.6:
                        status_anp = f"CONFORME ANP (Variação de {pct_variacao:.2f}% dentro da tolerância legal ±0.6%)"
                    else:
                        status_anp = f"ALERTA ANP (Variação de {pct_variacao:.2f}% excede tolerância legal de ±0.6%)"
                        tanques_fora_tolerancia += 1
                elif saida_bicos > Decimal("0.0"):
                    variacao_litros = Decimal("0.0")
                    pct_variacao = 0.0
                    status_anp = "CONFORME (Vendas ativas nos bicos; medição física de régua/sonda não lançada neste turno)"
                else:
                    variacao_litros = Decimal("0.0")
                    pct_variacao = 0.0
                    status_anp = "CONFORME (Sem movimentação no tanque neste turno)"

                tanques_auditados.append({
                    "codtan": codtan,
                    "combustivel": comb,
                    "capacidade_litros": float(cap),
                    "saldo_inicial": float(s_ini),
                    "saldo_final": float(s_fim),
                    "saida_tanque_litros": float(dif_estoque_fisico),
                    "saida_bicos_litros": float(saida_bicos),
                    "variacao_litros": float(variacao_litros),
                    "variacao_percentual": pct_variacao,
                    "tolerancia_anp_percentual": 0.6,
                    "status_anp": status_anp
                })

            # D. Diagnósticos e Resumo Executivo
            tem_furo_caixa = diferenca_financeira < Decimal("-1.00")
            tem_sobra_caixa = diferenca_financeira > Decimal("1.00")
            tem_divergencia_pista = abs(dif_pista_total_litros) >= Decimal("0.01")
            encerrantes_pendentes = (tot_litros_faturados_encerrante == Decimal("0.0") and tot_litros_automacao > Decimal("0.0"))
            caixa_em_aberto = not todos_caixas_fechados

            if caixa_em_aberto:
                if encerrantes_pendentes:
                    status_conciliacao = "TURNO_EM_ANDAMENTO (Caixa aberto e encerrantes pendentes)"
                    score_conformidade = 85.0
                else:
                    status_conciliacao = "TURNO_EM_ANDAMENTO"
                    score_conformidade = 90.0
            elif tem_furo_caixa and tem_divergencia_pista:
                status_conciliacao = "DIVERGENCIA_CRITICA"
                score_conformidade = 50.0
            elif encerrantes_pendentes:
                status_conciliacao = "PENDENCIA_ENCERRANTE"
                score_conformidade = 80.0
            elif tem_furo_caixa:
                status_conciliacao = "FURO_DE_CAIXA"
                score_conformidade = 70.0
            elif tem_sobra_caixa:
                status_conciliacao = "SOBRA_DE_CAIXA"
                score_conformidade = 85.0
            elif tem_divergencia_pista:
                status_conciliacao = "DIVERGENCIA_PISTA"
                score_conformidade = 75.0
            else:
                status_conciliacao = "CONCILIADO"
                score_conformidade = 100.0

            if caixa_em_aberto:
                diag_caixa = (
                    f"CAIXA EM ANDAMENTO: Operador(es) com caixa aberto no PDV. "
                    f"Faturamento PDV apurado até o momento: R$ {float(faturamento_caixa_apurado):.2f} ({origem_faturamento_caixa}). "
                    f"A conciliação definitiva de sobra/falta será apurada no encerramento formal do caixa."
                )
            elif tem_furo_caixa:
                diag_caixa = (
                    f"FURO DE CAIXA: Falta apurada de R$ {abs(float(diferenca_financeira)):.2f} "
                    f"(Caixa declarou R$ {float(faturamento_caixa_apurado):.2f} vs R$ {float(faturamento_pista_esperado):.2f} faturados na pista)."
                )
            elif tem_sobra_caixa:
                diag_caixa = (
                    f"SOBRA DE CAIXA: Sobra apurada de R$ {float(diferenca_financeira):.2f} "
                    f"(Caixa declarou R$ {float(faturamento_caixa_apurado):.2f} vs R$ {float(faturamento_pista_esperado):.2f} faturados na pista)."
                )
            else:
                diag_caixa = (
                    f"CAIXA CONCILIADO: Valores declarados batem 100% com as saídas faturadas da pista "
                    f"(R$ {float(faturamento_caixa_apurado):.2f})."
                )

            if encerrantes_pendentes:
                diag_pista = (
                    f"ENCERRANTES PENDENTES: Automação CBC04 registrou {float(tot_litros_automacao):.3f} L "
                    f"({total_abast_count} abastecimentos) totalizando R$ {float(tot_fat_automacao):.2f}, "
                    f"mas os encerrantes de fechamento ainda não foram digitados no módulo fechabomba."
                )
            elif abs(dif_pista_total_litros) < Decimal("0.01"):
                diag_pista = f"PISTA 100% CONCILIADA: Encerrantes mecânicos e automação Companytec batem perfeitamente ({float(tot_litros_faturados_encerrante):.3f} L)."
            elif dif_pista_total_litros > Decimal("0.0"):
                diag_pista = f"DIVERGÊNCIA DE PISTA: Automação registrou +{float(dif_pista_total_litros):.3f} L a mais que os encerrantes faturados."
            else:
                diag_pista = f"DIVERGÊNCIA DE PISTA: Encerrantes mecânicos avançaram +{float(abs(dif_pista_total_litros)):.3f} L além da telemetria CBC04 (possível abastecimento manual sem automação)."

            if tanques_fora_tolerancia == 0:
                diag_tanques = f"CONFORME ANP: Todos os {len(tanques_auditados)} tanques encontram-se dentro da tolerância volumétrica permitida de ±0.6%."
            else:
                diag_tanques = f"ALERTA ANP: {tanques_fora_tolerancia} tanque(s) apresentaram variação térmica/volumétrica superior ao limite legal de ±0.6%."

            recomendacoes = []
            if encerrantes_pendentes:
                recomendacoes.append("Solicitar ao chefe de pista a leitura física e o lançamento formal dos encerrantes finais no sistema ERP.")
            if caixa_em_aberto:
                recomendacoes.append("Finalizar o fechamento dos caixas no PDV para emissão da conciliação contábil definitiva.")
            elif tem_furo_caixa:
                recomendacoes.append("Conferir comprovantes de cartão e cédulas físicas com o operador de caixa para apurar o motivo da diferença.")
            elif tem_sobra_caixa:
                recomendacoes.append("Verificar se houve recebimento de cliente não lançado no caixa ou lançamento incorreto de forma de pagamento.")
            if tot_afericao_litros == Decimal("0.0"):
                recomendacoes.append("Nenhuma aferição de balde (20L) registrada para este turno.")
            else:
                recomendacoes.append(f"Registrada aferição técnica de {float(tot_afericao_litros):.2f} L em conformidade com as normas do Inmetro.")
            if tanques_fora_tolerancia > 0:
                recomendacoes.append("Verificar calibração dos bicos e medição de régua/telemetria eletrônica nos tanques com alerta.")

            resultado = {
                "status": "ok",
                "data_auditada": str(data_alvo),
                "data_solicitada": data or "hoje",
                "turno_auditado": turno or "TODOS OS TURNOS",
                "aviso_data": aviso_data,
                "resumo_executivo": {
                    "status_conciliacao": status_conciliacao,
                    "score_conformidade_pct": score_conformidade,
                    "faturamento_pista_total": float(faturamento_pista_esperado),
                    "origem_faturamento_pista": origem_faturamento_pista,
                    "faturamento_caixa_total": float(faturamento_caixa_apurado),
                    "origem_faturamento_caixa": origem_faturamento_caixa,
                    "diferenca_financeira_caixa": float(diferenca_financeira),
                    "diagnostico_caixa": diag_caixa,
                    "diagnostico_pista": diag_pista,
                    "diagnostico_tanques": diag_tanques,
                },
                "triangulacao_pista": {
                    "total_bicos_auditados": len(bicos_auditados),
                    "total_litros_bruto_encerrante": float(tot_litros_bruto_encerrante),
                    "total_litros_encerrante": float(tot_litros_faturados_encerrante),
                    "total_afericoes_litros": float(tot_afericao_litros),
                    "total_litros_faturados_encerrante": float(tot_litros_faturados_encerrante),
                    "total_faturamento_encerrante": float(tot_fat_encerrante),
                    "total_abastecimentos_automacao": total_abast_count,
                    "total_litros_automacao": float(tot_litros_automacao),
                    "total_faturamento_automacao": float(tot_fat_automacao),
                    "diferenca_litros_pista": float(dif_pista_total_litros),
                    "detalhamento_bicos": bicos_auditados,
                },
                "triangulacao_caixa": {
                    "total_caixas_auditados": len(caixas_auditados),
                    "caixas": caixas_auditados,
                    "totais_caixa": {
                        "dinheiro": float(tot_dinh),
                        "cartao": float(tot_cart),
                        "prazo": float(tot_prazo),
                        "convenio": float(tot_conv),
                        "total_declarado": float(tot_declarado),
                        "total_cupons_pdv": float(total_pedidos_pdv),
                    },
                },
                "balanco_tanques": {
                    "total_tanques_auditados": len(tanques_auditados),
                    "tanques_fora_tolerancia_anp": tanques_fora_tolerancia,
                    "detalhamento_tanques": tanques_auditados,
                },
                "recomendacoes_auditoria": recomendacoes,
            }

            resultado_limpo, _ = sanitize_dict(resultado)
            return resultado_limpo

        except Exception as e:
            return {
                "status": "indisponivel",
                "motivo": f"Falha na execução da auditoria de turno no ERP (porta 5433): {e}",
            }
