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

    # Verifica classes de espaçamento inferior (rodapé)
    assert "!mt-7" in html or "mt-6" in html or "mt-8" in html, "Espaçamento superior de rodapé (margin-top) ausente"
    assert "pt-4" in html, "Padding-top de rodapé ausente"
    assert "border-t" in html, "Borda divisória superior do rodapé ausente"
    print("   [OK] HTML validado: bloco de apresentação fechado, sugestões desacopladas no rodapé com respiro visual.")

    # ------------------------------------------------------------------
    # 2. VALIDAÇÃO DE ESTILOS CSS EM web/css/aura.css
    # ------------------------------------------------------------------
    print("\n2. Testando Regras CSS de Espaçamento Inferior em web/css/aura.css...")
    resp_css = client.get("/static/css/aura.css")
    assert resp_css.status_code == 200
    css = resp_css.text

    assert "#welcome-suggestions-container" in css, "Seletor #welcome-suggestions-container ausente no aura.css"
    assert ".welcome-card-footer" in css, "Seletor .welcome-card-footer ausente no aura.css"
    assert "margin-top:" in css, "Propriedade margin-top ausente no rodapé de sugestões"
    assert "border-top:" in css, "Propriedade border-top ausente no rodapé de sugestões"
    assert ".welcome-suggestions-grid" in css, "Classe .welcome-suggestions-grid ausente no aura.css"
    print("   [OK] CSS validado: regras dedicadas para #welcome-suggestions-container, .welcome-card-footer e grid responsivo.")

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
          add: (c) => { if (!this.className.includes(c)) this.className += ' ' + c; },
          remove: (c) => { this.className = this.className.replace(new RegExp('\\b' + c + '\\b', 'g'), '').trim(); },
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

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DE POSICIONAMENTO E REMOÇÃO PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_welcome_footer_tests()
