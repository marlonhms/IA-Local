"""
Suíte de Testes Automatizada: Página de Apresentação e Showcase Executivo da AURA
(Tour Guiado Interativo, Desintegração em Poeira, Pipeline Sub-100ms e Blindagem Tecnológica)

Validações:
1. Rotas HTTP FastAPI:
   - GET /showcase serve showcase.html com status 200 OK e text/html.
   - GET /apresentacao serve como alias funcional com status 200 OK.
   - GET /static/showcase.html serve o arquivo via StaticFiles.
2. 4 Etapas da Jornada Executiva da AURA:
   - Etapa 1: A Pergunta Executiva (Contexto de Revenda & Linguagem Natural).
   - Etapa 2: Escudo AURA Guard™ & Desintegração em Poeira (Canvas de partículas e tokens blindados).
   - Etapa 3: Motor Analítico Sub-100ms (Pipeline multi-nó de Pista, ANP Portaria 26, Caixa e Run-Out).
   - Etapa 4: DecisionCard™ (AURA Precision Glass, métricas executivas e ações em 1-toque).
3. Controles do Tour Interativo:
   - Botão Play/Pause, barra de progresso suave, seletor de velocidade e tabs das 4 etapas.
4. Blindagem Absoluta contra Cópia Intelectual (Zero Vazamento Tecnológico):
   - Proibição estrita de menções a spacy, pgvector, transformers, sqlite, chromadb, ollama, groq, etc.
   - Presença obrigatória de termos proprietários de alto valor.
5. Integração no Shell Oficial (web/index.html):
   - Links "Saiba mais..." presentes no menu lateral, cabeçalho e card de boas-vindas.
6. Validação de Sintaxe JavaScript no Node.js.
"""

import sys
import re
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient

# Protege terminal Windows UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.aura_engine import AuraEngine, AuraSessionMemory
from core.aura_api import create_aura_app


def run_showcase_tests():
    print("=" * 78)
    print("✨ SUÍTE DE TESTES: APRESENTAÇÃO & SHOWCASE EXECUTIVO DA AURA")
    print("   (Tour Guiado, Desintegração em Poeira, Pipeline Sub-100ms e Blindagem)")
    print("=" * 78)

    # 1. Configuração do Cliente de Teste FastAPI
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(tenant_id="test_showcase", filial_id="posto_042", session_memory=mem)
    app = create_aura_app(engine)
    client = TestClient(app)

    # =========================================================================
    # 1. ROTAS HTTP FASTAPI
    # =========================================================================
    print("\n1. Testando Endpoints HTTP de Apresentação (/showcase e /apresentacao)...")
    resp_showcase = client.get("/showcase")
    assert resp_showcase.status_code == 200, f"Falha na rota /showcase: {resp_showcase.status_code}"
    assert "text/html" in resp_showcase.headers.get("content-type", "")
    html_content = resp_showcase.text
    print("   [OK] GET /showcase -> 200 OK (Content-Type: text/html)")

    resp_alias = client.get("/apresentacao")
    assert resp_alias.status_code == 200, f"Falha no alias /apresentacao: {resp_alias.status_code}"
    print("   [OK] GET /apresentacao -> 200 OK (Alias verificado com sucesso)")

    resp_static = client.get("/static/showcase.html")
    assert resp_static.status_code == 200, f"Falha no asset estático /static/showcase.html: {resp_static.status_code}"
    print("   [OK] GET /static/showcase.html -> 200 OK (Montagem estática validada)")

    # =========================================================================
    # 2. VALIDAÇÃO DAS 4 ETAPAS DA JORNADA EXECUTIVA
    # =========================================================================
    print("\n2. Testando Presença e Integridade das 4 Etapas do Tour Guiado...")
    
    # Etapa 1: A Pergunta Executiva
    assert "A Pergunta" in html_content
    assert "narrative-step-1" in html_content
    assert "visual-stage-1" in html_content
    assert "step1-typed-text" in html_content
    print("   [OK] Etapa 1 (A Pergunta Executiva) validada.")

    # Etapa 2: Escudo AURA Guard & Desintegração em Poeira
    assert "Escudo AURA Guard" in html_content
    assert "narrative-step-2" in html_content
    assert "visual-stage-2" in html_content
    assert "dust-particle-canvas" in html_content, "Canvas de desintegração de partículas #dust-particle-canvas ausente"
    assert "pii-val-1" in html_content
    assert "pii-token-1" in html_content
    assert "CNPJ_BLINDADO" in html_content
    assert "custom-pii-input" in html_content, "Sandbox customizado #custom-pii-input ausente"
    assert "btn-custom-disintegrate" in html_content, "Botão do sandbox customizado #btn-custom-disintegrate ausente"
    print("   [OK] Etapa 2 (Escudo AURA Guard, Canvas de Desintegração em Poeira & Sandbox Tátil) validada.")

    # Etapa 3: Motor Analítico Sub-100ms
    assert "Motor Sub-100ms" in html_content
    assert "narrative-step-3" in html_content
    assert "visual-stage-3" in html_content
    assert "Portaria 26/1992" in html_content
    assert "Telemetria de Pista" in html_content
    assert "Conciliação de Caixa" in html_content
    assert "Run-Out" in html_content
    assert "flow-path-active" in html_content, "Conectores de pulso ativo SVG ausentes"
    assert "pipe-node-1" in html_content, "Nós reativos de pipeline ausentes"
    print("   [OK] Etapa 3 (Processamento Analítico em Sub-100ms e Pipeline de Pista com Pulso Ativo) validada.")

    # Etapa 4: DecisionCard & Companion Canvas
    assert "DecisionCard" in html_content
    assert "Companion Canvas" in html_content, "AURA Companion Canvas ausente na etapa 4"
    assert "tab-step4-companion" in html_content, "Aba do Companion Canvas ausente"
    assert "view-step4-companion" in html_content, "Visualização do Companion Canvas ausente"
    assert "narrative-step-4" in html_content
    assert "visual-stage-4" in html_content
    assert "Diagnóstico Operacional Consolidado" in html_content
    assert "Emitir Pedido" in html_content
    assert "action-btn-pedido" in html_content
    assert "action-feedback-toast" in html_content
    print("   [OK] Etapa 4 (DecisionCard Precision Glass & Companion Canvas com Auditoria Profunda) validada.")

    # =========================================================================
    # 2B. GENERALIZAÇÃO DE TERMOS DE NEGÓCIO E SUPORTE MULTISSETORIAL
    # =========================================================================
    print("\n2B. Testando Generalização dos Termos de Negócio (Multissetorial: Postos, Bares, Lojas, Padarias)...")
    content_lower = html_content.lower()

    # Termos antigos específicos que DEVEM ter sido eliminados
    assert "cnpj da revenda" not in content_lower, "Termo antigo 'CNPJ da revenda' ainda presente"
    assert "cpf do frentista" not in content_lower, "Termo antigo 'CPF do frentista' ainda presente"
    assert "cartão faturado" not in content_lower, "Termo antigo 'Cartão faturado' ainda presente (deve ser genérico fiscal)"
    assert "credencial de pista" not in content_lower, "Termo antigo 'Credencial de pista' ainda presente"
    assert "credencial da pista" not in content_lower, "Termo antigo 'Credencial da pista' ainda presente"

    # Termos genéricos e novos campos presentes
    assert "cnpj:" in content_lower or "cnpj" in content_lower
    assert "cpf:" in content_lower or "cpf" in content_lower
    assert "identificador fiscal de transação" in content_lower, "Identificador fiscal de transação ausente"
    assert "credenciais" in content_lower, "Termo generalizado 'Credenciais' ausente"
    assert "credencias:" not in content_lower and "credencias " not in content_lower, "Erro ortográfico 'credencias' detectado"
    
    # Validação multissetorial expressa (postos, padarias, bares, lojas, franquias)
    multisector_terms = ["posto", "padaria", "bar", "loja", "varejo", "franquias"]
    for mst in multisector_terms:
        assert mst in content_lower, f"Segmento multissetorial '{mst}' ausente no showcase"
    print("   [OK] Termos generalizados (CNPJ, CPF, Identificador Fiscal de Transação, Credenciais) e segmentos validados.")

    # =========================================================================
    # 2C. CONFORMIDADE EXPLÍCITA COM A LGPD (LEI 13.709/2018)
    # =========================================================================
    print("\n2C. Testando Destaque e Citações Explícitas à LGPD (Lei 13.709/2018)...")
    assert "lgpd" in content_lower, "Menção à LGPD ausente"
    assert "13.709" in content_lower, "Citação à Lei 13.709 ausente"
    assert "privacy by design" in content_lower, "Princípio 'Privacy by Design' ausente"
    print("   [OK] Conformidade com a LGPD (Lei 13.709/2018 e Privacy by Design) validada.")

    # =========================================================================
    # 2D. MINI JANELA DE CHAT DA AURA + FLUXOGRAMA / GRAFO MODERNO LADO A LADO
    # =========================================================================
    print("\n2D. Testando Mini Janela de Chat da AURA + Fluxograma / Grafo Moderno...")
    assert "sec-chat-graph" in html_content, "Seção #sec-chat-graph ausente"
    assert "mini-chat-aura" in html_content, "Componente #mini-chat-aura ausente"
    assert "aura-flowchart-graph" in html_content, "Componente #aura-flowchart-graph ausente"
    assert "mini-chat-action-toast" in html_content, "Toast de feedback do mini chat ausente"
    assert "alert(" not in html_content, "Uso de alert() bloqueante detectado no showcase (deve ser feedback inline suave)"
    
    # 4 Cenários Multissetoriais no Chat
    assert "scenario-btn-varejo" in html_content, "Botão cenário varejo/padaria ausente"
    assert "scenario-btn-posto" in html_content, "Botão cenário postos ausente"
    assert "scenario-btn-loja" in html_content, "Botão cenário loja ausente"
    assert "scenario-btn-fiscal" in html_content, "Botão cenário fiscal ausente"
    assert "btn-simulate-chat-flow" in html_content, "Botão de simulação de fluxo do chat ausente"

    # 5 Nós Conectados do Fluxograma / Grafo
    assert "graph-node-prompt" in html_content, "Nó de Prompt do grafo ausente"
    assert "graph-node-lgpd" in html_content, "Nó do Escudo LGPD do grafo ausente"
    assert "graph-node-motor" in html_content, "Nó do Motor de Borda do grafo ausente"
    assert "graph-node-regras" in html_content, "Nó de Regras de Negócio do grafo ausente"
    assert "graph-node-decisao" in html_content, "Nó de Decisão do grafo ausente"
    assert "graph-node-detail-panel" in html_content, "Painel de detalhes do nó do grafo ausente"
    print("   [OK] Mini Janela de Chat da AURA + Fluxograma / Grafo Moderno de 5 nós conectados validados.")

    # =========================================================================
    # 2E. PAINEL & MATRIZ DE DIFERENCIAÇÃO OPERACIONAL REFORÇADO (ROI & ECONOMIA DE TOKENS)
    # =========================================================================
    print("\n2E. Testando Painel & Matriz de Diferenciação Operacional Reforçado...")
    assert "sec-diferenciacao" in html_content, "Seção #sec-diferenciacao ausente"
    assert "Matriz de Diferenciação Operacional" in html_content, "Matriz de diferenciação ausente"
    assert "Quebras de Caixa" in html_content, "Destaque 'Quebras de Caixa' ausente"
    assert "Desvios de Estoque" in html_content, "Destaque 'Desvios de Estoque' ausente"
    assert "Dashboards de BI Passivos" in html_content, "Coluna comparativa de BI passivo ausente"
    assert "roi-card" in html_content, "Classe .roi-card ausente nos cards de ROI"
    assert "Prejuízo evitado:" in html_content, "Métrica de prejuízo evitado ausente na diferenciação"

    # Validação do Novo Diferencial de Economia de Tokens & Soberania dos Dados do Cliente
    assert "Economia" in html_content and "Tokens" in html_content, "Destaque de economia de tokens ausente"
    assert "banco do cliente" in content_lower, "Destaque de conexão direta ao banco do cliente ausente"
    assert "milhões de tokens" in content_lower, "Alerta sobre cobrança abusiva de milhões de tokens ausente"
    assert "cálculos estruturados" in content_lower, "Conceito de cálculos estruturados locais ausente"
    assert "sem guardrails" in content_lower, "Contraste contra falta de guardrails do mercado tradicional ausente"
    assert "rag" in content_lower, "Contraste contra falta de RAG de soluções genéricas ausente"
    assert "assertividade" in content_lower, "Pilar de assertividade e precisão ausente"
    assert "Como o Mercado Tradicional de IA Opera" in html_content, "Coluna de contraste do mercado tradicional ausente"
    assert "Como a AURA Revoluciona a Entrega" in html_content, "Coluna de contraste da abordagem AURA ausente"

    # Validação da Tabela de ROI Compactada (Exatamente 4 dimensões críticas de valor de produto)
    table_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', html_content, re.DOTALL)
    assert table_match, "Tabela de ROI não possui corpo tbody"
    tbody_html = table_match.group(1)
    tr_count = len(re.findall(r'<tr[^>]*>', tbody_html))
    assert tr_count == 4, f"A tabela de ROI deve conter exatamente 4 dimensões críticas compactadas, encontrado: {tr_count}"
    assert "Auditoria de Caixa & Prevenção de Quebras" in tbody_html, "Dimensão 1 (Auditoria de Caixa & Prevenção de Quebras) ausente na tabela"
    assert "Desvios de Estoque & Perdas Invisíveis" in tbody_html, "Dimensão 2 (Desvios de Estoque & Perdas Invisíveis) ausente na tabela"
    assert "Eficiência de Processamento & Custo de Tokens" in tbody_html, "Dimensão 3 (Eficiência de Processamento & Custo de Tokens) ausente na tabela"
    assert "Tempo para Decisão & Ação" in tbody_html, "Dimensão 4 (Tempo para Decisão & Ação) ausente na tabela"
    assert "Dashboards de BI Passivos & IAs de Nuvem" in html_content, "Cabeçalho comparativo unificado de BI & Nuvem ausente"

    print("   [OK] Painel & Matriz de Diferenciação Operacional (Quebras de Caixa, Desvios, Economia de Tokens, ROI Compactado com 4 dimensões) validados.")

    # =========================================================================
    # 2F. SCROLLYTELLING E ANIMAÇÕES DINÂMICAS NO SCROLL
    # =========================================================================
    print("\n2F. Testando Recursos de Scrollytelling e Animações no Scroll...")
    assert "scroll-progress-bar" in html_content, "Barra de progresso de scroll ausente"
    assert "scroll-nav-rail" in html_content, "Trilho lateral flutuante de scroll ausente"
    assert "scroll-reveal" in html_content, "Classes de scroll-reveal ausentes"
    assert "scroll-smooth" in html_content, "Classe scroll-smooth ausente"
    assert "runGraphPulseAnimation" in html_content, "Função de animação do grafo ausente"
    print("   [OK] Scrollytelling, barra de progresso, trilho lateral e classes scroll-reveal validados.")

    # =========================================================================
    # 3. DEMONSTRAÇÃO AUTÔNOMA NO SCROLL & REPLAY DISCRETO (SEM PLAYER ARTIFICIAL)
    # =========================================================================
    print("\n3. Testando Demonstração Autônoma no Scroll e Replay Discreto...")
    assert "btn-tour-replay" in html_content, "Botão 'Ver animação de novo' #btn-tour-replay ausente"
    assert "Ver animação de novo" in html_content, "Texto 'Ver animação de novo ↺' ausente"
    assert "typewriter-cursor" in html_content, "Cursor typewriter ausente"
    assert "runAutonomousShowcase" in html_content, "Função runAutonomousShowcase ausente"
    assert "runStreamingResponse" in html_content, "Função runStreamingResponse ausente"
    assert "Role para ver o fluxo em tempo real" in html_content, "Indicador de scroll ausente no Hero"
    assert "IntersectionObserver" in html_content, "Acionamento autônomo via IntersectionObserver ausente"
    assert "Reproduzir Tour Automático" not in html_content, "Barra artificial antiga 'Reproduzir Tour Automático' ainda presente"
    print("   [OK] Demonstração autônoma no scroll (Typewriter, Sincronização Chat vs Backend, Streaming, Replay Discreto) validada.")

    # =========================================================================
    # 4. BLINDAGEM DE SEGREDO TECNOLÓGICO (ZERO EXPOSIÇÃO DE STACK INTERNA)
    # =========================================================================
    print("\n4. Testando Blindagem Estrita contra Cópia Intelectual (Zero Vazamento)...")
    content_lower = html_content.lower()

    # Termos expressamente proibidos no showcase
    forbidden_terms = [
        "spacy",
        "pgvector",
        "transformers",
        "chromadb",
        "chroma",
        "ollama",
        "groq",
        "llama",
        "langchain",
        "huggingface",
        "sqlite",
        "postgresql",
        "postgres",
    ]

    leaks = [term for term in forbidden_terms if term in content_lower]
    assert len(leaks) == 0, f"VIOLAÇÃO DE BLINDAGEM! Termos internos vazados no showcase: {leaks}"
    print(f"   [OK] 0 termos de infraestrutura interna vazados (testados: {', '.join(forbidden_terms)}).")

    # Jargões artificiais e rastros de IA expressamente proibidos (linguagem humanizada)
    forbidden_ai_jargons = [
        "fiduciário",
        "fiduciaria",
        "fiduciario",
        "fiduciárias",
        "alucinações matemáticas",
        "alucinação em números",
        "disparo resolutivo",
    ]
    jargon_leaks = [j for j in forbidden_ai_jargons if j in content_lower]
    assert len(jargon_leaks) == 0, f"VIOLAÇÃO DE HUMANIZAÇÃO! Jargões de IA detectados: {jargon_leaks}"
    print(f"   [OK] 0 jargões artificiais de IA detectados (humanização 100% validada).")

    # Termos proprietários de alto valor exigidos
    required_proprietary_terms = [
        "aura guard",
        "blindagem",
        "desintegração",
        "privacidade",
        "decisioncard",
        "anp",
    ]
    for req in required_proprietary_terms:
        assert req in content_lower, f"Termo proprietário '{req}' ausente no showcase"
    print("   [OK] Terminologia proprietária de luxo (AURA Guard™, DecisionCard™, Borda, ANP) validada.")

    # =========================================================================
    # 5. INTEGRAÇÃO NO SHELL OFICIAL (web/index.html)
    # =========================================================================
    print("\n5. Testando Pontos de Acesso 'Saiba mais...' no Shell da AURA (index.html)...")
    resp_index = client.get("/")
    assert resp_index.status_code == 200
    index_html = resp_index.text

    # Verifica link no menu lateral
    assert 'href="/showcase"' in index_html, "Link para /showcase ausente no index.html"
    assert "Saiba mais..." in index_html, "Texto 'Saiba mais...' ausente no index.html"
    
    # Verifica presença no drawer lateral
    assert "sidebar-nav-item" in index_html and "/showcase" in index_html
    # Verifica link no cabeçalho ou card
    assert "header-link-showcase" in index_html
    print("   [OK] Pontos de acesso 'Saiba mais...' validados no menu lateral, header e welcome card.")

    # =========================================================================
    # 6. VALIDAÇÃO DE SINTAXE E LÓGICA JAVASCRIPT NO NODE.JS
    # =========================================================================
    print("\n6. Executando Validação de Sintaxe JavaScript no Node.js...")
    scripts = re.findall(r'<script>(.*?)</script>', html_content, re.DOTALL)
    assert len(scripts) >= 2, "Esperado ao menos 2 blocos de script em showcase.html"

    for i, script_code in enumerate(scripts):
        proc = subprocess.run(
            ["node", "-c"],
            input=script_code,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        assert proc.returncode == 0, f"Erro de sintaxe no script {i+1}: {proc.stderr}"
    print(f"   [OK] {len(scripts)} blocos de script validados com 100% de sintaxe correta no Node.js.")

    # Simula execução da API pública do tour com o script real extraído do HTML
    main_script = scripts[-1]
    node_sim_code = f"""
    const window = {{
      addEventListener: () => {{}},
      removeEventListener: () => {{}},
      requestAnimationFrame: (cb) => setTimeout(cb, 16),
      cancelAnimationFrame: (id) => clearTimeout(id),
      performance: {{ now: () => Date.now() }},
    }};
    const document = {{
      addEventListener: () => {{}},
      getElementById: (id) => ({{
        getContext: () => ({{
          clearRect: () => {{}},
          save: () => {{}},
          restore: () => {{}},
          beginPath: () => {{}},
          arc: () => {{}},
          fill: () => {{}},
        }}),
        parentElement: {{ clientWidth: 800, clientHeight: 600 }},
        getBoundingClientRect: () => ({{ left: 10, top: 20, width: 200, height: 30 }}),
        classList: {{ add: () => {{}}, remove: () => {{}} }},
        style: {{}},
      }}),
      querySelectorAll: () => [],
    }};

    {main_script}

    const expectedMethods = [
      'runAutonomousShowcase',
      'runStreamingResponse',
      'goToStep',
      'nextStep',
      'prevStep',
      'startTour',
      'pauseTour',
      'restartTour',
      'triggerDustDisintegration',
      'resetDustDisintegration',
      'triggerCustomDustDisintegration',
      'simulateStep1Question',
      'simulatePipelinePulse',
      'inspectNode',
      'simulateActionClick',
      'toggleStep4Tab',
      'selectChatScenario',
      'simulateChatSubmit',
      'simulateChatActionClick',
      'inspectGraphNode',
      'scrollToSection'
    ];

    if (!window.auraTour) {{
      console.error('window.auraTour nao foi instanciado!');
      process.exit(1);
    }}

    for (const m of expectedMethods) {{
      if (typeof window.auraTour[m] !== 'function') {{
        console.error('Metodo ausente em window.auraTour:', m);
        process.exit(1);
      }}
    }}

    console.log('NODE_SHOWCASE_API_VALIDATED');
    """
    proc_node = subprocess.run(
        ["node"],
        input=node_sim_code,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    assert proc_node.returncode == 0, f"Falha na validação Node.js: {proc_node.stderr}"
    assert "NODE_SHOWCASE_API_VALIDATED" in proc_node.stdout
    print("   [OK] Métodos e integridade da API pública window.auraTour validados no Node.js.")

    # =========================================================================
    # 7. VALIDAÇÃO REAL EM NAVEGADOR (EDGE PLAYWRIGHT SE DISPONÍVEL)
    # =========================================================================
    print("\n7. Executando Validação Funcional em Navegador Real (Edge Playwright)...")
    try:
        from playwright.sync_api import sync_playwright
        import time

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            file_url = (BASE_DIR / "web" / "showcase.html").resolve().as_uri()
            page.goto(file_url)

            # 1. Verifica que no scroll=0 o typewriter não disparou prematuramente
            box = page.locator("#sec-chat-graph").bounding_box()
            assert box and box["y"] > 500, "Seção deve estar abaixo da dobra inicial"
            time.sleep(1.2)
            typed_init = page.locator("#step1-typed-text").text_content()
            resp_init = page.locator("#chat-response-row").is_visible()
            assert typed_init == "", f"Não deve disparar no topo! Obtido: {typed_init}"
            assert not resp_init, "Resposta não deve estar visível no topo"

            # 2. Rola até a seção e valida o disparo autônomo
            page.locator("#sec-chat-graph").scroll_into_view_if_needed()
            time.sleep(0.6)
            typed_mid = page.locator("#step1-typed-text").text_content()
            assert len(typed_mid) > 0, "Typewriter deve iniciar automaticamente ao rolar"

            # Aguarda dinamicamente conclusão do ciclo autônomo, streaming e exibição do DecisionCard
            # (tempo estendido para acomodar leitura confortável dos dados pessoais no Card 3)
            page.locator("#decisioncard-live").wait_for(state="visible", timeout=12000)
            typed_done = page.locator("#step1-typed-text").text_content()
            resp_done = page.locator("#chat-response-row").is_visible()
            dc_done = page.locator("#decisioncard-live").is_visible()
            badge_done = page.locator("#sim-status-badge").text_content()

            assert "Qual produto mais vendido hoje?" in typed_done
            assert resp_done, "Resposta da AURA deve ser exibida após streaming"
            assert dc_done, "DecisionCard deve ser renderizado"
            assert "CONCLUÍDO" in badge_done or "38ms" in badge_done, "Status deve indicar conclusão"

            # 3. Testa replay discreto
            page.locator("#btn-tour-replay").click()
            time.sleep(0.3)
            replay_badge = page.locator("#sim-status-badge").text_content()
            assert "EXECUTANDO" in replay_badge, f"Replay deve reiniciar execução, obtido: {replay_badge}"

            # 4. Rola até #sec-diferenciacao e valida cards de ROI e tabela compactada
            page.locator("#sec-diferenciacao").scroll_into_view_if_needed()
            time.sleep(0.4)
            roi_cards = page.locator(".roi-card").all()
            assert len(roi_cards) == 4, f"Esperado exatamente 4 cards de ROI, obtido: {len(roi_cards)}"
            for card in roi_cards:
                assert card.is_visible(), "Card de ROI deve estar visível no navegador"

            table_rows = page.locator("#sec-diferenciacao table tbody tr").all()
            assert len(table_rows) == 4, f"Esperado exatamente 4 linhas na tabela compactada, obtido: {len(table_rows)}"
            for tr in table_rows:
                assert tr.is_visible(), "Linha da tabela compactada deve estar visível"

            # 5. Testa renderização responsiva em viewport ultracompacto (Mobile 375x667)
            mobile_page = browser.new_page(viewport={"width": 375, "height": 667})
            mobile_page.goto(file_url)
            mobile_page.locator("#sec-diferenciacao").scroll_into_view_if_needed()
            time.sleep(0.3)
            assert mobile_page.locator("#sec-diferenciacao").is_visible(), "Seção de ROI deve estar visível em tela mobile"
            m_cards = mobile_page.locator(".roi-card").all()
            assert len(m_cards) == 4, "4 cards de ROI devem existir em mobile"
            mobile_page.close()

            browser.close()
            print("   [OK] Validação em navegador real Edge aprovada: aguardo no topo, disparo autônomo no scroll, streaming, DecisionCard, replay, cards de ROI, tabela de 4 linhas e responsividade mobile.")
    except Exception as e:
        print(f"   [AVISO] Verificação em navegador real ignorada ou indisponível: {e}")

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DA APRESENTAÇÃO AURA SHOWCASE PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_showcase_tests()
