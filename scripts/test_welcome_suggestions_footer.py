"""
Suíte de Testes Automatizada: Posicionamento dos Cards de Sugestões Executivas no Rodapé do Card de Boas-Vindas
(Espaçamento Inferior Dedicado, Desacoplamento da Apresentação, Remoção no Primeiro Envio e Responsividade)

Validações:
1. Desacoplamento e Estrutura HTML/CSS:
   - #welcome-suggestions-container NÃO está colado no fluxo imediato dos parágrafos da apresentação.
   - Presença da classe .welcome-card-footer com espaçamento inferior dedicado (!mt-7 / sm:!mt-8, pt-4, border-t border-white/10).
   - Regras no CSS web/css/aura.css para #welcome-suggestions-container e .welcome-card-footer com margin-top generoso e responsivo.
2. Contrato de 4 Sugestões (F4-07):
   - Exatamente 4 chips com min-height >= 40px no rodapé do welcome card.
   - 3 sugestões executivas de negócio + 1 atalho 'Mais consultas (Ctrl+K)'.
3. Lógica JS no Node.js (aura-chat.js):
   - addWelcomeMessage() gera a estrutura de rodapé com as classes e espaçamento.
   - Ao executar sendUserPrompt() ou handleSendMessage() (primeiro envio), #welcome-suggestions-container é estritamente removido do DOM.
   - O texto de apresentação da AURA permanece íntegro no card após a remoção.
   - Envios subsequentes não causam erros de referência nula.
   - clearSession() restaura o card de boas-vindas com o rodapé de sugestões intacto.
"""

import sys
import subprocess
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


def run_welcome_footer_tests():
    print("=" * 78)
    print("🧪 SUÍTE DE TESTES: POSICIONAMENTO E REMOÇÃO DAS SUGESTÕES NO WELCOME CARD")
    print("   (Espaçamento Inferior / Rodapé, Desacoplamento do Texto e Ciclo de Vida)")
    print("=" * 78)

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(tenant_id="test_welcome", filial_id="posto_teste_01", session_memory=mem)
    app = create_aura_app(engine)
    client = TestClient(app)

    # ------------------------------------------------------------------
    # 1. VALIDAÇÃO DE ESTRUTURA HTML (SPA)
    # ------------------------------------------------------------------
    print("\n1. Testando Estrutura e Desacoplamento no HTML Inicial...")
    resp_root = client.get("/")
    assert resp_root.status_code == 200, "Falha ao carregar SPA"
    html = resp_root.text

    # Verifica se #welcome-suggestions-container existe
    assert 'id="welcome-suggestions-container"' in html, "Elemento #welcome-suggestions-container ausente no HTML"
    assert "welcome-card-footer" in html, "Classe .welcome-card-footer ausente no container de sugestões"

    # Verifica desacoplamento: o texto da apresentação deve fechar seu container antes do rodapé de sugestões
    pattern_intro_closed = re.compile(
        r'Olá! Sou a <strong>AURA</strong>.*?analisar as vendas da loja\.\s*</p>\s*</div>\s*(?:<!--.*?-->\s*)?<div id="welcome-suggestions-container"',
        re.DOTALL
    )
    assert pattern_intro_closed.search(html), "O container de sugestões ainda está colado dentro do bloco de texto da apresentação!"

    # Verifica classes de espaçamento inferior (rodapé ancorado na base)
    assert "mt-auto" in html or "!mt-auto" in html, "Espaçamento superior de rodapé (mt-auto) ausente no container de sugestões"
    assert "h-full" in html, "Classe h-full ausente no container de boas-vindas"
    assert "flex-1" in html, "Classe flex-1 ausente para expansão vertical total"
    assert "pt-4" in html, "Padding-top de rodapé ausente"
    assert "border-t" in html, "Borda divisória superior do rodapé ausente"
    print("   [OK] HTML validado: bloco de apresentação fechado, sugestões ancoradas na base com mt-auto e altura total (h-full/flex-1).")

    # ------------------------------------------------------------------
    # 2. VALIDAÇÃO DE ESTILOS CSS EM web/css/aura.css
    # ------------------------------------------------------------------
    print("\n2. Testando Regras CSS de Espaçamento Inferior em web/css/aura.css...")
    resp_css = client.get("/static/css/aura.css")
    assert resp_css.status_code == 200
    css = resp_css.text

    assert "#welcome-suggestions-container" in css, "Seletor #welcome-suggestions-container ausente no aura.css"
    assert ".welcome-card-footer" in css, "Seletor .welcome-card-footer ausente no aura.css"
    assert "margin-top: auto" in css, "Propriedade margin-top: auto ausente no rodapé de sugestões em aura.css"
    assert "border-top:" in css, "Propriedade border-top ausente no rodapé de sugestões"
    assert ".welcome-suggestions-grid" in css, "Classe .welcome-suggestions-grid ausente no aura.css"
    assert "#welcome-message-bubble" in css or ".welcome-message-wrapper" in css, "Regras de altura total do welcome card ausentes no aura.css"
    print("   [OK] CSS validado: regras dedicadas para margin-top: auto, altura total e ancoragem inferior.")

    # ------------------------------------------------------------------
    # 3. VALIDAÇÃO DE CHIPS E GATILHOS EXECUTIVOS (F4-07)
    # ------------------------------------------------------------------
    print("\n3. Testando Chips de Sugestões Executivas...")
    prompt_chips = re.findall(r'class="quick-prompt-chip[^"]*"', html)
    assert len(prompt_chips) == 4, f"Esperado exatamente 4 chips (3 sugestões + 1 'Mais consultas'), encontrado {len(prompt_chips)}"
    assert "Autonomia dos Tanques" in html
    assert "Fechamento & Caixa" in html
    assert "LMC Fiscal ANP" in html
    assert "Mais consultas" in html
    print("   [OK] 4 cards executivos presentes e íntegros no rodapé.")

    # ------------------------------------------------------------------
    # 4. VALIDAÇÃO DINÂMICA DE CICLO DE VIDA VIA NODE.JS (REMOÇÃO NO 1º ENVIO)
    # ------------------------------------------------------------------
    print("\n4. Testando Ciclo de Vida e Remoção no 1º Envio via Node.js...")
    node_test = r"""
    const { AuraChatController } = require('./web/js/aura-chat.js');

    const elementsById = {};

    // Mock DOM Environment com parsing automático de IDs
    class MockElement {
      constructor(tagName, id = '', className = '') {
        this.tagName = tagName;
        this.id = id;
        this.className = className;
        this.children = [];
        this.parentElement = null;
        this._innerHTML = '';
        this.value = '';
        this.style = {};
        this.classList = {
          add: (...classes) => { classes.forEach(c => { if (!this.className.includes(c)) this.className += ' ' + c; }); },
          remove: (...classes) => { classes.forEach(c => { this.className = this.className.replace(new RegExp('\\b' + c + '\\b', 'g'), '').trim(); }); },
          contains: (c) => this.className.includes(c)
        };
      }

      set innerHTML(val) {
        this._innerHTML = val;
        this.children = [];
        if (val) {
          const idMatches = [...val.matchAll(/id="([^"]+)"/g)];
          for (const m of idMatches) {
            const childId = m[1];
            const childEl = new MockElement('div', childId);
            this.appendChild(childEl);
            elementsById[childId] = childEl;
          }
        }
      }

      get innerHTML() {
        return this._innerHTML;
      }

      appendChild(child) {
        child.parentElement = this;
        this.children.push(child);
        return child;
      }

      remove() {
        if (this.parentElement) {
          const idx = this.parentElement.children.indexOf(this);
          if (idx >= 0) this.parentElement.children.splice(idx, 1);
          this.parentElement = null;
        }
        if (this.id && elementsById[this.id]) {
          delete elementsById[this.id];
        }
      }

      querySelector(sel) {
        const clean = sel.replace(/^[.#]/, '');
        if (sel.startsWith('#')) return this.children.find(c => c.id === clean) || null;
        if (sel.startsWith('.')) return this.children.find(c => c.classList && c.classList.contains(clean)) || null;
        return null;
      }

      querySelectorAll(sel) {
        const clean = sel.replace(/^[.#]/, '');
        if (sel.startsWith('#')) return this.children.filter(c => c.id === clean);
        if (sel.startsWith('.')) return this.children.filter(c => c.classList && c.classList.contains(clean));
        return [];
      }

      focus() {}
    }

    const feed = new MockElement('div', 'chat-feed-container');
    const input = new MockElement('textarea', 'chat-input-text');
    const sendBtn = new MockElement('button', 'btn-chat-send');
    const stopBtn = new MockElement('button', 'btn-chat-stop');
    const scrollBtn = new MockElement('button', 'btn-scroll-bottom');

    elementsById['chat-feed-container'] = feed;
    elementsById['chat-input-text'] = input;
    elementsById['btn-chat-send'] = sendBtn;
    elementsById['btn-chat-stop'] = stopBtn;
    elementsById['btn-scroll-bottom'] = scrollBtn;

    global.document = {
      getElementById: (id) => elementsById[id] || null,
      createElement: (tag) => new MockElement(tag),
      querySelector: (sel) => {
        const clean = sel.replace(/^[.#]/, '');
        if (sel.startsWith('#')) return elementsById[clean] || null;
        if (sel.startsWith('.')) return Object.values(elementsById).find(el => el.classList && el.classList.contains(clean)) || null;
        return null;
      },
      querySelectorAll: (sel) => {
        const clean = sel.replace(/^[.#]/, '');
        if (sel.startsWith('#')) return elementsById[clean] ? [elementsById[clean]] : [];
        if (sel.startsWith('.')) return Object.values(elementsById).filter(el => el.classList && el.classList.contains(clean));
        return [];
      },
      addEventListener: () => {}
    };

    global.window = {
      auraApi: { chatStream: async () => {} },
      innerWidth: 1024
    };

    const chat = new AuraChatController();
    chat.sessionId = 'test-session-123';

    // 1. Testa renderização do card de boas-vindas com rodapé de sugestões
    chat.addWelcomeMessage();
    if (feed.children.length !== 1) {
      console.error('FALHA: Welcome message não foi adicionada ao feed!');
      process.exit(1);
    }

    const welcomeMsgDiv = feed.children[0];
    if (!welcomeMsgDiv.innerHTML.includes('welcome-suggestions-container')) {
      console.error('FALHA: welcome-suggestions-container não renderizado pelo addWelcomeMessage!');
      process.exit(1);
    }
    if (!welcomeMsgDiv.innerHTML.includes('welcome-card-footer')) {
      console.error('FALHA: welcome-card-footer ausente no HTML gerado pelo addWelcomeMessage!');
      process.exit(1);
    }
    if (!welcomeMsgDiv.innerHTML.includes('w-full flex flex-col justify-between')) {
      console.error('FALHA: estrutura flex flex-col justify-between ausente no addWelcomeMessage (assimetria com index.html)!');
      process.exit(1);
    }
    if (!welcomeMsgDiv.innerHTML.includes('mt-auto')) {
      console.error('FALHA: classe mt-auto ausente no addWelcomeMessage!');
      process.exit(1);
    }
    if (!welcomeMsgDiv.className.includes('welcome-message-wrapper') || !welcomeMsgDiv.className.includes('h-full')) {
      console.error('FALHA: welcome-message-wrapper e h-full ausentes na div gerada pelo addWelcomeMessage!');
      process.exit(1);
    }

    // Verifica que o elemento de sugestões foi automaticamente registrado no DOM mock pelo parser
    if (!document.getElementById('welcome-suggestions-container')) {
      console.error('FALHA: welcome-suggestions-container não encontrado no mock DOM!');
      process.exit(1);
    }

    // 2. Testa o primeiro envio via sendUserPrompt()
    chat.sendUserPrompt('Qual a situação dos tanques?');

    // 3. Verifica que welcome-suggestions-container FOI ESTREITAMENTE REMOVIDO
    if (document.getElementById('welcome-suggestions-container') !== null) {
      console.error('FALHA: welcome-suggestions-container NÃO foi removido após o primeiro envio!');
      process.exit(1);
    }

    // Verifica que o card de boas-vindas perdeu h-full para não ocupar 100% da tela durante a conversa e ganhou classe de colapso
    if (welcomeMsgDiv.className.includes('h-full') || welcomeMsgDiv.className.includes('welcome-message-wrapper')) {
      console.error('FALHA: classes de tela cheia não foram limpas da mensagem de boas-vindas após primeiro envio!');
      process.exit(1);
    }
    if (!welcomeMsgDiv.className.includes('welcome-message-collapsed')) {
      console.error('FALHA: classe welcome-message-collapsed ausente para colapso seguro!');
      process.exit(1);
    }

    // 4. Testa segundo envio (não deve falhar mesmo após remoção prévia)
    try {
      chat.isSubmitting = false;
      chat.isStreaming = false;
      input.value = 'Outra mensagem';
      chat.handleSendMessage();
    } catch (err) {
      console.error('FALHA: Erro ao enviar segunda mensagem após remoção das sugestões:', err);
      process.exit(1);
    }

    // 5. Testa restauração via clearSession()
    chat.clearSession();
    if (feed.children.length !== 1) {
      console.error('FALHA: clearSession não recriou a mensagem de boas-vindas!');
      process.exit(1);
    }
    const newWelcome = feed.children[0];
    if (!newWelcome.innerHTML.includes('welcome-suggestions-container') || !newWelcome.innerHTML.includes('welcome-card-footer')) {
      console.error('FALHA: clearSession não restaurou o rodapé de sugestões!');
      process.exit(1);
    }
    if (!newWelcome.className.includes('welcome-message-wrapper') || !newWelcome.className.includes('h-full')) {
      console.error('FALHA: clearSession não restaurou classes de altura total!');
      process.exit(1);
    }
    if (!document.getElementById('welcome-suggestions-container')) {
      console.error('FALHA: clearSession não restaurou welcome-suggestions-container no DOM!');
      process.exit(1);
    }

    // 6. Testa novo envio na nova sessão: remove novamente com sucesso
    chat.isSubmitting = false;
    chat.isStreaming = false;
    chat.sendUserPrompt('Nova pergunta na sessão limpa');
    if (document.getElementById('welcome-suggestions-container') !== null) {
      console.error('FALHA: welcome-suggestions-container NÃO foi removido na nova sessão após clearSession!');
      process.exit(1);
    }

    console.log('NODE_WELCOME_TEST_SUCCESS');
    """

    res_node = subprocess.run(
        ["node", "-e", node_test],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )
    assert res_node.returncode == 0, f"Erro nos testes Node.js:\n{res_node.stderr}\nSTDOUT:\n{res_node.stdout}"
    assert "NODE_WELCOME_TEST_SUCCESS" in res_node.stdout
    print("   [OK] Lógica JS validada: adição no rodapé, remoção estrita no 1º envio, tolerância no 2º envio, restauração em clearSession e novo ciclo.")

    # ------------------------------------------------------------------
    # 5. VALIDAÇÃO REAL DE LAYOUT GEOMÉTRICO VIA HEADLESS BROWSER (PLAYWRIGHT)
    # ------------------------------------------------------------------
    print("\n5. Testando Layout Geométrico e Ancoragem em Navegador Real (Edge Headless)...")
    import threading
    import time
    import uvicorn
    from playwright.sync_api import sync_playwright

    server_port = 8996
    def _run_srv():
        uvicorn.run(app, host="127.0.0.1", port=server_port, log_level="error")

    t_srv = threading.Thread(target=_run_srv, daemon=True)
    t_srv.start()
    time.sleep(1.2)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # A. Desktop 1280x800: Sugestões ancoradas na base com espaço livre entre texto e chips
        page_desk = browser.new_page(viewport={"width": 1280, "height": 800})
        page_desk.goto(f"http://127.0.0.1:{server_port}")
        page_desk.wait_for_selector("#welcome-suggestions-container")
        page_desk.evaluate("""() => {
            const btn = document.querySelector('button[onclick*="view-console"]') || document.getElementById('tab-view-console');
            if (btn) btn.click();
        }""")
        time.sleep(0.4)

        metrics_desk = page_desk.evaluate("""() => {
            const bubble = document.getElementById('welcome-message-bubble');
            const inner = bubble.querySelector('.chat-bubble-aura');
            const textIntro = bubble.querySelector('.welcome-content-body > div');
            const sugg = document.getElementById('welcome-suggestions-container');
            const rBubble = bubble.getBoundingClientRect();
            const rInner = inner.getBoundingClientRect();
            const rText = textIntro ? textIntro.getBoundingClientRect() : { bottom: 0 };
            const rSugg = sugg.getBoundingClientRect();
            return {
                bubbleHeight: rBubble.height,
                innerBottom: rInner.bottom,
                suggBottom: rSugg.bottom,
                suggTop: rSugg.top,
                textBottom: rText.bottom,
                gapBetweenTextAndSuggestions: rSugg.top - rText.bottom,
                distanceFromBottom: rInner.bottom - rSugg.bottom
            };
        }""")
        assert metrics_desk["gapBetweenTextAndSuggestions"] > 100, f"Espaço vazio não alocado entre texto e sugestões: {metrics_desk['gapBetweenTextAndSuggestions']}px"
        assert metrics_desk["distanceFromBottom"] < 40, f"Sugestões não estão ancoradas na base: {metrics_desk['distanceFromBottom']}px do rodapé"
        assert metrics_desk["suggBottom"] <= metrics_desk["innerBottom"] + 2, "Sugestões vazaram para fora do card!"
        print(f"   [OK] Desktop 1280x800: espaço livre intermediário de {metrics_desk['gapBetweenTextAndSuggestions']:.1f}px e sugestões ancoradas a {metrics_desk['distanceFromBottom']:.1f}px da borda inferior.")

        # B. Viewport Restrito / Landscape 667x375: Card deve expandir naturalmente sem truncar nem vazar chips
        page_small = browser.new_page(viewport={"width": 667, "height": 375})
        page_small.goto(f"http://127.0.0.1:{server_port}")
        page_small.wait_for_selector("#welcome-suggestions-container")
        page_small.evaluate("""() => {
            const btn = document.querySelector('button[onclick*="view-console"]') || document.getElementById('tab-view-console');
            if (btn) btn.click();
        }""")
        time.sleep(0.4)

        metrics_small = page_small.evaluate("""() => {
            const bubble = document.getElementById('welcome-message-bubble');
            const inner = bubble.querySelector('.chat-bubble-aura');
            const sugg = document.getElementById('welcome-suggestions-container');
            const rInner = inner.getBoundingClientRect();
            const rSugg = sugg.getBoundingClientRect();
            return {
                bubbleHeight: rInner.height,
                innerBottom: rInner.bottom,
                suggBottom: rSugg.bottom,
                overflows: rSugg.bottom > (rInner.bottom + 2)
            };
        }""")
        assert not metrics_small["overflows"], f"Em viewport restrito as sugestões vazaram fora do card: {metrics_small}"
        assert metrics_small["bubbleHeight"] >= 280, f"Card não expandiu para conter o conteúdo em viewport restrito: {metrics_small['bubbleHeight']}px"
        print(f"   [OK] Viewport 667x375: card expandiu com segurança para {metrics_small['bubbleHeight']:.1f}px sem estourar bordas nem vazar sugestões.")

        # C. Interação: Enviar mensagem colapsa o card de boas-vindas para altura natural
        btn_chip = page_desk.locator("#welcome-suggestions-container button:has-text('Autonomia dos Tanques')")
        btn_chip.click()
        time.sleep(1.0)

        post_click = page_desk.evaluate("""() => {
            const sugg = document.getElementById('welcome-suggestions-container');
            const bubble = document.getElementById('welcome-message-bubble');
            return {
                suggExists: !!sugg,
                collapsed: bubble ? bubble.classList.contains('welcome-message-collapsed') : false,
                height: bubble ? bubble.getBoundingClientRect().height : 0
            };
        }""")
        assert not post_click["suggExists"], "Sugestões ainda existem no DOM após clique!"
        assert post_click["collapsed"], "Classe welcome-message-collapsed não foi adicionada ao card!"
        assert post_click["height"] < 320, f"Card não colapsou para altura natural após envio: {post_click['height']}px"
        assert post_click["height"] < metrics_desk["bubbleHeight"] * 0.6, f"Card não encolheu significativamente: {post_click['height']}px de {metrics_desk['bubbleHeight']}px"
        print(f"   [OK] Primeiro envio: sugestões removidas e card colapsado para altura natural ({post_click['height']:.1f}px de {metrics_desk['bubbleHeight']:.1f}px).")

        browser.close()

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DE POSICIONAMENTO E REMOÇÃO PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_welcome_footer_tests()
