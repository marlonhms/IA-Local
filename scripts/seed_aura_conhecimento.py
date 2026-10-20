"""
Script de Indexacao & Seeding da Base de Auto-Conhecimento e Meta-RAG da AURA
(PostgreSQL 16 + pgvector nativo Windows na porta 5433).

Funcionalidades:
- Criacao e manutencao idempotente da tabela `aura_core.aura_conhecimento_vetores` (e public).
- Geracao de vetores halfvec(768) via Google Gemini API (gemini-embedding-001)
  com fallback deterministico offline para ambientes isolados.
- Delta Hashing deterministico (hash_md5) para evitar chamadas redundantes de API (>95% de economia).
- Indices HNSW (ef_construction=128), GIN Full-Text Search (tsvector STORED em portugues),
  indices b-tree de modulo/topico e hash_md5.
- Populacao dos 26 chunks oficiais da AURA (15 operacionais do sistema + 11 normativos tecnicos de combustiveis).
"""

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

# Garante saida UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

# Adiciona o diretorio raiz ao path para importacoes absolutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    AURA_CORE_SCHEMA,
    DB_VECTOR_CONFIG,
    DEFAULT_EMBEDDING_MODEL,
    GEMINI_API_KEY,
)


def gerar_embedding_deterministico(texto: str, dim: int = 768) -> list[float]:
    """
    Gera vetor deterministico pseudo-aleatorio unitario baseado no hash SHA-256 do texto.
    Suporta dimensoes customizadas (ex: 768 para pgvector halfvec nativo da AURA, ou 1536 para compatibilidade).
    Utilizado para testes hermeticos, modo offline ou contingencia de cota da API.
    """
    seed_val = int(hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed_val)
    vec = [rng.gauss(0.0, 1.0) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


# Catalogo canonico dos 26 chunks oficiais da AURA (Operacionais + Normativos Tecnicos)
CONHECIMENTO_SEEDS: list[dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. Panorama Operacional e Cockpit Executivo
    # -------------------------------------------------------------------------
    {
        "modulo": "cockpit",
        "topico": "panorama_operacional",
        "titulo": "Panorama Operacional do Posto",
        "subtitulo": "Cockpit executivo em tempo real com metricas vitais de pista, tanques e faturamento",
        "conteudo": (
            "O Panorama Operacional e o painel central (Cockpit) da AURA e o guia principal de ajuda executiva do posto. "
            "Ele consolida os KPIs mais criticos em cards de alta densidade visual: faturamento total do dia em tempo real, "
            "volume consolidado vendido em litros, margem media bruta, status consolidado dos tanques de combustiveis, resumo "
            "de pendencias de turno e alertas de pista. Foi projetado para dar ao proprietario ou gerente uma visao holistica instantanea "
            "de 360 graus da revenda logo ao abrir o sistema."
        ),
        "metadados": {
            "categoria": "operacional",
            "modulo_sistema": "cockpit",
            "prioridade": "alta",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "cards": ["kpi_faturamento", "kpi_volume", "kpi_tanques", "kpi_alertas"],
            "tipo": "dashboard",
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "cockpit",
            "label": "Abrir Panorama Operacional",
        },
        "tags": ["cockpit", "panorama", "visao geral", "dashboard", "kpis", "faturamento", "tempo real", "inicio", "ajuda", "ajuda do sistema", "guia", "manual", "telas", "modulos", "sistema", "suporte", "como usar"],
    },
    {
        "modulo": "cockpit",
        "topico": "tanques_ullage",
        "titulo": "Monitoramento de Tanques e Espaco Livre de Descarga (Ullage)",
        "subtitulo": "Medicao volumetrica, autonomia em horas e calculo de descarga em multiplos de 5.000 L",
        "conteudo": (
            "O modulo de Tanques exibe o volume atual de cada combustivel (Gasolina Comum, Gasolina Aditivada, "
            "Etanol, Diesel S10, Diesel S500), capacidade total e percentual de ocupacao com mini-graficos termicos. "
            "O grande diferencial analitico e o calculo de Ullage (espaco livre para descarga em multiplos exatos de "
            "compartimento de caminhao de 5.000 L) e a projecao matematica de run-out (tempo ate esgotamento com base no "
            "consumo horario medio L/h), sinalizando com cores verde, amarelo ou vermelho quando um tanque atinge nivel critico "
            "e sugerindo a compra de carretas antecipadamente."
        ),
        "metadados": {
            "categoria": "operacional",
            "modulo_sistema": "tanques",
            "capacidade_padrao_compartimento": 5000,
        },
        "elementos_ui": {
            "tab": "cockpit",
            "componente": "tanques_grid",
            "cards_tanque": ["tq1_gc", "tq2_ga", "tq3_et", "tq4_s10"],
            "metricas": ["volume_litros", "capacidade_litros", "ocupacao_pct", "autonomia_horas", "ullage_5k"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "cockpit",
            "label": "Ver Tanques no Cockpit",
        },
        "tags": ["tanques", "ullage", "combustivel", "gasolina", "diesel", "etanol", "autonomia", "runout", "descarga", "caminhao", "compartimento", "5000l"],
    },
    {
        "modulo": "cockpit",
        "topico": "vazao_bicos_filtro",
        "titulo": "Auditoria de Vazao de Bicos e Alerta de Filtro Obstruido",
        "subtitulo": "Monitoramento de vazao em L/min com deteccao automatica de bicos lerdos (<30 L/min)",
        "conteudo": (
            "A auditoria de bicos da AURA analisa a vazao instantanea e media de cada bico de abastecimento (em litros por minuto: L/min) "
            "aferida pela automacao de pista. Quando a vazao de um bico cai abaixo de 30 L/min (ou discrepante da media da bomba), a AURA emite "
            "imediatamente um alerta preventivo de filtro sujo ou bomba estrangulada. Isso evita filas na pista, reclamacoes de clientes de bico lerdo "
            "e desgaste prematuro dos blocos medidores."
        ),
        "metadados": {
            "categoria": "manutencao_pista",
            "threshold_vazao_alerta_l_min": 30.0,
        },
        "elementos_ui": {
            "tab": "cockpit",
            "secao": "pista_bicos",
            "metricas": ["bico_id", "combustivel", "vazao_l_min", "status_filtro"],
            "threshold_alerta": 30.0,
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "cockpit",
            "label": "Inspecionar Bicos de Abastecimento",
        },
        "tags": ["bicos", "vazao", "litros por minuto", "l min", "filtro", "filtro sujo", "filtro obstruido", "bico lento", "bico lerdo", "bomba", "pista"],
    },
    {
        "modulo": "cockpit",
        "topico": "desempenho_frentistas",
        "titulo": "Desempenho da Equipe de Pista e Conversao de Aditivada",
        "subtitulo": "Ranking de frentistas, ticket medio, volume faturado e percentual de conversao de gasolina aditivada",
        "conteudo": (
            "Exibe o ranking de produtividade da equipe de pista em tempo real. Avalia faturamento total por operador, volume fisico abastecido, "
            "ticket medio e a taxa de conversao de Gasolina Aditivada (meta recomendada: 25% a 30% sobre o total de gasolina). Permite ao gestor "
            "identificar frentistas de alto rendimento, premiar a equipe, calibrar comissoes e identificar operadores que necessitam de treinamento "
            "em abordagem e vendas adicionais de aditivos e lubrificantes."
        ),
        "metadados": {
            "categoria": "gestao_equipe",
            "meta_conversao_aditivada_pct": 25.0,
        },
        "elementos_ui": {
            "tab": "cockpit",
            "secao": "ranking_frentistas",
            "colunas": ["matricula", "nome", "faturamento", "volume_l", "conversao_aditivada_pct", "ticket_medio"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "cockpit",
            "label": "Ver Ranking de Frentistas",
        },
        "tags": ["frentistas", "ranking", "aditivada", "conversao", "ticket medio", "equipe", "produtividade", "operadores", "comissao"],
    },

    # -------------------------------------------------------------------------
    # 2. Conciliacao Operacional, Turnos e Triangulacao Fiscal
    # -------------------------------------------------------------------------
    {
        "modulo": "conciliacao",
        "topico": "cbc04_vs_pdv",
        "titulo": "Triangulacao Automacao CBC04 vs Vendas Fiscais PDV",
        "subtitulo": "Confronto milimetrico entre pulsos de encerrantes da automacao Companytec e cupons NFC-e/SAT",
        "conteudo": (
            "A AURA cruza diretamente os dados de abastecimentos registrados pelo concentrador de pista Companytec CBC04 com os cupons fiscais "
            "emitidos pelo sistema de PDV no ERP. Essa triangulacao identifica imediatamente abastecimentos nao faturados na pista, frentistas "
            "que liberaram bico sem emitir cupom, abastecimentos cancelados indevidamente ou divergencias de encerrantes, prevenindo perdas financeiras "
            "e furos ocultos antes do fechamento do caixa."
        ),
        "metadados": {
            "categoria": "conciliacao_fiscal",
            "hardware_homologado": "Companytec CBC04",
        },
        "elementos_ui": {
            "tab": "triggers",
            "ferramenta": "conciliacao_turno",
            "filtros": ["data", "turno", "bico"],
            "comparativo": ["volume_cbc04", "volume_pdv", "delta_litros", "delta_reais"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Auditar Automacao CBC04 vs PDV",
        },
        "tags": ["cbc04", "companytec", "pdv", "automacao", "fiscal", "encerrante", "triangulacao", "furo", "cupom fiscal", "abastecimento pendente"],
    },
    {
        "modulo": "conciliacao",
        "topico": "auditoria_turno",
        "titulo": "Auditoria de Fechamento de Turno e Quebra de Caixa",
        "subtitulo": "Conferencia do 1º, 2º e 3º turno: batimento de dinheiro, cartao, PIX, faturado e encerrantes",
        "conteudo": (
            "Ferramenta analitica que audita os fechamentos dos turnos (1º Turno Manha, 2º Turno Tarde e 3º Turno Noite/Madrugada). Cruza o volume medido "
            "nos encerrantes das bombas com o faturamento declarado no caixa por forma de pagamento (Dinheiro, Cartao Debito/Credito, PIX, Faturado e Vale). "
            "Calcula o score de conformidade do turno, aponta sobras ou faltas de caixa (quebras) e especifica exatamente se a divergencia ocorreu na pista fisica "
            "ou no lancamento do caixa."
        ),
        "metadados": {
            "categoria": "conciliacao_caixa",
            "turnos": ["1_manha", "2_tarde", "3_noite"],
        },
        "elementos_ui": {
            "tab": "triggers",
            "ferramenta": "auditoria_turno",
            "cards": ["score_conformidade", "triangulacao_caixa", "triangulacao_pista", "quebra_caixa"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Conferir Fechamento de Turno",
        },
        "tags": ["fechamento de turno", "conciliacao", "turno", "caixa", "quebra de caixa", "furo", "sobra", "falta", "1 turno", "2 turno", "3 turno", "pix", "cartao"],
    },
    {
        "modulo": "fiscal",
        "topico": "lmc_anp",
        "titulo": "Livro de Movimentacao de Combustiveis (LMC Oficial ANP)",
        "subtitulo": "Auditoria estrita da Portaria ANP 26/1992, perdas e ganhos termicos com teto de ±0,6%",
        "conteudo": (
            "Gera e audita o Livro de Movimentacao de Combustiveis (LMC) exigido pela ANP conforme Portaria 26/1992. O motor calcula o balanco diario por tanque "
            "e combustivel: Estoque de Abertura + Recebimentos (Descargas) - Vendas Faturadas = Fechamento Escriturado. Em seguida, compara com a Medicao Fisica da regua/telemetria "
            "para apurar a Variacao Volumetrica (Delta Litros e Delta %). Se a variacao ultrapassar o limite regulamentar estrito de ±0,6%, a AURA aciona alerta vermelho fiscal de inconformidade "
            "para investigacao imediata de perda termica, calibracao ou vazamento."
        ),
        "metadados": {
            "categoria": "fiscal_regulatorio",
            "norma": "Portaria ANP nº 26/1992",
            "tolerancia_limite_pct": 0.60,
        },
        "elementos_ui": {
            "tab": "triggers",
            "ferramenta": "lmc_anp",
            "tabela": "balanco_lmc",
            "campos": ["abertura", "recebimento", "vendas", "escriturado", "fisico", "variacao_litros", "variacao_pct", "status_anp"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Abrir Relatorio LMC ANP",
        },
        "tags": ["lmc", "anp", "portaria 26", "livro de movimentacao", "tolerancia anp", "0.6%", "perda termica", "ganho termico", "estoque escriturado", "medicao fisica", "fiscal"],
    },

    # -------------------------------------------------------------------------
    # 3. Loja de Conveniencia, Gatilhos e Console
    # -------------------------------------------------------------------------
    {
        "modulo": "conveniencia",
        "topico": "market_basket_combos",
        "titulo": "Inteligencia de Vendas Cruzadas e Market Basket Analysis (Apriori)",
        "subtitulo": "Mineracao de regras de associacao na conveniencia, calculo de Lift, Suporte e combos para o PDV",
        "conteudo": (
            "Aplica algoritmos de associacao de mercado (Market Basket Analysis / Apriori) sobre o historico de cupons fiscais da loja de conveniencia. Identifica produtos frequentemente "
            "adquiridos em conjunto (ex: Cerveja + Carvao + Gelo, Cafe Expresso + Pao de Queijo, Energetico + Salgadinho). Para cada par ou trio, calcula as metricas de Suporte, Confianca e Lift (> 1.2), "
            "sugerindo scripts de vendas assertivos para operadores de caixa oferecerem no balcao e organizando o merchandising fisico das prateleiras para maximizar o ticket medio."
        ),
        "metadados": {
            "categoria": "conveniencia",
            "algoritmo": "Apriori / Market Basket Analysis",
            "lift_minimo": 1.2,
        },
        "elementos_ui": {
            "tab": "triggers",
            "ferramenta": "conveniencia_vendas_cruzadas",
            "cards_combos": ["combo_titulo", "itens", "lift", "confianca", "ticket_estimado", "script_balcao"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Ver Combos da Conveniencia",
        },
        "tags": ["conveniencia", "combos", "cross-sell", "vendas cruzadas", "market basket", "apriori", "lift", "loja", "pdv", "cerveja", "cafe", "ticket medio"],
    },
    {
        "modulo": "triggers",
        "topico": "radar_acoes_rapidas",
        "titulo": "Radar de Acoes Rapidas e Gatilhos Analiticos de 1-Clique",
        "subtitulo": "Grid tatico de botoes prontos para disparar auditorias operacionais instantaneas sem digitacao",
        "conteudo": (
            "A aba de Acoes Rapidas (Triggers) reune um grid categorizado de botoes de execucao instantanea. Com apenas um clique, o gestor dispara qualquer auditoria complexa sem precisar redigir mensagens "
            "ou lembrar comandos: 'Autonomia dos Tanques', 'Conferir Turno Hoje', 'LMC ANP Oficial', 'Combos de Conveniencia', 'Vazao dos Bicos', 'Top Clientes' e 'Saude do Banco de Dados'. Possui filtros rapidos "
            "por categoria (Todos, Combustiveis, Caixa, Pista, Loja) e sincroniza a resposta diretamente no inspetor ou chat."
        ),
        "metadados": {
            "categoria": "atalhos_operacionais",
        },
        "elementos_ui": {
            "tab": "triggers",
            "filtros": ["todos", "combustiveis", "caixa", "pista", "loja"],
            "grid_acoes": ["btn_tanques", "btn_turno", "btn_lmc", "btn_combos", "btn_bicos", "btn_clientes", "btn_sre"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Abrir Acoes Rapidas",
        },
        "tags": ["acoes rapidas", "gatilhos", "triggers", "botoes", "1 clique", "atalhos", "auditorias rapidas", "executar", "grid"],
    },
    {
        "modulo": "triggers",
        "topico": "inspetor_duplo",
        "titulo": "Inspetor Duplo: Visualizacao Formatada vs JSON Bruto",
        "subtitulo": "Detalhamento analitico em dois formatos com botao de copia de payload e envio para a AURA",
        "conteudo": (
            "O Inspetor Duplo localiza-se na aba de Gatilhos e exibe o resultado minucioso de qualquer ferramenta executada. Ele possui duas abas de inspecao: 'Visualizacao Formatada' (cards executivos com tabelas, "
            "percentuais, badges e destaques amigaveis) e 'JSON Tecnico' (o payload estruturado completo retornado pelo ERP/PostgreSQL). Inclui botoes utilitarios para 'Copiar JSON' diretamente para a area de transferencia "
            "e 'Enviar para a AURA' para tirar duvidas cognitivas sobre os dados apurados."
        ),
        "metadados": {
            "categoria": "ferramenta_tecnica",
        },
        "elementos_ui": {
            "tab": "triggers",
            "container": "inspector-dual-panel",
            "abas": ["tab-inspector-formatted", "tab-inspector-json"],
            "acoes": ["btn-copy-json", "btn-send-to-aura"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Ver Inspetor de Gatilhos",
        },
        "tags": ["inspetor", "inspetor duplo", "json", "formatado", "detalhes", "copiar json", "enviar aura", "payload", "depuracao", "conferencia"],
    },
    {
        "modulo": "console",
        "topico": "chat_assistente",
        "titulo": "Console Cognitivo da AURA: Chat Executivo e Streaming",
        "subtitulo": "Interface de dialogo executivo em linguagem natural, streaming token-a-token e sintese sob demanda",
        "conteudo": (
            "O Console Cognitivo e a interface de conversa principal da AURA. Permite ao usuario fazer perguntas livres sobre o posto ('Qual tanque acaba primeiro?', 'O turno 1 bateu?', 'Quanto custa a Heineken?'). "
            "Possui streaming de respostas token-a-token via SSE, identificacao visual de intencoes (Chips coloridos), cards interativos de ferramentas analiticas, badge de telemetria SRE com tempo de resposta em milissegundos "
            "e historico de sessao multi-turn duravel."
        ),
        "metadados": {
            "categoria": "interface_cognitiva",
        },
        "elementos_ui": {
            "tab": "console",
            "feed": "chat-feed-container",
            "input": "chat-input-text",
            "botoes": ["btn-chat-send", "btn-chat-stop", "btn-chat-clear"],
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "console",
            "label": "Abrir Console Cognitivo",
        },
        "tags": ["chat", "console", "assistente", "conversa", "streaming", "perguntas", "linguagem natural", "sessao", "comandos", "dialogo", "duvidas", "ajuda cognitiva"],
    },
    {
        "modulo": "split",
        "topico": "visao_split",
        "titulo": "Visao Integrada Split: Cockpit e Chat Bipartidos Lado a Lado",
        "subtitulo": "Layout bipartido simultaneo com painel operacional a esquerda e chat executivo a direita",
        "conteudo": (
            "A Visao Split divide a tela em duas colunas sincronizadas em tempo real. No lado esquerdo, mantem o Panorama Operacional visivel com mini-tanques, faturamento e alertas em monitoramento continuo. "
            "No lado direito, oferece uma janela dedicada do Console Cognitivo para dialogar com a AURA. Permite gerenciar a pista e fazer diagnosticos simultaneos sem perder a visibilidade dos indicadores-chave "
            "de desempenho, ideal para telas de desktop, monitores widescreen e tablets de retaguarda."
        ),
        "metadados": {
            "categoria": "layout_interface",
        },
        "elementos_ui": {
            "tab": "split",
            "layout": "grid-split-screen",
            "painel_esquerdo": "split-cockpit-sidebar",
            "painel_direito": "split-chat-container",
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "split",
            "label": "Ativar Visao Integrada Split",
        },
        "tags": ["split", "visao dividida", "lado a lado", "bipartido", "multitarefa", "cockpit e chat", "tela dupla", "monitor"],
    },
    {
        "modulo": "navegacao",
        "topico": "menu_hamburguer_liquid_glass",
        "titulo": "Menu Lateral Hamburguer em Design Acrilico Liquid Glass",
        "subtitulo": "Gaveta deslizante com blur fosco, atalhos executivos, controle de som e alternancia de modulos",
        "conteudo": (
            "O Menu Hamburguer e acessivel pelo botao de menu com tres barras no topo esquerdo do cabecalho ou deslizando a tela. Possui acabamento moderno 'Liquid Glass' em vidro fosco acrilico com desfoque de fundo (backdrop-blur). "
            "Reune atalhos rapidos para alternar entre as 4 abas (Console Cognitivo, Panorama Cockpit, Gatilhos Analiticos e Visao Split), perguntas frequentes prontas de 1-toque, acionamento da Command Palette (Ctrl+K), "
            "controle de audio sensorial e limpeza de sessao."
        ),
        "metadados": {
            "categoria": "navegacao_ui",
        },
        "elementos_ui": {
            "botao_trigger": "btn-toggle-sidebar",
            "drawer": "aura-sidebar-drawer",
            "overlay": "aura-sidebar-overlay",
            "estilo": "liquid-glass-acrylic",
        },
        "ui_action": {
            "action": "open_sidebar",
            "target": "sidebar",
            "label": "Abrir Menu Lateral Hamburguer",
        },
        "tags": ["menu", "menu lateral", "hamburguer", "liquid glass", "gaveta", "drawer", "navegacao", "atalhos", "acrilico", "design", "painel lateral"],
    },
    {
        "modulo": "navegacao",
        "topico": "command_palette_ctrl_k",
        "titulo": "Command Palette Global e Navegacao Rapida (Atalho Ctrl+K)",
        "subtitulo": "Buscador instantaneo flutuante para comandos, relatorios, telas e atalhos do posto",
        "conteudo": (
            "A Command Palette e o centro de comando rapido da AURA. Pode ser acionada a qualquer momento pressionando o atalho de teclado 'Ctrl + K' ou clicando no botao de busca rapida. "
            "Permite buscar instantaneamente comandos operacionais, trocar de aba, executar diagnosticos de tanques, abrir LMC ou acionar o chat sem tirar as maos do teclado. A pesquisa conta com "
            "filtragem em tempo real e destaque visual das opcoes disponiveis."
        ),
        "metadados": {
            "categoria": "navegacao_atalho",
            "atalho": "Ctrl+K",
        },
        "elementos_ui": {
            "atalho_teclado": "Ctrl+K",
            "botao": "btn-open-palette",
            "modal": "aura-command-palette-modal",
            "input_busca": "palette-search-input",
        },
        "ui_action": {
            "action": "open_command_palette",
            "target": "palette",
            "label": "Pressione Ctrl+K ou Abrir Paleta",
        },
        "tags": ["ctrl+k", "ctrl k", "command palette", "paleta de comandos", "busca rapida", "atalho de teclado", "navegacao rapida", "comandos", "atalho", "atalhos"],
    },
    {
        "modulo": "acessibilidade",
        "topico": "feedback_sensorial_audio",
        "titulo": "Feedback Sensorial e Sons Taticos (Web Audio API)",
        "subtitulo": "Chimes discretos em ondas senoidais sintetizadas para confirmacao de acoes sem poluicao sonora",
        "conteudo": (
            "O sistema de feedback sonoro da AURA utiliza a Web Audio API nativa do navegador para sintetizar ondas sonoras suteis e elegantes (chimes senoidais entre 500Hz e 800Hz) ao executar cliques, "
            "alternar abas, receber mensagens e concluir auditorias. Vem em modo discreto (mudo) por padrao para ambientes de trabalho e pode ser ativado a qualquer momento pelo botao de alto-falante "
            "no cabecalho ou no menu lateral. Garante confirmacao tatil e sensorial sem necessidade de carregar arquivos de audio pesados."
        ),
        "metadados": {
            "categoria": "acessibilidade_som",
        },
        "elementos_ui": {
            "componente": "window.auraAudio",
            "botao_header": "btn-toggle-sfx",
            "botao_drawer": "sidebar-btn-toggle-sfx",
            "frequencias_hz": [500, 600, 660, 700, 800],
        },
        "ui_action": {
            "action": "toggle_audio",
            "target": "audio",
            "label": "Ativar/Desativar Sons Taticos",
        },
        "tags": ["audio", "som", "sfx", "sons", "chime", "web audio api", "feedback sensorial", "mudo", "efeito sonoro", "acessibilidade", "volume", "mutar", "desmutar"],
    },

    # -------------------------------------------------------------------------
    # 4. Normas Tecnicas: ANP (Portaria 26/1992 e Resolucao 894/2022)
    # -------------------------------------------------------------------------
    {
        "modulo": "compliance_anp",
        "topico": "lmc_tolerancia_variacao_perdas_sobras",
        "titulo": "Tolerancia Legal de Perdas e Sobras no LMC (0,60%) - Portaria ANP 26/1992",
        "subtitulo": "Limite regulatorio de perda ou ganho fisico volumetrico de ate 0,60% e apuracao de quebra",
        "conteudo": (
            "A Portaria ANP nº 26/1992 estabelece que a variacao volumetrica maxima admissivel entre o estoque fisico "
            "e o estoque contabil apurado no Livro de Movimentacao de Combustiveis (LMC) e de ±0,60% (zero virgula sessenta por cento) "
            "sobre o volume total de saidas (vendas) de cada combustivel no mes de apuracao. "
            "A formula regulatoria oficial de apuracao e: Variacao_Percentual = ((Estoque_Fisico_Final - Estoque_Contabil_Final) / Total_Saidas) * 100. "
            "Variacoes dentro do intervalo de -0,60% a +0,60% sao consideradas perdas ou ganhos normais decorrentes de evaporacao natural, "
            "dilatacao ou contracao termica nos tanques subterraneos. Desvios que ultrapassem ±0,60% configuram indicio de nao conformidade grave, "
            "exigindo sindicancia operacional imediata, teste de estanqueidade nos tanques e linhas para descarte de vazamentos ambientais, "
            "vistoria no concentrador de pista e calibracao volumetrica das bombas medidoras."
        ),
        "metadados": {
            "norma": "Portaria ANP nº 26/1992",
            "orgao": "ANP",
            "tolerancia_maxima_percentual": 0.60,
            "tipo_livro": "LMC",
            "penalidades": "Notificacao, autuacao fiscal e exigencia de laudo de estanqueidade",
            "prazo_guarda_anos": 5,
            "formula": "((Estoque_Fisico - Estoque_Contabil) / Total_Saidas) * 100",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_LMCReport",
            "componente": "LMCReport",
            "tipo": "auditoria_regulatoria",
        },
        "ui_action": {
            "action": "open_lmc",
            "target": "lmc_report",
            "label": "Auditar Variacao Volumetrica LMC",
        },
        "tags": ["lmc", "anp 26/1992", "portaria anp 26", "tolerancia lmc", "0.60%", "perda de combustivel", "sobra fisica", "variacao volumetrica", "tanque subterraneo", "estanqueidade", "livro de movimentacao de combustiveis"],
    },
    {
        "modulo": "compliance_anp",
        "topico": "lmc_escrituracao_diaria_guarda_5_anos",
        "titulo": "Obrigatoriedade de Escrituracao Diaria do LMC e Guarda por 5 Anos",
        "subtitulo": "Prazos de escrituracao, fechamento ate o 5º dia util subsequente e retencao documental",
        "conteudo": (
            "A Portaria ANP nº 26/1992 e a Resolucao ANP nº 894/2022 determinam a obrigatoriedade de escrituracao diaria do Livro de Movimentacao de Combustiveis (LMC) "
            "pelo revendedor varejista de combustiveis. Os lancamentos de estoques de abertura, recebimentos por notas fiscais eletronicas, encerrantes de bombas "
            "e estoque fisico medido devem ser efetuados diariamente no fechamento do turno ou do dia. "
            "O prazo limite de consolidacao e encerramento mensal da escrituracao do LMC e impreterivelmente ate o 5º dia util do mes subsequente ao periodo de apuracao. "
            "O revendedor varejista e legalmente obrigado a manter os livros escriturados (impressos ou em formato eletronico homologado com assinatura digital), "
            "juntamente com as respectivas notas fiscais de entrada e relatorios de afericao, arquivados no proprio posto revendedor e permanentemente "
            "disponiveis a fiscalizacao da ANP, PROCON e Receita Estadual pelo prazo minimo de 5 (cinco) anos. A falta de apresentacao do LMC enseja auto de infracao "
            "com aplicacao de multas severas e possivel interdicao do estabelecimento."
        ),
        "metadados": {
            "norma": "Portaria ANP nº 26/1992 / Resolucao ANP nº 894/2022",
            "orgao": "ANP",
            "prazo_escrituracao": "Diario, fechamento ate o 5º dia util do mes subsequente",
            "prazo_guarda_anos": 5,
            "local_guarda": "No proprio posto revendedor",
            "sancoes": "Multa grave e interdicao cautelar por desobediencia a dever legal",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_LMCReport",
            "componente": "LMCReport",
            "tipo": "fechamento_diario",
        },
        "ui_action": {
            "action": "open_lmc_history",
            "target": "lmc_report",
            "label": "Verificar Arquivo de LMC (5 Anos)",
        },
        "tags": ["lmc", "escrituracao diaria", "prazo 5 dia util", "guarda 5 anos", "portaria 26/1992", "resolucao 894/2022", "fiscalizacao anp", "documentacao contabil", "fechamento de mes", "arquivamento legal"],
    },
    {
        "modulo": "compliance_anp",
        "topico": "anp_894_fidelidade_bandeira_identificacao_precos",
        "titulo": "Fidelidade a Bandeira e Identificacao de Precos na Testeira - Resolucao ANP 894/2022",
        "subtitulo": "Deveres de ostentacao de bandeira, correspondencia de precos e transparencia ao consumidor",
        "conteudo": (
            "A Resolucao ANP nº 894/2022 regulamenta os direitos e deveres dos revendedores varejistas de combustiveis automotivos. "
            "O posto com contrato de exclusividade de bandeira (posto bandeirado) deve comercializar exclusivamente combustiveis fornecidos pela distribuidora detentora da marca, "
            "sendo expressamente vedada a compra de terceiros ou o uso de bandeira branca enganosa. "
            "Postos bandeira branca (sem distribuidora exclusiva) devem identificar com clareza a distribuidora fornecedora em cada bico de abastecimento. "
            "E obrigatoria a instalacao de painel de precos na entrada do posto e testeira, visivel a partir da via publica tanto de dia quanto de noite. "
            "O valor exibido no painel de precos deve corresponder com exatidao matematica ao preco registrado no display da bomba medidora. "
            "Havendo divergencia de valor, prevalece obrigatoriamente o menor preco em favor do consumidor. "
            "Descontos vinculados a aplicativos de fidelidade, cashback ou cartoes proprietarios devem ser exibidos de forma clara, informando o preco real sem desconto com igual ou maior destaque."
        ),
        "metadados": {
            "norma": "Resolucao ANP nº 894/2022",
            "orgao": "ANP",
            "artigos": "Art. 18 ao 26",
            "regra_preco": "Preco da testeira deve ser identico ao da bomba; menor preco prevalece em caso de erro",
            "bandeira": "Exclusividade estrita para postos bandeirados; identificacao do fornecedor para bandeira branca",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_BenchmarkComparisonUI",
            "componente": "BenchmarkComparisonUI",
            "tipo": "painel_precos",
        },
        "ui_action": {
            "action": "open_price_manager",
            "target": "precos_bomba",
            "label": "Conferir Painel de Precos e Bombas",
        },
        "tags": ["resolucao anp 894/2022", "anp 894", "fidelidade a bandeira", "painel de precos", "testeira", "preco na bomba", "bandeira branca", "direitos do consumidor", "placa de precos"],
    },
    {
        "modulo": "compliance_anp",
        "topico": "anp_894_testes_qualidade_amostra_testemunha",
        "titulo": "Testes Obrigatorios de Qualidade na Pista, Amostras-Testemunha e Recusa de Cargas - Resolucao ANP 894/2022",
        "subtitulo": "Ensaio de proveta (27% ± 1%), termodensimetro, guarda de amostras e protocolo de recusa de combustivel",
        "conteudo": (
            "A Resolucao ANP nº 894/2022 estabelece a obrigatoriedade de o posto revendedor realizar gratuitamente e na presenca do consumidor, "
            "sempre que solicitado antes ou durante o abastecimento, os seguintes ensaios de qualidade na pista: "
            "1. Teste de proveta para determinacao do teor de etanol anidro na gasolina comum e aditivada, cujo limite oficial obrigatorio e de 27% com tolerancia de ±1% (faixa de 26% a 28%); "
            "2. Teste do termodensimetro para etanol hidratado, devendo a coluna indicadora estar imersa na linha de flutuacao regular com massa especifica entre 0,8074 e 0,8110 g/cm³ a 20ºC; "
            "3. Teste de densidade e aspecto do oleo diesel com densimetro calibrado. "
            "O posto deve manter equipamentos aferidos e em perfeito estado de funcionamento na pista (proveta de 100 ml com tampa, termodensimetro e termometro homologado). "
            "Na chegada do caminhao-tanque, o revendedor e obrigado a efetuar a verificacao dos lacres e testes de recebimento antes de autorizar o descarregamento nos tanques subterraneos. "
            "Caso qualquer ensaio aponte combustivel fora de especificacao (teor de etanol divergente, presenca de agua ou massa especifica inadequada), o posto deve adotar o procedimento formal de recusa: "
            "1. Impedir imediatamente o descarregamento da carga no tanque; "
            "2. Reter a amostra-testemunha comprobatoria de cada compartimento em frascos ambar de 1 litro lacrados e identificados; "
            "3. Lavrar no verso do DACTE ou DANFE a recusa motivada detalhando os parametros reprovados com data, hora e assinatura do motorista; "
            "4. Notificar a distribuidora fornecedora e comunicar formalmente o fato a fiscalizacao da ANP. "
            "As amostras-testemunha validas devem ser mantidas sob guarda por no minimo 6 (seis) meses para pericia tecnica em caso de contestacao de conformidade."
        ),
        "metadados": {
            "norma": "Resolucao ANP nº 894/2022",
            "orgao": "ANP",
            "gasolina_teor_etanol": "27% com tolerancia de ±1% (26% a 28%)",
            "etanol_massa_especifica": "0.8074 a 0.8110 g/cm3 a 20C",
            "guarda_amostra_testemunha_meses": 6,
            "procedimento_recusa_combustivel": "Impedir descarregamento, lavrar ressalva com parametros reprovados no verso do DACTE/DANFE com assinatura do motorista, lacrar amostra de 1L em frasco ambar e notificar distribuidora e ANP",
            "equipamentos_obrigatorios": "Proveta 100ml com tampa, termodensimetro, termometro de petroleo, densimetro de diesel",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_QualityTestUI",
            "componente": "QualityTestUI",
            "tipo": "qualidade_combustivel",
        },
        "ui_action": {
            "action": "open_quality_checklist",
            "target": "testes_qualidade",
            "label": "Registrar Teste de Qualidade na Pista",
        },
        "tags": ["teste de proveta", "teor alcoolico", "27% gas", "resolucao anp 894", "qualidade combustivel", "etanol hidratado", "termodensimetro", "amostra testemunha", "frasco ambar", "ensaio de pista", "recusa de combustivel", "combustivel fora de especificacao", "recusa de descarregamento", "devolucao caminhao tanque"],
    },

    # -------------------------------------------------------------------------
    # 5. Metrologia Legal INMETRO (Portaria 559/2016 e RTM)
    # -------------------------------------------------------------------------
    {
        "modulo": "metrologia_inmetro",
        "topico": "inmetro_559_tolerancia_bombas_100ml",
        "titulo": "Tolerancia Metrologica Legal de Bombas (±100 ml em 20 L) - Portaria INMETRO 559/2016",
        "subtitulo": "Erro Maximo Admissivel (EMA) de ±0,50% em vazao nominal e reduzida em balde padrao de 20 litros",
        "conteudo": (
            "A Portaria INMETRO nº 559/2016 aprova o Regulamento Tecnico Metrologico (RTM) para bombas medidoras de combustiveis liquidos. "
            "O regulamento estabelece que o Erro Maximo Admissivel (EMA) nas operacoes de medicao em servico e de ±100 ml para uma dosagem de 20 litros, "
            "o que corresponde a uma tolerancia volumetrica relativa de ±0,50% (zero virgula cinquenta por cento). "
            "O ensaio metrologico oficial de pista deve ser executado obrigatoriamente tanto em vazao nominal (vazao maxima com gatilho totalmente aberto) "
            "quanto em vazao reduzida (vazao minima com gatilho no primeiro estagio), utilizando medida de volume de 20 litros aferida, calibrada e com lacre intacto emitido pelo IPEM/INMETRO. "
            "Se a afericao acusar volume inferior a -100 ml (por exemplo, -120 ml em 20L), a bomba esta entregando menos combustivel do que o cobrado, "
            "configurando infracao metrologica gravissima passivel de interdicao cautelar imediata do bico, auto de infracao e penalidade criminal (crime contra a ordem economica). "
            "Se a afericao indicar volume superior a +100 ml, o posto esta incorrendo em quebra financeira oculta (entregando mais produto do que o faturado), "
            "devendo providenciar ajuste corretivo imediato por oficina metrologica credenciada e autorizada pelo IPEM."
        ),
        "metadados": {
            "norma": "Portaria INMETRO nº 559/2016",
            "orgao": "INMETRO / IPEM",
            "erro_maximo_admissivel_ml": 100,
            "volume_padrao_litros": 20,
            "tolerancia_percentual": 0.50,
            "ensaios_vazao": "Vazao nominal (maxima) e vazao reduzida (estrangulada), ambas com EMA ±100 ml em 20L",
            "instrumento": "Medida de volume padrao de 20 litros com certificado de calibracao valido",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_ShiftReconciliationUI",
            "componente": "ShiftReconciliationUI",
            "tipo": "auditoria_metrologica",
        },
        "ui_action": {
            "action": "open_shift_reconciliation",
            "target": "reconciliacao_bombas",
            "label": "Auditar Metrologia de Bicos (INMETRO)",
        },
        "tags": ["inmetro 559/2016", "portaria 559", "rtm inmetro", "tolerancia de bombas", "100ml em 20l", "erro maximo admissivel", "ema", "afericao de bico", "balde padrao 20 litros", "ipem", "calibracao", "vazao nominal", "vazao reduzida"],
    },
    {
        "modulo": "metrologia_inmetro",
        "topico": "inmetro_559_afericao_estorno_lacres",
        "titulo": "Afericao Diaria de Bicos, Estorno Fiscal e Lacres de Seguranca - Portaria INMETRO 559/2016",
        "subtitulo": "Procedimentos de ensaio matinal, retorno ao tanque sem cupom e integridade dos lacres",
        "conteudo": (
            "A Portaria INMETRO nº 559/2016 e as boas praticas operacionais de postos exigem a realizacao de verificacao volumetrica (afericao) "
            "de todos os bicos antes do inicio da operacao diaria do posto revendedor. "
            "Todo combustivel retirado da bomba no ensaio com a medida padrao de 20 litros deve ser imediatamente devolvido ao tanque subterraneo do mesmo produto. "
            "O volume movimentado na afericao altera os encerrantes mecanicos e eletronicos da bomba medidora. Portanto, a automacao de pista (concentrador) "
            "e o sistema de PDV devem registrar a operacao estritamente sob o codigo de afericao tecnica, cancelando o pulso de venda para nao emitir cupom fiscal (NFC-e) "
            "nem onerar indevidamente o fechamento de caixa do frentista ou gerar tributacao indevida de ICMS. "
            "Os blocos medidores, transdutores de pulsos (encoders) e a CPU das bombas possuem lacres metrologicos fisicos e eletronicos instalados pelo IPEM. "
            "E expressamente vedado a qualquer funcionario do posto romper, violar ou alterar esses lacres. Toda intervencao tecnica exige chamado formal de "
            "oficina autorizada e credenciada pelo IPEM, com emissao do Termo de Intervencao Tecnica."
        ),
        "metadados": {
            "norma": "Portaria INMETRO nº 559/2016",
            "orgao": "INMETRO",
            "procedimento": "Afericao no balde padrao de 20L, retorno imediato ao tanque de origem, estorno fiscal",
            "lacres": "Fisicos e eletronicos; violacao sujeita a interdicao e processo criminal",
            "registro_fiscal": "Lancamento como afericao no ERP para abater de encerrantes sem gerar cupom",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_ShiftReconciliationUI",
            "componente": "ShiftReconciliationUI",
            "tipo": "conciliacao_afericao",
        },
        "ui_action": {
            "action": "register_calibration",
            "target": "afericoes_bico",
            "label": "Lancar Afericao de Bico no Turno",
        },
        "tags": ["afericao de bico", "estorno fiscal", "inmetro 559/2016", "lacre metrologico", "ipem", "retorno ao tanque", "sem cupom", "encerrante", "conciliacao de turno", "oficina autorizada"],
    },

    # -------------------------------------------------------------------------
    # 6. Seguranca Operacional e Ambiental (Portaria ANP 858/2021 e Resolucao 41/2013)
    # -------------------------------------------------------------------------
    {
        "modulo": "compliance_anp",
        "topico": "anp_858_seguranca_pista_descarte_sao",
        "titulo": "Seguranca na Pista de Abastecimento e Descarte de Efluentes SAO - Portaria ANP 858/2021 & Resolucao 41/2013",
        "subtitulo": "Avisos de seguranca obrigatorios, abastecimento em recipientes certificados e caixa SAO",
        "conteudo": (
            "A Portaria ANP nº 858/2021 e a Resolucao ANP nº 41/2013 regulamentam as condicoes de seguranca operacional, protecao ambiental "
            "e saude ocupacional nos postos revendedores de combustiveis. "
            "Na pista de abastecimento, e obrigatoria a exibicao de avisos ostensivos de seguranca: 'Desligue o motor', 'Nao fume', 'Desligue o celular', "
            "alem da advertencia sobre os riscos de eletricidade estatica. "
            "O abastecimento fora do tanque de veiculos automotores so pode ser efetuado em recipientes rigidos certificados pelo INMETRO "
            "(bombonas plasticas ou metalicas com selo do INMETRO), sendo terminantemente proibido o enchimento de garrafas PET, sacolas plasticas ou vasilhames de vidro. "
            "Para protecao do lencol freatico e da rede pluvial, todo o piso da pista de abastecimento e da lavagem de veiculos deve ser impermeabilizado "
            "e direcionado para a Caixa Separadora de Agua e Oleo (SAO). "
            "O revendedor e responsavel pela manutencao e desassoreamento periodico da SAO, destinando a borra oleosa e o oleo recolhido "
            "exclusivamente para empresas coletoras e re-refinadoras licenciadas pelo orgao ambiental estadual e com certificado de destinacao de residuos (MTR)."
        ),
        "metadados": {
            "norma": "Portaria ANP nº 858/2021 / Resolucao ANP nº 41/2013",
            "orgao": "ANP / Orgao Ambiental Estadual",
            "sinalizacao_obrigatoria": "Desligar motor, nao fumar, desligar celular, recipiente certificado INMETRO",
            "meio_ambiente": "Piso impermeabilizado, caixa separadora SAO com destinacao certificada MTR",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_SafetyCheckUI",
            "componente": "SafetyCheckUI",
            "tipo": "seguranca_ambiental",
        },
        "ui_action": {
            "action": "open_safety_audit",
            "target": "auditoria_seguranca",
            "label": "Inspecionar Caixa SAO e Avisos",
        },
        "tags": ["seguranca na pista", "anp 858/2021", "resolucao anp 41/2013", "caixa separadora sao", "recipiente inmetro", "garrafa pet proibida", "desligue motor", "meio ambiente", "licenca de operacao", "residuos oleosos"],
    },

    # -------------------------------------------------------------------------
    # 7. Legislacao Tributaria (CONFAZ, LC 192/2022 e STF Tema 201)
    # -------------------------------------------------------------------------
    {
        "modulo": "tributario_combustiveis",
        "topico": "tributario_icms_monofasico_vs_st_pmpf",
        "titulo": "Regime de ICMS Monofasico (LC 192/2022) vs ICMS-ST com PMPF CONFAZ",
        "subtitulo": "Aliquota ad rem em R$/L para Diesel e GLP versus substituicao tributaria com PMPF para Etanol e GNV",
        "conteudo": (
            "A tributacao de combustiveis no Brasil opera sob dois regimes juridicos distintos: "
            "1. Regime de ICMS Monofasico (Lei Complementar nº 192/2022 e Convenios ICMS CONFAZ): incide sobre Oleo Diesel (S10 e S500), Biodiesel e GLP. "
            "O imposto e recolhido em uma unica etapa na refinaria ou no importador, com aliquota unica nacional fixa em reais por litro (aliquota 'ad rem'), "
            "nao variando com o preco de venda da bomba. O revendedor varejista nao destaca, nao apura debito nem recolhe ICMS proprio sobre a venda desses produtos. "
            "2. Regime de Substituicao Tributaria (ICMS-ST com PMPF): permanece em vigor para Etanol Hidratado Combustivel (EHC) e GNV na maioria dos estados. "
            "A distribuidora recolhe o ICMS presumido antecipadamente calculando uma base presumida sobre o Preco Medio Ponderado ao Consumidor Final (PMPF), "
            "divulgado quinzenalmente pelo CONFAZ em Atos COTEPE publicados no Diario Oficial da Uniao. "
            "O revendedor deve acompanhar as alteracoes no Ato COTEPE quinzenal para antecipar reajustes no custo de aquisicao junto as distribuidoras."
        ),
        "metadados": {
            "norma": "Lei Complementar nº 192/2022 / Atos COTEPE CONFAZ",
            "orgao": "CONFAZ / SEFAZ",
            "regime_diesel": "Monofasico ad rem (R$/L nacional uniforme)",
            "regime_etanol_gnv": "Substituicao Tributaria (ICMS-ST) com base no PMPF quinzenal",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_MarginAnalysisUI",
            "componente": "MarginAnalysisUI",
            "tipo": "tributario_icms",
        },
        "ui_action": {
            "action": "open_tax_analysis",
            "target": "pmpf_cotepe",
            "label": "Analisar Regime Tributario de Combustiveis",
        },
        "tags": ["icms monofasico", "lc 192/2022", "icms-st", "pmpf", "confaz", "ato cotepe", "tributacao diesel", "tributacao etanol", "aliquota ad rem", "substituicao tributaria"],
    },
    {
        "modulo": "tributario_combustiveis",
        "topico": "tributario_restituicao_icms_st_tema_201_stf",
        "titulo": "Restituicao e Complementacao de ICMS-ST em Combustiveis (STF Tema 201)",
        "subtitulo": "Direito de ressarcimento quando o preco na bomba e inferior a base presumida do PMPF",
        "conteudo": (
            "O Supremo Tribunal Federal (STF), no julgamento de repercussao geral do Tema 201 (RE 593.849), firmou a tese juridica de que "
            "e devida a restituicao da diferenca do ICMS pago a mais no regime de substituicao tributaria para frente se a base de calculo efetiva "
            "da operacao for inferior a presumida. "
            "No varejo de combustiveis (aplicavel ao Etanol Hidratado e GNV sob regime de PMPF), caso o posto venda o produto ao consumidor final por preco "
            "inferior ao PMPF fixado no Ato COTEPE utilizado pela distribuidora para retencao, o revendedor tem direito lidimo de pleitear o ressarcimento "
            "do valor pago a maior junto a Secretaria de Fazenda Estadual (SEFAZ). "
            "Em contrapartida, dependendo da regulamentacao de cada unidade federativa, caso o posto pratique preco de venda na bomba superior ao PMPF de referencia, "
            "pode ser exigida a complementacao do imposto. "
            "A auditoria automatizada do PMPF vs Preco Medio Praticado pela AURA identifica mensalmente se o posto possui creditos fiscais a restituir ou passivos a complementar."
        ),
        "metadados": {
            "norma": "STF Tema 201 (RE 593.849) / Atos COTEPE CONFAZ",
            "orgao": "STF / SEFAZ",
            "tese": "Direito a restituicao do ICMS-ST pago a maior se base de calculo real for menor que presumida",
            "impacto_financeiro": "Recuperacao de creditos tributarios acumulados em Etanol Hidratado",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_ExecutiveDecisionUI",
            "componente": "ExecutiveDecisionUI",
            "tipo": "recuperacao_tributaria",
        },
        "ui_action": {
            "action": "open_tax_refund_audit",
            "target": "restituicao_icms",
            "label": "Calcular Credito de Ressarcimento ICMS-ST",
        },
        "tags": ["tema 201 stf", "restituicao icms-st", "ressarcimento pmpf", "sefaz", "etanol hidratado", "credito tributario", "recuperacao de impostos", "complementacao de icms", "ato cotepe", "direito tributario"],
    },

    # -------------------------------------------------------------------------
    # 8. Governanca Financeira e Macroeconomia BACEN
    # -------------------------------------------------------------------------
    {
        "modulo": "macroeconomia_bacen",
        "topico": "bacen_custo_carregamento_estoque_selic",
        "titulo": "Custo de Carregamento de Estoque Subterraneo via Taxa Selic (BACEN)",
        "subtitulo": "Calculo de capital imobilizado, carrying cost diario e giro otimo de compras",
        "conteudo": (
            "O capital de giro imobilizado em estoques subterraneos de combustiveis (tipicamente entre 40.000 e 150.000 litros por posto) "
            "possui um custo financeiro diario de oportunidade regido pela Taxa Selic oficial divulgada pelo Banco Central do Brasil (Serie 11 e 432 do SGS). "
            "A formula analitica de carregamento de estoque adotada pela AURA e: "
            "Custo_Diario_Carregamento = (Volume_Estocado_Litros * Preco_Custo_Compra) * ((Taxa_Selic_Anual / 100) / 252) * Dias_Estoque. "
            "Por exemplo, com a Selic a 10,75% ao ano e um estoque de R$ 300.000 em combustiveis, o custo de carregamento e de aproximadamente R$ 127,97 por dia. "
            "Em momentos de juros elevados, manter excesso de produto estocado reduz o fluxo de caixa livre e gera perda silenciosa de rentabilidade. "
            "O motor preditivo da AURA calcula o Lote Economico de Reposicao (EOQ adaptado para bacias de caminhao de 5.000L), "
            "balanceando o risco de desabastecimento (run-out) contra o custo de oportunidade financeiro Selic."
        ),
        "metadados": {
            "norma": "Series SGS 11 e 432 BACEN / Metodologia EOQ Financeiro",
            "orgao": "BACEN",
            "taxa_referencia": "Taxa Selic meta e diaria anualizada base 252 dias uteis",
            "formula": "(Volume * Custo) * (Selic / 252)",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_PredictiveScenarioUI",
            "componente": "PredictiveScenarioUI",
            "tipo": "gestao_financeira",
        },
        "ui_action": {
            "action": "open_inventory_optimization",
            "target": "otimizacao_compras",
            "label": "Analisar Custo de Carregamento Selic",
        },
        "tags": ["bacen", "taxa selic", "custo de carregamento", "carrying cost", "capital de giro", "estoque subterraneo", "lote economico", "otimizacao de compras", "run-out", "lucratividade"],
    },
    {
        "modulo": "macroeconomia_bacen",
        "topico": "bacen_paridade_importacao_cambio_ptax",
        "titulo": "Paridade de Precos de Importacao (PPI) e Sensibilidade ao Cambio PTAX",
        "subtitulo": "Correlacao entre cotacao do Dolar PTAX (Serie 1 BACEN), petroleo Brent e reajuste de refinaria",
        "conteudo": (
            "O custo de aquisicao de combustiveis das refinarias e importadoras no Brasil esta intrinsecamente atrelado a Paridade de Precos de Importacao (PPI), "
            "calculada pela cotacao internacional do petroleo tipo Brent (em USD/barril) combinada com a taxa de cambio oficial do Dolar PTAX (Serie 1 do SGS BACEN). "
            "Flutuacoes cambiais acumuladas superiores a 3% em periodos inferiores a 10 dias uteis exercem forte pressao sobre as margens das refinarias e distribuidoras, "
            "antecipando reajustes na tabela de precos de atacado em um horizonte preditivo de 7 a 14 dias corridos. "
            "A AURA monitora a taxa PTAX diaria para emitir recomendacoes taticas antecipadas de compra de combustivel: ao identificar tendencia iminente de elevacao, "
            "sugere a antecipacao de pedidos de caminhao-tanque completo para capturar ganho de estocagem antes do aumento oficial repassado pela distribuidora."
        ),
        "metadados": {
            "norma": "Serie SGS 1 BACEN / Politica de Precos de Refinarias",
            "orgao": "BACEN",
            "indicador": "Dolar Comercial PTAX Venda e Compra",
            "gatilho_alerta": "Variacao acumulada de cambio > 3% em 10 dias uteis",
        },
        "elementos_ui": {
            "tab": "cockpit",
            "widget": "render_BenchmarkComparisonUI",
            "componente": "BenchmarkComparisonUI",
            "tipo": "projecao_cambio",
        },
        "ui_action": {
            "action": "open_market_forecast",
            "target": "previsao_mercado",
            "label": "Ver Tendencia Cambial e Precos da Refinaria",
        },
        "tags": ["dolar ptax", "cambio bacen", "paridade de importacao", "ppi", "petroleo brent", "aumento de combustivel", "previsao de compras", "distribuidora", "mercado de combustiveis"],
    },
]

# Alias canonico para compatibilidade total com versoes anteriores
CONHECIMENTO_CHUNKS: list[dict[str, Any]] = CONHECIMENTO_SEEDS


def calcular_hash_conhecimento(
    modulo: str,
    topico: str,
    titulo: str,
    subtitulo: str,
    conteudo: str,
    elementos_ui: dict[str, Any],
    ui_action: dict[str, Any],
    tags: list[str],
    metadados: dict[str, Any] | None = None,
) -> str:
    """Calcula hash deterministico MD5 para Change Data Capture (CDC) no banco vetorial."""
    el_str = json.dumps(elementos_ui or {}, sort_keys=True)
    act_str = json.dumps(ui_action or {}, sort_keys=True)
    meta_str = json.dumps(metadados or {}, sort_keys=True)
    tags_str = ",".join(sorted(tags or []))
    payload = f"{modulo.strip()}|{topico.strip()}|{titulo.strip()}|{subtitulo.strip()}|{conteudo.strip()}|{el_str}|{act_str}|{tags_str}|{meta_str}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def inicializar_tabela_conhecimento(conn_vec, schema_name: str = "aura_core"):
    """
    Garante a existencia do schema, extensao vector, tabela aura_conhecimento_vetores,
    colunas enriquecidas (metadados, hash_md5, atualizado_em), coluna gerada tsv e indices HNSW/GIN.
    """
    with conn_vec.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")

        # 1. Cria a tabela base se nao existir
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.aura_conhecimento_vetores (
                id SERIAL PRIMARY KEY,
                modulo VARCHAR(50) NOT NULL,
                topico VARCHAR(100) NOT NULL,
                titulo VARCHAR(150) NOT NULL,
                subtitulo VARCHAR(255),
                conteudo TEXT NOT NULL,
                metadados JSONB DEFAULT '{{}}'::jsonb,
                elementos_ui JSONB DEFAULT '{{}}'::jsonb,
                ui_action JSONB DEFAULT '{{}}'::jsonb,
                tags TEXT[],
                embedding halfvec(768),
                hash_md5 VARCHAR(32),
                criado_em TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW()
            );
        """)

        # 2. Assegura a existencia de colunas caso a tabela tenha sido criada previamente por DDL legado
        cur.execute(f"""
            ALTER TABLE {schema_name}.aura_conhecimento_vetores 
            ADD COLUMN IF NOT EXISTS metadados JSONB DEFAULT '{{}}'::jsonb;
        """)
        cur.execute(f"""
            ALTER TABLE {schema_name}.aura_conhecimento_vetores 
            ADD COLUMN IF NOT EXISTS hash_md5 VARCHAR(32);
        """)
        cur.execute(f"""
            ALTER TABLE {schema_name}.aura_conhecimento_vetores 
            ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT NOW();
        """)

        # 3. Assegura a existencia da coluna gerada tsvector (tsv)
        cur.execute(f"""
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = '{schema_name}' 
              AND table_name = 'aura_conhecimento_vetores' 
              AND column_name = 'tsv';
        """)
        if not cur.fetchone():
            cur.execute(f"""
                ALTER TABLE {schema_name}.aura_conhecimento_vetores 
                ADD COLUMN tsv tsvector GENERATED ALWAYS AS (
                    to_tsvector('portuguese'::regconfig,
                        coalesce(titulo, '') || ' ' ||
                        coalesce(subtitulo, '') || ' ' ||
                        coalesce(modulo, '') || ' ' ||
                        coalesce(topico, '') || ' ' ||
                        coalesce(conteudo, '')
                    )
                ) STORED;
            """)

        # 4. Assegura restricao UNIQUE (modulo, topico)
        cur.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'uq_aura_conhecimento_modulo_topico'
                      AND conrelid = '{schema_name}.aura_conhecimento_vetores'::regclass
                ) THEN
                    ALTER TABLE {schema_name}.aura_conhecimento_vetores 
                    ADD CONSTRAINT uq_aura_conhecimento_modulo_topico UNIQUE (modulo, topico);
                END IF;
            END $$;
        """)

        # 5. Indices HNSW, GIN FTS, B-Trees
        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema_name}_conhecimento_hnsw 
            ON {schema_name}.aura_conhecimento_vetores USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 24, ef_construction = 128);
        """)

        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema_name}_conhecimento_tsv_gin 
            ON {schema_name}.aura_conhecimento_vetores USING gin (tsv);
        """)

        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema_name}_conhecimento_modulo_topico 
            ON {schema_name}.aura_conhecimento_vetores (modulo, topico);
        """)

        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema_name}_conhecimento_hash_md5 
            ON {schema_name}.aura_conhecimento_vetores (hash_md5);
        """)

        conn_vec.commit()
    print(f"   [OK] Tabela '{schema_name}.aura_conhecimento_vetores' e indices HNSW + GIN + BTree verificados.")


def seed_conhecimento(
    conn_vec,
    reindex_all: bool = False,
    schema_name: str = "aura_core",
) -> dict[str, int]:
    """
    Popula os chunks oficiais da AURA utilizando Delta Hashing (hash_md5).
    Gera vetores via API Gemini com fallback deterministico automatico.
    Garante idempotencia estrita com ON CONFLICT (modulo, topico) DO UPDATE.
    """
    inicializar_tabela_conhecimento(conn_vec, schema_name=schema_name)

    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
        except Exception as e:  # noqa: BLE001
            print(f"   [AVISO] Nao foi possivel configurar API Gemini: {e}")

    # Carrega estado existente da tabela
    existing_records: dict[str, dict[str, Any]] = {}
    with conn_vec.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT id, modulo, topico, hash_md5, (embedding IS NOT NULL) AS has_embedding
            FROM {schema_name}.aura_conhecimento_vetores;
        """)
        for row in cur.fetchall():
            key = f"{row['modulo']}|{row['topico']}"
            existing_records[key] = dict(row)

    stats = {
        "total": len(CONHECIMENTO_SEEDS),
        "inseridos": 0,
        "atualizados": 0,
        "ignorados_cdc": 0,
        "erros": 0,
    }

    print(f"\n2. Analisando {stats['total']} chunks de conhecimento para seeding no schema '{schema_name}'...")

    for chunk in CONHECIMENTO_SEEDS:
        modulo = chunk["modulo"]
        topico = chunk["topico"]
        titulo = chunk["titulo"]
        subtitulo = chunk.get("subtitulo", "")
        conteudo = chunk["conteudo"]
        metadados = chunk.get("metadados", {})
        elementos_ui = chunk.get("elementos_ui", {})
        ui_action = chunk.get("ui_action", {})
        tags = chunk.get("tags", [])

        h_calc = calcular_hash_conhecimento(
            modulo=modulo,
            topico=topico,
            titulo=titulo,
            subtitulo=subtitulo,
            conteudo=conteudo,
            elementos_ui=elementos_ui,
            ui_action=ui_action,
            tags=tags,
            metadados=metadados,
        )

        key = f"{modulo}|{topico}"
        existing = existing_records.get(key)

        # Delta check CDC
        if existing and not reindex_all and existing.get("hash_md5") == h_calc and existing.get("has_embedding"):
            stats["ignorados_cdc"] += 1
            continue

        # Texto para vetorizacao
        texto_embedding = (
            f"Modulo: {modulo} | Topico: {topico} | Titulo: {titulo}\n"
            f"Subtitulo: {subtitulo}\n"
            f"Conteudo: {conteudo}\n"
            f"Tags: {', '.join(tags)}"
        )

        embedding_vector = None
        if GEMINI_API_KEY:
            try:
                res_emb = genai.embed_content(
                    model=DEFAULT_EMBEDDING_MODEL,
                    content=texto_embedding,
                    output_dimensionality=768,
                    task_type="retrieval_document",
                )
                embedding_vector = res_emb.get("embedding")
            except Exception as e:  # noqa: BLE001
                # Log discreto e contingencia deterministica
                print(f"   [AVISO] API Gemini nao disponivel para ({modulo}/{topico}): {e}. Usando fallback deterministico.")
                embedding_vector = None

        if not embedding_vector:
            embedding_vector = gerar_embedding_deterministico(texto_embedding, dim=768)

        vec_str = str(embedding_vector)

        try:
            with conn_vec.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {schema_name}.aura_conhecimento_vetores (
                        modulo, topico, titulo, subtitulo, conteudo, metadados, elementos_ui, ui_action, tags,
                        embedding, hash_md5, atualizado_em
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::halfvec, %s, NOW())
                    ON CONFLICT (modulo, topico) DO UPDATE SET
                        titulo = EXCLUDED.titulo,
                        subtitulo = EXCLUDED.subtitulo,
                        conteudo = EXCLUDED.conteudo,
                        metadados = EXCLUDED.metadados,
                        elementos_ui = EXCLUDED.elementos_ui,
                        ui_action = EXCLUDED.ui_action,
                        tags = EXCLUDED.tags,
                        embedding = EXCLUDED.embedding,
                        hash_md5 = EXCLUDED.hash_md5,
                        atualizado_em = NOW();
                """, (
                    modulo,
                    topico,
                    titulo,
                    subtitulo,
                    conteudo,
                    json.dumps(metadados, ensure_ascii=False),
                    json.dumps(elementos_ui, ensure_ascii=False),
                    json.dumps(ui_action, ensure_ascii=False),
                    tags,
                    vec_str,
                    h_calc,
                ))
                conn_vec.commit()

            if existing:
                stats["atualizados"] += 1
                print(f"   [UPDATE] ({modulo}/{topico}) '{titulo}' atualizado com novo hash.")
            else:
                stats["inseridos"] += 1
                print(f"   [INSERT] ({modulo}/{topico}) '{titulo}' indexado com sucesso.")

        except Exception as e:  # noqa: BLE001
            stats["erros"] += 1
            print(f"   [ERRO] Falha ao indexar chunk ({modulo}/{topico}): {e}")

    print("\n" + "=" * 60)
    print(f"  RESULTADO DO SEEDING [{schema_name.upper()}]:")
    print(f"  • Total Chunks: {stats['total']}")
    print(f"  • Inseridos: {stats['inseridos']}")
    print(f"  • Atualizados: {stats['atualizados']}")
    print(f"  • Ignorados por CDC (Delta Hash identico): {stats['ignorados_cdc']}")
    print(f"  • Erros: {stats['erros']}")
    print("=" * 60)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Seeding & Indexacao da Base de Auto-Conhecimento e Normas Tecnicas da AURA (pgvector)")
    parser.add_argument("--reindex-all", action="store_true", help="Forca reindexacao total ignorando Delta Hash")
    parser.add_argument("--verify", action="store_true", help="Apenas verifica a tabela e contagem de chunks")
    parser.add_argument("--schema", type=str, default=AURA_CORE_SCHEMA, help="Schema alvo no PostgreSQL (padrao: aura_core)")
    parser.add_argument("--both-schemas", action="store_true", help="Aplica seeding tanto em aura_core quanto em public")
    args = parser.parse_args()

    print("=" * 70)
    print("  AURA META-RAG: SEEDING DA BASE DE AUTO-CONHECIMENTO E NORMAS TECNICAS")
    print("=" * 70)

    try:
        conn_vec = psycopg2.connect(**DB_VECTOR_CONFIG)
        print(f"   [OK] Conectado ao banco Vetorial (posto_ai na porta {DB_VECTOR_CONFIG.get('port', 5433)})")
    except Exception as e:  # noqa: BLE001
        print(f"   [ERRO FATAL] Nao foi possivel conectar ao banco Vetorial ({DB_VECTOR_CONFIG.get('port', 5433)}): {e}")
        sys.exit(1)

    schemas_to_seed = ["aura_core", "public"] if args.both_schemas else [args.schema]

    try:
        for sch in schemas_to_seed:
            if args.verify:
                inicializar_tabela_conhecimento(conn_vec, schema_name=sch)
                with conn_vec.cursor() as cur:
                    cur.execute(f"SELECT count(*), count(embedding) FROM {sch}.aura_conhecimento_vetores;")
                    tot, tot_emb = cur.fetchone()
                    print(f"\n   [VERIFY:{sch}] Total de Chunks: {tot} | Com Embeddings: {tot_emb}")
            else:
                seed_conhecimento(conn_vec, reindex_all=args.reindex_all, schema_name=sch)
    finally:
        conn_vec.close()


if __name__ == "__main__":
    main()
