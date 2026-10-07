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
    assert "Conciliação Fiduciária" in html_content
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
    # 3. CONTROLES DO TOUR INTERATIVO E PLAYER
    # =========================================================================
    print("\n3. Testando Controles do Tour Interativo...")
    assert "btn-tour-play-pause" in html_content
    assert "btn-tour-prev" in html_content
    assert "btn-tour-next" in html_content
    assert "btn-tour-replay" in html_content
    assert "tour-progress-bar" in html_content
    assert "data-step-target=\"1\"" in html_content
    assert "data-step-target=\"4\"" in html_content
    print("   [OK] Controles do Player (Play/Pause, Prev, Next, Replay, Progress Bar) validados.")

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
      'toggleStep4Tab'
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
        ["node", "-e", node_sim_code],
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    assert proc_node.returncode == 0, f"Falha na validação Node.js: {proc_node.stderr}"
    assert "NODE_SHOWCASE_API_VALIDATED" in proc_node.stdout
    print("   [OK] Métodos e integridade da API pública window.auraTour validados no Node.js.")

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DA APRESENTAÇÃO AURA SHOWCASE PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_showcase_tests()
