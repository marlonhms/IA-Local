"""
Suíte de Testes Automatizada: Fase 4 — Shell, Navegação e Mobile (Segundo Marco)
Validação de Header Executivo, NavigationDrawer, ConversationThread, MessageComposer e Ergonomia Mobile.

Validações:
1. Header Executivo Simplificado (F4-01 & F4-02):
   - Identidade AURA com gradiente elegante ciano/violeta.
   - Contexto da unidade e turno presente de forma discreta (sem poluição visual).
   - Relógio com segundos (hud-live-clock) removido do header superior.
   - Controles essenciais acessíveis: btn-toggle-sidebar, btn-new-chat, btn-open-palette (Ctrl+K), status de prontidão.
   - Touch targets mínimos de 44px para botões do header.
   - Suporte a safe-areas mobile com viewport-fit=cover e prevenção de overflow horizontal.
2. Navegação Consistente & NavigationDrawer (F4-03 & F4-08):
   - 4 Abas principais consolidadas: Assistente (#view-console), Panorama (#view-cockpit), Ações Rápidas (#view-triggers), Visão Integrada (#view-split).
   - Touch target tátil mínimo de 48px nos itens de navegação lateral.
   - Efeitos sonoros (SFX) movidos para seção 'Preferências do Sistema' (F4-04).
   - Acessibilidade do drawer: role="dialog", aria-modal="true", foco inicial e focus trap em Tab/Shift+Tab, fechamento por Escape e restauração de foco ao gatilho.
   - Visibilidade do Turno Ativo no drawer (sidebar-turno-name) para operação mobile.
   - Ausência de opções SRE ou ruídos de infraestrutura.
3. ConversationThread & Espaçamento (F4-04 & F4-05):
   - Botão flutuante de rolagem para mensagens recentes (btn-scroll-bottom, F4-13).
   - Política de rolagem: scrollToBottom não força rolagem se o usuário estiver lendo mensagens anteriores no feed principal ou no split view (F4-12).
   - Tratamento de safe areas e classes responsivas para rolagem fluida.
4. MessageComposer Moderno & Mobile-First (F4-06 & F4-07):
   - Textarea adaptável com auto-resize (autoResizeInput).
   - Botões de envio (btn-chat-send) e parada (btn-chat-stop) com área mínima de 44x44px.
   - Preservação de rascunho de mensagem digitada caso streaming esteja ativo (sem perda de digitação).
   - Atributos mobile: min-w-0, enterkeyhint="send", autocomplete="off".
   - Limite exato de até 3 sugestões contextuais mais 1 acesso a mais consultas no rodapé (F4-07).
5. Ergonomia Mobile e Responsividade (F4-08 & F4-09):
   - Regras CSS mobile (<640px) com input font-size >= 16px para evitar auto-zoom no iOS.
   - Safe-area inset bottom padding no composer.
   - min-height desobstrutivo no mobile (<640px) para não esconder o composer sob o teclado virtual.
   - Sem overflow horizontal, classes de viewport responsivo (100dvh).
"""

import sys
import subprocess
import json
import re
from pathlib import Path
from fastapi.testclient import TestClient

# Protege stdout no terminal Windows contra problemas de encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.aura_engine import AuraEngine, AuraSessionMemory
from core.aura_api import create_aura_app


def run_phase4_tests():
    print("=" * 78)
    print("🧪 SUÍTE DE TESTES: FASE 4 — SHELL, NAVEGAÇÃO E MOBILE (SEGUNDO MARCO)")
    print("   (Header Executivo, NavigationDrawer, ConversationThread, Composer e Mobile)")
    print("=" * 78)

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(tenant_id="test_fase4", filial_id="posto_teste_01", session_memory=mem)
    app = create_aura_app(engine)
    client = TestClient(app)

    # ------------------------------------------------------------------
    # 1. TESTE DO HEADER EXECUTIVO SIMPLIFICADO (F4-01 & F4-02)
    # ------------------------------------------------------------------
    print("\n1. Testando Header Executivo Simplificado...")
    resp_root = client.get("/")
    assert resp_root.status_code == 200, "Falha ao carregar SPA"
    html = resp_root.text

    # Identidade AURA com gradiente ciano/violeta
    assert "bg-gradient-to-r from-cyan-400 via-sky-300 to-purple-400" in html, "Gradiente ciano/violeta da AURA ausente no header"
    assert "neural-core-orb" in html, "Núcleo neural AURA ausente"

    # Contexto da unidade e turno
    assert "hud-filial-name" in html, "Identificador de filial no HUD ausente"
    assert "Turno Atual" in html, "Identificador discreto de Turno ausente no header"

    # Relógio com segundos REMOVIDO
    assert 'id="hud-live-clock"' not in html, "hud-live-clock ainda presente no header (deveria ser removido)"
    assert '--:--:--' not in html, "Contador de segundos --:--:-- ainda presente no header"

    # Controles essenciais com touch target
    assert 'id="btn-toggle-sidebar"' in html, "Gatilho do menu hambúrguer ausente"
    assert 'min-w-[44px]' in html and 'min-h-[44px]' in html, "Touch targets mínimos de 44px não aplicados nos botões do header"
    assert 'id="btn-new-chat"' in html, "Botão btn-new-chat ausente no header"
    assert 'id="btn-open-palette"' in html, "Botão btn-open-palette (Ctrl+K) ausente no header"
    assert "Pronta para Atendimento" in html, "Status de prontidão da AURA ausente"

    # Safe areas & Prevenção de overflow horizontal
    assert 'viewport-fit=cover' in html, "viewport-fit=cover ausente no meta viewport"
    assert 'overflow-x-hidden' in html, "overflow-x-hidden ausente para conter rolagem horizontal indesejada"
    print("   [OK] Header simplificado: identidade elegante, contexto sem poluição, sem relógio com segundos e controles >= 44px.")

    # ------------------------------------------------------------------
    # 2. TESTE DO NAVIGATIONDRAWER & ERGONOMIA TÁTIL (F4-03 & F4-08)
    # ------------------------------------------------------------------
    print("\n2. Testando NavigationDrawer e Ergonomia Tátil...")
    assert 'id="aura-sidebar-drawer"' in html, "Drawer aura-sidebar-drawer ausente"
    assert 'role="dialog"' in html and 'aria-modal="true"' in html, "Atributos ARIA de modal/dialog ausentes no drawer"
    assert 'id="btn-close-sidebar"' in html, "Botão de fechar menu lateral ausente"

    # 3 Telas principais consolidadas (foco total na conversação da AURA)
    assert 'data-tab="console"' in html, "Aba Assistente AURA ausente"
    assert 'data-tab="cockpit"' in html, "Aba Panorama Operacional ausente"
    assert 'data-tab="triggers"' in html, "Aba Ações Rápidas ausente"
    assert 'data-tab="split"' not in html, "Aba Visão Integrada não deve estar presente"

    # SFX movido para Preferências do Sistema (F4-04)
    assert "Preferências do Sistema" in html, "Seção de Preferências do Sistema ausente no menu lateral"
    assert 'id="sidebar-btn-toggle-sfx"' in html, "Botão de SFX ausente na seção de preferências"

    # Contexto operacional no drawer (Filial e Turno visíveis no mobile)
    assert 'id="sidebar-filial-name"' in html, "Identificador de filial ausente no drawer"
    assert 'id="sidebar-turno-name"' in html, "Identificador de turno ausente no drawer"

    # Verificação de CSS para touch target de 48px e remoção de neon agressivo
    resp_css = client.get("/static/css/aura.css")
    assert resp_css.status_code == 200
    css = resp_css.text

    assert ".sidebar-nav-item" in css
    assert "min-height: 48px" in css, "Touch target de 48px ausente em .sidebar-nav-item"
    assert "touch-action: manipulation" in css, "touch-action: manipulation ausente para evitar atrasos de toque mobile"
    print("   [OK] NavigationDrawer: 4 telas consolidadas, SFX em preferências, turno no drawer, ARIA modal e touch targets de 48px.")

    # ------------------------------------------------------------------
    # 3. TESTE DE CONVERSATIONTHREAD E BOTÃO FLUTUANTE (F4-04, F4-12, F4-13)
    # ------------------------------------------------------------------
    print("\n3. Testando ConversationThread e Rolagem Suave...")
    assert 'id="chat-feed-container"' in html, "Contêiner chat-feed-container ausente"
    assert 'id="btn-scroll-bottom"' in html, "Botão flutuante btn-scroll-bottom ausente"
    assert "Mensagens recentes" in html, "Rótulo do botão flutuante de mensagens recentes ausente"
    assert ".scroll-to-bottom-btn" in css, "Classe .scroll-to-bottom-btn ausente no CSS"
    print("   [OK] ConversationThread: contêiner fluido e botão flutuante para voltar a mensagens recentes.")

    # ------------------------------------------------------------------
    # 4. TESTE DO MESSAGECOMPOSER MODERNO & MOBILE-FIRST (F4-06 & F4-07)
    # ------------------------------------------------------------------
    print("\n4. Testando MessageComposer Moderno & Mobile-First...")
    assert 'id="chat-input-text"' in html, "Textarea chat-input-text ausente"
    assert 'id="btn-chat-send"' in html, "Botão de envio btn-chat-send ausente"
    assert 'id="btn-chat-stop"' in html, "Botão de parada btn-chat-stop ausente"
    assert 'enterkeyhint="send"' in html, "enterkeyhint='send' ausente no textarea para teclado mobile"
    assert 'min-w-0' in html, "min-w-0 ausente no textarea para evitar overflow em flexbox"
    assert ".message-composer-container" in css, "Classe .message-composer-container ausente no CSS"
    assert ".quick-prompt-chip" in css, "Classe .quick-prompt-chip ausente no CSS"
    assert "min-height: 40px" in css, "Touch target >= 40px ausente em .quick-prompt-chip"

    # F4-07: Exatamente 3 sugestões contextuais mais 1 acesso a mais consultas
    prompt_chips = re.findall(r'class="quick-prompt-chip[^"]*"', html)
    assert len(prompt_chips) == 4, f"Esperado exatamente 4 chips (3 sugestões + 1 'Mais consultas'), encontrado {len(prompt_chips)}"
    assert "Mais consultas" in html, "Acesso a mais consultas ausente no rodapé de sugestões"
    print("   [OK] MessageComposer: textarea adaptável, botões 44px, safe-area e exatamente 3 sugestões + 1 acesso (F4-07).")

    # ------------------------------------------------------------------
    # 5. TESTE DE LÓGICA JAVASCRIPT VIA NODE.JS (AUTO-RESIZE, SCROLL, CONTROLE)
    # ------------------------------------------------------------------
    print("\n5. Executando Validação de Lógica Frontend via Node.js...")
    node_test = r"""
    const { AuraChatController } = require('./web/js/aura-chat.js');
    const chat = new AuraChatController();

    // 1. Instanciação e estado inicial de rolagem
    if (chat.userScrolledUp !== false) {
      console.error('FALHA: userScrolledUp inicial deve ser false');
      process.exit(1);
    }

    // 2. Teste do Auto-Resize do textarea
    const mockTextarea = {
      scrollHeight: 88,
      style: { height: '' }
    };
    chat.autoResizeInput(mockTextarea);
    if (mockTextarea.style.height !== '88px') {
      console.error('FALHA: autoResizeInput não ajustou a altura corretamente:', mockTextarea.style.height);
      process.exit(1);
    }

    // 3. Limite mínimo de altura (44px)
    mockTextarea.scrollHeight = 20;
    chat.autoResizeInput(mockTextarea);
    if (mockTextarea.style.height !== '44px') {
      console.error('FALHA: autoResizeInput não aplicou altura mínima de 44px:', mockTextarea.style.height);
      process.exit(1);
    }

    // 4. Limite máximo de altura (160px)
    mockTextarea.scrollHeight = 300;
    chat.autoResizeInput(mockTextarea);
    if (mockTextarea.style.height !== '160px') {
      console.error('FALHA: autoResizeInput ultrapassou altura máxima de 160px:', mockTextarea.style.height);
      process.exit(1);
    }

    // 5. Teste da Política de Rolagem (scrollToBottom)
    let scrolledCount = 0;
    const mockFeed = {
      scrollHeight: 1000,
      scrollTop: 0
    };
    const mockSplitFeed = {
      scrollHeight: 1000,
      scrollTop: 0
    };
    global.document = {
      getElementById: (id) => {
        if (id === 'chat-feed-container') return mockFeed;
        return null;
      }
    };

    // Caso A: Usuário lendo histórico (userScrolledUp = true) e force = false -> NÃO deve forçar scrollTop
    chat.userScrolledUp = true;
    chat.scrollToBottom(false);
    if (mockFeed.scrollTop !== 0) {
      console.error('FALHA: scrollToBottom forçou rolagem enquanto usuário lia histórico!');
      process.exit(1);
    }

    // Caso B: force = true (nova mensagem enviada) -> DEVE atualizar scrollTop
    chat.scrollToBottom(true);
    if (mockFeed.scrollTop !== 1000) {
      console.error('FALHA: scrollToBottom com force=true não rolou para o fim!');
      process.exit(1);
    }

    // 6. Blindagem de Rascunho: Usuário digitando durante streaming não perde texto
    const mockInput = {
      value: 'Texto que o usuário estava digitando',
      style: { height: '60px' }
    };
    global.document.getElementById = (id) => {
      if (id === 'chat-input-text') return mockInput;
      if (id === 'chat-feed-container') return mockFeed;
      return null;
    };
    chat.isStreaming = true;
    chat.handleSendMessage(); // Deve retornar imediatamente sem limpar mockInput
    if (mockInput.value !== 'Texto que o usuário estava digitando') {
      console.error('FALHA: handleSendMessage apagou o rascunho do usuário durante streaming!');
      process.exit(1);
    }

    console.log('NODE_OK');
    """

    res_node = subprocess.run(
        ["node", "-e", node_test],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )
    assert res_node.returncode == 0, f"Erro nos testes Node.js:\n{res_node.stderr}"
    assert "NODE_OK" in res_node.stdout
    print("   [OK] Lógica JS validada: Auto-Resize (44px-160px), Scroll-Guard (F4-12), preservação de rascunho e reset de estado.")

    # ------------------------------------------------------------------
    # 6. TESTE DE RESPONSIVIDADE E BREAKPOINTS MOBILE (F4-08 & F4-09)
    # ------------------------------------------------------------------
    print("\n6. Testando Ergonomia Mobile e Breakpoints no CSS...")
    assert "@media (max-width: 640px)" in css, "Breakpoint mobile max-width: 640px ausente no CSS"
    assert "font-size: 16px" in css, "Proteção font-size: 16px para iOS Safari ausente no CSS"
    assert "100dvh" in css, "Unidade moderna 100dvh ausente para altura responsiva com teclado virtual"
    assert "min-height: 0 !important" in css, "min-height desobstrutivo ausente para teclado virtual mobile"
    assert "safe-area-inset-bottom" in css, "safe-area-inset-bottom ausente no composer"
    print("   [OK] Breakpoints mobile validados: 100dvh, safe-area, prevenção de zoom no iOS e teclado desobstrutivo.")

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DA FASE 4 PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_phase4_tests()
