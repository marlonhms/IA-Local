"""
Roteador Semântico Vetorial (Semantic Intent Router com pgvector)
Classificação de intenções operacionais para postos de combustíveis e PDV.

Tecnologias:
- PostgreSQL 16 + pgvector (0.8.6+) com busca vetorial halfvec(768) e índice HNSW
- Embeddings via Google Gemini API (gemini-embedding-001)
- Latência de busca vetorial sub-5ms (< 5ms)
- Cache em memória LRU para queries repetidas (< 0.1ms)
- Threshold de confiança calibrado com fallback gracioso para heurísticas
- Telemetria e observabilidade SRE integradas
"""

import os
import re
import sys
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from config.settings import (
    DB_VECTOR_CONFIG,
    DEFAULT_EMBEDDING_MODEL,
    GEMINI_API_KEY,
)

logger = logging.getLogger("SemanticRouter")

# Catálogo canônico das 9 intenções operacionais do sistema
INTENT_EXEMPLARS: Dict[str, Dict[str, Any]] = {
    "auditoria_turno": {
        "descricao": "Auditoria de fechamento de turno, conciliação de pista e caixa, furos e quebras",
        "exemplos": [
            "Como fechou o 1º turno hoje?",
            "Auditoria de fechamento de turno",
            "Teve furo de caixa ou de pista?",
            "Houve sobra ou falta de caixa na pista?",
            "O caixa bateu com o que saiu dos bicos?",
            "Conciliação de turno e conferência de encerrantes",
            "Teve quebra de caixa ou divergência hoje?",
            "Como foi o encerramento do turno da noite?",
            "Conferir encerrantes das bombas e automação CBC04",
            "Sobrou ou faltou dinheiro no fechamento?",
            "deu ruim no fechamento do turno?",
            "sobro troco no 3 turno?",
            "o caixa bateu?",
            "auditoria de pista hoje",
            "relatório de fechamento de turno",
        ]
    },
    "previsao_tanques": {
        "descricao": "Previsão de esgotamento de combustível (run-out), autonomia e sugestão de pedidos",
        "exemplos": [
            "Quando vai acabar a Gasolina Comum?",
            "Previsão de esgotamento dos tanques",
            "Qual tanque está mais crítico hoje?",
            "Preciso pedir combustível para o fim de semana?",
            "Qual a autonomia dos tanques de combustível?",
            "Quando vai acabar o diesel s10?",
            "Quando seca o tanque de etanol?",
            "Qual a previsão de run-out dos tanques?",
            "Sugestão de compra de carreta de combustível",
            "Qual o espaço livre de descarga e ullage nos tanques?",
            "Quanto tempo dura o estoque de gasolina?",
            "vai faltar gasosa no fim de semana?",
            "quando o diesel acaba?",
            "quantos compartimentos cabem no tanque?",
            "risco de secar combustível no sábado",
        ]
    },
    "desempenho_pista_frentistas": {
        "descricao": "Auditoria de pista, desempenho de frentistas, vazão de bicos e conversão de aditivada",
        "exemplos": [
            "Qual frentista vendeu mais gasolina aditivada hoje?",
            "Tem algum bico com problema ou vazão lenta?",
            "Como está o desempenho da equipe de pista?",
            "Ranking dos frentistas e produtividade",
            "Qual frentista tem o maior ticket médio?",
            "Vazão dos bicos da bomba e filtro sujo",
            "Bico com filtro obstruído ou vazão baixa",
            "Conversão de aditivada dos operadores de pista",
            "Teve abastecimento suspeito ou anomalia na pista?",
            "os frentista renderam bem hoje?",
            "tem bico lerdo na bomba 2?",
            "quem é o frentista que mais faturou?",
            "anomalias operacionais de pista",
            "time de pista hoje",
        ]
    },
    "vendas_analitico": {
        "descricao": "Análise analítica de vendas, faturamento geral, últimos itens vendidos no PDV",
        "exemplos": [
            "Qual o produto mais vendido hoje?",
            "Quanto faturou o posto hoje?",
            "Qual foi o último produto vendido?",
            "Histórico de vendas e faturamento do dia",
            "Resumo de faturamento e cupons fiscais emitidos",
            "Qual o total faturado no dia de ontem?",
            "O que foi vendido por último no PDV?",
            "qual o faturamento total da firma?",
            "quantos litros foram vendidos hoje no total?",
            "venda recente de produtos",
            "como estão as vendas hoje?",
        ]
    },
    "estoque_posicao": {
        "descricao": "Posição física de estoque de produtos, almoxarifado e nível de produtos",
        "exemplos": [
            "Qual o saldo físico do estoque de produtos?",
            "Quanto tem de gasolina no tanque?",
            "Quanto tem no estoque de lubrificante?",
            "Qual o saldo do tanque 1?",
            "Itens com estoque baixo ou em falta na conveniência",
            "Saldo atual de mercadorias no estoque",
            "quanto tem de mercadoria na prateleira?",
            "tem produto acabando no estoque?",
            "posição geral de estoque da loja",
        ]
    },
    "clientes_ranking": {
        "descricao": "Ranking de clientes, maiores compradores, faturamento por cliente e cadastros",
        "exemplos": [
            "Quem é o cliente que mais comprou?",
            "Ranking de clientes por faturamento",
            "Cadastro de clientes no sistema",
            "Qual cliente teve o maior gasto no posto?",
            "Histórico de consumo do cliente faturado",
            "maior comprador da frota este mês",
            "qual o melhor cliente da empresa?",
            "lista dos principais compradores",
        ]
    },
    "sre_metricas": {
        "descricao": "Observabilidade e telemetria SRE, saúde do PostgreSQL, cache hit e latência",
        "exemplos": [
            "Qual a saúde do banco de dados?",
            "Métricas de SRE e cache hit ratio",
            "Estatísticas dos índices HNSW e conexões ativas",
            "Latência média de busca e consultas",
            "Como está o uso de memória do postgres?",
            "telemetria do banco e pg_stat",
            "status do servidor de dados",
        ]
    },
    "dados_filial": {
        "descricao": "Dados cadastrais da filial do posto, CNPJ, razão social, endereço e PDV",
        "exemplos": [
            "Qual o CNPJ da filial?",
            "Qual é o endereço do posto?",
            "Qual é a filial e dados da empresa?",
            "Razão social e localização da filial",
            "Qual o PDV cadastrado no sistema?",
            "dados cadastrais do posto matriz",
            "qual a inscrição estadual da empresa?",
        ]
    },
    "catalogo_produtos": {
        "descricao": "Busca híbrida no catálogo de produtos, preços, marcas, cervejas, lubrificantes",
        "exemplos": [
            "Qual o preço da cerveja Heineken?",
            "Qual o preço da gasolina comum?",
            "Quanto custa o diesel s10?",
            "Tem óleo lubrificante Lubrax 5W30 e qual o valor?",
            "Preço do carvão e gelo na conveniência",
            "Quanto tá a Coca-Cola 2 litros?",
            "Preço do Red Bull lata 250ml",
            "quanto custa o lubrificante 15w40?",
            "tem cigarro e qual o preço?",
        ]
    },
}


def classificar_intencao_heuristica(pergunta: str) -> str:
    """
    Classificador determinístico baseado em regras léxicas e heurísticas de posto.
    Usado como fallback ultrarrápido (sub-milissegundo) para o roteador semântico.
    """
    p = pergunta.lower()

    # 0. Conciliação de Turnos & Auditoria de Pista
    termos_auditoria_exatos = [
        "fechamento de turno", "fechamento do turno", "fechar turno", "fechou o turno",
        "fechou o 1º turno", "fechou o 2º turno", "fechou o 3º turno",
        "fechou o 1o turno", "fechou o 2o turno", "fechou o 3o turno",
        "fechou o primeiro turno", "fechou o segundo turno", "fechou o terceiro turno",
        "auditar fechamento", "auditoria de turno", "auditoria de pista", "auditoria do turno",
        "conciliação de turno", "conciliacao de turno", "conciliação de turnos", "conciliacao de turnos",
        "conciliar turno", "conciliar turnos", "conciliação", "conciliacao",
        "furo de caixa", "furo de pista", "furo de bico", "furos de caixa",
        "sobra de caixa", "falta de caixa", "quebra de caixa", "quebra de pista",
        "caixa bateu", "bateu o caixa", "bateu com a pista", "bateu com o caixa",
        "saiu dos bicos", "saiu do bico", "conferir turno", "conferência de turno", "conferencia de turno",
        "auditar turno", "auditar pista", "auditar o turno", "conferência de pista", "conferencia de pista",
        "relatório de fechamento", "relatorio de fechamento", "divergência na pista", "divergencia na pista",
        "divergência de pista", "divergencia de pista", "diferença de caixa", "diferenca de caixa",
        "diferença no turno", "diferenca no turno", "sobrou ou faltou", "o encerrante bateu", "bateu os bicos",
        "bateu o turno"
    ]
    if any(t in p for t in termos_auditoria_exatos):
        return "auditoria_turno"

    tem_raiz_auditoria = any(k in p for k in [
        "turno", "fechamento", "concilia", "furo", "quebra", "auditar", "auditoria", 
        "conferência", "conferencia", "encerramento", "divergência", "divergencia", "encerrante"
    ])
    if ("frentista" in p or "frentistas" in p) and not any(k in p for k in ["furo", "quebra", "bateu", "sobra", "falta", "concilia"]):
        pass
    elif tem_raiz_auditoria:
        if any(w in p for w in [
            "hoje", "ontem", "anteontem", "como foi", "como fechou", "qual foi", "qual o", "resumo",
            "bateu", "caixa", "bomba", "bico", "sobra", "falta", "1º", "2º", "3º", "1o", "2o", "3o",
            "primeiro", "segundo", "terceiro", "manhã", "manha", "tarde", "noite", "madrugada", "teve", "houve"
        ]):
            return "auditoria_turno"

    # 1. Previsão de Esgotamento de Combustível (Run-Out Forecast) & Sugestão de Pedidos
    termos_previsao_exatos = [
        "quando vai acabar", "quando acaba", "vai acabar", "vai secar", "quando seca", "quando vai secar",
        "previsão de esgotamento", "previsao de esgotamento", "previsão dos tanques", "previsao dos tanques",
        "previsão de tanque", "previsao de tanque", "esgotamento dos tanques", "esgotamento do tanque",
        "esgotamento de combustível", "esgotamento de combustivel", "run-out", "run out", "runout",
        "autonomia dos tanques", "autonomia do tanque", "autonomia de combustível", "autonomia de combustivel",
        "autonomia de combustíveis", "autonomia de combustiveis", "qual a autonomia", "qual é a autonomia",
        "quanto tempo dura", "quanto tempo resta", "duração do estoque", "duracao do estoque", "tempo de estoque",
        "vai durar", "vai terminar", "quando termina", "tanque mais crítico", "tanque mais critico",
        "qual tanque está mais crítico", "qual tanque esta mais critico",
        "tanques mais críticos", "tanques mais criticos", "mais crítico hoje", "mais critico hoje",
        "pedir combustível", "pedir combustivel", "pedir gasolina", "pedir diesel", "pedir etanol",
        "preciso pedir", "preciso comprar combustível", "preciso comprar combustivel", "sugestão de pedido",
        "sugestao de pedido", "sugestão de compra", "sugestao de compra", "pedido de carreta", "pedido de caminhão",
        "pedido de caminhao", "espaço livre para descarga", "espaco livre para descarga", "espaço livre de descarga",
        "espaco livre de descarga", "espaço de descarga", "espaco de descarga", "espaço para descarga", "espaco para descarga",
        "espaço livre", "espaco livre", "ullage", "quanto cabe de descarga", "quantos compartimentos",
        "quantos litros cabem", "quanto cabe no tanque"
    ]
    if any(t in p for t in termos_previsao_exatos):
        return "previsao_tanques"

    tem_termo_preditivo = any(k in p for k in [
        "previsão", "previsao", "acabar", "acaba", "acabam", "secar", "seca", "secam",
        "esgotamento", "esgotar", "esgota", "autonomia", "run-out", "runout", "run out",
        "durar", "dura", "duram", "duração", "duracao", "resta", "restam", "terminar", "termina",
        "pedir", "comprar", "compra", "pedido", "pedidos",
        "descarga", "ullage", "carreta", "compartimento", "compartimentos", "cabe", "cabem"
    ])
    tem_termo_combustivel_ou_tanque = any(w in p for w in [
        "gasolina", "diesel", "etanol", "álcool", "alcool", "arla", "combustível", "combustivel", "combustíveis", "combustiveis",
        "tanque", "tanques", "tq"
    ])

    if tem_termo_preditivo and tem_termo_combustivel_ou_tanque:
        if not any(preco_word in p for preco_word in ["preço", "preco", "custa", "valor"]):
            return "previsao_tanques"

    if "quanto tempo" in p and tem_termo_combustivel_ou_tanque:
        return "previsao_tanques"

    if "fim de semana" in p and any(w in p for w in ["combustível", "combustivel", "pedir", "comprar", "tanque", "tanques", "gasolina", "diesel", "etanol", "preciso"]):
        return "previsao_tanques"

    if "crítico" in p or "critico" in p:
        if any(w in p for w in ["tanque", "tanques", "combustível", "combustivel", "hoje", "posto", "qual"]):
            return "previsao_tanques"

    # 2. Perguntas sobre estoque, saldo e tanques de combustível
    termos_estoque = [
        "estoque", "mais estoque", "maior estoque", "saldo de estoque", "saldo em estoque",
        "quanto tem de", "quanto tem no tanque", "nível do tanque", "nivel do tanque", "tanque", "tanques",
        "quantidade em estoque", "itens em estoque", "saldo físico", "saldo fisico", "falta de produto",
        "estoque baixo", "acabando", "tem no estoque", "tem em estoque", "com mais estoque", "com maior estoque"
    ]
    if any(t in p for t in termos_estoque) or (("saldo" in p or "estoque" in p) and any(w in p for w in ["produto", "mais", "tem", "qual", "quanto", "hoje", "maior", "nível", "nivel"])):
        return "estoque_posicao"

    # 3. Perguntas sobre clientes, ranking de compradores e cadastros
    termos_clientes = [
        "cliente", "clientes", "mais comprou", "maior comprador", "ranking de clientes",
        "quem mais comprou", "qual cliente", "cadastro de cliente", "clientes cadastrados",
        "consumidor final", "compras do cliente", "gasto por cliente"
    ]
    if any(t in p for t in termos_clientes) or ("cliente" in p and any(w in p for w in ["mais", "quem", "qual", "comprou", "gasta", "ranking", "total", "cadastrado", "cadastro"])):
        return "clientes_ranking"

    # 4. Desempenho de Frentistas, Vazão de Bicos & Auditoria Operacional de Pista
    termos_pista_exatos = [
        "ranking dos frentistas", "ranking de frentistas", "ranking frentistas",
        "desempenho dos frentistas", "desempenho de frentistas", "desempenho da equipe",
        "desempenho da equipe de pista", "desempenho da pista", "desempenho de pista",
        "equipe de pista", "time de pista", "produtividade dos frentistas", "produtividade da pista",
        "produtividade da equipe", "vazão dos bicos", "vazao dos bicos", "vazão das bombas",
        "vazao das bombas", "vazão do bico", "vazao do bico", "vazão da bomba", "vazao da bomba",
        "bico com problema", "bicos com problema", "vazão lenta", "vazao lenta", "vazão baixa",
        "vazao baixa", "bico lento", "bicos lentos", "filtro sujo", "filtro lento", "filtro obstruído",
        "filtro obstruido", "filtro da bomba", "filtro do bico", "bomba lenta", "bombas lentas",
        "troca de filtro", "trocar filtro", "conversão de aditivada", "conversao de aditivada",
        "conversão de gasolina aditivada", "conversao de gasolina aditivada", "vendas de aditivada",
        "venda de aditivada", "quem vendeu mais aditivada", "vendeu mais gasolina aditivada",
        "vendeu mais aditivada", "maior conversão", "maior conversao", "ticket médio dos frentistas",
        "ticket medio dos frentistas", "ticket médio por frentista", "ticket medio por frentista",
        "maior ticket médio", "maior ticket medio", "qual frentista tem o maior ticket médio",
        "qual frentista tem o maior ticket medio", "anomalias na pista", "anomalias de pista",
        "anomalia na pista", "anomalia de pista", "anomalias da pista", "filtro de combustível",
        "filtro de combustivel"
    ]
    if any(t in p for t in termos_pista_exatos):
        return "desempenho_pista_frentistas"

    if "frentista" in p or "frentistas" in p:
        return "desempenho_pista_frentistas"

    if any(w in p for w in ["vazão", "vazao", "filtro"]) and any(w in p for w in ["bico", "bicos", "bomba", "bombas", "lenta", "lento", "sujo", "suja", "problema", "obstruído", "obstruido", "baixa", "baixo"]):
        return "desempenho_pista_frentistas"

    if "aditivada" in p and any(w in p for w in ["vendeu", "vendeu mais", "conversão", "conversao", "ranking", "quem", "campeão", "campeao", "líder", "lider"]):
        return "desempenho_pista_frentistas"

    if ("ticket médio" in p or "ticket medio" in p) and any(w in p for w in ["frentista", "frentistas", "pista", "maior", "quem", "qual", "equipe"]):
        return "desempenho_pista_frentistas"

    if any(w in p for w in ["anomalia", "anomalias", "suspeito", "suspeitos", "suspeita", "suspeitas", "irregular", "irregulares", "atípico", "atipico"]) and any(w in p for w in ["pista", "bico", "bomba", "abastecimento", "abastecimentos"]):
        return "desempenho_pista_frentistas"

    if any(w in p for w in ["equipe", "time"]) and any(w in p for w in ["pista", "frentista", "frentistas"]):
        return "desempenho_pista_frentistas"

    if "desempenho" in p and any(w in p for w in ["equipe", "time", "pista", "frentista", "frentistas"]):
        return "desempenho_pista_frentistas"

    # 5. Perguntas sobre vendas, faturamento, último produto vendido e abastecimentos
    termos_vendas = [
        "mais vendido", "mais vendidos", "ranking de vendas", "ranking", "campeão de venda", 
        "quanto vendeu", "faturamento", "total de vendas", "histórico de venda", "vendas hoje",
        "vendas de hoje", "como estao as vendas", "como estão as vendas", "vendas do dia",
        "quanto faturou", "total faturado", "resumo do dia", "resumo de vendas", "relatório de vendas",
        "abastecimentos", "quantos abastecimentos", "movimento de hoje", "movimento do caixa",
        "litros vendidos", "litragem", "ultimo produto", "último produto", "ultimo produto vendido",
        "último produto vendido", "última venda", "ultima venda", "ultimas vendas", "últimas vendas",
        "o que vendeu por ultimo", "o que vendeu por último", "o que foi vendido", "vendeu agora",
        "último item vendido", "ultimo item vendido", "venda recente", "vendas recentes",
        "último item", "ultimo item", "itens vendidos", "produtos vendidos", "o que vendeu",
        "ultimo vendido", "último vendido"
    ]
    if any(t in p for t in termos_vendas) or (
        ("venda" in p or "vendas" in p or "vendido" in p or "vendidos" in p or "vendeu" in p) and 
        any(w in p for w in ["hoje", "ontem", "dia", "como", "quanto", "total", "geral", "resumo", "ultimo", "último", "recente", "recentes", "agora", "foi", "qual", "identifica", "identificar"])
    ):
        return "vendas_analitico"

    # 6. Perguntas sobre SRE, banco de dados e observabilidade
    termos_sre = ["métrica", "metricas", "sre", "cache hit", "latência", "índice hnsw", "saúde do banco", "pg_stat"]
    if any(t in p for t in termos_sre):
        return "sre_metricas"

    # 7. Perguntas cadastrais da filial
    termos_filial = [
        "qual é a filial", "qual o nome do posto", "qual o cnpj", "endereço da filial", 
        "endereco da filial", "endereço do posto", "endereco do posto", "qual o pdv",
        "dados da filial", "dados do posto"
    ]
    if any(t in p for t in termos_filial):
        return "dados_filial"

    # Padrão: busca no catálogo de produtos (RAG Híbrido)
    return "catalogo_produtos"


class SemanticRouter:
    """
    Roteador Semântico Vetorial utilizando PostgreSQL 16 + pgvector.
    Mapeia perguntas em linguagem natural para as 9 intenções operacionais do Ai.la.
    """

    def __init__(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        rag_engine: Optional[Any] = None,
        confidence_threshold: float = 0.58,
        cache_max_size: int = 500,
    ):
        self.db_config = db_config or DB_VECTOR_CONFIG
        self.rag_engine = rag_engine
        self.confidence_threshold = confidence_threshold
        self.cache_max_size = cache_max_size

        # Cache em memória para consultas idênticas ou normalizadas (latência < 0.1ms)
        self._memory_cache: Dict[str, Tuple[str, float, Dict[str, Any]]] = {}

        # Métricas internas SRE
        self._metrics = {
            "total_routes": 0,
            "cache_hits": 0,
            "vector_pgvector_hits": 0,
            "heuristic_fallbacks": 0,
            "total_pgvector_latency_ms": 0.0,
            "total_routing_latency_ms": 0.0,
        }

    def _get_connection(self):
        """Retorna uma nova conexão com o PostgreSQL do pgvector."""
        return psycopg2.connect(**self.db_config)

    def init_table(self):
        """Garante a existência da tabela intencoes_vetores e índice HNSW no posto_ai."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS intencoes_vetores (
                        id SERIAL PRIMARY KEY,
                        intencao VARCHAR(50) NOT NULL,
                        descricao TEXT NOT NULL,
                        exemplo_frase TEXT NOT NULL,
                        embedding halfvec(768),
                        criado_em TIMESTAMP DEFAULT NOW()
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_intencoes_vetores_hnsw 
                    ON intencoes_vetores USING hnsw (embedding halfvec_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)
                conn.commit()

    def count_intents(self) -> int:
        """Retorna o número de exemplos de intenções indexados."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM intencoes_vetores WHERE embedding IS NOT NULL;")
                    row = cur.fetchone()
                    return row[0] if row else 0
        except Exception:
            return 0

    def seed_intents(self, force: bool = False) -> int:
        """
        Popula a tabela intencoes_vetores com os exemplares canônicos das 9 intenções.
        Gera embeddings via Gemini e indexa no pgvector com halfvec(768).
        """
        self.init_table()
        current_count = self.count_intents()
        if current_count > 0 and not force:
            logger.info(f"Tabela 'intencoes_vetores' já possui {current_count} registros. Seeding ignorado.")
            return current_count

        if not self.rag_engine:
            from core.rag_engine import HybridRAGEngine
            self.rag_engine = HybridRAGEngine(db_config=self.db_config)

        total_inseridos = 0
        exemplos_lote = []
        for intencao, dados in INTENT_EXEMPLARS.items():
            desc = dados["descricao"]
            for frase in dados["exemplos"]:
                exemplos_lote.append((intencao, desc, frase))

        logger.info(f"Gerando embeddings para {len(exemplos_lote)} frases de intenções...")

        # Gera embeddings em lotes para respeitar limites da API
        batch_size = 20
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if force:
                    cur.execute("TRUNCATE TABLE intencoes_vetores RESTART IDENTITY;")

                for i in range(0, len(exemplos_lote), batch_size):
                    chunk = exemplos_lote[i:i + batch_size]
                    textos = [f"Intenção: {item[0]} | Pergunta Típica: {item[2]}" for item in chunk]

                    try:
                        import google.generativeai as genai
                        res = genai.embed_content(
                            model=DEFAULT_EMBEDDING_MODEL,
                            content=textos,
                            output_dimensionality=768,
                            task_type="retrieval_document"
                        )
                        embeddings = res["embedding"]

                        for (intencao, desc, frase), emb in zip(chunk, embeddings):
                            cur.execute("""
                                INSERT INTO intencoes_vetores (intencao, descricao, exemplo_frase, embedding)
                                VALUES (%s, %s, %s, %s::halfvec);
                            """, (intencao, desc, frase, str(emb)))
                            total_inseridos += 1

                        conn.commit()
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Erro ao gerar embeddings do lote {i}: {e}")

        logger.info(f"Seeding concluído: {total_inseridos} intenções indexadas em intencoes_vetores.")
        return total_inseridos

    def route(
        self,
        query_text: str,
        query_vector: Optional[List[float]] = None,
        use_cache: bool = True,
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Roteia a pergunta para a melhor intenção operacional:
        1. Cache em memória (< 0.1ms)
        2. Busca vetorial via pgvector cosine distance (< 5ms)
        3. Fallback gracioso para heurísticas determinísticas se similaridade < threshold ou falha
        """
        t0 = time.perf_counter()
        self._metrics["total_routes"] += 1
        query_norm = query_text.strip().lower()

        # 1. Checa cache em memória
        if use_cache and query_norm in self._memory_cache:
            self._metrics["cache_hits"] += 1
            intencao, conf, cached_telemetry = self._memory_cache[query_norm]
            latency_ms = (time.perf_counter() - t0) * 1000
            telemetry = dict(cached_telemetry)
            telemetry["method"] = "memory_cache"
            telemetry["total_routing_latency_ms"] = round(latency_ms, 3)
            return intencao, conf, telemetry

        # 2. Roteamento Vetorial via pgvector
        pg_latency_ms = 0.0
        emb_latency_ms = 0.0
        emb_gerado = query_vector

        try:
            if not emb_gerado:
                if not self.rag_engine:
                    from core.rag_engine import HybridRAGEngine
                    self.rag_engine = HybridRAGEngine(db_config=self.db_config)
                t_emb = time.perf_counter()
                emb_gerado = self.rag_engine.gerar_embedding(query_text, task_type="retrieval_query")
                emb_latency_ms = (time.perf_counter() - t_emb) * 1000

            t_pg = time.perf_counter()
            sql = """
                SELECT 
                    intencao, 
                    exemplo_frase, 
                    descricao,
                    1 - (embedding <=> %s::halfvec) AS similarity
                FROM intencoes_vetores
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::halfvec
                LIMIT 1;
            """
            vec_str = str(emb_gerado)
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (vec_str, vec_str))
                    melhor_match = cur.fetchone()

            pg_latency_ms = (time.perf_counter() - t_pg) * 1000
            self._metrics["total_pgvector_latency_ms"] += pg_latency_ms

            if melhor_match:
                similarity = float(melhor_match["similarity"])
                intencao_detectada = melhor_match["intencao"]

                # Verifica se atinge o threshold de confiança
                if similarity >= self.confidence_threshold:
                    self._metrics["vector_pgvector_hits"] += 1
                    total_ms = (time.perf_counter() - t0) * 1000
                    self._metrics["total_routing_latency_ms"] += total_ms

                    telemetry = {
                        "intent": intencao_detectada,
                        "confidence": round(similarity, 4),
                        "method": "vector_pgvector",
                        "matched_phrase": melhor_match["exemplo_frase"],
                        "matched_desc": melhor_match["descricao"],
                        "pgvector_latency_ms": round(pg_latency_ms, 2),
                        "embedding_latency_ms": round(emb_latency_ms, 2),
                        "total_routing_latency_ms": round(total_ms, 2),
                        "confidence_threshold": self.confidence_threshold,
                        "query_vector": emb_gerado,
                    }

                    if len(self._memory_cache) < self.cache_max_size:
                        self._memory_cache[query_norm] = (intencao_detectada, similarity, telemetry)

                    return intencao_detectada, similarity, telemetry

        except Exception as e:
            logger.warning(f"Roteamento vetorial falhou ({e}). Acionando fallback heurístico.")

        # 3. Fallback Gracioso para Heurísticas Determinísticas
        self._metrics["heuristic_fallbacks"] += 1
        intencao_heuristica = classificar_intencao_heuristica(query_text)
        total_ms = (time.perf_counter() - t0) * 1000
        self._metrics["total_routing_latency_ms"] += total_ms

        telemetry = {
            "intent": intencao_heuristica,
            "confidence": 0.50,
            "method": "heuristic_fallback",
            "matched_phrase": "Heurística regex/keywords",
            "pgvector_latency_ms": round(pg_latency_ms, 2),
            "embedding_latency_ms": round(emb_latency_ms, 2),
            "total_routing_latency_ms": round(total_ms, 2),
            "confidence_threshold": self.confidence_threshold,
            "query_vector": emb_gerado,
        }

        if len(self._memory_cache) < self.cache_max_size:
            self._memory_cache[query_norm] = (intencao_heuristica, 0.50, telemetry)

        return intencao_heuristica, 0.50, telemetry

    def get_sre_telemetry(self) -> Dict[str, Any]:
        """Retorna telemetria operacional de SRE do roteador semântico."""
        tot = max(self._metrics["total_routes"], 1)
        avg_pg = self._metrics["total_pgvector_latency_ms"] / max(self._metrics["vector_pgvector_hits"], 1)
        avg_tot = self._metrics["total_routing_latency_ms"] / tot

        return {
            "total_routes": self._metrics["total_routes"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_hit_ratio_percent": round(100.0 * self._metrics["cache_hits"] / tot, 2),
            "vector_pgvector_hits": self._metrics["vector_pgvector_hits"],
            "vector_hit_ratio_percent": round(100.0 * self._metrics["vector_pgvector_hits"] / tot, 2),
            "heuristic_fallbacks": self._metrics["heuristic_fallbacks"],
            "fallback_ratio_percent": round(100.0 * self._metrics["heuristic_fallbacks"] / tot, 2),
            "avg_pgvector_latency_ms": round(avg_pg, 2),
            "avg_total_routing_latency_ms": round(avg_tot, 2),
            "cached_entries_in_memory": len(self._memory_cache),
        }
