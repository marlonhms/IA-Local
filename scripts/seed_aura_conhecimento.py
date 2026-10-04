"""
Script de Indexação & Seeding da Base de Auto-Conhecimento e Meta-RAG da AURA
(PostgreSQL 16 + pgvector no Docker na porta 5434).

Funcionalidades:
- Criação e manutenção idempotente da tabela `public.aura_conhecimento_vetores`.
- Geração de vetores halfvec(768) via Google Gemini API (gemini-embedding-001).
- Delta Hashing determinístico (hash_md5) para evitar chamadas redundantes de API (>95% de economia).
- Índices HNSW (ef_construction=128), GIN Full-Text Search (tsvector STORED em português),
  índices b-tree de modulo/tópico e hash_md5.
- População dos 15 chunks atômicos oficiais da arquitetura da AURA.
"""

import os
import sys
import json
import time
import hashlib
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai

# Garante saída UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona o diretório raiz ao path para importações absolutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    GEMINI_API_KEY,
    DB_VECTOR_CONFIG,
    DEFAULT_EMBEDDING_MODEL,
)

# Catálogo canônico dos 15 chunks atômicos oficiais da AURA
CONHECIMENTO_CHUNKS: List[Dict[str, Any]] = [
    {
        "modulo": "cockpit",
        "topico": "panorama_operacional",
        "titulo": "Panorama Operacional do Posto",
        "subtitulo": "Cockpit executivo em tempo real com métricas vitais de pista, tanques e faturamento",
        "conteudo": (
            "O Panorama Operacional é o painel central (Cockpit) da AURA e o guia principal de ajuda executiva do posto. "
            "Ele consolida os KPIs mais críticos em cards de alta densidade visual: faturamento total do dia em tempo real, "
            "volume consolidado vendido em litros, margem média bruta, status consolidado dos tanques de combustíveis, resumo "
            "de pendências de turno e alertas de pista. Foi projetado para dar ao proprietário ou gerente uma visão holística instantânea "
            "de 360 graus da revenda logo ao abrir o sistema."
        ),
        "elementos_ui": {
            "tab": "cockpit",
            "cards": ["kpi_faturamento", "kpi_volume", "kpi_tanques", "kpi_alertas"],
            "tipo": "dashboard"
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "cockpit",
            "label": "Abrir Panorama Operacional"
        },
        "tags": ["cockpit", "panorama", "visao geral", "dashboard", "kpis", "faturamento", "tempo real", "inicio", "ajuda", "ajuda do sistema", "guia", "manual", "telas", "modulos", "sistema", "suporte", "como usar"]
    },
    {
        "modulo": "cockpit",
        "topico": "tanques_ullage",
        "titulo": "Monitoramento de Tanques e Espaço Livre de Descarga (Ullage)",
        "subtitulo": "Medição volumétrica, autonomia em horas e cálculo de descarga em múltiplos de 5.000 L",
        "conteudo": (
            "O módulo de Tanques exibe o volume atual de cada combustível (Gasolina Comum, Gasolina Aditivada, "
            "Etanol, Diesel S10, Diesel S500), capacidade total e percentual de ocupação com mini-gráficos térmicos. "
            "O grande diferencial analítico é o cálculo de Ullage (espaço livre para descarga em múltiplos exatos de "
            "compartimento de caminhão de 5.000 L) e a projeção matemática de run-out (tempo até esgotamento com base no "
            "consumo horário médio L/h), sinalizando com cores verde, amarelo ou vermelho quando um tanque atinge nível crítico "
            "e sugerindo a compra de carretas antecipadamente."
        ),
        "elementos_ui": {
            "tab": "cockpit",
            "componente": "tanques_grid",
            "cards_tanque": ["tq1_gc", "tq2_ga", "tq3_et", "tq4_s10"],
            "metricas": ["volume_litros", "capacidade_litros", "ocupacao_pct", "autonomia_horas", "ullage_5k"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "cockpit",
            "label": "Ver Tanques no Cockpit"
        },
        "tags": ["tanques", "ullage", "combustivel", "gasolina", "diesel", "etanol", "autonomia", "runout", "descarga", "caminhao", "compartimento", "5000l"]
    },
    {
        "modulo": "cockpit",
        "topico": "vazao_bicos_filtro",
        "titulo": "Auditoria de Vazão de Bicos e Alerta de Filtro Obstruído",
        "subtitulo": "Monitoramento de vazão em L/min com detecção automática de bicos lerdos (<30 L/min)",
        "conteudo": (
            "A auditoria de bicos da AURA analisa a vazão instantânea e média de cada bico de abastecimento (em litros por minuto - L/min) "
            "aferida pela automação de pista. Quando a vazão de um bico cai abaixo de 30 L/min (ou discrepante da média da bomba), a AURA emite "
            "imediatamente um alerta preventivo de filtro sujo ou bomba estrangulada. Isso evita filas na pista, reclamações de clientes de bico lerdo "
            "e desgaste prematuro dos blocos medidores."
        ),
        "elementos_ui": {
            "tab": "cockpit",
            "secao": "pista_bicos",
            "metricas": ["bico_id", "combustivel", "vazao_l_min", "status_filtro"],
            "threshold_alerta": 30.0
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "cockpit",
            "label": "Inspecionar Bicos de Abastecimento"
        },
        "tags": ["bicos", "vazao", "litros por minuto", "l min", "filtro", "filtro sujo", "filtro obstruido", "bico lento", "bico lerdo", "bomba", "pista"]
    },
    {
        "modulo": "cockpit",
        "topico": "desempenho_frentistas",
        "titulo": "Desempenho da Equipe de Pista e Conversão de Aditivada",
        "subtitulo": "Ranking de frentistas, ticket médio, volume faturado e percentual de conversão de gasolina aditivada",
        "conteudo": (
            "Exibe o ranking de produtividade da equipe de pista em tempo real. Avalia faturamento total por operador, volume físico abastecido, "
            "ticket médio e a taxa de conversão de Gasolina Aditivada (meta recomendada: 25% a 30% sobre o total de gasolina). Permite ao gestor "
            "identificar frentistas de alto rendimento, premiar a equipe, calibrar comissões e identificar operadores que necessitam de treinamento "
            "em abordagem e vendas adicionais de aditivos e lubrificantes."
        ),
        "elementos_ui": {
            "tab": "cockpit",
            "secao": "ranking_frentistas",
            "colunas": ["matricula", "nome", "faturamento", "volume_l", "conversao_aditivada_pct", "ticket_medio"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "cockpit",
            "label": "Ver Ranking de Frentistas"
        },
        "tags": ["frentistas", "ranking", "aditivada", "conversao", "ticket medio", "equipe", "produtividade", "operadores", "comissao"]
    },
    {
        "modulo": "conciliacao",
        "topico": "cbc04_vs_pdv",
        "titulo": "Triangulação Automação CBC04 vs Vendas Fiscais PDV",
        "subtitulo": "Confronto milimétrico entre pulsos de encerrantes da automação Companytec e cupons NFC-e/SAT",
        "conteudo": (
            "A AURA cruza diretamente os dados de abastecimentos registrados pelo concentrador de pista Companytec CBC04 com os cupons fiscais "
            "emitidos pelo sistema de PDV no ERP. Essa triangulação identifica imediatamente abastecimentos não faturados na pista, frentistas "
            "que liberaram bico sem emitir cupom, abastecimentos cancelados indevidamente ou divergências de encerrantes, prevenindo perdas financeiras "
            "e furos ocultos antes do fechamento do caixa."
        ),
        "elementos_ui": {
            "tab": "triggers",
            "ferramenta": "conciliacao_turno",
            "filtros": ["data", "turno", "bico"],
            "comparativo": ["volume_cbc04", "volume_pdv", "delta_litros", "delta_reais"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Auditar Automação CBC04 vs PDV"
        },
        "tags": ["cbc04", "companytec", "pdv", "automacao", "fiscal", "encerrante", "triangulacao", "furo", "cupom fiscal", "abastecimento pendente"]
    },
    {
        "modulo": "conciliacao",
        "topico": "auditoria_turno",
        "titulo": "Auditoria de Fechamento de Turno e Quebra de Caixa",
        "subtitulo": "Conferência do 1º, 2º e 3º turno: batimento de dinheiro, cartão, PIX, faturado e encerrantes",
        "conteudo": (
            "Ferramenta analítica que audita os fechamentos dos turnos (1º Turno Manhã, 2º Turno Tarde e 3º Turno Noite/Madrugada). Cruza o volume medido "
            "nos encerrantes das bombas com o faturamento declarado no caixa por forma de pagamento (Dinheiro, Cartão Débito/Crédito, PIX, Faturado e Vale). "
            "Calcula o score de conformidade do turno, aponta sobras ou faltas de caixa (quebras) e especifica exatamente se a divergência ocorreu na pista física "
            "ou no lançamento do caixa."
        ),
        "elementos_ui": {
            "tab": "triggers",
            "ferramenta": "auditoria_turno",
            "cards": ["score_conformidade", "triangulacao_caixa", "triangulacao_pista", "quebra_caixa"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Conferir Fechamento de Turno"
        },
        "tags": ["fechamento de turno", "conciliacao", "turno", "caixa", "quebra de caixa", "furo", "sobra", "falta", "1 turno", "2 turno", "3 turno", "pix", "cartao"]
    },
    {
        "modulo": "fiscal",
        "topico": "lmc_anp",
        "titulo": "Livro de Movimentação de Combustíveis (LMC Oficial ANP)",
        "subtitulo": "Auditoria estrita da Portaria ANP 26/1992, perdas e ganhos térmicos com teto de ±0,6%",
        "conteudo": (
            "Gera e audita o Livro de Movimentação de Combustíveis (LMC) exigido pela ANP conforme Portaria 26/1992. O motor calcula o balanço diário por tanque "
            "e combustível: Estoque de Abertura + Recebimentos (Descargas) - Vendas Faturadas = Fechamento Escriturado. Em seguida, compara com a Medição Física da régua/telemetria "
            "para apurar a Variação Volumétrica (Δ Litros e Δ %). Se a variação ultrapassar o limite regulamentar estrito de ±0,6%, a AURA aciona alerta vermelho fiscal de inconformidade "
            "para investigação imediata de perda térmica, calibração ou vazamento."
        ),
        "elementos_ui": {
            "tab": "triggers",
            "ferramenta": "lmc_anp",
            "tabela": "balanco_lmc",
            "campos": ["abertura", "recebimento", "vendas", "escriturado", "fisico", "variacao_litros", "variacao_pct", "status_anp"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Abrir Relatório LMC ANP"
        },
        "tags": ["lmc", "anp", "portaria 26", "livro de movimentacao", "tolerancia anp", "0.6%", "perda termica", "ganho termico", "estoque escriturado", "medicao fisica", "fiscal"]
    },
    {
        "modulo": "conveniencia",
        "topico": "market_basket_combos",
        "titulo": "Inteligência de Vendas Cruzadas e Market Basket Analysis (Apriori)",
        "subtitulo": "Mineração de regras de associação na conveniência, cálculo de Lift, Suporte e combos para o PDV",
        "conteudo": (
            "Aplica algoritmos de associação de mercado (Market Basket Analysis / Apriori) sobre o histórico de cupons fiscais da loja de conveniência. Identifica produtos frequentemente "
            "adquiridos em conjunto (ex: Cerveja + Carvão + Gelo, Café Expresso + Pão de Queijo, Energético + Salgadinho). Para cada par ou trio, calcula as métricas de Suporte, Confiança e Lift (> 1.2), "
            "sugerindo scripts de vendas assertivos para operadores de caixa oferecerem no balcão e organizando o merchandising físico das prateleiras para maximizar o ticket médio."
        ),
        "elementos_ui": {
            "tab": "triggers",
            "ferramenta": "conveniencia_vendas_cruzadas",
            "cards_combos": ["combo_titulo", "itens", "lift", "confianca", "ticket_estimado", "script_balcao"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Ver Combos da Conveniência"
        },
        "tags": ["conveniencia", "combos", "cross-sell", "vendas cruzadas", "market basket", "apriori", "lift", "loja", "pdv", "cerveja", "cafe", "ticket medio"]
    },
    {
        "modulo": "triggers",
        "topico": "radar_acoes_rapidas",
        "titulo": "Radar de Ações Rápidas e Gatilhos Analíticos de 1-Clique",
        "subtitulo": "Grid tático de botões prontos para disparar auditorias operacionais instantâneas sem digitação",
        "conteudo": (
            "A aba de Ações Rápidas (Triggers) reúne um grid categorizado de botões de execução instantânea. Com apenas um clique, o gestor dispara qualquer auditoria complexa sem precisar redigir mensagens "
            "ou lembrar comandos: 'Autonomia dos Tanques', 'Conferir Turno Hoje', 'LMC ANP Oficial', 'Combos de Conveniência', 'Vazão dos Bicos', 'Top Clientes' e 'Saúde do Banco de Dados'. Possui filtros rápidos "
            "por categoria (Todos, Combustíveis, Caixa, Pista, Loja) e sincroniza a resposta diretamente no inspetor ou chat."
        ),
        "elementos_ui": {
            "tab": "triggers",
            "filtros": ["todos", "combustiveis", "caixa", "pista", "loja"],
            "grid_acoes": ["btn_tanques", "btn_turno", "btn_lmc", "btn_combos", "btn_bicos", "btn_clientes", "btn_sre"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Abrir Ações Rápidas"
        },
        "tags": ["acoes rapidas", "gatilhos", "triggers", "botoes", "1 clique", "atalhos", "auditorias rapidas", "executar", "grid"]
    },
    {
        "modulo": "triggers",
        "topico": "inspetor_duplo",
        "titulo": "Inspetor Duplo: Visualização Formatada vs JSON Bruto",
        "subtitulo": "Detalhamento analítico em dois formatos com botão de cópia de payload e envio para a AURA",
        "conteudo": (
            "O Inspetor Duplo localiza-se na aba de Gatilhos e exibe o resultado minucioso de qualquer ferramenta executada. Ele possui duas abas de inspeção: 'Visualização Formatada' (cards executivos com tabelas, "
            "percentuais, badges e destaques amigáveis) e 'JSON Técnico' (o payload estruturado completo retornado pelo ERP/PostgreSQL). Inclui botões utilitários para 'Copiar JSON' diretamente para a área de transferência "
            "e 'Enviar para a AURA' para tirar dúvidas cognitivas sobre os dados apurados."
        ),
        "elementos_ui": {
            "tab": "triggers",
            "container": "inspector-dual-panel",
            "abas": ["tab-inspector-formatted", "tab-inspector-json"],
            "acoes": ["btn-copy-json", "btn-send-to-aura"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "triggers",
            "label": "Ver Inspetor de Gatilhos"
        },
        "tags": ["inspetor", "inspetor duplo", "json", "formatado", "detalhes", "copiar json", "enviar aura", "payload", "depuracao", "conferencia"]
    },
    {
        "modulo": "console",
        "topico": "chat_assistente",
        "titulo": "Console Cognitivo da AURA: Chat Executivo e Streaming",
        "subtitulo": "Interface de diálogo executivo em linguagem natural, streaming token-a-token e síntese sob demanda",
        "conteudo": (
            "O Console Cognitivo é a interface de conversa principal da AURA. Permite ao usuário fazer perguntas livres sobre o posto ('Qual tanque acaba primeiro?', 'O turno 1 bateu?', 'Quanto custa a Heineken?'). "
            "Possui streaming de respostas token-a-token via SSE, identificação visual de intenções (Chips coloridos), cards interativos de ferramentas analíticas, badge de telemetria SRE com tempo de resposta em milissegundos "
            "e histórico de sessão multi-turn durável."
        ),
        "elementos_ui": {
            "tab": "console",
            "feed": "chat-feed-container",
            "input": "chat-input-text",
            "botoes": ["btn-chat-send", "btn-chat-stop", "btn-chat-clear"]
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "console",
            "label": "Abrir Console Cognitivo"
        },
        "tags": ["chat", "console", "assistente", "conversa", "streaming", "perguntas", "linguagem natural", "sessao", "comandos", "dialogo", "duvidas", "ajuda cognitiva"]
    },
    {
        "modulo": "split",
        "topico": "visao_split",
        "titulo": "Visão Integrada Split: Cockpit e Chat Bipartidos Lado a Lado",
        "subtitulo": "Layout bipartido simultâneo com painel operacional à esquerda e chat executivo à direita",
        "conteudo": (
            "A Visão Split divide a tela em duas colunas sincronizadas em tempo real. No lado esquerdo, mantém o Panorama Operacional visível com mini-tanques, faturamento e alertas em monitoramento contínuo. "
            "No lado direito, oferece uma janela dedicada do Console Cognitivo para dialogar com a AURA. Permite gerenciar a pista e fazer diagnósticos simultâneos sem perder a visibilidade dos indicadores-chave "
            "de desempenho, ideal para telas de desktop, monitores widescreen e tablets de retaguarda."
        ),
        "elementos_ui": {
            "tab": "split",
            "layout": "grid-split-screen",
            "painel_esquerdo": "split-cockpit-sidebar",
            "painel_direito": "split-chat-container"
        },
        "ui_action": {
            "action": "switch_tab",
            "target": "split",
            "label": "Ativar Visão Integrada Split"
        },
        "tags": ["split", "visao dividida", "lado a lado", "bipartido", "multitarefa", "cockpit e chat", "tela dupla", "monitor"]
    },
    {
        "modulo": "navegacao",
        "topico": "menu_hamburguer_liquid_glass",
        "titulo": "Menu Lateral Hambúrguer em Design Acrílico Liquid Glass",
        "subtitulo": "Gaveta deslizante com blur fosco, atalhos executivos, controle de som e alternância de módulos",
        "conteudo": (
            "O Menu Hambúrguer é acessível pelo botão de menu com três barras no topo esquerdo do cabeçalho ou deslizando a tela. Possui acabamento moderno 'Liquid Glass' em vidro fosco acrílico com desfoque de fundo (backdrop-blur). "
            "Reúne atalhos rápidos para alternar entre as 4 abas (Console Cognitivo, Panorama Cockpit, Gatilhos Analíticos e Visão Split), perguntas frequentes prontas de 1-toque, acionamento da Command Palette (Ctrl+K), "
            "controle de áudio sensorial e limpeza de sessão."
        ),
        "elementos_ui": {
            "botao_trigger": "btn-toggle-sidebar",
            "drawer": "aura-sidebar-drawer",
            "overlay": "aura-sidebar-overlay",
            "estilo": "liquid-glass-acrylic"
        },
        "ui_action": {
            "action": "open_sidebar",
            "target": "sidebar",
            "label": "Abrir Menu Lateral Hambúrguer"
        },
        "tags": ["menu", "menu lateral", "hamburguer", "liquid glass", "gaveta", "drawer", "navegacao", "atalhos", "acrilico", "design", "painel lateral"]
    },
    {
        "modulo": "navegacao",
        "topico": "command_palette_ctrl_k",
        "titulo": "Command Palette Global e Navegação Rápida (Atalho Ctrl+K)",
        "subtitulo": "Buscador instantâneo flutuante para comandos, relatórios, telas e atalhos do posto",
        "conteudo": (
            "A Command Palette é o centro de comando rápido da AURA. Pode ser acionada a qualquer momento pressionando o atalho de teclado 'Ctrl + K' ou clicando no botão de busca rápida. "
            "Permite buscar instantaneamente comandos operacionais, trocar de aba, executar diagnósticos de tanques, abrir LMC ou acionar o chat sem tirar as mãos do teclado. A pesquisa conta com "
            "filtragem em tempo real e destaque visual das opções disponíveis."
        ),
        "elementos_ui": {
            "atalho_teclado": "Ctrl+K",
            "botao": "btn-open-palette",
            "modal": "aura-command-palette-modal",
            "input_busca": "palette-search-input"
        },
        "ui_action": {
            "action": "open_command_palette",
            "target": "palette",
            "label": "Pressione Ctrl+K ou Abrir Paleta"
        },
        "tags": ["ctrl+k", "ctrl k", "command palette", "paleta de comandos", "busca rapida", "atalho de teclado", "navegacao rapida", "comandos", "atalho", "atalhos"]
    },
    {
        "modulo": "acessibilidade",
        "topico": "feedback_sensorial_audio",
        "titulo": "Feedback Sensorial e Sons Táticos (Web Audio API)",
        "subtitulo": "Chimes discretos em ondas senoidais sintetizadas para confirmação de ações sem poluição sonora",
        "conteudo": (
            "O sistema de feedback sonoro da AURA utiliza a Web Audio API nativa do navegador para sintetizar ondas sonoras sutis e elegantes (chimes senoidais entre 500Hz e 800Hz) ao executar cliques, "
            "alternar abas, receber mensagens e concluir auditorias. Vem em modo discreto (mudo) por padrão para ambientes de trabalho e pode ser ativado a qualquer momento pelo botão de alto-falante "
            "no cabeçalho ou no menu lateral. Garante confirmação tátil e sensorial sem necessidade de carregar arquivos de áudio pesados."
        ),
        "elementos_ui": {
            "componente": "window.auraAudio",
            "botao_header": "btn-toggle-sfx",
            "botao_drawer": "sidebar-btn-toggle-sfx",
            "frequencias_hz": [500, 600, 660, 700, 800]
        },
        "ui_action": {
            "action": "toggle_audio",
            "target": "audio",
            "label": "Ativar/Desativar Sons Táticos"
        },
        "tags": ["audio", "som", "sfx", "sons", "chime", "web audio api", "feedback sensorial", "mudo", "efeito sonoro", "acessibilidade", "volume", "mutar", "desmutar"]
    }
]


def calcular_hash_conhecimento(
    modulo: str,
    topico: str,
    titulo: str,
    subtitulo: str,
    conteudo: str,
    elementos_ui: Dict[str, Any],
    ui_action: Dict[str, Any],
    tags: List[str]
) -> str:
    """Calcula hash determinístico MD5 para Change Data Capture (CDC) no banco vetorial."""
    el_str = json.dumps(elementos_ui or {}, sort_keys=True)
    act_str = json.dumps(ui_action or {}, sort_keys=True)
    tags_str = ",".join(sorted(tags or []))
    payload = f"{modulo.strip()}|{topico.strip()}|{titulo.strip()}|{subtitulo.strip()}|{conteudo.strip()}|{el_str}|{act_str}|{tags_str}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def inicializar_tabela_conhecimento(conn_vec):
    """Garante a existência da tabela aura_conhecimento_vetores, tsvector e índices HNSW/GIN."""
    with conn_vec.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Função auxiliar immutable para permitir uso de array_to_string no tsvector STORED
        cur.execute("""
            CREATE OR REPLACE FUNCTION public.immutable_array_to_string(arr text[], sep text)
            RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE
            RETURN array_to_string(arr, sep);
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.aura_conhecimento_vetores (
                id SERIAL PRIMARY KEY,
                modulo VARCHAR(50) NOT NULL,
                topico VARCHAR(100) NOT NULL,
                titulo VARCHAR(150) NOT NULL,
                subtitulo VARCHAR(255),
                conteudo TEXT NOT NULL,
                elementos_ui JSONB,
                ui_action JSONB,
                tags TEXT[],
                embedding halfvec(768),
                hash_md5 VARCHAR(32),
                atualizado_em TIMESTAMP DEFAULT NOW(),
                tsv tsvector GENERATED ALWAYS AS (
                    to_tsvector('portuguese'::regconfig,
                        coalesce(titulo, '') || ' ' ||
                        coalesce(subtitulo, '') || ' ' ||
                        coalesce(modulo, '') || ' ' ||
                        coalesce(topico, '') || ' ' ||
                        coalesce(conteudo, '') || ' ' ||
                        coalesce(public.immutable_array_to_string(tags, ' '), '')
                    )
                ) STORED,
                CONSTRAINT uq_aura_conhecimento_modulo_topico UNIQUE (modulo, topico)
            );
        """)

        # Índices HNSW, GIN FTS, B-Trees
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_aura_conhecimento_hnsw 
            ON public.aura_conhecimento_vetores USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 128);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_aura_conhecimento_tsv_gin 
            ON public.aura_conhecimento_vetores USING gin (tsv);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_aura_conhecimento_modulo_topico 
            ON public.aura_conhecimento_vetores (modulo, topico);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_aura_conhecimento_hash_md5 
            ON public.aura_conhecimento_vetores (hash_md5);
        """)

        conn_vec.commit()
    print("   [OK] Tabela 'aura_conhecimento_vetores' e índices HNSW + GIN + BTree verificados.")


def seed_conhecimento(conn_vec, reindex_all: bool = False) -> Dict[str, int]:
    """
    Popula os chunks oficiais da AURA utilizando Delta Hashing (hash_md5).
    Soma zero chamadas de API se o conteúdo não mudou.
    """
    inicializar_tabela_conhecimento(conn_vec)

    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)

    # Carrega estado existente da tabela
    existing_records: Dict[str, Dict[str, Any]] = {}
    with conn_vec.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, modulo, topico, hash_md5, (embedding IS NOT NULL) AS has_embedding
            FROM public.aura_conhecimento_vetores;
        """)
        for row in cur.fetchall():
            key = f"{row['modulo']}|{row['topico']}"
            existing_records[key] = dict(row)

    stats = {
        "total": len(CONHECIMENTO_CHUNKS),
        "inseridos": 0,
        "atualizados": 0,
        "ignorados_cdc": 0,
        "erros": 0
    }

    print(f"\n2. Analisando {stats['total']} chunks de auto-conhecimento para seeding...")

    for chunk in CONHECIMENTO_CHUNKS:
        modulo = chunk["modulo"]
        topico = chunk["topico"]
        titulo = chunk["titulo"]
        subtitulo = chunk.get("subtitulo", "")
        conteudo = chunk["conteudo"]
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
            tags=tags
        )

        key = f"{modulo}|{topico}"
        existing = existing_records.get(key)

        # Delta check
        if existing and not reindex_all:
            if existing.get("hash_md5") == h_calc and existing.get("has_embedding"):
                stats["ignorados_cdc"] += 1
                continue

        # Precisa gerar embedding
        texto_embedding = (
            f"Módulo: {modulo} | Tópico: {topico} | Título: {titulo}\n"
            f"Subtítulo: {subtitulo}\n"
            f"Conteúdo: {conteudo}\n"
            f"Tags: {', '.join(tags)}"
        )

        try:
            res_emb = genai.embed_content(
                model=DEFAULT_EMBEDDING_MODEL,
                content=texto_embedding,
                output_dimensionality=768,
                task_type="retrieval_document"
            )
            embedding_vector = res_emb["embedding"]
            vec_str = str(embedding_vector)

            with conn_vec.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.aura_conhecimento_vetores (
                        modulo, topico, titulo, subtitulo, conteudo, elementos_ui, ui_action, tags,
                        embedding, hash_md5, atualizado_em
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::halfvec, %s, NOW())
                    ON CONFLICT (modulo, topico) DO UPDATE SET
                        titulo = EXCLUDED.titulo,
                        subtitulo = EXCLUDED.subtitulo,
                        conteudo = EXCLUDED.conteudo,
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
                    json.dumps(elementos_ui, ensure_ascii=False),
                    json.dumps(ui_action, ensure_ascii=False),
                    tags,
                    vec_str,
                    h_calc
                ))
                conn_vec.commit()

            if existing:
                stats["atualizados"] += 1
                print(f"   [UPDATE] ({modulo}/{topico}) '{titulo}' atualizado com novo hash.")
            else:
                stats["inseridos"] += 1
                print(f"   [INSERT] ({modulo}/{topico}) '{titulo}' indexado com sucesso.")

        except Exception as e:
            stats["erros"] += 1
            print(f"   [ERRO] Falha ao indexar chunk ({modulo}/{topico}): {e}")

    print("\n" + "=" * 60)
    print("  RESULTADO DO SEEDING DE AUTO-CONHECIMENTO:")
    print(f"  • Total Chunks: {stats['total']}")
    print(f"  • Inseridos: {stats['inseridos']}")
    print(f"  • Atualizados: {stats['atualizados']}")
    print(f"  • Ignorados por CDC (Delta Hash idêntico): {stats['ignorados_cdc']}")
    print(f"  • Erros: {stats['erros']}")
    print("=" * 60)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Seeding & Indexação da Base de Auto-Conhecimento da AURA (pgvector)")
    parser.add_argument("--reindex-all", action="store_true", help="Força reindexação total ignorando Delta Hash")
    parser.add_argument("--verify", action="store_true", help="Apenas verifica a tabela e contagem de chunks")
    args = parser.parse_args()

    print("=" * 70)
    print("  AURA META-RAG: SEEDING DA BASE DE AUTO-CONHECIMENTO (POSTGRESQL 16)")
    print("=" * 70)

    try:
        conn_vec = psycopg2.connect(**DB_VECTOR_CONFIG)
        print(f"   [OK] Conectado ao banco Vetorial (posto_ai na porta {DB_VECTOR_CONFIG.get('port', 5434)})")
    except Exception as e:
        print(f"   [ERRO FATAL] Não foi possível conectar ao banco Vetorial (5434): {e}")
        sys.exit(1)

    try:
        if args.verify:
            inicializar_tabela_conhecimento(conn_vec)
            with conn_vec.cursor() as cur:
                cur.execute("SELECT count(*), count(embedding) FROM public.aura_conhecimento_vetores;")
                tot, tot_emb = cur.fetchone()
                print(f"\n   [VERIFY] Total de Chunks: {tot} | Com Embeddings: {tot_emb}")
        else:
            seed_conhecimento(conn_vec, reindex_all=args.reindex_all)
    finally:
        conn_vec.close()


if __name__ == "__main__":
    main()
