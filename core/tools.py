"""
Ferramentas de Negócio e Integração da IA (Tools).
Conecta o Agente às bases relacionais (ERP na porta 5433) e vetoriais (pgvector na porta 5434).
"""

import re
import unicodedata
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple, List, Set
from datetime import datetime, date, time, timedelta

from config.settings import DB_ERP_CONFIG
from core.rag_engine import HybridRAGEngine
from core.sanitizer import sanitize_dict

_last_working_erp_port: Optional[int] = None


def get_erp_connection(timeout: Optional[int] = None) -> psycopg2.extensions.connection:
    """
    Obtém conexão com o banco de dados ERP do posto.
    Tenta primeiramente a última porta funcional ou a configurada no .env (5433).
    Se a conexão for recusada ou falhar (ex: serviço parado no Windows),
    realiza fallback automático para a porta 5435 (ou vice-versa), garantindo resiliência.
    """
    global _last_working_erp_port
    config = dict(DB_ERP_CONFIG)
    configured_port = int(config.get("port", 5433))
    effective_timeout = timeout if timeout is not None else int(config.get("connect_timeout", 5))

    ports_to_try = []
    if _last_working_erp_port:
        ports_to_try.append(_last_working_erp_port)
    if configured_port not in ports_to_try:
        ports_to_try.append(configured_port)
    for alt in (5435, 5433):
        if alt not in ports_to_try:
            ports_to_try.append(alt)

    last_err = None
    for port in ports_to_try:
        try_config = dict(config)
        try_config["port"] = port
        try_config["connect_timeout"] = effective_timeout
        try:
            conn = psycopg2.connect(**try_config)
            _last_working_erp_port = port
            return conn
        except Exception as e:
            last_err = e
            continue

    raise last_err or psycopg2.OperationalError(
        f"Não foi possível conectar ao banco ERP ({config.get('host')}) nas portas testadas ({ports_to_try})."
    )


class PostoTools:
    """Conjunto de ferramentas operacionais executáveis pelo Agente."""

    def __init__(self, rag_engine: HybridRAGEngine):
        self.rag = rag_engine

    def dados_cadastrais_filial(self) -> dict:
        """Retorna os dados cadastrais da empresa/filial do ERP ou fallback."""
        info = {
            "idempresa": "00001",
            "nome": "POSTO PILOTO MODELO",
            "razao_social": "POSTO PILOTO MODELO LTDA",
            "cnpj": "00.000.000/0001-00",
            "endereco": "Avenida Central, 1000 - Centro",
            "pdv": "001",
        }
        try:
            conn = get_erp_connection()
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

    def consultar_conhecimento_aura(self, termo: str, top_k: int = 2, query_vector: list = None) -> dict:
        """Executa busca híbrida de auto-conhecimento e meta-RAG na base de dados da AURA."""
        return self.rag.search_hybrid_conhecimento(termo, top_k=top_k, query_vector=query_vector)

    def consultar_analise_vendas_erp(self, tipo: str = "mais_vendidos") -> dict:
        """
        Consulta dados analíticos de vendas e abastecimentos no banco ERP (porta 5433).
        Retorna últimos produtos vendidos (conveniência e pista), faturamento geral,
        dados de hoje e ranking dos mais vendidos.
        """
        try:
            conn = get_erp_connection()
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
            conn = get_erp_connection()
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
            conn = get_erp_connection()
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
            conn = get_erp_connection()
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

    @staticmethod
    def obter_consumo_benchmark(combustivel_nome: str) -> float:
        """
        Retorna a taxa diária de consumo médio de referência (litros/dia)
        típica do mercado brasileiro para postos de serviços urbanos e rodoviários.
        """
        c = (combustivel_nome or "").upper().strip()
        if "ADITIVADA" in c or "GRID" in c or "V-POWER" in c or "OCTAPRO" in c:
            return 1200.0
        elif "COMUM" in c or "GASOLINA" in c:
            return 3000.0
        elif "ETANOL" in c or "ALCOOL" in c:
            return 1500.0
        elif "S10" in c or "S-10" in c:
            return 4000.0
        elif "S500" in c or "S-500" in c or "DIESEL" in c:
            return 1800.0
        elif "ARLA" in c:
            return 150.0
        else:
            return 1000.0

    @staticmethod
    def calcular_autonomia_tanque(
        saldo: Decimal,
        capacidade: Decimal,
        consumo_diario: Decimal,
        margem_critica_pct: Decimal = Decimal("0.15"),
        data_referencia: Optional[datetime] = None
    ) -> dict:
        """
        Calcula a autonomia matemática (crítica e run-out total) de um tanque de combustível.
        Fórmula Crítica: Autonomia = (Saldo Atual - Estoque Crítico 15%) / Consumo Médio Diário.
        """
        saldo = Decimal(str(saldo if saldo is not None else 0.0))
        capacidade = Decimal(str(capacidade if capacidade is not None else 0.0))
        consumo_diario = Decimal(str(consumo_diario if consumo_diario is not None else 0.0))
        margem_critica_pct = Decimal(str(margem_critica_pct if margem_critica_pct is not None else 0.15))
        agora = data_referencia or datetime.now()

        pct_ocupacao = round(float(saldo / capacidade * Decimal("100.0")), 2) if capacidade > Decimal("0.0") else 0.0

        estoque_critico = capacidade * margem_critica_pct
        saldo_util_critico = saldo - estoque_critico

        if consumo_diario <= Decimal("0.0"):
            alerta_critico = saldo_util_critico <= Decimal("0.0")
            if saldo <= Decimal("0.0"):
                status_operacional = "ESGOTADO (SECO)"
                data_hora_critico = "JÁ EM NÍVEL CRÍTICO (< 15%)"
                data_hora_runout = "ESGOTADO (Tanque seco - 0 L)"
            elif alerta_critico:
                status_operacional = "NÍVEL CRÍTICO"
                data_hora_critico = "JÁ EM NÍVEL CRÍTICO (< 15%)"
                data_hora_runout = "SEM CONSUMO REGISTRADO"
            else:
                status_operacional = "SEM CONSUMO"
                data_hora_critico = "SEM CONSUMO REGISTRADO"
                data_hora_runout = "SEM CONSUMO REGISTRADO"

            return {
                "capacidade_litros": float(capacidade),
                "saldo_atual_litros": float(saldo),
                "ocupacao_pct": pct_ocupacao,
                "estoque_critico_15pct_litros": float(round(estoque_critico, 2)),
                "saldo_util_critico_litros": float(round(max(Decimal("0.0"), saldo_util_critico), 2)),
                "consumo_diario_litros": 0.0,
                "consumo_horario_litros": 0.0,
                "autonomia_critica_dias": 0.0,
                "autonomia_critica_horas": 0.0,
                "autonomia_runout_dias": 0.0,
                "autonomia_runout_horas": 0.0,
                "data_hora_critico": data_hora_critico,
                "data_hora_runout": data_hora_runout,
                "alerta_critico": alerta_critico,
                "status_operacional": status_operacional,
            }

        consumo_horario = consumo_diario / Decimal("24.0")

        # 1. Autonomia até o Nível Crítico (15% da capacidade)
        if saldo_util_critico <= Decimal("0.0"):
            autonomia_critica_dias = Decimal("0.0")
            autonomia_critica_horas = Decimal("0.0")
            data_hora_critico = "JÁ EM NÍVEL CRÍTICO (< 15%)"
            alerta_critico = True
            status_operacional = "NÍVEL CRÍTICO" if saldo > Decimal("0.0") else "ESGOTADO (SECO)"
        else:
            autonomia_critica_dias = saldo_util_critico / consumo_diario
            autonomia_critica_horas = autonomia_critica_dias * Decimal("24.0")
            dt_crit = agora + timedelta(hours=float(autonomia_critica_horas))
            data_hora_critico = dt_crit.strftime("%Y-%m-%d %H:%M")
            alerta_critico = False
            status_operacional = "OPERACIONAL NORMAL"

        # 2. Autonomia até o Esgotamento Total (Run-Out / Tanque Seco 0 Litros)
        if saldo <= Decimal("0.0"):
            autonomia_runout_dias = Decimal("0.0")
            autonomia_runout_horas = Decimal("0.0")
            data_hora_runout = "ESGOTADO (Tanque seco - 0 L)"
        else:
            autonomia_runout_dias = saldo / consumo_diario
            autonomia_runout_horas = autonomia_runout_dias * Decimal("24.0")
            dt_ro = agora + timedelta(hours=float(autonomia_runout_horas))
            data_hora_runout = dt_ro.strftime("%Y-%m-%d %H:%M")

        return {
            "capacidade_litros": float(round(capacidade, 2)),
            "saldo_atual_litros": float(round(saldo, 2)),
            "ocupacao_pct": pct_ocupacao,
            "estoque_critico_15pct_litros": float(round(estoque_critico, 2)),
            "saldo_util_critico_litros": float(round(max(Decimal("0.0"), saldo_util_critico), 2)),
            "consumo_diario_litros": float(round(consumo_diario, 2)),
            "consumo_horario_litros": float(round(consumo_horario, 2)),
            "autonomia_critica_dias": float(round(autonomia_critica_dias, 2)),
            "autonomia_critica_horas": float(round(autonomia_critica_horas, 2)),
            "autonomia_runout_dias": float(round(autonomia_runout_dias, 2)),
            "autonomia_runout_horas": float(round(autonomia_runout_horas, 2)),
            "data_hora_critico": data_hora_critico,
            "data_hora_runout": data_hora_runout,
            "alerta_critico": alerta_critico,
            "status_operacional": status_operacional,
        }

    @staticmethod
    def calcular_sugestao_carreta(
        capacidade: Decimal,
        saldo: Decimal,
        multiplo_compartimento: Decimal = Decimal("5000.0")
    ) -> dict:
        """
        Calcula o espaço livre para descarga (ullage) e a sugestão de pedido
        padronizado em compartimentos estanques de carreta/caminhão-tanque (5k, 10k, 15k L).
        """
        capacidade = Decimal(str(capacidade if capacidade is not None else 0.0))
        saldo = Decimal(str(saldo if saldo is not None else 0.0))
        multiplo = Decimal(str(multiplo_compartimento if multiplo_compartimento is not None else 5000.0))

        # Espaço físico seguro limitado à capacidade total (evita transbordo em caso de saldo contábil negativo)
        ullage = max(Decimal("0.0"), min(capacidade, capacidade - saldo))
        pct_livre = round(float(ullage / capacidade * Decimal("100.0")), 2) if capacidade > Decimal("0.0") else 0.0

        if multiplo > Decimal("0.0"):
            compartimentos_5k = int(ullage // multiplo)
            volume_sugerido = Decimal(str(compartimentos_5k)) * multiplo
        else:
            compartimentos_5k = 0
            volume_sugerido = Decimal("0.0")

        return {
            "espaco_livre_ullage_litros": float(round(ullage, 2)),
            "percentual_livre_pct": pct_livre,
            "compartimentos_5k": compartimentos_5k,
            "volume_sugerido_litros": float(round(volume_sugerido, 2)),
            "multiplo_padrao_litros": float(multiplo),
        }

    def prever_esgotamento_tanques(
        self,
        filtro_combustivel: Optional[str] = None,
        consumo_diario_custom: Optional[Dict[str, float]] = None,
        margem_critica_pct: float = 0.15,
        data_referencia: Optional[datetime] = None,
    ) -> dict:
        """
        Motor de Previsão de Esgotamento de Combustível (Run-Out Forecast) &
        Sugestão Inteligente de Pedidos de Caminhão-Tanque.
        Conecta ao ERP PostgreSQL (porta 5433).
        """
        try:
            conn = get_erp_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Posição atual dos tanques (com fallback para produtos via codlmc)
                cur.execute("""
                    SELECT 
                        TRIM(t.codtan) AS codtan,
                        COALESCE(
                            NULLIF(TRIM(t.prl_ds_produto_lmc), ''),
                            NULLIF(TRIM(p.nompro), ''),
                            'COMBUSTÍVEL ' || TRIM(t.codtan)
                        ) AS combustivel,
                        ROUND(COALESCE(t.capacidade, 0)::numeric, 2) AS capacidade_litros,
                        ROUND(COALESCE(t.qtdeat, 0)::numeric, 2) AS saldo_atual_litros
                    FROM tanques t
                    LEFT JOIN (
                        SELECT DISTINCT ON (TRIM(codlmc)) TRIM(codlmc) AS codlmc, nompro
                        FROM produtos
                        WHERE codlmc IS NOT NULL AND TRIM(codlmc) != ''
                        ORDER BY TRIM(codlmc), codpro
                    ) p ON p.codlmc = TRIM(t.codlmc)
                    ORDER BY t.codtan;
                """)
                linhas_tanques = cur.fetchall()

                # 2. Vínculos de bicos por tanque na tabela bombas
                cur.execute("""
                    SELECT 
                        TRIM(b.codbom) AS codbom,
                        TRIM(b.codtan) AS codtan,
                        TRIM(b.codpro) AS codpro
                    FROM bombas b
                    WHERE b.codtan IS NOT NULL;
                """)
                linhas_bombas = cur.fetchall()

                # 3. Telemetria de consumo em abastecimentos
                cur.execute("""
                    SELECT 
                        COALESCE(TRIM(a.tanque), TRIM(b.codtan)) AS codtan,
                        TRIM(a.codpro) AS codpro,
                        COALESCE(TRIM(p.nompro), TRIM(t.prl_ds_produto_lmc)) AS produto_nome,
                        COUNT(*)::int AS total_abastecimentos,
                        ROUND(COALESCE(SUM(a.litros), 0)::numeric, 3) AS total_litros,
                        MIN(a.data) AS data_min,
                        MAX(a.data) AS data_max,
                        COUNT(DISTINCT a.data)::int AS dias_com_venda
                    FROM abastecimentos a
                    LEFT JOIN bombas b ON b.codbom = a.bomba
                    LEFT JOIN tanques t ON t.codtan = COALESCE(a.tanque, b.codtan)
                    LEFT JOIN produtos p ON p.codpro = a.codpro
                    WHERE a.abt_bl_venda_cancelada IS NOT TRUE
                    GROUP BY COALESCE(TRIM(a.tanque), TRIM(b.codtan)), TRIM(a.codpro), p.nompro, t.prl_ds_produto_lmc;
                """)
                linhas_telemetria = cur.fetchall()

                # 4. Total de abastecimentos gerais na base para metadados
                cur.execute("""
                    SELECT 
                        COUNT(*)::int AS total_abast_geral,
                        ROUND(COALESCE(SUM(litros), 0)::numeric, 3) AS total_litros_geral,
                        MIN(data) AS primeira_data_abast,
                        MAX(data) AS ultima_data_abast,
                        COUNT(DISTINCT data)::int AS total_dias_base
                    FROM abastecimentos
                    WHERE abt_bl_venda_cancelada IS NOT TRUE;
                """)
                telemetria_geral = cur.fetchone() or {}

                conn.close()

            agora = data_referencia or datetime.now()

            # Mapeamento de bicos por tanque
            bicos_por_tanque: Dict[str, List[str]] = {}
            for rb in linhas_bombas:
                c_tan = rb['codtan']
                if c_tan:
                    bicos_por_tanque.setdefault(c_tan, []).append(rb['codbom'])

            # Mapeamento de telemetria por tanque
            telemetria_por_tanque: Dict[str, List[dict]] = {}
            for rt in linhas_telemetria:
                c_tan = rt['codtan']
                if c_tan:
                    telemetria_por_tanque.setdefault(c_tan, []).append(rt)

            # Função auxiliar interna de normalização de categoria de combustível
            def normalizar_categoria(nome: str) -> str:
                n = (nome or "").upper().strip()
                if "ADITIVADA" in n or "GRID" in n or "V-POWER" in n:
                    return "GASOLINA ADITIVADA"
                elif "COMUM" in n or "GASOLINA" in n:
                    return "GASOLINA COMUM"
                elif "ETANOL" in n or "ALCOOL" in n:
                    return "ETANOL"
                elif "S10" in n or "S-10" in n:
                    return "DIESEL S10"
                elif "S500" in n or "S-500" in n or "DIESEL" in n:
                    return "DIESEL S500"
                elif "ARLA" in n:
                    return "ARLA"
                return n or "OUTROS"

            # Identificar tanques por categoria normalizada
            tanques_por_cat: Dict[str, List[dict]] = {}
            for t in linhas_tanques:
                cat = normalizar_categoria(t['combustivel'])
                tanques_por_cat.setdefault(cat, []).append(t)

            # Determinar a taxa diária de consumo para cada combustível
            consumo_combustivel_info: Dict[str, dict] = {}
            dias_base = max(1, int(telemetria_geral.get('total_dias_base') or 1))

            for cat, lista_tanques in tanques_por_cat.items():
                # Verificar se há override explícito customizado
                custom_rate = None
                if consumo_diario_custom:
                    for k, v in consumo_diario_custom.items():
                        if k.upper() in cat or cat in k.upper():
                            custom_rate = float(v)
                            break

                if custom_rate is not None:
                    consumo_combustivel_info[cat] = {
                        "taxa_diaria": custom_rate,
                        "origem": "parametro_customizado",
                        "aviso": None
                    }
                else:
                    # Verificar telemetria real em abastecimentos
                    abasts_cat = []
                    for t in lista_tanques:
                        abasts_cat.extend(telemetria_por_tanque.get(t['codtan'], []))

                    total_litros_cat = sum(float(r['total_litros'] or 0.0) for r in abasts_cat)
                    total_abast_cat = sum(int(r['total_abastecimentos'] or 0) for r in abasts_cat)

                    # Critério para telemetria significativa: >= 100 L e >= 10 abastecimentos
                    if total_litros_cat >= 100.0 and total_abast_cat >= 10:
                        taxa_calc = round(total_litros_cat / dias_base, 2)
                        consumo_combustivel_info[cat] = {
                            "taxa_diaria": max(10.0, taxa_calc),
                            "origem": "historico_telemetria",
                            "aviso": f"Consumo calculado a partir de {total_abast_cat} abastecimentos ({total_litros_cat:.2f} L em {dias_base} dias)."
                        }
                    else:
                        taxa_bm = self.obter_consumo_benchmark(cat)
                        consumo_combustivel_info[cat] = {
                            "taxa_diaria": taxa_bm,
                            "origem": "referencia_mercado (fallback telemetria reduzida)",
                            "aviso": f"Base local com registros reduzidos ({total_litros_cat:.2f} L em {total_abast_cat} abastecimentos). Aplicada taxa de referência de mercado ({taxa_bm:.1f} L/dia)."
                        }

            # Processamento individual de cada tanque
            tanques_processados = []
            sugestoes_pedidos = []

            for t in linhas_tanques:
                codtan = t['codtan']
                comb = t['combustivel']
                cat = normalizar_categoria(comb)
                cap = Decimal(str(t['capacidade_litros'] or 0.0))
                saldo = Decimal(str(t['saldo_atual_litros'] or 0.0))
                bicos = bicos_por_tanque.get(codtan, [])

                # Se o tanque for mini-tanque ou reserva inativa (capacidade <= 1000 e saldo == 0)
                is_inativo = (cap <= Decimal("1000.0") and saldo == Decimal("0.0"))
                tanques_cat_op = [tk for tk in tanques_por_cat.get(cat, []) if not (Decimal(str(tk['capacidade_litros'] or 0)) <= Decimal("1000.0") and Decimal(str(tk['saldo_atual_litros'] or 0)) == Decimal("0.0"))]

                # Consumo específico do tanque (ou override por código de tanque)
                consumo_tanque_custom = None
                if consumo_diario_custom:
                    if codtan in consumo_diario_custom:
                        consumo_tanque_custom = float(consumo_diario_custom[codtan])
                    elif f"tanque {codtan}".lower() in [k.lower() for k in consumo_diario_custom.keys()]:
                        for k, v in consumo_diario_custom.items():
                            if str(int(codtan)) in k:
                                consumo_tanque_custom = float(v)
                                break

                info_comb = consumo_combustivel_info.get(cat, {"taxa_diaria": 1000.0, "origem": "referencia_mercado"})

                if is_inativo:
                    consumo_diario_tanque = Decimal("0.0")
                    origem_taxa = "tanque_inativo"
                elif consumo_tanque_custom is not None:
                    consumo_diario_tanque = Decimal(str(consumo_tanque_custom))
                    origem_taxa = "parametro_customizado_tanque"
                else:
                    taxa_total_cat = Decimal(str(info_comb["taxa_diaria"]))
                    qtd_op = max(1, len(tanques_cat_op))
                    # Distribuição igualitária entre os tanques operacionais da mesma categoria
                    consumo_diario_tanque = round(taxa_total_cat / Decimal(str(qtd_op)), 2)
                    origem_taxa = info_comb["origem"]

                # Cálculos matemáticos
                res_auto = self.calcular_autonomia_tanque(
                    saldo=saldo,
                    capacidade=cap,
                    consumo_diario=consumo_diario_tanque,
                    margem_critica_pct=Decimal(str(margem_critica_pct)),
                    data_referencia=agora
                )
                res_carr = self.calcular_sugestao_carreta(
                    capacidade=cap,
                    saldo=saldo,
                    multiplo_compartimento=Decimal("5000.0")
                )

                # Avaliação de Urgência e Prazo de Compra
                if is_inativo:
                    urgencia = "INATIVO"
                    prazo_ideal = "Tanque inativo / reserva técnica desativada"
                    status_operacional = "INATIVO"
                elif saldo <= Decimal("0.0"):
                    urgencia = "CRÍTICA / IMEDIATA"
                    prazo_ideal = "Comprar IMEDIATAMENTE (tanque seco - 0 litros)"
                    status_operacional = "ESGOTADO (SECO)"
                elif res_auto["alerta_critico"]:
                    urgencia = "CRÍTICA / IMEDIATA"
                    prazo_ideal = "Comprar IMEDIATAMENTE hoje (saldo em nível de risco abaixo de 15%)"
                    status_operacional = "NÍVEL CRÍTICO"
                elif res_auto["autonomia_critica_horas"] <= 24.0:
                    urgencia = "ALTA"
                    prazo_ideal = "Emitir pedido hoje para entrega em até 24 horas"
                    status_operacional = "ALERTA (Próximo do Crítico)"
                elif res_auto["autonomia_critica_dias"] <= 3.0:
                    urgencia = "MÉDIA"
                    prazo_ideal = "Emitir pedido em até 48 horas (Atenção para o Fim de Semana)"
                    status_operacional = "ATENÇÃO"
                else:
                    urgencia = "CONFORTÁVEL"
                    dias_reaval = max(1, int(res_auto["autonomia_critica_dias"] - 2))
                    prazo_ideal = f"Estoque regular. Reavaliar compra em {dias_reaval} dias"
                    status_operacional = "OPERACIONAL NORMAL"

                item_tanque = {
                    "codtan": codtan,
                    "combustivel": comb,
                    "categoria": cat,
                    "capacidade_litros": res_auto["capacidade_litros"],
                    "saldo_atual_litros": res_auto["saldo_atual_litros"],
                    "ocupacao_pct": res_auto["ocupacao_pct"],
                    "estoque_critico_15pct_litros": res_auto["estoque_critico_15pct_litros"],
                    "saldo_util_critico_litros": res_auto["saldo_util_critico_litros"],
                    "consumo_diario_litros": res_auto["consumo_diario_litros"],
                    "consumo_horario_litros": res_auto["consumo_horario_litros"],
                    "origem_taxa_consumo": origem_taxa,
                    "autonomia_critica_dias": res_auto["autonomia_critica_dias"],
                    "autonomia_critica_horas": res_auto["autonomia_critica_horas"],
                    "autonomia_runout_dias": res_auto["autonomia_runout_dias"],
                    "autonomia_runout_horas": res_auto["autonomia_runout_horas"],
                    "data_hora_critico": res_auto["data_hora_critico"],
                    "data_hora_runout": res_auto["data_hora_runout"],
                    "espaco_livre_ullage_litros": res_carr["espaco_livre_ullage_litros"],
                    "percentual_livre_pct": res_carr["percentual_livre_pct"],
                    "compartimentos_5k": res_carr["compartimentos_5k"],
                    "volume_sugerido_litros": res_carr["volume_sugerido_litros"],
                    "bicos_conectados": bicos,
                    "alerta_critico": res_auto["alerta_critico"],
                    "status_operacional": status_operacional,
                    "urgencia_pedido": urgencia,
                    "prazo_ideal_compra": prazo_ideal,
                }
                tanques_processados.append(item_tanque)

                # Sugestão de pedido se o tanque for operacional e houver espaço para descarga
                if not is_inativo and res_carr["volume_sugerido_litros"] > 0:
                    sugestoes_pedidos.append({
                        "tanque": codtan,
                        "combustivel": comb,
                        "categoria": cat,
                        "volume_sugerido_litros": res_carr["volume_sugerido_litros"],
                        "compartimentos_5k": res_carr["compartimentos_5k"],
                        "espaco_livre_ullage_litros": res_carr["espaco_livre_ullage_litros"],
                        "autonomia_critica_dias": res_auto["autonomia_critica_dias"],
                        "autonomia_runout_horas": res_auto["autonomia_runout_horas"],
                        "urgencia": urgencia,
                        "prazo_ideal": prazo_ideal,
                        "justificativa": (
                            f"Saldo atual de {res_auto['saldo_atual_litros']} L ({res_auto['ocupacao_pct']}%) "
                            f"com autonomia de {res_auto['autonomia_runout_horas']:.1f}h. "
                            f"Espaço livre comporta {res_carr['compartimentos_5k']} compartimento(s) de 5.000 L ({res_carr['volume_sugerido_litros']} L)."
                        )
                    })

            # Consolidação por Categoria de Combustível
            resumo_combustiveis = []
            for cat, t_list in tanques_por_cat.items():
                t_processados_cat = [t for t in tanques_processados if t['categoria'] == cat and t['status_operacional'] != 'INATIVO']
                if not t_processados_cat:
                    continue

                cap_tot = sum(t['capacidade_litros'] for t in t_processados_cat)
                saldo_tot = sum(t['saldo_atual_litros'] for t in t_processados_cat)
                crit_tot = sum(t['estoque_critico_15pct_litros'] for t in t_processados_cat)
                ullage_tot = sum(t['espaco_livre_ullage_litros'] for t in t_processados_cat)
                vol_sug_tot = sum(t['volume_sugerido_litros'] for t in t_processados_cat)
                bocas_tot = sum(t['compartimentos_5k'] for t in t_processados_cat)

                taxa_dia_tot = consumo_combustivel_info.get(cat, {}).get("taxa_diaria", 1000.0)
                taxa_hora_tot = round(taxa_dia_tot / 24.0, 2) if taxa_dia_tot > 0 else 0.0

                saldo_util_tot = max(0.0, saldo_tot - crit_tot)
                pct_ocup_media = round((saldo_tot / cap_tot * 100.0), 2) if cap_tot > 0 else 0.0

                if taxa_dia_tot <= 0.0:
                    auto_crit_dias = 0.0
                    auto_crit_horas = 0.0
                    auto_ro_dias = 0.0
                    auto_ro_horas = 0.0
                    alerta_crit = saldo_util_tot <= 0.0
                    dt_crit_txt = "JÁ EM NÍVEL CRÍTICO (< 15%)" if alerta_crit else "SEM CONSUMO REGISTRADO"
                    dt_ro_txt = "ESGOTADO (Tanque seco - 0 L)" if saldo_tot <= 0.0 else "SEM CONSUMO REGISTRADO"
                    urg_comb = "CRÍTICA / IMEDIATA" if alerta_crit else "SEM CONSUMO"
                    prazo_comb = "Comprar IMEDIATAMENTE (reserva de segurança de 15% atingida)" if alerta_crit else "Sem consumo para estimar prazo"
                else:
                    if saldo_util_tot <= 0.0:
                        auto_crit_dias = 0.0
                        auto_crit_horas = 0.0
                        dt_crit_txt = "JÁ EM NÍVEL CRÍTICO (< 15%)"
                        alerta_crit = True
                    else:
                        auto_crit_dias = round(saldo_util_tot / taxa_dia_tot, 2)
                        auto_crit_horas = round(auto_crit_dias * 24.0, 2)
                        dt_c = agora + timedelta(hours=auto_crit_horas)
                        dt_crit_txt = dt_c.strftime("%Y-%m-%d %H:%M")
                        alerta_crit = False

                    if saldo_tot <= 0.0:
                        auto_ro_dias = 0.0
                        auto_ro_horas = 0.0
                        dt_ro_txt = "ESGOTADO (Tanque seco - 0 L)"
                    else:
                        auto_ro_dias = round(saldo_tot / taxa_dia_tot, 2)
                        auto_ro_horas = round(auto_ro_dias * 24.0, 2)
                        dt_ro = agora + timedelta(hours=auto_ro_horas)
                        dt_ro_txt = dt_ro.strftime("%Y-%m-%d %H:%M")

                    if alerta_crit:
                        urg_comb = "CRÍTICA / IMEDIATA"
                        prazo_comb = "Comprar IMEDIATAMENTE (reserva de segurança de 15% atingida)"
                    elif auto_crit_horas <= 24.0:
                        urg_comb = "ALTA"
                        prazo_comb = "Emitir pedido hoje para entrega em até 24h"
                    elif auto_crit_dias <= 3.0:
                        urg_comb = "MÉDIA"
                        prazo_comb = "Emitir pedido em até 48h (Atenção para o Fim de Semana)"
                    else:
                        urg_comb = "CONFORTÁVEL"
                        prazo_comb = f"Estoque regular. Reavaliar em {max(1, int(auto_crit_dias - 2))} dias"

                resumo_combustiveis.append({
                    "combustivel": cat,
                    "tanques_vinculados": [t['codtan'] for t in t_processados_cat],
                    "capacidade_total_litros": cap_tot,
                    "saldo_total_litros": round(saldo_tot, 2),
                    "ocupacao_media_pct": pct_ocup_media,
                    "estoque_critico_15pct_litros": round(crit_tot, 2),
                    "saldo_util_critico_litros": round(saldo_util_tot, 2),
                    "consumo_medio_diario_litros": round(taxa_dia_tot, 2),
                    "consumo_medio_horario_litros": taxa_hora_tot,
                    "origem_consumo": consumo_combustivel_info.get(cat, {}).get("origem"),
                    "aviso_consumo": consumo_combustivel_info.get(cat, {}).get("aviso"),
                    "autonomia_critica_dias": auto_crit_dias,
                    "autonomia_critica_horas": auto_crit_horas,
                    "autonomia_runout_dias": auto_ro_dias,
                    "autonomia_runout_horas": auto_ro_horas,
                    "data_hora_critico": dt_crit_txt,
                    "data_hora_runout": dt_ro_txt,
                    "espaco_livre_descarga_ullage": round(ullage_tot, 2),
                    "volume_sugerido_compra_litros": vol_sug_tot,
                    "compartimentos_5k_sugeridos": bocas_tot,
                    "alerta_critico": alerta_crit,
                    "urgencia_pedido": urg_comb,
                    "prazo_ideal_compra": prazo_comb,
                })

            # Ordenação de urgência: prioridade para tanques com menor autonomia
            sugestoes_pedidos.sort(key=lambda s: (s['autonomia_critica_dias'], s['autonomia_runout_horas']))

            # Aplicação do Filtro de Combustível / Tanque (se especificado)
            tanques_retorno = tanques_processados
            combustiveis_retorno = resumo_combustiveis
            sugestoes_retorno = sugestoes_pedidos

            if filtro_combustivel:
                filtro_clean = str(filtro_combustivel).upper().strip()
                tanques_retorno = [
                    t for t in tanques_processados
                    if filtro_clean in t['combustivel'].upper() or filtro_clean in t['categoria'].upper() or filtro_clean == t['codtan'] or filtro_clean in f"TANQUE {t['codtan']}".upper()
                ]
                combustiveis_retorno = [
                    c for c in resumo_combustiveis
                    if filtro_clean in c['combustivel'].upper() or any(filtro_clean == t_cod or filtro_clean in f"TANQUE {t_cod}".upper() for t_cod in c.get('tanques_vinculados', []))
                ]
                sugestoes_retorno = [
                    s for s in sugestoes_pedidos
                    if filtro_clean in s['combustivel'].upper() or filtro_clean in s['categoria'].upper() or filtro_clean == s['tanque'] or filtro_clean in f"TANQUE {s['tanque']}".upper()
                ]

            tot_vol_sugerido = sum(s['volume_sugerido_litros'] for s in sugestoes_retorno)
            tot_bocas_5k = sum(s['compartimentos_5k'] for s in sugestoes_retorno)

            # Tanque Mais Crítico (calculado no escopo filtrado do retorno)
            tanques_ativos = [t for t in tanques_retorno if t['status_operacional'] != 'INATIVO']
            tanque_mais_critico = None
            tanque_operacional_mais_critico = None
            tanques_zerados_secos = [t['codtan'] for t in tanques_ativos if t['saldo_atual_litros'] <= 0]

            if tanques_ativos:
                tanque_mais_critico = min(tanques_ativos, key=lambda t: (t['autonomia_runout_horas'], t['ocupacao_pct']))
                tanques_com_saldo = [t for t in tanques_ativos if t['saldo_atual_litros'] > 0]
                if tanques_com_saldo:
                    tanque_operacional_mais_critico = min(tanques_com_saldo, key=lambda t: (t['autonomia_runout_horas'], t['ocupacao_pct']))
                else:
                    tanque_operacional_mais_critico = tanque_mais_critico

            # Combustível Mais Urgente (calculado no escopo filtrado do retorno)
            combustivel_mais_urgente = None
            if combustiveis_retorno:
                combustivel_mais_urgente = min(combustiveis_retorno, key=lambda c: (c['autonomia_critica_dias'], c['autonomia_runout_horas']))

            # Alerta Preventivo de Fim de Semana (calculado no escopo filtrado do retorno)
            combustiveis_em_risco_fds = [
                c['combustivel'] for c in combustiveis_retorno
                if c['autonomia_runout_dias'] < 4.0 or c['autonomia_critica_dias'] < 2.5
            ]
            alerta_fim_de_semana = len(combustiveis_em_risco_fds) > 0
            if alerta_fim_de_semana:
                diag_fds = (
                    f"ALERTA FIM DE SEMANA ATIVO: {len(combustiveis_em_risco_fds)} combustível(is) "
                    f"({', '.join(combustiveis_em_risco_fds)}) possuem autonomia inferior a 4 dias e podem secar "
                    f"durante o pico de movimento do sábado/domingo. Como as bases das distribuidoras não faturam no domingo, "
                    f"recomenda-se emitir os pedidos imediatamente para recebimento até sexta-feira."
                )
            elif not combustiveis_retorno:
                diag_fds = "Nenhum combustível encontrado para o filtro aplicado."
            else:
                diag_fds = "Estoque suficiente para atravessar o fim de semana com margem de segurança confortável nos combustíveis analisados."

            # Montagem do Resultado Estruturado
            resultado = {
                "status": "ok",
                "timestamp_previsao": agora.strftime("%Y-%m-%d %H:%M"),
                "filtro_aplicado": filtro_combustivel,
                "resumo_executivo": {
                    "status_geral": "ALERTA_ESTOQUE_CRITICO" if any(t.get('alerta_critico') for t in tanques_retorno) else ("ESTOQUE_ESTAVEL" if tanques_retorno else "SEM_REGISTROS"),
                    "tanque_mais_critico": {
                        "codtan": tanque_mais_critico['codtan'],
                        "combustivel": tanque_mais_critico['combustivel'],
                        "saldo_atual_litros": tanque_mais_critico['saldo_atual_litros'],
                        "capacidade_litros": tanque_mais_critico['capacidade_litros'],
                        "ocupacao_pct": tanque_mais_critico['ocupacao_pct'],
                        "autonomia_critica_horas": tanque_mais_critico['autonomia_critica_horas'],
                        "autonomia_runout_horas": tanque_mais_critico['autonomia_runout_horas'],
                        "autonomia_runout_dias": tanque_mais_critico['autonomia_runout_dias'],
                        "run_out_estimado": tanque_mais_critico['data_hora_runout'],
                        "urgencia": tanque_mais_critico['urgencia_pedido'],
                        "prazo_ideal": tanque_mais_critico['prazo_ideal_compra']
                    } if tanque_mais_critico else None,
                    "tanque_operacional_mais_critico": {
                        "codtan": tanque_operacional_mais_critico['codtan'],
                        "combustivel": tanque_operacional_mais_critico['combustivel'],
                        "saldo_atual_litros": tanque_operacional_mais_critico['saldo_atual_litros'],
                        "capacidade_litros": tanque_operacional_mais_critico['capacidade_litros'],
                        "ocupacao_pct": tanque_operacional_mais_critico['ocupacao_pct'],
                        "autonomia_critica_horas": tanque_operacional_mais_critico['autonomia_critica_horas'],
                        "autonomia_runout_horas": tanque_operacional_mais_critico['autonomia_runout_horas'],
                        "autonomia_runout_dias": tanque_operacional_mais_critico['autonomia_runout_dias'],
                        "run_out_estimado": tanque_operacional_mais_critico['data_hora_runout'],
                        "urgencia": tanque_operacional_mais_critico['urgencia_pedido'],
                        "prazo_ideal": tanque_operacional_mais_critico['prazo_ideal_compra']
                    } if tanque_operacional_mais_critico else None,
                    "tanques_zerados_secos": tanques_zerados_secos,
                    "combustivel_mais_urgente": combustivel_mais_urgente['combustivel'] if combustivel_mais_urgente else None,
                    "total_volume_sugerido_litros": tot_vol_sugerido,
                    "total_compartimentos_5k": tot_bocas_5k,
                    "alerta_fim_de_semana": alerta_fim_de_semana,
                    "combustiveis_em_risco_fim_de_semana": combustiveis_em_risco_fds,
                    "diagnostico_fim_de_semana": diag_fds,
                },
                "previsao_por_combustivel": combustiveis_retorno,
                "detalhamento_tanques": tanques_retorno,
                "sugestoes_pedidos_carreta": sugestoes_retorno,
                "telemetria_consumo": {
                    "total_abastecimentos_base": telemetria_geral.get('total_abast_geral', 0),
                    "total_litros_base": float(telemetria_geral.get('total_litros_geral') or 0.0),
                    "periodo_analisado": f"{telemetria_geral.get('primeira_data_abast')} a {telemetria_geral.get('ultima_data_abast')}",
                    "margem_critica_adotada_pct": margem_critica_pct * 100.0,
                    "multiplo_padrao_compartimento_litros": 5000.0
                }
            }

            resultado_limpo, _ = sanitize_dict(resultado)
            return resultado_limpo

        except Exception as e:
            return {
                "status": "indisponivel",
                "motivo": f"Falha na previsão de esgotamento de tanques no ERP (porta 5433): {e}",
            }

    @staticmethod
    def calcular_vazao_bico(litros: Any, tempo: Any, produto_nome: str = "") -> dict:
        """
        Calcula a vazão em Litros/Minuto (L/min) a partir do volume e do tempo de abastecimento.
        Avalia se a vazão está normal (35-45 L/min), lenta (25-30 L/min) ou crítica (< 25 L/min).
        """
        if tempo is None or str(tempo).strip() == "":
            return {
                "tempo_segundos": None,
                "vazao_l_min": None,
                "status_vazao": "SEM_REGISTRO_TEMPO",
                "alerta_filtro_lento": False,
                "recomendacao": "Tempo de abastecimento não registrado pela automação CBC04."
            }

        segundos = 0.0
        try:
            if isinstance(tempo, (int, float, Decimal)):
                segundos = float(tempo)
            else:
                t_str = str(tempo).strip()
                if ":" in t_str:
                    parts = t_str.split(":")
                    if len(parts) == 2:
                        segundos = float(parts[0]) * 60.0 + float(parts[1])
                    elif len(parts) == 3:
                        segundos = float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
                    else:
                        segundos = float(parts[0])
                else:
                    clean = re.sub(r"[^\d.]", "", t_str)
                    segundos = float(clean) if clean else 0.0
        except Exception:
            segundos = 0.0

        vol = float(litros or 0.0)
        if segundos <= 0.0 or vol <= 0.0:
            return {
                "tempo_segundos": segundos,
                "vazao_l_min": 0.0,
                "status_vazao": "SEM_FLUXO",
                "alerta_filtro_lento": False,
                "recomendacao": "Abastecimento sem volume ou tempo computado."
            }

        vazao = round((vol / (segundos / 60.0)), 2)

        # Regra de Arla32 (vazão nominal reduzida ~15-20 L/min)
        is_arla = "ARLA" in (produto_nome or "").upper()
        limite_critico = 10.0 if is_arla else 25.0
        limite_alerta = 15.0 if is_arla else 30.0

        if vazao < limite_critico:
            status = "CRÍTICO_FILTRO_OBSTRUÍDO"
            alerta = True
            rec = (
                f"Alerta crítico: Vazão média de {vazao:.1f} L/min severamente abaixo de {limite_critico} L/min. "
                f"Filtro de linha/bomba obstruído. Trocar elemento filtrante com urgência para evitar "
                f"aquecimento e travamento do motor da bomba."
            )
        elif vazao < limite_alerta:
            status = "ALERTA_VAZAO_LENTA"
            alerta = True
            rec = (
                f"Atenção operacional: Vazão lenta de {vazao:.1f} L/min (abaixo de {limite_alerta} L/min). "
                f"Início de colmatação do filtro de combustível. Agendar substituição preventiva do filtro."
            )
        elif vazao <= 50.0:
            status = "REGULAR_NORMAL"
            alerta = False
            rec = f"Vazão de {vazao:.1f} L/min em faixa operacional padrão comercial (35 a 45 L/min)."
        else:
            status = "ALTA_VAZAO"
            alerta = False
            rec = "Vazão de alto fluxo (bomba especial para caminhões/diesel ou descalibração volumétrica)."

        return {
            "tempo_segundos": round(segundos, 1),
            "vazao_l_min": vazao,
            "status_vazao": status,
            "alerta_filtro_lento": alerta,
            "recomendacao": rec
        }

    @staticmethod
    def calcular_conversao_aditivada(litros_comum: Any, litros_aditivada: Any) -> dict:
        """
        Calcula o índice de conversão de Gasolina Aditivada sobre o total de Gasolina vendida.
        """
        l_comum = max(0.0, float(litros_comum or 0.0))
        l_adit = max(0.0, float(litros_aditivada or 0.0))
        total_gas = l_comum + l_adit

        if total_gas <= 0.0:
            return {
                "total_gasolina_litros": 0.0,
                "gasolina_comum_litros": 0.0,
                "gasolina_aditivada_litros": 0.0,
                "conversao_aditivada_pct": 0.0,
                "classificacao_conversao": "SEM_VENDAS_GASOLINA",
                "avaliacao": "Sem volume de gasolina registrado no período."
            }

        taxa = round((l_adit / total_gas) * 100.0, 2)
        if taxa >= 30.0:
            clas = "EXCELENTE"
            aval = f"Alta performance comercial ({taxa}%). Superou a meta de mercado (30%) com alta geração de margem líquida."
        elif taxa >= 15.0:
            clas = "BOM"
            aval = f"Desempenho satisfatório ({taxa}%). Conversão dentro da média recomendada para postos urbanos."
        elif taxa >= 5.0:
            clas = "REGULAR"
            aval = f"Conversão moderada ({taxa}%). Oportunidade de alavancagem de margem via abordagem ativa de aditivada no box."
        else:
            clas = "BAIXO"
            aval = f"Baixa conversão ({taxa}%). Concentração excessiva em Gasolina Comum de baixa margem. Recomendado treinamento de vendas."

        return {
            "total_gasolina_litros": round(total_gas, 3),
            "gasolina_comum_litros": round(l_comum, 3),
            "gasolina_aditivada_litros": round(l_adit, 3),
            "conversao_aditivada_pct": taxa,
            "classificacao_conversao": clas,
            "avaliacao": aval
        }

    def auditar_desempenho_pista_frentistas(
        self,
        filtro: Optional[str] = None,
        data: Optional[str] = None,
        turno: Optional[str] = None,
        frentista: Optional[str] = None,
        bico: Optional[str] = None,
        vazao_bicos_custom: Optional[Dict[str, float]] = None
    ) -> dict:
        """
        Auditoria Operacional de Pista & Desempenho de Frentistas no ERP (porta 5433).
        
        Funcionalidades:
        1. Detecção de Bicos com Vazão Lenta (Alerta Preventivo de Filtro Sujo < 25-30 L/min).
        2. Ranking de Produtividade dos Frentistas (Volume L, Faturamento R$, Ticket Médio e Conversão de Aditivada).
        3. Detecção de Anomalias de Pista (micro-abastecimentos, valores repetidos, abastecimentos manuais e cancelamentos).
        4. Blindagem LGPD de identificadores e conformidade com boas práticas operacionais.
        """
        conn = None
        try:
            conn = get_erp_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Resolução inteligente de parâmetros e filtros
                filtro_str = (filtro or "").strip()
                data_alvo = data
                turno_alvo = turno
                frentista_alvo = frentista
                bico_alvo = bico

                if filtro_str:
                    f_low = filtro_str.lower()
                    if f_low in ["hoje", "ontem", "anteontem"]:
                        data_alvo = f_low
                    elif re.search(r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b", filtro_str) or re.search(r"\b\d{1,2}[-/.]\d{1,2}(?:[-/.]\d{4})?\b", filtro_str):
                        data_alvo = filtro_str
                    elif any(t in f_low for t in ["1º", "2º", "3º", "1o", "2o", "3o", "primeiro", "segundo", "terceiro"]):
                        turno_alvo = filtro_str
                    elif re.search(r"\b(?:bico|bomba)\s*0*([0-9]{1,3})\b", f_low):
                        m_b = re.search(r"\b(?:bico|bomba)\s*0*([0-9]{1,3})\b", f_low)
                        bico_alvo = f"{int(m_b.group(1)):03d}"
                    elif any(w in f_low for w in ["italo", "botan", "marcio", "sergio", "erivas", "cristian", "marlon", "davi", "samarina", "frentista", "operador", "colaborador", "matrícula", "matricula"]):
                        frentista_alvo = filtro_str

                # Resolução de data
                cur.execute("SELECT CURRENT_DATE;")
                data_hoje = cur.fetchone()['current_date']
                aviso_periodo = None
                data_filtro_db = None

                if data_alvo:
                    if str(data_alvo).lower() == "hoje":
                        cur.execute("SELECT COUNT(*) as c FROM abastecimentos WHERE data = %s;", (data_hoje,))
                        if cur.fetchone()['c'] > 0:
                            data_filtro_db = str(data_hoje)
                        else:
                            cur.execute("SELECT MAX(data) as max_d FROM abastecimentos;")
                            max_d = cur.fetchone()['max_d']
                            data_filtro_db = str(max_d) if max_d else str(data_hoje)
                            aviso_periodo = f"Sem abastecimentos registrados para a data de hoje ({data_hoje}). Exibindo data mais recente com movimentação: {data_filtro_db}."
                    elif str(data_alvo).lower() == "ontem":
                        dt_ontem = data_hoje - timedelta(days=1)
                        data_filtro_db = str(dt_ontem)
                    elif str(data_alvo).lower() == "anteontem":
                        dt_ante = data_hoje - timedelta(days=2)
                        data_filtro_db = str(dt_ante)
                    else:
                        m_iso = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", str(data_alvo))
                        if m_iso:
                            y, m, d = m_iso.groups()
                            data_filtro_db = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                        else:
                            m_br = re.search(r"\b(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{4}))?\b", str(data_alvo))
                            if m_br:
                                d, m, y = m_br.groups()
                                ano = int(y) if y else 2026
                                data_filtro_db = f"{ano:04d}-{int(m):02d}-{int(d):02d}"
                            else:
                                data_filtro_db = str(data_alvo)

                # 2. Consultar Abastecimentos no ERP
                query_abast = """
                    SELECT 
                        a.controle,
                        TRIM(a.bomba) AS bico,
                        a.data,
                        a.hora,
                        ROUND(COALESCE(a.litros, 0)::numeric, 3) AS litros,
                        ROUND(COALESCE(a.total, 0)::numeric, 2) AS total,
                        ROUND(COALESCE(a.pu, 0)::numeric, 3) AS pu,
                        TRIM(a.codpro) AS codpro,
                        COALESCE(TRIM(p.nompro), 'COMBUSTÍVEL ' || TRIM(a.codpro)) AS nompro,
                        TRIM(a.idfrentista) AS idfrentista,
                        COALESCE(TRIM(f.nome), 'PISTA NÃO IDENTIFICADA') AS frentista_nome,
                        a.tempo,
                        a.abt_ds_tempo,
                        COALESCE(a.abt_bl_venda_cancelada, False) AS venda_cancelada,
                        a.string_full,
                        TRIM(a.turno) AS turno
                    FROM abastecimentos a
                    LEFT JOIN produtos p ON p.codpro = a.codpro
                    LEFT JOIN funcionarios f ON (TRIM(f.matr) = TRIM(a.idfrentista) OR TRIM(f.cartaoidentfid) = TRIM(a.idfrentista))
                    WHERE 1=1
                """
                params_abast = []
                if data_filtro_db:
                    query_abast += " AND a.data = %s"
                    params_abast.append(data_filtro_db)
                if turno_alvo:
                    t_dig = re.search(r"(\d)", str(turno_alvo))
                    if t_dig:
                        query_abast += " AND a.turno ILIKE %s"
                        params_abast.append(f"%{t_dig.group(1)}%")
                if frentista_alvo:
                    frent_termo = re.sub(r"^(?:frentista|operador|colaborador|matr[ií]cula)\s*", "", str(frentista_alvo), flags=re.IGNORECASE).strip()
                    if frent_termo.isdigit():
                        num_mat = int(frent_termo)
                        matr_5d = f"{num_mat:05d}"
                        query_abast += " AND (TRIM(a.idfrentista) = %s OR TRIM(a.idfrentista) = %s OR f.nome ILIKE %s)"
                        params_abast.extend([matr_5d, str(num_mat), f"%{frent_termo}%"])
                    else:
                        query_abast += " AND (f.nome ILIKE %s OR a.idfrentista ILIKE %s)"
                        params_abast.extend([f"%{frent_termo}%", f"%{frent_termo}%"])
                if bico_alvo:
                    b_num = str(bico_alvo).strip()
                    if b_num.isdigit():
                        b_pad = f"{int(b_num):03d}"
                        b_clean = b_num.lstrip("0") or "0"
                        query_abast += " AND (TRIM(a.bomba) = %s OR TRIM(a.bomba) = %s)"
                        params_abast.extend([b_pad, b_clean])
                    else:
                        query_abast += " AND TRIM(a.bomba) ILIKE %s"
                        params_abast.append(f"%{b_num}%")

                query_abast += " ORDER BY a.data DESC, a.hora DESC;"
                cur.execute(query_abast, params_abast)
                linhas_abastecimentos = cur.fetchall()

                # Se nenhum abastecimento com a data especificada, verificar se há dados na base
                cur.execute("""
                    SELECT 
                        COUNT(*) AS total_geral,
                        MIN(data) AS min_data,
                        MAX(data) AS max_data
                    FROM abastecimentos;
                """)
                stats_base = cur.fetchone()

                # 3. Consultar Bicos físicos cadastrados em bombas
                cur.execute("""
                    SELECT 
                        TRIM(b.codbom) AS bico,
                        TRIM(b.bom_ds_referencia) AS bomba_fisica,
                        TRIM(b.codtan) AS tanque,
                        TRIM(b.codpro) AS codpro,
                        COALESCE(TRIM(p.nompro), 'COMBUSTÍVEL ' || TRIM(b.codpro)) AS nompro,
                        COALESCE(b.bic_fl_ativo, 'S') AS ativo,
                        COALESCE(b.bic_fl_abastecimento_manual, 'N') AS manual_permitido
                    FROM bombas b
                    LEFT JOIN produtos p ON p.codpro = b.codpro
                    ORDER BY b.codbom;
                """)
                bicos_cadastrados = cur.fetchall()

            # Função auxiliar de categorização de combustível
            def categorizar_combustivel(nome: str) -> str:
                n = (nome or "").upper().strip()
                if "ADITIVADA" in n or "GRID" in n or "V-POWER" in n or "OCTAPRO" in n or "PODIUM" in n:
                    return "GASOLINA ADITIVADA"
                elif "COMUM" in n or "GASOLINA" in n:
                    return "GASOLINA COMUM"
                elif "ETANOL" in n or "ALCOOL" in n or "ÁLCOOL" in n:
                    return "ETANOL"
                elif "S10" in n or "S-10" in n:
                    return "DIESEL S10"
                elif "S500" in n or "S-500" in n or "DIESEL" in n:
                    return "DIESEL S500"
                elif "ARLA" in n:
                    return "ARLA"
                return "OUTROS"

            # 4. Agrupamento de Abastecimentos por Bico e por Frentista
            abasts_por_bico: Dict[str, List[dict]] = {}
            abasts_por_frentista: Dict[str, List[dict]] = {}

            for a in linhas_abastecimentos:
                c_bico = a['bico']
                if c_bico:
                    abasts_por_bico.setdefault(c_bico, []).append(a)

                c_frent = a['idfrentista'] or "SEM_IDENTIFICACAO"
                abasts_por_frentista.setdefault(c_frent, []).append(a)

            # 5. Auditoria de Vazão dos Bicos (Detecção de Filtro Lento)
            bicos_auditoria = []
            bicos_com_alerta = []

            for b in bicos_cadastrados:
                cod_bico = b['bico']
                bomba_fisica = b['bomba_fisica']
                comb_bico = b['nompro']
                cat_bico = categorizar_combustivel(comb_bico)
                is_ativo = (b['ativo'] == 'S')
                abasts_bico = abasts_por_bico.get(cod_bico, [])
                qtd_abast_bico = len(abasts_bico)
                vol_tot_bico = sum(float(x['litros'] or 0.0) for x in abasts_bico)

                if not is_ativo:
                    bicos_auditoria.append({
                        "bico": cod_bico,
                        "bomba_fisica": bomba_fisica,
                        "tanque": b['tanque'],
                        "combustivel": comb_bico,
                        "categoria": cat_bico,
                        "status_operacional": "INATIVO / DESATIVADO",
                        "total_abastecimentos": qtd_abast_bico,
                        "volume_total_litros": round(vol_tot_bico, 3),
                        "vazao_media_l_min": 0.0,
                        "status_vazao": "INATIVO",
                        "origem_vazao": "cadastro_erp",
                        "alerta_filtro_lento": False,
                        "recomendacao": "Bico desativado no cadastro do ERP."
                    })
                    continue

                # Determinação da vazão do bico
                # 1. Verificar override customizado (ex: aferição manual com proveta)
                vazao_custom = None
                if vazao_bicos_custom:
                    clean_bico = cod_bico.lstrip("0") or "0"
                    if cod_bico in vazao_bicos_custom:
                        vazao_custom = float(vazao_bicos_custom[cod_bico])
                    elif clean_bico in vazao_bicos_custom:
                        vazao_custom = float(vazao_bicos_custom[clean_bico])

                if vazao_custom is not None:
                    res_vazao = self.calcular_vazao_bico(litros=vazao_custom, tempo=60.0, produto_nome=comb_bico)
                    origem_vazao = "medicao_afericao_custom"
                    vazao_media = vazao_custom
                    rec_bico = res_vazao["recomendacao"]
                else:
                    # 2. Verificar telemetria real de tempo nos abastecimentos do bico
                    vazoes_reais = []
                    for x in abasts_bico:
                        tempo_reg = x.get('tempo') or x.get('abt_ds_tempo')
                        if tempo_reg:
                            res_x = self.calcular_vazao_bico(litros=x['litros'], tempo=tempo_reg, produto_nome=comb_bico)
                            if res_x['vazao_l_min'] and res_x['vazao_l_min'] > 0:
                                vazoes_reais.append(res_x['vazao_l_min'])

                    if vazoes_reais:
                        vazao_media = round(sum(vazoes_reais) / len(vazoes_reais), 2)
                        res_vazao = self.calcular_vazao_bico(litros=vazao_media, tempo=60.0, produto_nome=comb_bico)
                        origem_vazao = "telemetria_tempo_cbc04"
                        rec_bico = res_vazao["recomendacao"]
                    else:
                        # 3. Baseline calibrado nominal de pista
                        if cat_bico == "ARLA":
                            vazao_media = 18.0
                        elif "DIESEL" in cat_bico:
                            vazao_media = 42.0
                        else:
                            vazao_media = 38.0
                        res_vazao = self.calcular_vazao_bico(litros=vazao_media, tempo=60.0, produto_nome=comb_bico)
                        if qtd_abast_bico > 0:
                            origem_vazao = "estimativa_nominal_calibrada"
                            rec_bico = f"Vazão estimada por baseline nominal ({vazao_media:.1f} L/min). Automação CBC04 sem telemetria de duração registrada nos abastecimentos deste período."
                        else:
                            origem_vazao = "sem_movimento_periodo"
                            rec_bico = f"Sem abastecimentos registrados para este bico no período analisado. Baseline de referência da bomba: {vazao_media:.1f} L/min."

                item_bico = {
                    "bico": cod_bico,
                    "bomba_fisica": bomba_fisica,
                    "tanque": b['tanque'],
                    "combustivel": comb_bico,
                    "categoria": cat_bico,
                    "status_operacional": "ATIVO",
                    "total_abastecimentos": qtd_abast_bico,
                    "volume_total_litros": round(vol_tot_bico, 3),
                    "vazao_media_l_min": vazao_media,
                    "status_vazao": res_vazao["status_vazao"],
                    "origem_vazao": origem_vazao,
                    "alerta_filtro_lento": res_vazao["alerta_filtro_lento"],
                    "recomendacao": rec_bico
                }
                bicos_auditoria.append(item_bico)
                if res_vazao["alerta_filtro_lento"]:
                    bicos_com_alerta.append(item_bico)

            # Ordenação dos bicos fora do laço principal
            bicos_auditoria.sort(key=lambda item: (not item['alerta_filtro_lento'], item['vazao_media_l_min']))

            # 6. Produtividade & Ranking dos Frentistas
            frentistas_processados = []

            for mat, abasts_f in abasts_por_frentista.items():
                nome_f = next((x['frentista_nome'] for x in abasts_f if x.get('frentista_nome') and x['frentista_nome'] != 'PISTA NÃO IDENTIFICADA'), abasts_f[0]['frentista_nome'] if abasts_f else "Frentista")
                tot_abast_f = len(abasts_f)
                tot_litros_f = sum(float(x['litros'] or 0.0) for x in abasts_f)
                tot_fat_f = sum(float(x['total'] or 0.0) for x in abasts_f)
                ticket_medio_f = round((tot_fat_f / tot_abast_f), 2) if tot_abast_f > 0 else 0.0
                vol_medio_f = round((tot_litros_f / tot_abast_f), 3) if tot_abast_f > 0 else 0.0

                l_gas_comum = sum(float(x['litros'] or 0.0) for x in abasts_f if categorizar_combustivel(x['nompro']) == "GASOLINA COMUM")
                l_gas_adit = sum(float(x['litros'] or 0.0) for x in abasts_f if categorizar_combustivel(x['nompro']) == "GASOLINA ADITIVADA")
                l_die_s500 = sum(float(x['litros'] or 0.0) for x in abasts_f if categorizar_combustivel(x['nompro']) == "DIESEL S500")
                l_die_s10 = sum(float(x['litros'] or 0.0) for x in abasts_f if categorizar_combustivel(x['nompro']) == "DIESEL S10")
                l_etanol = sum(float(x['litros'] or 0.0) for x in abasts_f if categorizar_combustivel(x['nompro']) == "ETANOL")
                l_arla = sum(float(x['litros'] or 0.0) for x in abasts_f if categorizar_combustivel(x['nompro']) == "ARLA")

                res_conv_adit = self.calcular_conversao_aditivada(litros_comum=l_gas_comum, litros_aditivada=l_gas_adit)
                tot_die = l_die_s500 + l_die_s10
                taxa_s10 = round((l_die_s10 / tot_die * 100.0), 2) if tot_die > 0 else 0.0

                frentistas_processados.append({
                    "matricula": mat,
                    "nome": nome_f,
                    "identificado": (mat != "SEM_IDENTIFICACAO"),
                    "total_abastecimentos": tot_abast_f,
                    "total_litros": round(tot_litros_f, 3),
                    "faturamento_reais": round(tot_fat_f, 2),
                    "ticket_medio_reais": ticket_medio_f,
                    "volume_medio_litros": vol_medio_f,
                    "litros_gasolina_comum": round(l_gas_comum, 3),
                    "litros_gasolina_aditivada": round(l_gas_adit, 3),
                    "total_gasolina_litros": res_conv_adit["total_gasolina_litros"],
                    "conversao_aditivada_pct": res_conv_adit["conversao_aditivada_pct"],
                    "classificacao_conversao": res_conv_adit["classificacao_conversao"],
                    "litros_diesel_s500": round(l_die_s500, 3),
                    "litros_diesel_s10": round(l_die_s10, 3),
                    "total_diesel_litros": round(tot_die, 3),
                    "conversao_diesel_s10_pct": taxa_s10,
                    "litros_etanol": round(l_etanol, 3),
                    "litros_arla": round(l_arla, 3),
                })

            # Ordenação do Ranking (prioridade: colaboradores identificados primeiro, depois volume e faturamento)
            frentistas_processados.sort(key=lambda f: (f['identificado'], f['total_litros'], f['faturamento_reais']), reverse=True)

            ranking_frentistas = []
            pos_colaborador = 1
            for f in frentistas_processados:
                f_item = dict(f)
                if f['identificado']:
                    f_item["posicao_ranking"] = pos_colaborador
                    pos_colaborador += 1
                else:
                    f_item["posicao_ranking"] = None

                destaques = []
                if f['conversao_aditivada_pct'] >= 25.0 and f['litros_gasolina_aditivada'] > 0:
                    destaques.append("Top Conversão de Aditivada")
                if f['ticket_medio_reais'] >= 80.0:
                    destaques.append("Alto Ticket Médio")
                if f_item["posicao_ranking"] == 1:
                    destaques.append("Líder de Litragem da Pista")
                if not f['identificado']:
                    destaques.append("Abastecimentos sem Cartão/FID")

                f_item["destaque_performance"] = " | ".join(destaques) if destaques else "Operação Padrão"
                ranking_frentistas.append(f_item)

            # Identificação de Campeões Individuais (somente colaboradores identificados)
            colaboradores = [f for f in ranking_frentistas if f['identificado']]
            campeao_volume = max(colaboradores, key=lambda f: f['total_litros']) if colaboradores else None
            campeao_faturamento = max(colaboradores, key=lambda f: f['faturamento_reais']) if colaboradores else None
            colaboradores_com_adit = [f for f in colaboradores if f['litros_gasolina_aditivada'] > 0]
            if colaboradores_com_adit:
                campeao_aditivada = max(colaboradores_com_adit, key=lambda f: (f['litros_gasolina_aditivada'], f['conversao_aditivada_pct']))
            else:
                campeao_aditivada = None
            maior_ticket_medio = max(colaboradores, key=lambda f: f['ticket_medio_reais']) if colaboradores else None

            # 7. Detecção de Anomalias de Pista
            anomalias = []
            abasts_ordenados_tempo = sorted(linhas_abastecimentos, key=lambda x: (x['data'], x['hora']))

            for idx, a in enumerate(abasts_ordenados_tempo):
                ctrl = a['controle']
                bico_reg = a['bico']
                dt_str = str(a['data'])
                hr_str = str(a['hora'])
                vol = float(a['litros'] or 0.0)
                tot = float(a['total'] or 0.0)
                string_full = str(a.get('string_full') or "")

                # Anomalia 1: Micro-abastecimento (< 1.0 L ou < R$ 5.00)
                if 0.0 < vol < 1.0 or (0.0 < tot < 5.00 and vol < 2.0):
                    anomalias.append({
                        "controle": ctrl,
                        "tipo": "MICRO_ABASTECIMENTO",
                        "gravidade": "MEDIA",
                        "bico": bico_reg,
                        "data_hora": f"{dt_str} {hr_str}",
                        "litros": vol,
                        "total_reais": tot,
                        "frentista": a['frentista_nome'],
                        "motivo": f"Volume atípico de {vol:.3f} L (R$ {tot:.2f}). Possível teste de bico, gotejamento ou acionamento indevido."
                    })

                # Anomalia 2: Abastecimento Manual
                if "MANUAL" in string_full.upper():
                    anomalias.append({
                        "controle": ctrl,
                        "tipo": "ABASTECIMENTO_MANUAL",
                        "gravidade": "ALTA",
                        "bico": bico_reg,
                        "data_hora": f"{dt_str} {hr_str}",
                        "litros": vol,
                        "total_reais": tot,
                        "frentista": a['frentista_nome'],
                        "motivo": f"Abastecimento inserido manualmente no PDV ({string_full}) sem captura direta do concentrador CBC04."
                    })

                # Anomalia 3: Venda Cancelada
                if a.get('venda_cancelada'):
                    anomalias.append({
                        "controle": ctrl,
                        "tipo": "VENDA_CANCELADA",
                        "gravidade": "ALTA",
                        "bico": bico_reg,
                        "data_hora": f"{dt_str} {hr_str}",
                        "litros": vol,
                        "total_reais": tot,
                        "frentista": a['frentista_nome'],
                        "motivo": "Abastecimento com venda cancelada no PDV/Pista."
                    })

                # Anomalia 4: Horário Atípico (madrugada entre 23:00 e 05:00)
                if a.get('hora') is not None:
                    hr_val = a['hora']
                    if hasattr(hr_val, 'hour'):
                        hr_num = hr_val.hour
                    else:
                        try:
                            hr_num = int(str(hr_val).strip().split(":")[0])
                        except Exception:
                            hr_num = -1
                    if hr_num >= 23 or (0 <= hr_num < 5):
                        anomalias.append({
                            "controle": ctrl,
                            "tipo": "HORARIO_ATIPICO",
                            "gravidade": "BAIXA",
                            "bico": bico_reg,
                            "data_hora": f"{dt_str} {hr_str}",
                            "litros": vol,
                            "total_reais": tot,
                            "frentista": a['frentista_nome'],
                            "motivo": f"Abastecimento realizado fora do horário de pico comercial ({hr_str})."
                        })

                # Anomalia 5: Valores Idênticos Consecutivos (intervalo curto na pista)
                if idx > 0:
                    prev = abasts_ordenados_tempo[idx - 1]
                    mesmo_valor = (float(prev['total'] or 0.0) == tot and tot > 0)
                    if mesmo_valor:
                        intervalo_seg = None
                        try:
                            d_curr = a['data'] if isinstance(a.get('data'), date) else datetime.strptime(str(a.get('data')), "%Y-%m-%d").date() if a.get('data') else None
                            d_prev = prev['data'] if isinstance(prev.get('data'), date) else datetime.strptime(str(prev.get('data')), "%Y-%m-%d").date() if prev.get('data') else None
                            
                            def parse_time(t_val):
                                if t_val is None:
                                    return None
                                if hasattr(t_val, 'hour'):
                                    return t_val
                                parts = str(t_val).strip().split(":")
                                return time(int(parts[0]), int(parts[1]), int(float(parts[2])) if len(parts) > 2 else 0)

                            t_curr = parse_time(a.get('hora'))
                            t_prev = parse_time(prev.get('hora'))

                            if d_curr and t_curr and d_prev and t_prev:
                                dt_curr = datetime.combine(d_curr, t_curr)
                                dt_prev = datetime.combine(d_prev, t_prev)
                                intervalo_seg = abs((dt_curr - dt_prev).total_seconds())
                        except Exception:
                            intervalo_seg = None

                        is_repetido = False
                        if intervalo_seg is not None:
                            # Mesmo bico em menos de 10 min OU qualquer bico em menos de 2 min
                            if prev['bico'] == bico_reg and intervalo_seg <= 600:
                                is_repetido = True
                            elif intervalo_seg <= 120:
                                is_repetido = True
                        elif prev['bico'] == bico_reg and dt_str == str(prev.get('data')):
                            is_repetido = True

                        if is_repetido:
                            anomalias.append({
                                "controle": ctrl,
                                "tipo": "VALORES_REPETIDOS_CONSECUTIVOS",
                                "gravidade": "MEDIA",
                                "bico": bico_reg,
                                "data_hora": f"{dt_str} {hr_str}",
                                "litros": vol,
                                "total_reais": tot,
                                "frentista": a['frentista_nome'],
                                "motivo": f"Abastecimento em sequência imediata com valor idêntico ao controle anterior {prev['controle']} (R$ {tot:.2f})."
                            })

            # 8. Consolidação Geral dos Dados
            tot_litros_pista = sum(float(x['litros'] or 0.0) for x in linhas_abastecimentos)
            tot_fat_pista = sum(float(x['total'] or 0.0) for x in linhas_abastecimentos)
            tot_abast_count = len(linhas_abastecimentos)
            ticket_medio_pista = round(tot_fat_pista / tot_abast_count, 2) if tot_abast_count > 0 else 0.0
            vol_medio_pista = round(tot_litros_pista / tot_abast_count, 3) if tot_abast_count > 0 else 0.0

            gas_comum_pista = sum(float(x['litros'] or 0.0) for x in linhas_abastecimentos if categorizar_combustivel(x['nompro']) == "GASOLINA COMUM")
            gas_adit_pista = sum(float(x['litros'] or 0.0) for x in linhas_abastecimentos if categorizar_combustivel(x['nompro']) == "GASOLINA ADITIVADA")
            res_conv_geral = self.calcular_conversao_aditivada(litros_comum=gas_comum_pista, litros_aditivada=gas_adit_pista)

            die_s500_pista = sum(float(x['litros'] or 0.0) for x in linhas_abastecimentos if categorizar_combustivel(x['nompro']) == "DIESEL S500")
            die_s10_pista = sum(float(x['litros'] or 0.0) for x in linhas_abastecimentos if categorizar_combustivel(x['nompro']) == "DIESEL S10")
            tot_die_pista = die_s500_pista + die_s10_pista
            taxa_die_s10_pista = round((die_s10_pista / tot_die_pista * 100.0), 2) if tot_die_pista > 0 else 0.0

            # Avaliação do Status Geral da Pista
            if any(b.get('status_vazao') == "CRÍTICO_FILTRO_OBSTRUÍDO" for b in bicos_com_alerta):
                status_geral = "CRÍTICO_MANUTENÇÃO"
            elif bicos_com_alerta or any(an['gravidade'] == "ALTA" for an in anomalias):
                status_geral = "ALERTA_PISTA"
            else:
                status_geral = "OPERACIONAL_NORMAL"

            # 9. Geração de Recomendações Operacionais
            recomendacoes = []
            if bicos_com_alerta:
                bicos_str = ", ".join(f"Bico {b['bico']} ({b['vazao_media_l_min']:.1f} L/min)" for b in bicos_com_alerta)
                recomendacoes.append(
                    f"Manutenção Preventiva: Providenciar a troca imediata do filtro de combustível em: {bicos_str}. "
                    f"Vazão abaixo do limite mínimo de 30 L/min gera lentidão no atendimento e sobrecarga na bomba."
                )
            else:
                recomendacoes.append("Vazão Hidráulica: Todos os bicos operacionais avaliados operam em fluxo comercial adequado (35 a 45 L/min).")

            if res_conv_geral["conversao_aditivada_pct"] < 20.0 and res_conv_geral["total_gasolina_litros"] > 0:
                recomendacoes.append(
                    f"Incentivo Comercial: A taxa de conversão de Gasolina Aditivada da pista está em {res_conv_geral['conversao_aditivada_pct']}% "
                    f"(abaixo da meta de 25-30%). Capacitar a equipe de frentistas para oferta ativa no primeiro contato com o motorista."
                )
            elif res_conv_geral["total_gasolina_litros"] > 0:
                recomendacoes.append(
                    f"Vendas de Aditivada: Bom índice de conversão de aditivada apurado ({res_conv_geral['conversao_aditivada_pct']}%), "
                    f"garantindo margem líquida superior na pista."
                )

            anomalias_altas = [an for an in anomalias if an['gravidade'] == "ALTA"]
            if anomalias_altas:
                recomendacoes.append(
                    f"Controle de Perdas: Foram detectadas {len(anomalias_altas)} anomalia(s) de alta prioridade "
                    f"(abastecimentos manuais ou cancelados). Auditar a liberação de pista com o gerente do posto."
                )

            sem_ident = [f for f in ranking_frentistas if not f['identificado']]
            if sem_ident and sem_ident[0]['total_abastecimentos'] > 0:
                recomendacoes.append(
                    f"Rastreabilidade: {sem_ident[0]['total_abastecimentos']} abastecimento(s) foram finalizados sem "
                    f"identificação do colaborador via cartão RFID/Fid. Reforçar o uso do cartão em cada abastecimento."
                )

            bico_destaque = None
            if bico_alvo:
                b_pad = f"{int(bico_alvo):03d}" if str(bico_alvo).isdigit() else str(bico_alvo)
                bico_destaque = next((b for b in bicos_auditoria if b['bico'] == b_pad or b['bico'].lstrip('0') == b_pad.lstrip('0')), None)

            resultado = {
                "status": "ok",
                "timestamp_auditoria": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "periodo_analisado": {
                    "data_filtro": data_filtro_db,
                    "turno_filtro": turno_alvo,
                    "frentista_filtro": frentista_alvo,
                    "bico_filtro": bico_alvo,
                    "primeira_data_base": str(stats_base['min_data']) if stats_base else None,
                    "ultima_data_base": str(stats_base['max_data']) if stats_base else None,
                    "aviso_periodo": aviso_periodo,
                },
                "resumo_executivo": {
                    "status_geral": status_geral,
                    "total_abastecimentos": tot_abast_count,
                    "total_litros": round(tot_litros_pista, 3),
                    "faturamento_total_reais": round(tot_fat_pista, 2),
                    "ticket_medio_pista_reais": ticket_medio_pista,
                    "volume_medio_abastecimento_litros": vol_medio_pista,
                    "taxa_conversao_aditivada_geral_pct": res_conv_geral["conversao_aditivada_pct"],
                    "classificacao_conversao_aditivada": res_conv_geral["classificacao_conversao"],
                    "total_gasolina_comum_litros": round(gas_comum_pista, 3),
                    "total_gasolina_aditivada_litros": round(gas_adit_pista, 3),
                    "total_diesel_s500_litros": round(die_s500_pista, 3),
                    "total_diesel_s10_litros": round(die_s10_pista, 3),
                    "total_diesel_litros": round(tot_die_pista, 3),
                    "taxa_conversao_diesel_s10_pct": taxa_die_s10_pista,
                    "mensagem_aditivada": (
                        f"Líder em Aditivada: {campeao_aditivada['nome']} ({campeao_aditivada['conversao_aditivada_pct']}% de conversão)"
                        if campeao_aditivada else "Nenhum frentista registrou vendas de gasolina aditivada no período analisado."
                    ),
                    "bico_alvo_destaque": bico_destaque,
                    "campeao_volume": {
                        "matricula": campeao_volume['matricula'],
                        "nome": campeao_volume['nome'],
                        "total_litros": campeao_volume['total_litros'],
                        "total_abastecimentos": campeao_volume['total_abastecimentos']
                    } if campeao_volume else None,
                    "campeao_faturamento": {
                        "matricula": campeao_faturamento['matricula'],
                        "nome": campeao_faturamento['nome'],
                        "faturamento_reais": campeao_faturamento['faturamento_reais'],
                        "ticket_medio_reais": campeao_faturamento['ticket_medio_reais']
                    } if campeao_faturamento else None,
                    "campeao_aditivada": {
                        "matricula": campeao_aditivada['matricula'],
                        "nome": campeao_aditivada['nome'],
                        "litros_aditivada": campeao_aditivada['litros_gasolina_aditivada'],
                        "conversao_pct": campeao_aditivada['conversao_aditivada_pct']
                    } if campeao_aditivada else None,
                    "maior_ticket_medio": {
                        "matricula": maior_ticket_medio['matricula'],
                        "nome": maior_ticket_medio['nome'],
                        "ticket_medio_reais": maior_ticket_medio['ticket_medio_reais'],
                        "faturamento_reais": maior_ticket_medio['faturamento_reais']
                    } if maior_ticket_medio else None,
                    "bicos_com_alerta_filtro": len(bicos_com_alerta),
                    "total_anomalias_detectadas": len(anomalias)
                },
                "ranking_frentistas": ranking_frentistas,
                "auditoria_vazao_bicos": bicos_auditoria,
                "anomalias_detectadas": anomalias,
                "recomendacoes_operacionais": recomendacoes
            }

            resultado_limpo, _ = sanitize_dict(resultado)
            return resultado_limpo

        except Exception as e:
            return {
                "status": "indisponivel",
                "motivo": f"Falha na auditoria de pista e frentistas no ERP (porta 5433): {e}",
            }
        finally:
            if conn and not conn.closed:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def categorizar_combustivel(nome: str) -> str:
        """Categoriza o nome do combustível em grupos canônicos para relatórios operacionais."""
        n = (nome or "").upper().strip()
        if "ADITIVADA" in n or "GRID" in n or "V-POWER" in n or "OCTAPRO" in n or "PODIUM" in n:
            return "GASOLINA ADITIVADA"
        elif "COMUM" in n or "GASOLINA" in n:
            return "GASOLINA COMUM"
        elif "ETANOL" in n or "ALCOOL" in n or "ÁLCOOL" in n:
            return "ETANOL"
        elif "S10" in n or "S-10" in n:
            return "DIESEL S10"
        elif "S500" in n or "S-500" in n or "DIESEL" in n:
            return "DIESEL S500"
        elif "ARLA" in n:
            return "ARLA"
        return "OUTROS"

    @staticmethod
    def calcular_lmc_tanque(
        estoque_abertura: float,
        recebimento: float,
        vendas: float,
        estoque_fisico: float,
        tolerancia_pct: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Cálculo do Livro de Movimentação de Combustíveis (LMC) segundo Portaria ANP nº 26/1992.

        Equações Oficiais ANP:
        1. Fechamento Escriturado:
           E_e = E_a + R - V
           (E_a: Estoque de abertura, R: Recebimento/Descargas, V: Vendas totais registradas nos bicos)

        2. Estoque Físico:
           E_f: Medição direta na régua milimetrada (tabela de arqueação) ou sonda de telemetria Veeder-Root.

        3. Variação Volumétrica (Sobra / Falta):
           Δ_litros = E_f - E_e
           Δ_pct = (Δ_litros / V) * 100  (quando V > 0; se V == 0, 0.0)

        4. Margem Legal de Tolerância (±0.6%):
           |Δ_pct| <= 0.6% -> CONFORME_ANP
           |Δ_pct| >  0.6% -> ALERTA_FORA_TOLERANCIA_ANP
        """
        ea = float(estoque_abertura or 0.0)
        rec = float(recebimento or 0.0)
        v = float(vendas or 0.0)
        ef = float(estoque_fisico or 0.0)
        tol_pct = float(tolerancia_pct if tolerancia_pct is not None else 0.6)

        ee = round(ea + rec - v, 3)
        var_litros = round(ef - ee, 3)

        if var_litros > 0.0001:
            tipo_variacao = "ganho"
            nome_variacao = "Sobra / Ganho Volumétrico (Dilatação / Térmico)"
        elif var_litros < -0.0001:
            tipo_variacao = "perda"
            nome_variacao = "Perda / Quebra Volumétrica (Evaporação / Contração)"
        else:
            tipo_variacao = "nula"
            nome_variacao = "Sem variação (Perfeito alinhamento)"

        if v > 0:
            var_pct = round((var_litros / v) * 100.0, 4)
            tol_max_litros = round(v * (tol_pct / 100.0), 3)

            # Margem de tolerância da ANP (com epsilon 1e-7 para estabilidade numérica em exatamente 0.6%)
            if abs(var_pct) <= (tol_pct + 1e-7):
                status_anp = "CONFORME_ANP"
                dentro_tolerancia = True
                descricao_status = f"Dentro da margem de tolerância regulamentar da ANP (±{tol_pct}%)."
                if tipo_variacao == "ganho":
                    diagnostico = f"Variação positiva de +{abs(var_litros):.3f} L ({var_pct:+.2f}%) dentro da tolerância de ±{tol_pct}%. Provável expansão volumétrica por temperatura."
                elif tipo_variacao == "perda":
                    diagnostico = f"Perda volumétrica de -{abs(var_litros):.3f} L ({var_pct:+.2f}%) dentro da tolerância de ±{tol_pct}%. Provável evaporação ou contração térmica natural."
                else:
                    diagnostico = "Estoque físico medido coincide perfeitamente com o saldo contábil escriturado."
            else:
                status_anp = "ALERTA_FORA_TOLERANCIA_ANP"
                dentro_tolerancia = False
                descricao_status = f"FORA DA TOLERÂNCIA ANP: variação de {var_pct:+.2f}% excede a margem permitida de ±{tol_pct}%."
                if tipo_variacao == "perda":
                    diagnostico = (
                        f"Alerta Crítico: Perda excessiva de -{abs(var_litros):.3f} L ({var_pct:+.2f}% das vendas). "
                        f"Supera a tolerância legal de ±{tol_pct}%. Investigar imediatamente: "
                        f"possível vazamento no tanque ou linha de sucção, bicos entregando combustível a mais por descalibração, "
                        f"ou erro de leitura na régua/sonda."
                    )
                else:
                    diagnostico = (
                        f"Alerta Crítico: Ganho volumétrico excessivo de +{abs(var_litros):.3f} L ({var_pct:+.2f}% das vendas). "
                        f"Supera a tolerância legal de ±{tol_pct}%. Investigar imediatamente: "
                        f"falta de registro de descarga de combustível, bicos entregando a menos por desgaste, "
                        f"ou erro na tabela de arqueação do tanque."
                    )
        else:
            # Sem vendas no período: a tolerância permitida sobre vendas é de 0 litros
            var_pct = 0.0
            tol_max_litros = 0.0
            if abs(var_litros) <= 0.001:
                status_anp = "CONFORME_ANP"
                dentro_tolerancia = True
                descricao_status = f"Sem vendas registradas no período e estoque físico perfeitamente alinhado ao escriturado (±{tol_pct}%)."
                diagnostico = "Tanque sem vendas no período; estoque físico coincide perfeitamente com o saldo contábil escriturado."
            else:
                status_anp = "ALERTA_FORA_TOLERANCIA_ANP"
                dentro_tolerancia = False
                descricao_status = f"FORA DA TOLERÂNCIA ANP: Variação física de {var_litros:+.3f} L sem vendas no período (tolerância sobre vendas é 0 L)."
                if tipo_variacao == "perda":
                    diagnostico = (
                        f"Alerta Crítico: Perda volumétrica de -{abs(var_litros):.3f} L sem movimentação de vendas no período. "
                        f"Supera a tolerância permitida (0 L). Investigar imediatamente risco de vazamento subterrâneo, furto ou erro de régua."
                    )
                else:
                    diagnostico = (
                        f"Alerta Crítico: Sobra volumétrica de +{abs(var_litros):.3f} L sem movimentação de vendas no período. "
                        f"Supera a tolerância permitida (0 L). Investigar descarga de combustível não escriturada ou erro na medição da régua/sonda."
                    )

        return {
            "estoque_abertura": round(ea, 3),
            "recebimento": round(rec, 3),
            "vendas": round(v, 3),
            "estoque_escriturado": round(ee, 3),
            "estoque_fisico": round(ef, 3),
            "variacao_litros": round(var_litros, 3),
            "variacao_pct": round(var_pct, 4),
            "tolerancia_pct": tol_pct,
            "tolerancia_max_litros": round(tol_max_litros, 3),
            "dentro_tolerancia": dentro_tolerancia,
            "status_anp": status_anp,
            "tipo_variacao": tipo_variacao,
            "nome_variacao": nome_variacao,
            "descricao_status": descricao_status,
            "diagnostico": diagnostico,
        }

    def gerar_relatorio_lmc_anp(
        self,
        data: Optional[str] = None,
        combustivel: Optional[str] = None,
        tanque: Optional[str] = None,
        medicoes_fisicas_custom: Optional[Dict[str, float]] = None,
        recebimentos_custom: Optional[Dict[str, float]] = None,
        estoque_abertura_custom: Optional[Dict[str, float]] = None,
    ) -> dict:
        """
        Gera o Relatório Oficial do LMC (Livro de Movimentação de Combustíveis)
        conforme exigências da Portaria ANP nº 26/1992 e normas complementares.

        Realiza a conciliação entre estoque físico (medição régua/telemetria)
        e escriturado (abertura + recebimentos - vendas) para cada tanque,
        auditando a margem legal de tolerância de ±0.6%.
        """
        conn = None
        try:
            conn = get_erp_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Determinação da Data Alvo
                data_param = self.normalizar_data(data)
                aviso_data = None
                data_alvo = None

                cur.execute("SELECT CURRENT_DATE;")
                data_hoje = cur.fetchone()['current_date']

                if not data_param or data_param == "hoje":
                    cur.execute("SELECT COUNT(*) as c FROM abastecimentos WHERE data = %s AND abt_bl_venda_cancelada IS NOT TRUE;", (data_hoje,))
                    c_ab = cur.fetchone()['c']
                    cur.execute("SELECT COUNT(*) as c FROM fechabomba WHERE dtmov = %s;", (data_hoje,))
                    c_fb = cur.fetchone()['c']

                    if c_ab > 0 or c_fb > 0:
                        data_alvo = str(data_hoje)
                    else:
                        cur.execute("""
                            SELECT GREATEST(
                                (SELECT MAX(data) FROM abastecimentos WHERE abt_bl_venda_cancelada IS NOT TRUE),
                                (SELECT MAX(dtmov) FROM fechabomba)
                            ) as max_d;
                        """)
                        max_d = cur.fetchone()['max_d']
                        if max_d:
                            data_alvo = str(max_d)
                            aviso_data = (
                                f"Nenhuma movimentação registrada para hoje ({data_hoje}). "
                                f"Exibindo LMC da data mais recente com movimentação: {data_alvo}."
                            )
                        else:
                            data_alvo = str(data_hoje)
                elif data_param == "ontem":
                    cur.execute("SELECT (CURRENT_DATE - INTERVAL '1 day')::date as ontem;")
                    data_alvo = str(cur.fetchone()['ontem'])
                    cur.execute("SELECT COUNT(*) as c FROM abastecimentos WHERE data = %s AND abt_bl_venda_cancelada IS NOT TRUE;", (data_alvo,))
                    c_ab = cur.fetchone()['c']
                    cur.execute("SELECT COUNT(*) as c FROM fechabomba WHERE dtmov = %s;", (data_alvo,))
                    c_fb = cur.fetchone()['c']
                    if c_ab == 0 and c_fb == 0:
                        cur.execute("""
                            SELECT GREATEST(
                                (SELECT MAX(data) FROM abastecimentos WHERE abt_bl_venda_cancelada IS NOT TRUE),
                                (SELECT MAX(dtmov) FROM fechabomba)
                            ) as max_d;
                        """)
                        max_d = cur.fetchone()['max_d']
                        if max_d:
                            aviso_data = (
                                f"Nenhuma movimentação registrada para ontem ({data_alvo}). "
                                f"Exibindo LMC da data mais recente com movimentação: {max_d}."
                            )
                            data_alvo = str(max_d)
                elif data_param == "anteontem":
                    cur.execute("SELECT (CURRENT_DATE - INTERVAL '2 days')::date as anteontem;")
                    data_alvo = str(cur.fetchone()['anteontem'])
                    cur.execute("SELECT COUNT(*) as c FROM abastecimentos WHERE data = %s AND abt_bl_venda_cancelada IS NOT TRUE;", (data_alvo,))
                    c_ab = cur.fetchone()['c']
                    cur.execute("SELECT COUNT(*) as c FROM fechabomba WHERE dtmov = %s;", (data_alvo,))
                    c_fb = cur.fetchone()['c']
                    if c_ab == 0 and c_fb == 0:
                        cur.execute("""
                            SELECT GREATEST(
                                (SELECT MAX(data) FROM abastecimentos WHERE abt_bl_venda_cancelada IS NOT TRUE),
                                (SELECT MAX(dtmov) FROM fechabomba)
                            ) as max_d;
                        """)
                        max_d = cur.fetchone()['max_d']
                        if max_d:
                            aviso_data = (
                                f"Nenhuma movimentação registrada para anteontem ({data_alvo}). "
                                f"Exibindo LMC da data mais recente com movimentação: {max_d}."
                            )
                            data_alvo = str(max_d)
                else:
                    data_alvo = data_param
                    cur.execute("SELECT COUNT(*) as c FROM abastecimentos WHERE data = %s AND abt_bl_venda_cancelada IS NOT TRUE;", (data_alvo,))
                    c_ab = cur.fetchone()['c']
                    cur.execute("SELECT COUNT(*) as c FROM fechabomba WHERE dtmov = %s;", (data_alvo,))
                    c_fb = cur.fetchone()['c']
                    if c_ab == 0 and c_fb == 0:
                        aviso_data = f"Nenhuma movimentação de vendas ou encerrantes registrada para a data {data_alvo}."

                # 2. Dados Cadastrais dos Tanques
                cur.execute("""
                    SELECT 
                        TRIM(t.codtan) AS codtan,
                        COALESCE(
                            NULLIF(TRIM(t.prl_ds_produto_lmc), ''),
                            NULLIF(TRIM(p.nompro), ''),
                            'COMBUSTÍVEL ' || TRIM(t.codtan)
                        ) AS combustivel,
                        TRIM(t.codlmc) AS codlmc,
                        ROUND(COALESCE(t.capacidade, 0)::numeric, 3) AS capacidade_litros,
                        ROUND(COALESCE(t.qtdeat, 0)::numeric, 3) AS saldo_atual_litros,
                        ROUND(COALESCE(t.qtdean, 0)::numeric, 3) AS qtdean,
                        ROUND(COALESCE(t.iniciodia, 0)::numeric, 3) AS iniciodia,
                        ROUND(COALESCE(t.tan_vl_quantidade_fim, 0)::numeric, 3) AS tan_vl_quantidade_fim,
                        ROUND(COALESCE(t.volume, 0)::numeric, 3) AS volume
                    FROM tanques t
                    LEFT JOIN (
                        SELECT DISTINCT ON (TRIM(codlmc)) TRIM(codlmc) AS codlmc, nompro
                        FROM produtos
                        WHERE codlmc IS NOT NULL AND TRIM(codlmc) != ''
                        ORDER BY TRIM(codlmc), codpro
                    ) p ON p.codlmc = TRIM(t.codlmc)
                    ORDER BY t.codtan;
                """)
                linhas_tanques = cur.fetchall()

                # 3. Mapeamento de Bicos por Tanque
                cur.execute("""
                    SELECT 
                        TRIM(b.codbom) AS codbom,
                        TRIM(b.codtan) AS codtan,
                        TRIM(b.codpro) AS codpro
                    FROM bombas b
                    WHERE b.codtan IS NOT NULL;
                """)
                linhas_bombas = cur.fetchall()
                bicos_por_tanque: Dict[str, List[str]] = {}
                for rb in linhas_bombas:
                    c_tan = rb['codtan']
                    if c_tan:
                        bicos_por_tanque.setdefault(c_tan, []).append(rb['codbom'])

                # 4. Vendas do Dia por Tanque (abastecimentos Companytec)
                cur.execute("""
                    SELECT 
                        COALESCE(TRIM(a.tanque), TRIM(b.codtan)) AS codtan,
                        COUNT(*)::int AS total_abastecimentos,
                        ROUND(COALESCE(SUM(a.litros), 0)::numeric, 3) AS total_litros,
                        ROUND(COALESCE(SUM(a.total), 0)::numeric, 2) AS total_reais
                    FROM abastecimentos a
                    LEFT JOIN bombas b ON b.codbom = a.bomba
                    WHERE a.data = %s AND a.abt_bl_venda_cancelada IS NOT TRUE
                    GROUP BY COALESCE(TRIM(a.tanque), TRIM(b.codtan));
                """, (data_alvo,))
                vendas_abastecimentos = {r['codtan']: r for r in cur.fetchall() if r['codtan']}

                # 5. Vendas por Encerrantes do Dia (fechabomba)
                cur.execute("""
                    SELECT 
                        TRIM(fb.codtan) AS codtan,
                        COUNT(*)::int AS bicos_fechados,
                        ROUND(COALESCE(SUM(fb.qtdeaf), SUM(GREATEST(fb.enclts - fb.encltsa, 0)), 0)::numeric, 3) AS litros_encerrantes
                    FROM fechabomba fb
                    WHERE fb.dtmov = %s
                    GROUP BY TRIM(fb.codtan);
                """, (data_alvo,))
                vendas_encerrantes = {r['codtan']: r for r in cur.fetchall() if r['codtan']}

            # Helper para buscar parâmetros customizados com correspondência flexível
            def _obter_custom(mapa: Optional[Dict[str, float]], cod_t: str, nome_c: str) -> Optional[float]:
                if not mapa:
                    return None
                if cod_t in mapa:
                    return float(mapa[cod_t])
                try:
                    num = int(cod_t)
                    if str(num) in mapa:
                        return float(mapa[str(num)])
                    if num in mapa:
                        return float(mapa[num])
                except Exception:
                    pass
                for k, val in mapa.items():
                    ks = str(k).strip().lower()
                    if ks in [f"tanque {cod_t}", f"tq {cod_t}", f"tanque {int(cod_t) if cod_t.isdigit() else cod_t}", f"tq{int(cod_t) if cod_t.isdigit() else cod_t}"]:
                        return float(val)
                    if nome_c and ks in nome_c.lower():
                        return float(val)
                return None

            tanques_relatorio = []
            tanques_alerta = []
            tot_vendas = 0.0
            tot_rec = 0.0
            tot_escriturado = 0.0
            tot_fisico = 0.0
            tot_var_litros = 0.0

            # Normaliza filtros de tanque e combustível
            tanque_filtro_pad = None
            if tanque:
                t_str = str(tanque).strip().lower()
                m_dig = re.search(r"\d+", t_str)
                if m_dig:
                    tanque_filtro_pad = f"{int(m_dig.group(0)):03d}"
                else:
                    tanque_filtro_pad = t_str

            combustivel_filtro_cat = None
            if combustivel:
                combustivel_filtro_cat = self.categorizar_combustivel(combustivel)

            for t in linhas_tanques:
                cod_tan = t['codtan']
                nome_comb = t['combustivel']
                cat_comb = self.categorizar_combustivel(nome_comb)

                # Aplica filtros se especificados
                if tanque_filtro_pad:
                    t_pad_num = tanque_filtro_pad.lstrip('0') or '0'
                    c_tan_num = cod_tan.lstrip('0') or '0'
                    if cod_tan != tanque_filtro_pad and c_tan_num != t_pad_num:
                        continue

                if combustivel_filtro_cat and combustivel_filtro_cat != "OUTROS" and cat_comb != combustivel_filtro_cat:
                    if combustivel.strip().lower() not in nome_comb.lower():
                        continue

                # Vendas do dia (V)
                v_abast = vendas_abastecimentos.get(cod_tan)
                v_enc = vendas_encerrantes.get(cod_tan)

                vendas_l = 0.0
                total_reais = 0.0
                qtd_abast = 0
                if v_abast:
                    vendas_l = float(v_abast['total_litros'] or 0.0)
                    total_reais = float(v_abast['total_reais'] or 0.0)
                    qtd_abast = int(v_abast['total_abastecimentos'] or 0)
                elif v_enc:
                    vendas_l = float(v_enc['litros_encerrantes'] or 0.0)

                # Recebimentos / Descargas (R)
                rec_custom = _obter_custom(recebimentos_custom, cod_tan, nome_comb)
                recebimento_l = rec_custom if rec_custom is not None else 0.0

                # Estoque de Abertura (Ea)
                ea_custom = _obter_custom(estoque_abertura_custom, cod_tan, nome_comb)
                if ea_custom is not None:
                    abertura_l = ea_custom
                else:
                    iniciodia = float(t['iniciodia'] or 0.0)
                    qtdean = float(t['qtdean'] or 0.0)
                    saldo_at = float(t['saldo_atual_litros'] or 0.0)
                    if iniciodia > 0:
                        abertura_l = iniciodia
                    elif qtdean > 0:
                        abertura_l = qtdean
                    else:
                        calc_ea = saldo_at + vendas_l - recebimento_l
                        abertura_l = calc_ea if calc_ea >= 0 else saldo_at

                # Estoque Físico Medido (Ef)
                ef_custom = _obter_custom(medicoes_fisicas_custom, cod_tan, nome_comb)
                if ef_custom is not None:
                    fisico_l = ef_custom
                else:
                    tan_fim = float(t['tan_vl_quantidade_fim'] or 0.0)
                    vol = float(t['volume'] or 0.0)
                    saldo_at = float(t['saldo_atual_litros'] or 0.0)
                    if tan_fim > 0:
                        fisico_l = tan_fim
                    elif vol > 0:
                        fisico_l = vol
                    else:
                        fisico_l = saldo_at

                # Cálculo LMC Oficial
                calc = self.calcular_lmc_tanque(
                    estoque_abertura=abertura_l,
                    recebimento=recebimento_l,
                    vendas=vendas_l,
                    estoque_fisico=fisico_l,
                    tolerancia_pct=0.6,
                )

                bicos = bicos_por_tanque.get(cod_tan, [])

                item_tanque = {
                    "tanque": cod_tan,
                    "combustivel": nome_comb,
                    "categoria_combustivel": cat_comb,
                    "codlmc_anp": t['codlmc'] or "N/D",
                    "capacidade_litros": float(t['capacidade_litros'] or 0.0),
                    "bicos_vinculados": bicos,
                    "total_abastecimentos": qtd_abast,
                    "faturamento_vendas_reais": total_reais,
                    "movimentacao": {
                        "estoque_abertura_litros": calc["estoque_abertura"],
                        "recebimentos_descargas_litros": calc["recebimento"],
                        "vendas_bicos_litros": calc["vendas"],
                        "estoque_escriturado_litros": calc["estoque_escriturado"],
                        "estoque_fisico_medido_litros": calc["estoque_fisico"],
                    },
                    "auditoria_anp": {
                        "variacao_litros": calc["variacao_litros"],
                        "variacao_pct": calc["variacao_pct"],
                        "tolerancia_pct": calc["tolerancia_pct"],
                        "tolerancia_max_litros": calc["tolerancia_max_litros"],
                        "dentro_tolerancia": calc["dentro_tolerancia"],
                        "status_anp": calc["status_anp"],
                        "tipo_variacao": calc["tipo_variacao"],
                        "nome_variacao": calc["nome_variacao"],
                        "descricao_status": calc["descricao_status"],
                        "diagnostico": calc["diagnostico"],
                    }
                }

                tanques_relatorio.append(item_tanque)

                if not calc["dentro_tolerancia"]:
                    tanques_alerta.append({
                        "tanque": cod_tan,
                        "combustivel": nome_comb,
                        "variacao_litros": calc["variacao_litros"],
                        "variacao_pct": calc["variacao_pct"],
                        "tolerancia_max_litros": calc["tolerancia_max_litros"],
                        "diagnostico": calc["diagnostico"]
                    })

                tot_vendas += calc["vendas"]
                tot_rec += calc["recebimento"]
                tot_escriturado += calc["estoque_escriturado"]
                tot_fisico += calc["estoque_fisico"]
                tot_var_litros += calc["variacao_litros"]

            var_geral_pct = round((tot_var_litros / tot_vendas) * 100.0, 4) if tot_vendas > 0 else 0.0

            status_geral = "CONFORME_ANP" if len(tanques_alerta) == 0 else "ALERTA_FORA_TOLERANCIA_ANP"

            recomendacoes = []
            if len(tanques_alerta) > 0:
                t_nomes = ", ".join(f"Tanque {a['tanque']} ({a['combustivel']}: {a['variacao_pct']:+.2f}%)" for a in tanques_alerta)
                recomendacoes.append(
                    f"Ação Imediata ANP: Foi detectada variação volumétrica fora da margem regulamentar de ±0,6% em: {t_nomes}. "
                    f"Conforme a Portaria ANP nº 26/1992, proceder com apuração imediata das causas."
                )
                perdas = [a for a in tanques_alerta if a['variacao_litros'] < 0]
                if perdas:
                    recomendacoes.append(
                        "Investigação de Perdas: Realizar teste de estanqueidade nos tanques com quebra volumétrica excessiva "
                        "e aferição de bicos medidores com medida-padrão de 20 litros calibrada pelo INMETRO para descartar vazamentos ou sobre-entrega."
                    )
                sobras = [a for a in tanques_alerta if a['variacao_litros'] > 0]
                if sobras:
                    recomendacoes.append(
                        "Investigação de Sobras: Auditar notas fiscais de entrada e registros de descarga de caminhão-tanque "
                        "para verificar se houve descarga sem escrituração no LMC ou recalibrar a régua de medição."
                    )
            else:
                recomendacoes.append(
                    "Conformidade Regulamentar: Todos os tanques auditados operaram estritamente dentro da margem legal de tolerância de ±0,6% da Portaria ANP 26/1992."
                )

            recomendacoes.append(
                "Guarda de Documentos: Manter os registros diários do LMC arquivados e à disposição da fiscalização da ANP e órgãos fazendários pelo prazo regulamentar de 5 anos."
            )

            resultado = {
                "status": "ok",
                "timestamp_geracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "periodo_analisado": {
                    "data_lmc": data_alvo,
                    "aviso_data": aviso_data,
                    "filtro_combustivel": combustivel,
                    "filtro_tanque": tanque,
                },
                "resumo_executivo": {
                    "status_geral_anp": status_geral,
                    "total_tanques_analisados": len(tanques_relatorio),
                    "total_tanques_conformes": len(tanques_relatorio) - len(tanques_alerta),
                    "total_tanques_alerta": len(tanques_alerta),
                    "total_vendas_litros": round(tot_vendas, 3),
                    "total_recebimentos_litros": round(tot_rec, 3),
                    "total_estoque_escriturado_litros": round(tot_escriturado, 3),
                    "total_estoque_fisico_litros": round(tot_fisico, 3),
                    "variacao_volumetrica_total_litros": round(tot_var_litros, 3),
                    "variacao_volumetrica_geral_pct": var_geral_pct,
                    "tanques_em_alerta": tanques_alerta,
                },
                "tanques": tanques_relatorio,
                "recomendacoes_operacionais": recomendacoes,
            }

            resultado_limpo, _ = sanitize_dict(resultado)
            return resultado_limpo

        except Exception as e:
            return {
                "status": "indisponivel",
                "motivo": f"Falha na geração do LMC Oficial da ANP no ERP (porta 5433/5435): {e}",
            }
        finally:
            if conn and not conn.closed:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def calcular_metricas_associacao(
        total_transacoes: int,
        freq_a: int,
        freq_b: int,
        freq_ab: int,
    ) -> Dict[str, float]:
        """
        Calcula as métricas matemáticas canônicas de Market Basket Analysis (Regras de Associação):
        - Suporte(A -> B) = freq_ab / total_transacoes
        - Confiança(A -> B) = freq_ab / freq_a
        - Lift(A -> B) = Confiança(A -> B) / Suporte(B) = (freq_ab * total_transacoes) / (freq_a * freq_b)
        - Conviction(A -> B) = (1 - Suporte(B)) / (1 - Confiança(A -> B))
        Protegido contra divisão por zero e transações vazias.
        """
        if total_transacoes <= 0 or freq_a <= 0 or freq_b <= 0 or freq_ab <= 0:
            return {
                "suporte": 0.0,
                "suporte_a": 0.0,
                "suporte_b": 0.0,
                "confianca": 0.0,
                "lift": 0.0,
                "conviction": 1.0,
            }

        suporte_ab = freq_ab / total_transacoes
        suporte_a = freq_a / total_transacoes
        suporte_b = freq_b / total_transacoes
        confianca = freq_ab / freq_a

        if suporte_b > 0:
            lift = confianca / suporte_b
        else:
            lift = 0.0

        if confianca >= 1.0:
            conviction = 999.0  # Infinito prático
        elif confianca < 1.0 and (1.0 - confianca) > 0:
            conviction = (1.0 - suporte_b) / (1.0 - confianca)
        else:
            conviction = 1.0

        return {
            "suporte": round(suporte_ab, 4),
            "suporte_a": round(suporte_a, 4),
            "suporte_b": round(suporte_b, 4),
            "confianca": round(confianca, 4),
            "lift": round(lift, 4),
            "conviction": round(conviction, 4),
        }

    @staticmethod
    def calcular_regras_associacao(
        transacoes: List[List[Dict[str, Any]]],
        min_suporte: float = 0.005,
        min_confianca: float = 0.05,
        min_lift: float = 1.0,
        filtro_produto: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Minera regras de associação direcionadas (A -> B) a partir de listas de transações de conveniência.
        Gera métricas completas, impacto no ticket médio e scripts persuasivos para os operadores de caixa.
        """
        if not transacoes:
            return []

        total_transacoes = len(transacoes)
        if total_transacoes == 0:
            return []

        # 1. Contagem de frequências univariadas e bivariadas
        freq_itens: Dict[str, int] = {}
        produtos_info: Dict[str, Dict[str, Any]] = {}
        freq_pares: Dict[Tuple[str, str], int] = {}

        for cesta in transacoes:
            if not cesta:
                continue
            itens_unicos: Dict[str, Dict[str, Any]] = {}
            for item in cesta:
                c_sku = str(item.get("codpro", "")).strip()
                if c_sku and c_sku not in itens_unicos:
                    itens_unicos[c_sku] = item
                    if c_sku not in produtos_info:
                        produtos_info[c_sku] = {
                            "codpro": c_sku,
                            "nompro": str(item.get("nompro") or item.get("codpro") or c_sku).strip(),
                            "grupo": str(item.get("grupo") or "CONVENIÊNCIA").strip(),
                            "preco_unitario": float(item.get("preco_unitario") or item.get("preco") or 0.0),
                        }

            skus = sorted(itens_unicos.keys())
            for sku in skus:
                freq_itens[sku] = freq_itens.get(sku, 0) + 1

            for i in range(len(skus)):
                for j in range(i + 1, len(skus)):
                    p_par = (skus[i], skus[j])
                    freq_pares[p_par] = freq_pares.get(p_par, 0) + 1

        def _norm_str(s: Any) -> str:
            if not s:
                return ""
            n = unicodedata.normalize("NFD", str(s))
            n = "".join(c for c in n if unicodedata.category(c) != "Mn").lower()
            n = re.sub(r"[^a-z0-9]+", " ", n)
            return re.sub(r"\s+", " ", n).strip()

        STOP_FILTER_WORDS = {
            "o", "a", "os", "as", "um", "uma", "uns", "umas",
            "de", "do", "da", "dos", "das", "no", "na", "nos", "nas",
            "com", "para", "pra", "por", "produto", "mercadoria",
            "codigo", "cod", "item", "sku", "gelada", "gelado", "quente", "fria", "frio"
        }

        def _match_produto(filtro_txt: str, p_sku: str, p_nome: str) -> bool:
            fn = _norm_str(filtro_txt)
            if not fn:
                return True
            sku_n = _norm_str(p_sku)
            nom_n = _norm_str(p_nome)

            # 1. Match SKU (com ou sem zeros à esquerda se numérico)
            if fn == sku_n or (fn.isdigit() and sku_n.isdigit() and fn.lstrip("0") == sku_n.lstrip("0")):
                return True

            # 2. Substring direta no nome
            if fn in nom_n:
                return True

            # 3. Limpeza de stop words/artigos/adjetivos do filtro
            tokens = [t for t in fn.split() if t not in STOP_FILTER_WORDS and len(t) >= 1]
            if not tokens:
                tokens = [t for t in fn.split() if len(t) >= 1]

            frase_limpa = " ".join(tokens)
            if frase_limpa:
                if frase_limpa in nom_n:
                    return True
                if frase_limpa.isdigit() and sku_n.isdigit() and frase_limpa.lstrip("0") == sku_n.lstrip("0"):
                    return True

            # Checa se algum token numérico bate com o SKU
            for t in tokens:
                if t.isdigit() and sku_n.isdigit() and t.lstrip("0") == sku_n.lstrip("0"):
                    return True

            # Checa se todos os tokens significativos estão presentes no nome do produto
            if tokens and all(t in nom_n for t in tokens):
                return True

            return False

        regras: List[Dict[str, Any]] = []

        # 2. Avaliação de regras direcionadas (A -> B e B -> A)
        for (sku1, sku2), count_ab in freq_pares.items():
            sup_ab = count_ab / total_transacoes
            if sup_ab < min_suporte:
                continue

            info1 = produtos_info.get(sku1, {"codpro": sku1, "nompro": sku1, "preco_unitario": 0.0, "grupo": "CONVENIÊNCIA"})
            info2 = produtos_info.get(sku2, {"codpro": sku2, "nompro": sku2, "preco_unitario": 0.0, "grupo": "CONVENIÊNCIA"})

            direcoes = [(sku1, sku2, info1, info2), (sku2, sku1, info2, info1)]

            for a_sku, b_sku, a_info, b_info in direcoes:
                f_a = freq_itens.get(a_sku, 0)
                f_b = freq_itens.get(b_sku, 0)

                metricas = PostoTools.calcular_metricas_associacao(
                    total_transacoes=total_transacoes,
                    freq_a=f_a,
                    freq_b=f_b,
                    freq_ab=count_ab,
                )

                if metricas["confianca"] < min_confianca or metricas["lift"] < min_lift:
                    continue

                # Classificação da Sinergia
                lift_val = metricas["lift"]
                if lift_val >= 2.0:
                    classificacao = "FORTE_SINERGIA_CROSS_SELL"
                elif lift_val > 1.0:
                    classificacao = "ASSOCIACAO_POSITIVA"
                elif lift_val == 1.0:
                    classificacao = "INDEPENDENTE"
                else:
                    classificacao = "ASSOCIACAO_NEGATIVA"

                # Impacto Financeiro no Ticket Médio
                p_orig = float(a_info.get("preco_unitario", 0.0))
                p_rec = float(b_info.get("preco_unitario", 0.0))
                ticket_combo = round(p_orig + p_rec, 2)
                incr_pct = round((p_rec / p_orig) * 100.0, 1) if p_orig > 0 else 0.0

                if p_rec > 0.0:
                    script = (
                        f"Cliente comprou {a_info['nompro']}, ofereça {b_info['nompro']} "
                        f"por R$ {p_rec:.2f} (+{incr_pct:.1f}% no ticket)"
                    )
                else:
                    script = (
                        f"Cliente comprou {a_info['nompro']}, ofereça {b_info['nompro']} "
                        f"como complemento da compra"
                    )

                # Relevância com Filtro
                match_origem = False
                match_destino = False
                if filtro_produto:
                    match_origem = _match_produto(filtro_produto, a_info.get("codpro", ""), a_info.get("nompro", ""))
                    match_destino = _match_produto(filtro_produto, b_info.get("codpro", ""), b_info.get("nompro", ""))
                    if not (match_origem or match_destino):
                        continue

                regra_item = {
                    "produto_origem": a_info,
                    "produto_recomendado": b_info,
                    "metricas": {
                        "frequencia_conjunta": count_ab,
                        "suporte": metricas["suporte"],
                        "suporte_origem": metricas["suporte_a"],
                        "suporte_recomendado": metricas["suporte_b"],
                        "confianca": metricas["confianca"],
                        "lift": metricas["lift"],
                        "conviction": metricas["conviction"],
                    },
                    "impacto_financeiro": {
                        "preco_origem": p_orig,
                        "preco_recomendado": p_rec,
                        "ticket_combo": ticket_combo,
                        "incremento_ticket_reais": p_rec,
                        "incremento_ticket_pct": incr_pct,
                    },
                    "classificacao_sinergia": classificacao,
                    "script_sugerido_caixa": script,
                    "relevancia_filtro": "origem" if match_origem else ("destino" if match_destino else "geral"),
                }
                regras.append(regra_item)

        # 3. Ordenação: Prioridade para quando o produto filtrado é a origem (cross-sell direto)
        def chave_ordenacao(r):
            prioridade_filtro = 1 if r.get("relevancia_filtro") == "origem" else 0
            return (prioridade_filtro, r["metricas"]["lift"], r["metricas"]["confianca"], r["metricas"]["frequencia_conjunta"])

        regras.sort(key=chave_ordenacao, reverse=True)
        return regras

    def auditar_cesta_conveniencia_vendas_cruzadas(
        self,
        filtro_produto: Optional[str] = None,
        min_lift: float = 1.2,
        min_suporte: float = 0.005,
        min_confianca: float = 0.05,
        limit: int = 10,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Motor de Inteligência de Loja de Conveniência (Market Basket Analysis & Vendas Cruzadas).
        Analisa o comportamento de compra em cupons fiscais e pedidos do PDV (`pedido` + `itemped`),
        descobrindo afinidades entre mercadorias, minerando regras de associação (Suporte, Confiança e Lift)
        e gerando recomendações acionáveis de combos para alavancagem de ticket médio e margem de lucro.

        Parâmetros:
        - filtro_produto: Nome ou SKU para busca direcionada (ex: 'cerveja', 'coca-cola', '00022')
        - min_lift: Limiar mínimo de Lift (default 1.2; >= 2.0 indica forte sinergia comercial)
        - min_suporte: Suporte conjunto mínimo (default 0.005 ou 0.5% das vendas)
        - min_confianca: Confiança mínima (default 0.05 ou 5%)
        - limit: Quantidade máxima de recomendações de combos no ranking
        - data_inicio / data_fim: Intervalo opcional de datas YYYY-MM-DD
        """
        conn = None
        try:
            min_lift = float(min_lift) if min_lift is not None else 1.2
            min_suporte = float(min_suporte) if min_suporte is not None else 0.005
            min_confianca = float(min_confianca) if min_confianca is not None else 0.05
            limit = int(limit) if limit is not None else 10

            dt_ini_norm = self.normalizar_data(data_inicio) if data_inicio else None
            dt_fim_norm = self.normalizar_data(data_fim) if data_fim else None

            conn = get_erp_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = [
                    "(p.situ IS NULL OR p.situ != 'C')",
                    "(p.dtcanc IS NULL)",
                ]
                params: List[Any] = []

                if dt_ini_norm:
                    if dt_ini_norm == "hoje":
                        where_clauses.append("p.dtem = CURRENT_DATE")
                    elif dt_ini_norm == "ontem":
                        where_clauses.append("p.dtem = CURRENT_DATE - INTERVAL '1 day'")
                    else:
                        where_clauses.append("p.dtem >= %s")
                        params.append(dt_ini_norm)
                if dt_fim_norm:
                    if dt_fim_norm == "hoje":
                        where_clauses.append("p.dtem <= CURRENT_DATE")
                    elif dt_fim_norm == "ontem":
                        where_clauses.append("p.dtem <= CURRENT_DATE - INTERVAL '1 day'")
                    else:
                        where_clauses.append("p.dtem <= %s")
                        params.append(dt_fim_norm)

                where_sql = " AND ".join(where_clauses)

                query = f"""
                    SELECT 
                        TRIM(p.codi) AS pedido_id,
                        TRIM(p.cupom) AS cupom,
                        TRIM(p.pdv) AS pdv,
                        p.dtem AS data_venda,
                        ROUND(COALESCE(p.valortotal, 0)::numeric, 2) AS total_pedido,
                        TRIM(i.codpec) AS codpro,
                        COALESCE(NULLIF(TRIM(pr.nompro), ''), 'PRODUTO ' || TRIM(i.codpec)) AS nompro,
                        COALESCE(NULLIF(TRIM(g.grupo), ''), 'CONVENIÊNCIA') AS grupo,
                        ROUND(COALESCE(pr.valvenda, i.valunit, 0)::numeric, 2) AS preco_unitario,
                        ROUND(COALESCE(i.quant, 1)::numeric, 2) AS quantidade,
                        ROUND(COALESCE(i.valitem, 0)::numeric, 2) AS total_item
                    FROM pedido p
                    JOIN itemped i ON TRIM(i.pedido) = TRIM(p.codi)
                    LEFT JOIN produtos pr ON TRIM(pr.codpro) = TRIM(i.codpec)
                    LEFT JOIN grupos g ON TRIM(g.codi) = TRIM(pr.codgru)
                    WHERE {where_sql}
                    ORDER BY p.codi, i.controle;
                """
                cur.execute(query, params)
                linhas = cur.fetchall()

            # Agrupa itens por pedido
            transacoes_map: Dict[str, List[Dict[str, Any]]] = {}
            totais_pedidos: List[float] = []
            todos_skus: Set[str] = set()

            for r in linhas:
                ped_id = r["pedido_id"]
                if ped_id not in transacoes_map:
                    transacoes_map[ped_id] = []
                    totais_pedidos.append(float(r["total_pedido"] or 0.0))
                
                transacoes_map[ped_id].append({
                    "codpro": r["codpro"],
                    "nompro": r["nompro"],
                    "grupo": r["grupo"],
                    "preco_unitario": float(r["preco_unitario"] or 0.0),
                    "quantidade": float(r["quantidade"] or 1.0),
                    "total_item": float(r["total_item"] or 0.0),
                })
                todos_skus.add(r["codpro"])

            # Corrige totais de pedidos que possam ter vindo zerados do ERP
            for idx, (ped_id, itens) in enumerate(transacoes_map.items()):
                if idx < len(totais_pedidos) and totais_pedidos[idx] <= 0.0:
                    totais_pedidos[idx] = round(sum(it["total_item"] for it in itens), 2)

            lista_transacoes = list(transacoes_map.values())
            total_transacoes = len(lista_transacoes)
            transacoes_multiplas = [t for t in lista_transacoes if len(t) >= 2]
            total_multiplas = len(transacoes_multiplas)
            pct_multiplas = round((total_multiplas / total_transacoes) * 100.0, 2) if total_transacoes > 0 else 0.0

            ticket_medio_geral = round(sum(totais_pedidos) / total_transacoes, 2) if total_transacoes > 0 else 0.0

            # Minera regras de associação completas
            todas_regras = self.calcular_regras_associacao(
                transacoes=lista_transacoes,
                min_suporte=min_suporte,
                min_confianca=min_confianca,
                min_lift=min_lift,
                filtro_produto=filtro_produto,
            )

            top_combos = todas_regras[:limit]
            for idx, combo in enumerate(top_combos, start=1):
                combo["ranking"] = idx

            count_forte_sinergia = sum(1 for r in todas_regras if r["metricas"]["lift"] >= 2.0)
            maior_lift = max((r["metricas"]["lift"] for r in todas_regras), default=0.0)

            # Diagnóstico Estratégico
            if total_transacoes == 0:
                diagnostico = "Nenhuma venda registrada no período selecionado."
            elif total_multiplas == 0:
                diagnostico = (
                    "Todos os cupons emitidos continham apenas 1 único item. "
                    "Oportunidade urgente para implantar cultura ativa de vendas cruzadas e combos no PDV."
                )
            elif count_forte_sinergia > 0:
                diagnostico = (
                    f"Excelente potencial de cross-selling: {count_forte_sinergia} combo(s) identificados com Lift >= 2.0 "
                    f"(forte afinidade de consumo). Maior Lift apurado: {maior_lift:.2f}x."
                )
            elif len(todas_regras) > 0:
                diagnostico = (
                    f"Identificadas {len(todas_regras)} associações com correlação positiva (Lift entre {min_lift} e 2.0). "
                    "Boa oportunidade para agrupamento físico na loja."
                )
            else:
                diagnostico = (
                    f"Nenhuma regra atendeu ao critério mínimo de Lift >= {min_lift} para o filtro solicitado."
                )

            # Recomendações Práticas para o Gestor e Operadores de Caixa
            recomendacoes = []
            if top_combos:
                c_top = top_combos[0]
                recomendacoes.append(
                    f"Combo Destaque no PDV: Estimular ativamente a venda de '{c_top['produto_origem']['nompro']}' "
                    f"em conjunto com '{c_top['produto_recomendado']['nompro']}' (Lift {c_top['metricas']['lift']:.2f}x, "
                    f"Confiança {c_top['metricas']['confianca']*100:.1f}%), gerando aumento de {c_top['impacto_financeiro']['incremento_ticket_pct']:.1f}% no ticket médio."
                )
                recomendacoes.append(
                    "Layout & Merchandising: Posicionar produtos com alta afinidade lado a lado no balcão ou criar ilhas temáticas "
                    "(ex: carvão e gelo próximos aos refrigeradores de cerveja; balas e chocolates junto ao caixa)."
                )
                recomendacoes.append(
                    "Treinamento do Caixa: Capacitar os operadores para utilizar os scripts persuasivos sugeridos "
                    "sempre que o cliente apresentar o primeiro item da cesta."
                )
            else:
                recomendacoes.append(
                    "Promoções de Entrada: Criar combos promocionais iniciais (ex: 'Na compra de 1 café, leve 1 salgado por R$ X') "
                    "para estimular o hábito de compra de múltiplos itens."
                )

            resultado = {
                "status": "ok",
                "timestamp_geracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "parametros_consulta": {
                    "filtro_produto": filtro_produto,
                    "min_lift": min_lift,
                    "min_suporte": min_suporte,
                    "min_confianca": min_confianca,
                    "limit": limit,
                    "periodo": {
                        "data_inicio": data_inicio,
                        "data_fim": data_fim,
                    },
                },
                "resumo_executivo": {
                    "total_transacoes_analisadas": total_transacoes,
                    "total_transacoes_multiplos_itens": total_multiplas,
                    "pct_cestas_multiplos_itens": pct_multiplas,
                    "total_itens_distintos_conveniencia": len(todos_skus),
                    "total_regras_geradas": len(todas_regras),
                    "regras_com_forte_sinergia_lift_2": count_forte_sinergia,
                    "maior_lift_encontrado": round(maior_lift, 4),
                    "ticket_medio_conveniencia": ticket_medio_geral,
                    "diagnostico_estrategico": diagnostico,
                },
                "top_combos_cross_selling": top_combos,
                "regras_associacao_detalhadas": todas_regras,
                "recomendacoes_pdv_gestor": recomendacoes,
            }

            resultado_limpo, _ = sanitize_dict(resultado)
            return resultado_limpo

        except Exception as e:
            return {
                "status": "indisponivel",
                "motivo": f"Falha na análise de Market Basket da Loja de Conveniência no ERP: {e}",
            }
        finally:
            if conn and not conn.closed:
                try:
                    conn.close()
                except Exception:
                    pass


