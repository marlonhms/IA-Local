"""
Ponto de Entrada Principal (Main CLI) do Agente Inteligente do Posto & PDV.
Arquitetura:
- Motor: HybridRAGEngine (PostgreSQL 16 pgvector + GIN FTS + Reciprocal Rank Fusion)
- LLM: Google Gemini com Streaming de Resposta (TTFT reduzido para tempo real)
- Roteador de Ferramentas (Tool Routing):
    1. Vendas e Movimentação do PDV (pedido + itemped + abastecimentos)
    2. Posição de Estoque e Tanques (produtos + tanques)
    3. Análise de Clientes e Faturamento (clientes + pedido)
    4. Catálogo de Produtos com RAG Híbrido HNSW + GIN e Cache Semântico
    5. Telemetria SRE (PostgreSQL 16)
    6. Dados Cadastrais da Filial (empresa)
    7. Previsão de Esgotamento de Combustível (Run-Out) & Sugestão de Pedidos (tanques + abastecimentos)
    8. Auditoria de Fechamento de Turno & Conciliação de Pista (fechabomba + fechacaixa + CBC04)
    9. Auditoria de Desempenho de Frentistas & Pista (vazão de bicos, conversão de aditivada, anomalias)
"""

import os
import sys
import time
import json
import re
from typing import Tuple, Optional
import psycopg2
import google.generativeai as genai

# Garante saída em UTF-8 no terminal Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Adiciona o diretório raiz ao path para importações absolutas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    GEMINI_API_KEY,
    DB_ERP_CONFIG,
    FALLBACK_MODELS,
    BASE_DIR,
)
from core.rag_engine import HybridRAGEngine
from core.tools import PostoTools, get_erp_connection
from core.sanitizer import central_log_sanitizer
from core.semantic_router import SemanticRouter, classificar_intencao_heuristica


def classificar_intencao(pergunta: str, router: Optional[SemanticRouter] = None) -> str:
    """
    Classifica a intenção da pergunta do usuário.
    Se o SemanticRouter for fornecido, executa roteamento semântico vetorial com pgvector.
    Caso contrário, executa as heurísticas determinísticas com latência ultrarrápida.
    """
    if router is not None:
        intencao, _, _ = router.route(pergunta)
        return intencao
    return classificar_intencao_heuristica(pergunta)



def extrair_grupo(pergunta: str) -> str:
    """Extrai intenção de grupo (Metadata Filter) via palavras-chave."""
    p = pergunta.lower()
    if "cerveja" in p or "bebida" in p: return "BEBIDAS"
    if "óleo" in p or "oleo" in p or "lubrificante" in p: return "LUBRIFICANTES"
    if "cigarro" in p or "tabaco" in p: return "TABACO"
    if "conveniência" in p or "salgadinho" in p or "doce" in p: return "CONVENIENCIA"
    return None


def extrair_combustivel(pergunta: str) -> Optional[str]:
    """Extrai combustível ou código de tanque da pergunta do usuário."""
    p = pergunta.lower()

    # 1. Menção a tanque específico prioritária (evita falso positivo quando menciona tanque e combustível)
    m_tanque = re.search(r"\b(?:tanque|tq)\s*[-_]?\s*0*([0-9]{1,3})\b", p)
    if m_tanque:
        num = int(m_tanque.group(1))
        return f"{num:03d}"

    # 2. Combustíveis específicos
    if "gasolina aditivada" in p or "aditivada" in p or "grid" in p or "v-power" in p or "octapro" in p or "podium" in p or "premium" in p:
        return "GASOLINA ADITIVADA"
    if "gasolina comum" in p:
        return "GASOLINA COMUM"
    if "gasolinas" in p:
        return "GASOLINA"
    if "diesel s10" in p or "diesel s-10" in p or "s10" in p or "s-10" in p:
        return "DIESEL S10"
    if "diesel s500" in p or "diesel s-500" in p or "s500" in p or "s-500" in p or "diesel comum" in p:
        return "DIESEL S500"
    if "diesel" in p:
        return "DIESEL"
    if "etanol" in p or "álcool" in p or "alcool" in p:
        return "ETANOL"
    if "arla" in p:
        return "ARLA"
    if "gasolina" in p:
        return "GASOLINA COMUM"

    return None


def extrair_data_turno(pergunta: str) -> Tuple[Optional[str], Optional[str]]:
    """Extrai parâmetros de data e turno a partir da pergunta em linguagem natural."""
    p = pergunta.lower()
    
    # Identificação do Turno
    turno = None
    if re.search(r"\b(1[º°ªo]|primeir[oa]|manh[aã]|turno\s*1|1\s*turno)\b", p):
        turno = "1º TURNO"
    elif re.search(r"\b(2[º°ªo]|segund[oa]|tarde|turno\s*2|2\s*turno)\b", p):
        turno = "2º TURNO"
    elif re.search(r"\b(3[º°ªo]|terceir[oa]|noite|madrugada|turno\s*3|3\s*turno)\b", p):
        turno = "3º TURNO"

    # Identificação da Data
    data = None
    if "hoje" in p:
        data = "hoje"
    elif "anteontem" in p:
        data = "anteontem"
    elif "ontem" in p:
        data = "ontem"
    else:
        m_iso = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", p)
        if m_iso:
            y, m, d = m_iso.groups()
            data = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        else:
            m_br = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", p)
            if m_br:
                d, m, y = m_br.groups()
                data = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            else:
                m_dia_mes = re.search(r"\b(\d{1,2})[-/](\d{1,2})\b", p)
                if m_dia_mes:
                    d, m = m_dia_mes.groups()
                    data = f"2026-{int(m):02d}-{int(d):02d}"
                else:
                    meses = {
                        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
                        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
                    }
                    m_ext = re.search(r"\b(\d{1,2})\s+de\s+([a-zçãõ]+)(?:\s+de\s+(\d{4}))?", p)
                    if m_ext:
                        d, mes_str, ano_str = m_ext.groups()
                        mes_prefix = mes_str[:3]
                        if mes_prefix in meses:
                            ano = int(ano_str) if ano_str else 2026
                            data = f"{ano:04d}-{meses[mes_prefix]:02d}-{int(d):02d}"

    return data, turno


def extrair_bico(pergunta: str) -> Optional[str]:
    """Extrai número de bico ou bomba a partir da pergunta."""
    p = pergunta.lower()
    m_b = re.search(r"\b(?:bico|bomba)\s*0*([0-9]{1,3})\b", p)
    if m_b:
        num = int(m_b.group(1))
        return f"{num:03d}"
    return None


def extrair_frentista(pergunta: str) -> Optional[str]:
    """Extrai identificação ou nome de frentista a partir da pergunta."""
    p = pergunta.lower()

    # 1. Padrão numérico (matrícula / frentista / operador / colaborador)
    m_mat = re.search(r"\b(?:matr[ií]cula|frentista|operador|colaborador)\s*0*([0-9]{1,5})\b", p)
    if m_mat:
        num = int(m_mat.group(1))
        return f"{num:05d}"

    # 2. Padrão nominal precedido por 'frentista', 'operador' ou 'colaborador'
    m_nome = re.search(r"\b(?:frentista|operador|colaborador)\s+([a-zA-ZÀ-ÿ]{3,})\b", p)
    stop_words = {
        "hoje", "ontem", "anteontem", "com", "sem", "que", "mais", "menos", "qual", "quem",
        "tem", "teve", "houve", "de", "do", "da", "no", "na", "em", "um", "uma", "para", "por",
        "geral", "ranking", "pista", "equipe", "time", "vendeu", "faturou", "melhor", "maior",
        "pior", "menor", "bico", "bomba", "turno"
    }
    if m_nome:
        candidato = m_nome.group(1).lower()
        if candidato not in stop_words:
            return candidato.upper()

    # 3. Nomes conhecidos da equipe cadastrada no ERP
    nomes = [
        "italo", "botan", "marcio", "sergio", "erivas", "cristian", "marlon",
        "davi", "ruan", "vinicius", "robson", "gabriel", "ludmila", "samarina"
    ]
    for n in nomes:
        if re.search(rf"\b{n}\b", p):
            return n.upper()

    return None


def responder_com_streaming(prompt_sistema: str):
    """Gera resposta do Gemini com Streaming de tokens em tempo real."""
    t0 = time.perf_counter()
    ttft_ms = None
    primeiro_chunk = True
    texto_completo = []

    for m_name in FALLBACK_MODELS:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(
                prompt_sistema,
                stream=True,
                request_options={"timeout": 8}
            )

            for chunk in response:
                try:
                    texto = chunk.text
                except Exception:
                    continue

                if not texto:
                    continue

                if primeiro_chunk:
                    ttft_ms = (time.perf_counter() - t0) * 1000
                    primeiro_chunk = False

                sys.stdout.write(texto)
                sys.stdout.flush()
                texto_completo.append(texto)

            if texto_completo:
                total_llm_ms = (time.perf_counter() - t0) * 1000
                if ttft_ms is None:
                    ttft_ms = total_llm_ms
                return "".join(texto_completo), ttft_ms, total_llm_ms
        except Exception:
            continue

    msg_erro = "Não foi possível obter resposta dos modelos do Gemini no momento."
    print(msg_erro)
    return msg_erro, 0.0, (time.perf_counter() - t0) * 1000


def main():
    print("=" * 75)
    print("  AGENTE INTELIGENTE DO POSTO & PDV (Híbrido HNSW + Gemini Streaming)")
    print("  (PostgreSQL 16 pgvector + GIN FTS + Integração ERP)")
    print("=" * 75)

    if not GEMINI_API_KEY:
        print("\n[ERRO] Chave GEMINI_API_KEY não configurada no arquivo .env!")
        return

    # Inicializa motor, ferramentas e roteador semântico vetorial
    rag_engine = HybridRAGEngine()
    tools = PostoTools(rag_engine)
    router = SemanticRouter(rag_engine=rag_engine)

    print("\n0. Autenticando no Banco ERP (5433)...")
    senha_arquivo = BASE_DIR / "backups" / "erp_password.txt"
    if senha_arquivo.exists():
        try:
            with open(senha_arquivo, "r", encoding="utf-8-sig") as f:
                DB_ERP_CONFIG["password"] = f.read().strip("\ufeff \r\n\t")
        except Exception:
            pass

    while True:
        try:
            conn = get_erp_connection()
            conn.close()
            print("   [OK] Conectado ao ERP com sucesso.")
            # Salva a senha validada
            senha_arquivo.parent.mkdir(parents=True, exist_ok=True)
            with open(senha_arquivo, "w", encoding="utf-8") as f:
                f.write(DB_ERP_CONFIG["password"])
            break
        except Exception as e:
            if "utf-8" in str(e).lower() or "password" in str(e).lower() or "autenticação" in str(e).lower():
                print("\n   [AVISO] Senha do ERP inválida (ou expirada).")
                nova_senha = input("   Digite a senha do ERP de hoje: ").strip()
                DB_ERP_CONFIG["password"] = nova_senha
            else:
                print(f"   [ERRO] Falha ao conectar no ERP: {e}")
                break

    print("\n1. Verificando métricas de saúde do banco de dados (SRE)...")
    try:
        sre_data = tools.obter_telemetria_sre()
        t_stats = sre_data.get("table_stats", {})
        db_stats = sre_data.get("database_health", {})
        print(f"   [OK] Base Vetorial: {t_stats.get('total_rows')} produtos indexados")
        print(f"   [OK] Cache Hit Ratio: {db_stats.get('cache_hit_ratio_percent')}% | Conexões: {db_stats.get('active_connections')}")
    except Exception as e:
        print(f"   [AVISO] Telemetria inicial: {e}")

    print("\n2. Carregando dados cadastrais da filial...")
    dados_filial = tools.dados_cadastrais_filial()
    print(f"   [OK] Filial Conectada: {dados_filial.get('idempresa')} - {dados_filial.get('nome')} (PDV {dados_filial.get('pdv')})")

    print("\n" + "-" * 75)
    print("Agente pronto! Digite sua pergunta (ex: vendas, estoque, catálogo) ou 'sair':")
    print("-" * 75)

    while True:
        try:
            pergunta = input("\nVocê > ").strip()
            if not pergunta:
                continue
            if pergunta.lower() in ["sair", "exit", "quit"]:
                print("Encerrando sessão. Até logo!")
                break

            t_tool_start = time.perf_counter()
            intencao, confianca, telemetria_rota = router.route(pergunta)
            query_vector = telemetria_rota.get("query_vector")
            contexto_extra = ""
            telemetria_retrieval = None
            cache_hit = False

            metodo_label = "pgvector (halfvec 768d)" if telemetria_rota.get("method") == "vector_pgvector" else telemetria_rota.get("method")
            pg_lat = telemetria_rota.get("pgvector_latency_ms", 0.0)
            print(f"\n🔀 [ROTEADOR SEMÂNTICO] Intenção: {intencao.upper()} (Confiança: {confianca*100:.1f}% | Rota: {metodo_label} | Latência pgvector: {pg_lat:.2f}ms)")

            if intencao == "auditoria_turno":
                data_p, turno_p = extrair_data_turno(pergunta)
                print(f"\n🔀 [ROTEADOR] Intenção detectada: Auditoria de Pista & Conciliação de Turnos (ERP Tool)...")
                resultado_auditoria = tools.auditar_fechamento_turno(data=data_p, turno=turno_p)
                contexto_extra = f"Auditoria de Fechamento de Turno e Conciliação de Pista no ERP:\n{json.dumps(resultado_auditoria, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            elif intencao == "previsao_tanques":
                comb_filtro = extrair_combustivel(pergunta)
                print(f"\n🔮 [ROTEADOR] Intenção detectada: Previsão de Esgotamento & Sugestão de Pedidos (Run-Out Forecast)...")
                if comb_filtro:
                    print(f"⛽ [FILTRO ATIVO] Analisando combustível/tanque: {comb_filtro}")
                resultado_previsao = tools.prever_esgotamento_tanques(filtro_combustivel=comb_filtro)
                contexto_extra = f"Previsão de Esgotamento de Combustível (Run-Out Forecast) e Sugestão de Pedidos no ERP:\n{json.dumps(resultado_previsao, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            elif intencao == "desempenho_pista_frentistas":
                data_p, turno_p = extrair_data_turno(pergunta)
                frent_p = extrair_frentista(pergunta)
                bico_p = extrair_bico(pergunta)
                print(f"\n⛽ [ROTEADOR] Intenção detectada: Auditoria Operacional de Pista & Desempenho de Frentistas (ERP Tool)...")
                if frent_p:
                    print(f"👤 [FILTRO ATIVO] Analisando frentista: {frent_p}")
                if bico_p:
                    print(f"⛽ [FILTRO ATIVO] Analisando bico: {bico_p}")
                if data_p:
                    print(f"📅 [FILTRO ATIVO] Data alvo: {data_p}")
                resultado_pista = tools.auditar_desempenho_pista_frentistas(data=data_p, turno=turno_p, frentista=frent_p, bico=bico_p)
                contexto_extra = f"Auditoria Operacional de Pista, Vazão de Bicos e Desempenho de Frentistas no ERP:\n{json.dumps(resultado_pista, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            elif intencao == "lmc_anp":
                data_p, _ = extrair_data_turno(pergunta)
                comb_ou_tanque = extrair_combustivel(pergunta)
                tanque_filtro = None
                comb_filtro = None
                if comb_ou_tanque:
                    if comb_ou_tanque.isdigit() or (len(comb_ou_tanque) == 3 and comb_ou_tanque.isnumeric()):
                        tanque_filtro = comb_ou_tanque
                    else:
                        comb_filtro = comb_ou_tanque
                if not tanque_filtro:
                    m_tanque = re.search(r"\b(?:tanque|tq)\s*[-_]?\s*0*([0-9]{1,3})\b", pergunta.lower())
                    if m_tanque:
                        tanque_filtro = f"{int(m_tanque.group(1)):03d}"

                print(f"\n📋 [ROTEADOR] Intenção detectada: Livro de Movimentação de Combustíveis (LMC Oficial ANP)...")
                if data_p:
                    print(f"📅 [FILTRO ATIVO] Data LMC: {data_p}")
                if tanque_filtro:
                    print(f"⛽ [FILTRO ATIVO] Tanque LMC: {tanque_filtro}")
                elif comb_filtro:
                    print(f"⛽ [FILTRO ATIVO] Combustível LMC: {comb_filtro}")

                resultado_lmc = tools.gerar_relatorio_lmc_anp(
                    data=data_p,
                    combustivel=comb_filtro,
                    tanque=tanque_filtro
                )
                contexto_extra = f"Livro de Movimentação de Combustíveis (LMC ANP Portaria 26/1992):\n{json.dumps(resultado_lmc, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            elif intencao == "vendas_analitico":
                print("\n🔀 [ROTEADOR] Intenção detectada: Análise de Vendas (ERP Tool)...")
                resultado_vendas = tools.consultar_analise_vendas_erp(tipo="mais_vendidos")
                contexto_extra = f"Consulta de Histórico de Vendas no ERP:\n{json.dumps(resultado_vendas, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            elif intencao == "sre_metricas":
                print("\n🔀 [ROTEADOR] Intenção detectada: Telemetria SRE (PostgreSQL & Semantic Router Tool)...")
                sre_metricas = tools.obter_telemetria_sre()
                sre_metricas["semantic_router_metrics"] = router.get_sre_telemetry()
                contexto_extra = f"Métricas de Observabilidade SRE do Banco PostgreSQL 16 e Roteador Semântico:\n{json.dumps(sre_metricas, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            elif intencao == "dados_filial":
                print("\n🔀 [ROTEADOR] Intenção detectada: Cadastro da Filial...")
                contexto_extra = f"Dados da Filial:\n{json.dumps(dados_filial, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            elif intencao == "estoque_posicao":
                print("\n🔀 [ROTEADOR] Intenção detectada: Consulta de Estoque e Tanques (ERP Tool)...")
                resultado_estoque = tools.consultar_estoque_erp(termo=pergunta)
                contexto_extra = f"Posição Real de Estoque e Tanques no ERP (porta 5433):\n{json.dumps(resultado_estoque, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            elif intencao == "clientes_ranking":
                print("\n🔀 [ROTEADOR] Intenção detectada: Análise de Clientes e Faturamento (ERP Tool)...")
                resultado_clientes = tools.consultar_clientes_erp(termo=pergunta)
                contexto_extra = f"Dados de Clientes e Histórico de Compras no ERP (porta 5433):\n{json.dumps(resultado_clientes, ensure_ascii=False, indent=2, default=str)}\n"
                tool_latency_ms = (time.perf_counter() - t_tool_start) * 1000

            else:
                # Catálogo de produtos (RAG Híbrido HNSW + GIN) com Cache Semântico
                print("\n⚙️  [ROTEADOR] Intenção detectada: Catálogo (Busca Híbrida RRF)...")
                cache_data = tools.rag.check_semantic_cache(pergunta, query_vector=query_vector)
                query_vector = cache_data.get("query_vector") or query_vector
                
                if cache_data.get("resposta_llm"):
                    cache_hit = True
                    print(f"⚡ [CACHE SEMÂNTICO] Hit de cache semântico (Similaridade: {cache_data['cosine_similarity']:.4f})")
                    print("\n🤖 AGENTE (Cache):\n")
                    print(cache_data["resposta_llm"])
                    print("\n")
                    total_e2e_ms = (time.perf_counter() - t_tool_start) * 1000
                    print("-" * 75)
                    print("📊 [TELEMETRIA SRE DA REQUISIÇÃO]")
                    print(f"  • Rota: CATÁLOGO_PRODUTOS (CACHE HIT)")
                    print(f"  • 🏁 Latência Total E2E:  {round(total_e2e_ms, 2)} ms (Custo Zero)")
                    print("-" * 75)
                    continue
                
                grupo_filtro = extrair_grupo(pergunta)
                if grupo_filtro:
                    print(f"🔍 [FILTRO ATIVO] Limitando busca apenas à categoria: {grupo_filtro}")

                busca = tools.buscar_produtos_catalogo(pergunta, top_k=5, query_vector=query_vector, grupo_filter=grupo_filtro)
                produtos = busca["results"]
                telemetria_retrieval = busca["telemetry"]
                tool_latency_ms = telemetria_retrieval["total_retrieval_latency_ms"]

                contexto_extra = "Produtos recuperados do catálogo por RAG Híbrido (HNSW + Full-Text Search + RRF):\n"
                for p in produtos:
                    contexto_extra += (
                        f"- [{p.get('codpro')}] {p.get('nompro')} | Grupo: {p.get('grupo')} | "
                        f"Preço: R$ {p.get('preco', 0.0):.2f} (RRF: {p.get('rrf_score', 0.0):.4f} | "
                        f"Cosine: {p.get('cosine_similarity', 0.0):.2f} | FTS: {p.get('fts_score', 0.0):.2f})\n"
                    )

            # Blindagem de Privacidade e LGPD (Fase 1)
            contexto_sanitizado, counts_ctx = central_log_sanitizer.sanitize_text(contexto_extra)
            pergunta_sanitizada, counts_perg = central_log_sanitizer.sanitize_text(pergunta)
            total_redacted = sum(counts_ctx.values()) + sum(counts_perg.values())
            if total_redacted > 0:
                detalhes_redacted = ", ".join(f"{k}: {v}" for k, v in {**counts_ctx, **counts_perg}.items() if v > 0)
                print(f"🛡️  [LGPD SANITIZER] {total_redacted} dado(s) sensível(is) ofuscado(s) pré-prompt ({detalhes_redacted})")

            prompt_sistema = f"""
Você é o Agente Inteligente do Posto de Combustíveis e Loja de Conveniência.
Seu objetivo é orientar o atendente, operador do caixa ou cliente com clareza, rapidez e precisão.

Dados Cadastrais da Unidade:
- Filial: {dados_filial.get('idempresa')} - {dados_filial.get('nome')}
- Razão Social: {dados_filial.get('razao_social')}
- CNPJ: {dados_filial.get('cnpj')}
- Endereço: {dados_filial.get('endereco')}
- PDV: {dados_filial.get('pdv')}

Informações Recuperadas pelas Ferramentas do Sistema:
{contexto_sanitizado}

Pergunta do Usuário:
"{pergunta_sanitizada}"

Diretrizes:
1. Responda de forma direta, prestativa e profissional.
2. Se a pergunta for sobre produtos, indique claramente o nome, código (SKU) e preço.
3. Se a pergunta for sobre vendas, faturamento ou abastecimentos, utilize os dados fornecidos pelo ERP. Se o usuário perguntar sobre o último produto vendido ou últimas vendas, cite diretamente os dados da seção 'ultimo_produto_vendido_destaque' e 'ultimos_produtos_conveniencia' / 'ultimos_abastecimentos_pista', informando o nome do produto, código SKU, data e hora exata da venda, quantidade e valor total. Só mencione erro de credenciais se a ferramenta retornar status 'indisponivel'.
4. Se for sobre métricas ou SRE, explique a saúde do banco (cache hit ratio, status dos índices) de maneira técnica e clara.
5. Se a pergunta for sobre estoque, saldo disponível ou tanques de combustível, utilize os dados reais fornecidos pelo ERP. Apresente os saldos físicos (unidades ou litros), códigos (SKU) e percentuais de ocupação dos tanques de forma organizada e limpa.
6. Se a pergunta for sobre clientes, ranking de compradores ou dados cadastrais, utilize os dados da ferramenta de clientes do ERP. Respeite as boas práticas de LGPD mantendo CPF/CNPJ mascarados e explique com clareza a realidade operacional do PDV (onde o maior volume em postos é emitido sob 'CONSUMIDOR FINAL', a menos que cadastrado nominalmente).
7. Se a pergunta for sobre conciliação de turnos, fechamento de turno, furo de caixa ou auditoria de pista, utilize os dados da ferramenta de auditoria de turnos do ERP:
   - Apresente um parecer executivo claro e objetivo contendo:
     a) Status Geral da Conciliação (CONCILIADO, DIVERGÊNCIA DE PISTA, FURO DE CAIXA, SOBRA ou TURNO EM ANDAMENTO) e Score de Conformidade (%).
     b) Triangulação de Pista: compare o volume e faturamento teórico dos encerrantes físicos (fechabomba) com a telemetria em tempo real da automação Companytec CBC04 (abastecimentos), detalhando eventuais bicos divergentes ou pendências de digitação de encerrantes.
     c) Fechamento de Caixa: apresente os valores declarados pelos operadores (dinheiro, cartão, a prazo, convênio), status dos caixas (abertos ou fechados) e aponte eventuais furos (falta) ou sobras financeiras frente ao faturamento de combustível.
     d) Balanço dos Tanques: informe se a variação volumétrica apurada nos tanques está dentro da tolerância oficial da ANP (±0.6%).
     e) Recomendações: liste as ações práticas sugeridas para o gestor e equipe de pista.
8. Se a pergunta for sobre previsão de esgotamento de tanques (Run-Out Forecast), autonomia de combustível, espaço livre para descarga (ullage) ou sugestão de compra de carreta:
   - Apresente um parecer preditivo claro, técnico e executivo contendo:
     a) Tanque e Combustível Mais Crítico: identifique com destaque o tanque com menor autonomia em horas/dias e menor percentual de ocupação, informando se já está abaixo da margem de segurança de 15%.
     b) Autonomia e Projeção de Run-Out: informe em quantos dias/horas o produto atingirá o nível crítico (15%) e quando secará completamente (0L), projetando a data e hora estimadas de esgotamento.
     c) Espaço Livre para Descarga (Ullage): informe o volume livre disponível em cada tanque para recebimento de produto.
     d) Sugestão Inteligente de Pedidos: apresente os volumes sugeridos de compra em múltiplos padrão de compartimento de carreta (5.000 L, 10.000 L, 15.000 L...), indicando a urgência e prazo ideal de compra (com atenção especial para abastecer preventivamente antes do fim de semana).
9. Se a pergunta for sobre desempenho da equipe de pista, ranking de frentistas, conversão de aditivada, vazão de bicos (alerta preventivo de filtro lento/sujo) ou anomalias operacionais de pista, utilize os dados da ferramenta de auditoria de pista e frentistas do ERP:
   - Responda primeiro de forma direta, clara e objetiva à pergunta específica feita pelo usuário (ex: declare imediatamente o campeão de aditivada, o frentista com maior ticket médio, ou a vazão/alerta do bico consultado). Em seguida, apresente os pontos operacionais complementares:
     a) Desempenho dos Frentistas & Ranking: destaque os colaboradores líderes em volume (L) e faturamento (R$), ticket médio por atendimento e o índice de conversão de Gasolina Aditivada (meta recomendada: 25-30% para maximização de margem líquida). Caso a pesquisa seja de uma data específica sem vendas de aditivada pelos frentistas, informe com fidelidade aos dados.
     b) Vazão dos Bicos & Alerta Preventivo de Filtro Lento: informe o status de vazão dos bicos. Em bombas comerciais, a vazão normal é de 35 a 45 L/min. Se algum bico estiver com vazão lenta ou crítica (< 25-30 L/min), emita alerta imediato de manutenção preventiva para troca do elemento filtrante da bomba. Caso o bico não tenha tido movimentação no período ou tenha operado em estimativa nominal, esclareça com transparência.
     c) Detecção de Anomalias de Pista: reporte micro-abastecimentos suspeitos (< 1.0 L / < R$ 5), abastecimentos manuais sem automação CBC04, cancelamentos de venda, horários atípicos ou valores repetidos consecutivos.
     d) Recomendações Práticas: liste ações imediatas sugeridas para a gerência do posto.
10. Se a pergunta for sobre Livro de Movimentação de Combustíveis (LMC Oficial ANP Portaria 26/1992), balanço escriturado vs físico ou conformidade de tolerância regulamentar (±0.6%):
    - Apresente um parecer regulamentar e executivo claro contendo:
      a) Status Geral ANP (CONFORME_ANP ou ALERTA_FORA_TOLERANCIA_ANP) e período analisado.
      b) Balanço Volumétrico dos Tanques: detalhe para cada tanque o estoque de abertura (E_a), recebimentos/descargas (R), vendas faturadas nos bicos (V), estoque escriturado contábil (E_e = E_a + R - V) e estoque físico medido (E_f apurado por régua ou telemetria).
      c) Auditoria de Variação (Δ): informe a quebra ou sobra em litros (Δ_litros = E_f - E_e) e o percentual sobre as vendas (Δ% = (Δ_litros / V) * 100), comparando rigorosamente com a margem legal de ±0.6%.
      d) Diagnóstico Operacional: esclareça se a variação decorre de contração/expansão térmica natural dentro da tolerância ou se exige abertura imediata de sindicância para apurar vazamento em tubulações ou descalibração de bicos.
      e) Ações Obrigatórias: instrua sobre registros diários no livro e retenção fiscal por 5 anos para fiscalização da ANP/SEFAZ.
"""

            print("\n🤖 AGENTE (Streaming):\n")
            resposta_texto, ttft_ms, total_llm_ms = responder_com_streaming(prompt_sistema)
            print("\n")

            if intencao == "catalogo_produtos" and not cache_hit and query_vector:
                frases_bloqueio = ["não há registros", "erro", "indisponível", "não foi possível", "não encontrei", "no momento"]
                if not any(fb in resposta_texto.lower() for fb in frases_bloqueio):
                    tools.rag.save_semantic_cache(pergunta, query_vector, resposta_texto, produtos)

            total_e2e_ms = tool_latency_ms + total_llm_ms
            print("-" * 75)
            print("📊 [TELEMETRIA SRE DA REQUISIÇÃO]")
            print(f"  • Rota / Ferramenta:   {intencao.upper()}")
            print(f"  • Latência Ferramenta: {round(tool_latency_ms, 2)} ms")
            if total_redacted > 0:
                print(f"  • 🛡️ LGPD Protegido:    {total_redacted} dado(s) sensível(is) mascarado(s)")
            if telemetria_retrieval:
                print(f"    - Embedding Gemini:  {telemetria_retrieval.get('embedding_latency_ms', 0)} ms")
                print(f"    - PostgreSQL RRF:    {telemetria_retrieval.get('db_rrf_latency_ms', 0)} ms (HNSW ef={telemetria_retrieval.get('hnsw_ef_search', 100)})")
            print(f"  • ⚡ Time-To-First-Token: {round(ttft_ms, 2)} ms (Início da Resposta)")
            print(f"  • ⏳ Duração Total LLM:   {round(total_llm_ms, 2)} ms")
            print(f"  • 🏁 Latência Total E2E:  {round(total_e2e_ms, 2)} ms")
            print("-" * 75)

        except KeyboardInterrupt:
            print("\nEncerrado.")
            break
        except Exception as e:
            print(f"\n[Erro na consulta]: {e}")


if __name__ == "__main__":
    main()
