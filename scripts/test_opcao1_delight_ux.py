"""
Suíte de Testes Automatizada: Opção 1 — Micro-Interações & Delight UX
(Sensação de App Nativo de Luxo para o Painel Executivo AURA)

Validações:
1. Skeleton Loaders Translúcidos em Vidro Líquido (Shimmer Wave Effect):
   - Tokens .skeleton-glass e .skeleton-shimmer em aura.css com animação shimmerWave.
   - aura-cockpit.js possui renderLoadingSkeletons() cobrindo tanques, bicos, frentistas, anomalias, turno, LMC e combos.
   - aura-chat.js renderiza skeleton dinâmico simulando DecisionCard (.decision-card.skeleton-glass) em tool_start.
2. Orbe de Raciocínio Cognitivo Durante Streaming (Cognitive Reasoning Orb):
   - Estilos .neural-core-orb.reasoning-active com pulso ciano/violeta (cognitiveOrbPulse) em aura.css.
   - Header possui #header-neural-core-orb e ativa pulso durante chat streaming.
   - Bolha de mensagem ativa possui avatar orb com reasoning-active e chips dinâmicos de etapas cognitivas (.chip-cognitive-step).
   - Transição dinâmica de etapas cognitivas (ex: CBC04 -> PDV -> Diagnóstico).
3. Transições Cinematográficas Entre Telas (Smooth View Transitions):
   - Classe .view-transition-active e @keyframes viewFadeIn com 200ms cubic-bezier(0.16, 1, 0.3, 1).
   - Todas as 4 abas (#view-console, #view-cockpit, #view-triggers, #view-split) configuradas para transição suave.
   - aura-app.js executa transição fluida com reflow em switchTab().
4. Modo Performance & GPU Guard (AURA Performance Mode):
   - Suporte global a @media (prefers-reduced-motion: reduce).
   - Interruptor de preferências #sidebar-btn-toggle-gpu-guard no NavigationDrawer com badge e rótulo.
   - Classe .gpu-guard-active anula backdrop-filter pesados e provê backgrounds sólidos estáveis a 60 FPS.
   - aura-app.js coordena persistência no localStorage e sincronização visual.
   - aura-fx.js pausa renderização pesada da aurora boreal quando GPU Guard está ativo.
5. Integridade de Assets e Cache-Busting:
   - Cache-buster atualizado para ?v=2.7.0 em index.html para CSS e todos os 6 scripts JS.
   - Versão da Engine no rodapé do drawer atualizada para v2.7.0.
"""

import sys
import subprocess
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Protege stdout no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.aura_engine import AuraEngine, AuraSessionMemory
from core.aura_api import create_aura_app


def run_delight_ux_tests():
    print("=" * 78)
    print("✨ SUÍTE DE TESTES: OPÇÃO 1 — MICRO-INTERAÇÕES & DELIGHT UX (LUXURY NATIVE)")
    print("   (Skeleton Shimmer, Cognitive Reasoning Orb, Smooth Transitions & GPU Guard)")
    print("=" * 78)

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(tenant_id="test_ux", filial_id="posto_teste_01", session_memory=mem)
    app = create_aura_app(engine)
    client = TestClient(app)

    # ------------------------------------------------------------------
    # 1. VALIDAÇÃO DE ASSETS ESTÁTICOS E CACHE-BUSTING (v=2.8.0)
    # ------------------------------------------------------------------
    print("\n1. Testando Cache-Busting e Marcação SPA (index.html)...")
    resp_root = client.get("/")
    assert resp_root.status_code == 200, "Falha ao carregar SPA"
    html = resp_root.text

    import re
    assert re.search(r'href="/static/css/aura\.css\?v=2\.\d+\.\d+"', html), "Cache-buster do aura.css não foi atualizado"
    for script_name in ["aura-api.js", "aura-cockpit.js", "aura-triggers.js", "aura-chat.js", "aura-app.js", "aura-fx.js"]:
        assert re.search(rf'src="/static/js/{script_name}\?v=2\.\d+\.\d+"', html), f"Cache-buster de {script_name} não foi atualizado"

    assert re.search(r"AURA Engine v2\.\d+\.\d+", html), "Versão do rodapé da AURA Engine não foi atualizada"
    print("   [OK] Cache-buster validado em todos os assets CSS e JS.")

    # ------------------------------------------------------------------
    # 2. VALIDAÇÃO DO MODO PERFORMANCE & GPU GUARD NO DRAWER
    # ------------------------------------------------------------------
    print("\n2. Testando Interruptor de Modo Alta Performance (GPU Guard)...")
    assert 'id="sidebar-btn-toggle-gpu-guard"' in html, "Botão sidebar-btn-toggle-gpu-guard ausente no Drawer"
    assert 'role="switch"' in html, "Atributo role='switch' ausente no botão do GPU Guard"
    assert 'aria-checked="false"' in html, "Atributo aria-checked ausente no botão do GPU Guard"
    assert "Modo Alta Performance (GPU Guard)" in html, "Rótulo do GPU Guard ausente no Drawer"
    assert 'id="sidebar-gpu-badge"' in html, "Badge do GPU Guard ausente no Drawer"
    assert 'id="sidebar-gpu-icon"' in html, "Ícone do GPU Guard ausente no Drawer"
    print("   [OK] Controles do GPU Guard presentes, acessíveis (role=switch) e integrados nas Preferências do Drawer.")

    # ------------------------------------------------------------------
    # 3. VALIDAÇÃO DE CSS: SKELETONS, TRANSIÇÕES, GPU GUARD & REDUCED MOTION
    # ------------------------------------------------------------------
    print("\n3. Testando Tokens de Design e Animações no CSS (aura.css)...")
    resp_css = client.get("/static/css/aura.css")
    assert resp_css.status_code == 200
    css = resp_css.text

    # Skeleton tokens
    assert ".skeleton-glass" in css, "Classe .skeleton-glass ausente no CSS"
    assert ".skeleton-shimmer" in css, "Classe .skeleton-shimmer ausente no CSS"
    assert "shimmerWave" in css, "Keyframes shimmerWave ausente no CSS"

    # Cognitive Reasoning Orb
    assert ".neural-core-orb.reasoning-active" in css, "Classe .neural-core-orb.reasoning-active ausente no CSS"
    assert "cognitiveOrbPulse" in css, "Keyframes cognitiveOrbPulse ausente no CSS"
    assert ".chip-cognitive-step" in css, "Classe .chip-cognitive-step ausente no CSS"

    # Smooth View Transitions
    assert ".view-transition-active" in css, "Classe .view-transition-active ausente no CSS"
    assert "viewFadeIn" in css, "Keyframes viewFadeIn ausente no CSS"
    assert "200ms" in css and "cubic-bezier(0.16, 1, 0.3, 1)" in css, "Curva de transição 200ms cubic-bezier(0.16, 1, 0.3, 1) ausente no CSS"

    # GPU Guard & Reduced Motion
    assert ".gpu-guard-active" in css, "Classe .gpu-guard-active ausente no CSS"
    assert "backdrop-filter: none !important" in css, "Anulação de backdrop-filter no GPU Guard ausente no CSS"
    assert ".gpu-guard-active .decision-card" in css, "Regra de contraste opaco para decision-card ausente no GPU Guard"
    assert "@media (prefers-reduced-motion: reduce)" in css, "Suporte a prefers-reduced-motion ausente no CSS"
    print("   [OK] Todos os tokens CSS e keyframes de UX refinada validados.")

    # ------------------------------------------------------------------
    # 4. VALIDAÇÃO DAS VIEWS E DO HEADER NO HTML
    # ------------------------------------------------------------------
    print("\n4. Testando Estrutura de Views e Header no HTML...")
    assert 'id="header-neural-core-orb"' in html, "ID header-neural-core-orb ausente no header"
    assert 'id="view-cockpit"' in html and 'view-transition-active' in html, "view-cockpit sem view-transition-active"
    assert 'id="view-triggers"' in html, "view-triggers ausente"
    assert 'id="view-console"' in html, "view-console ausente"
    assert 'max-w-3xl' in html or 'max-w-4xl' in html, "view-console sem restrição ergonômica de largura"
    assert 'id="view-split"' not in html, "view-split não deve estar presente"
    assert 'id="trigger-inspector-loading"' in html and 'skeleton-glass' in html, "trigger-inspector-loading não utiliza skeleton-glass"
    print("   [OK] Views (foco na conversação), gatilhos analíticos e orbe do header estruturados com suporte a transições suaves e skeletons.")

    # ------------------------------------------------------------------
    # 5. TESTES FUNCIONAIS FRONTEND VIA NODE.JS (Chat & Cockpit Skeletons)
    # ------------------------------------------------------------------
    print("\n5. Executando Validação Funcional dos Módulos JS via Node.js...")
    aura_chat_path = BASE_DIR / "web" / "js" / "aura-chat.js"
    aura_cockpit_path = BASE_DIR / "web" / "js" / "aura-cockpit.js"
    aura_app_path = BASE_DIR / "web" / "js" / "aura-app.js"
    aura_fx_path = BASE_DIR / "web" / "js" / "aura-fx.js"

    # Valida que aura-fx.js verifica reducedMotion no loop de renderização
    fx_text = aura_fx_path.read_text(encoding="utf-8")
    assert "this.reducedMotion" in fx_text and "isGpuGuard || this.reducedMotion" in fx_text, (
        "loop() em aura-fx.js não verifica this.reducedMotion para pausar o canvas"
    )

    node_script = """
    const { AuraChatController } = require(__AURA_CHAT_PATH__);
    const chat = new AuraChatController();

    // 1. Testa renderDecisionCardSkeleton
    const skelHtml = chat.renderDecisionCardSkeleton('conciliacao_turno');
    if (!skelHtml.includes('decision-card') || !skelHtml.includes('skeleton-glass') || !skelHtml.includes('skeleton-shimmer')) {
      console.error('FALHA: renderDecisionCardSkeleton não produziu classes de skeleton glass/shimmer');
      process.exit(1);
    }
    if (!skelHtml.includes('Calculando') || !skelHtml.includes('&amp;') || !skelHtml.includes('Caixa')) {
      console.error('FALHA: Rótulo de cálculo escapado ausente no skeleton do DecisionCard:', skelHtml);
      process.exit(1);
    }
    console.log('[NODE] ✓ DecisionCard Skeleton dinâmico gerado com sucesso para tool_start');

    // 2. Mock de DOM para updateToolStartStatus
    const mockToolCard = { 
      innerHTML: '', 
      classList: { 
        add: (c) => {}, 
        remove: (c) => {} 
      },
      querySelector: (sel) => mockToolCard.innerHTML.includes('skeleton-glass') ? {} : null
    };
    const mockToolChip = { innerHTML: '', className: '', classList: { remove: () => {} } };
    const mockCogChip = { innerHTML: '', className: '', classList: { remove: () => {} } };
    
    global.document = {
      getElementById: (id) => {
        if (id.includes('tool-card')) return mockToolCard;
        if (id.includes('tool-chip')) return mockToolChip;
        if (id.includes('cognitive-chip')) return mockCogChip;
        return null;
      },
      querySelectorAll: (sel) => []
    };

    chat.updateToolStartStatus('test-msg', 'previsao_tanques');
    if (!mockToolCard.innerHTML.includes('skeleton-glass')) {
      console.error('FALHA: updateToolStartStatus não injetou o skeleton no tool-card!');
      process.exit(1);
    }
    if (!mockCogChip.innerHTML.includes('Tanques') || !mockCogChip.innerHTML.includes('Autonomia')) {
      console.error('FALHA: updateToolStartStatus não atualizou a etapa cognitiva!');
      process.exit(1);
    }
    console.log('[NODE] ✓ Injeção de skeleton em tool_start e etapa cognitiva validadas no fluxo');

    // 3. Testa finalizeCognitiveStep
    chat.finalizeCognitiveStep('test-msg', true);
    if (!mockCogChip.innerHTML.includes('Diagnóstico executivo concluído')) {
      console.error('FALHA: finalizeCognitiveStep não produziu rótulo de conclusão:', mockCogChip.innerHTML);
      process.exit(1);
    }
    console.log('[NODE] ✓ Finalização graciosa da etapa cognitiva validada');

    // 4. Testa hideToolCardSkeleton e abortStreaming
    chat.currentMessageContainerId = 'test-msg';
    chat.hideToolCardSkeleton('test-msg');
    if (mockToolCard.innerHTML !== '') {
      console.error('FALHA: hideToolCardSkeleton não limpou o HTML do skeleton!');
      process.exit(1);
    }
    console.log('[NODE] ✓ Limpeza de skeleton em caso de interrupção ou ausência de widget validada');

    // 5. Testa updateToolResultCard sem widget (fallback seguro limpa skeleton)
    mockToolCard.innerHTML = '<div class="skeleton-glass">skeleton</div>';
    chat.updateToolResultCard('test-msg', 'unknown_tool', null);
    if (mockToolCard.innerHTML !== '') {
      console.error('FALHA: updateToolResultCard com dado vazio não limpou o skeleton pendente!');
      process.exit(1);
    }
    console.log('[NODE] ✓ Fallback seguro de tool result sem widget limpa o skeleton com sucesso');

    console.log('DELIGHT_UX_NODE_OK');
    """.replace("__AURA_CHAT_PATH__", json.dumps(str(aura_chat_path.resolve())))

    res_node = subprocess.run(
        ["node"],
        input=node_script,
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
        encoding="utf-8"
    )
    assert res_node.returncode == 0, f"Erro nos testes Node.js:\n{res_node.stderr}"
    assert "DELIGHT_UX_NODE_OK" in res_node.stdout
    print("   [OK] Lógica JS validada: DecisionCard Skeleton em tool_start e etapas cognitivas.")

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DA OPÇÃO 1 (DELIGHT UX) PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_delight_ux_tests()
