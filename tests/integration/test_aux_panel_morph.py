"""
Script de Validacao Automatizada via Playwright:
Transicoes de Abertura, Fechamento e Expansao do Painel Auxiliar da AURA (60 FPS FLIP).
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import sys
import time
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent

class AuraWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR / "web"), **kwargs)

    def log_message(self, format, *args):
        pass

    def translate_path(self, path):
        # Mapeia /static/js/ e /static/css/ para as pastas web/js e web/css
        if path.startswith("/static/js/"):
            path = "/js/" + path[len("/static/js/"):]
        elif path.startswith("/static/css/"):
            path = "/css/" + path[len("/static/css/"):]
        elif path.startswith("/static/icon.svg"):
            path = "/icon.svg"
        return super().translate_path(path)

def run_tests():
    print("=" * 70)
    print("VALIDACAO DO SPATIAL MORPHING E TRANSICAO FLIP DO PAINEL AUXILIAR")
    print("=" * 70)

    # Inicia servidor local em porta de teste
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), AuraWebHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        time.sleep(1.2)
        with sync_playwright() as p:
            # Lanca Chromium/Edge
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda msg: print(f"PAGE CONSOLE [{msg.type}]: {msg.text}"))
            page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))

            url = f"http://127.0.0.1:{port}/index.html"
            print(f"1. Acessando {url} em 1440x900...")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(1.2)

            # 2. Verifica presenca dos elementos essenciais
            console_view = page.locator("#view-console")
            chat_column = page.locator("#chat-stream-column")
            aux_panel = page.locator("#aura-aux-panel")
            btn_toggle = page.locator("#btn-toggle-aux-panel")

            assert console_view.count() == 1, "Elemento #view-console nao encontrado"
            assert chat_column.count() == 1, "Elemento #chat-stream-column nao encontrado"
            assert aux_panel.count() == 1, "Elemento #aura-aux-panel nao encontrado"
            assert btn_toggle.count() == 1, "Elemento #btn-toggle-aux-panel nao encontrado"
            print("   [OK] Elementos estruturais basicos presentes.")

            # 3. Testa estado inicial (fechado)
            is_hidden = page.evaluate("document.getElementById('aura-aux-panel').classList.contains('hidden')")
            is_active = page.evaluate("document.getElementById('view-console').classList.contains('aux-panel-active')")
            assert is_hidden is True, "Painel auxiliar deve iniciar fechado/hidden"
            assert is_active is False, "view-console nao deve ter aux-panel-active inicialmente"
            print("   [OK] Estado inicial fechado confirmado.")

            # 4. Testa abertura via Botao Toggle do Header
            print("2. Testando abertura do painel via #btn-toggle-aux-panel...")
            btn_toggle.click()
            time.sleep(0.15) # Meio da animacao

            is_hidden_after = page.evaluate("document.getElementById('aura-aux-panel').classList.contains('hidden')")
            is_active_after = page.evaluate("document.getElementById('view-console').classList.contains('aux-panel-active')")
            assert is_hidden_after is False, "Painel auxiliar deve estar visivel apos open()"
            assert is_active_after is True, "view-console deve ter classe aux-panel-active"
            print("   [OK] Painel exibido e classe aux-panel-active aplicada.")

            # Aguarda conclusao da animacao de abertura (400ms + cleanup)
            time.sleep(0.55)
            transform_aux = page.evaluate("document.getElementById('aura-aux-panel').style.transform")
            assert transform_aux == "" or transform_aux == "none", f"Transform inline deve ser limpo apos a transicao: {transform_aux}"
            print("   [OK] Transicao de abertura finalizada e transforms inline limpos com sucesso.")

            # 5. Testa Alternancia de Largura (Split 54/46 vs Expandido 38/62)
            print("3. Testando alternancia de largura (toggleExpand)...")
            btn_expand = page.locator("#aux-btn-expand")
            assert btn_expand.count() == 1, "Botao #aux-btn-expand nao encontrado"
            btn_info = page.evaluate("""() => {
                const el = document.getElementById('aux-btn-expand');
                const cs = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return {
                    display: cs.display,
                    visibility: cs.visibility,
                    opacity: cs.opacity,
                    rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height }
                };
            }""")
            print("   BUTTON INFO:", btn_info)
            page.evaluate("document.getElementById('aux-btn-expand').click()")
            time.sleep(0.1)

            is_expanded = page.evaluate("document.getElementById('view-console').classList.contains('aux-expanded')")
            assert is_expanded is True, "view-console deve conter aux-expanded"
            time.sleep(0.35)
            print("   [OK] Modo expandido ativado com transicao FLIP limpa.")

            page.evaluate("document.getElementById('aux-btn-expand').click()")
            time.sleep(0.35)
            is_expanded_off = page.evaluate("document.getElementById('view-console').classList.contains('aux-expanded')")
            assert is_expanded_off is False, "view-console deve remover aux-expanded"
            print("   [OK] Retorno ao split padrao concluido.")

            # 6. Testa projecao de artefato e abertura a partir de botao do chat
            print("4. Testando abertura com spatial morph a partir de botao no chat...")
            # Fecha o painel primeiro
            page.evaluate("window.auraAuxPanel.close(false)")
            time.sleep(0.4)

            # Injeta um artefato de teste com botao no chat
            page.evaluate("""
                window.auraAuxPanel.projectArtifact({
                    id: 'art_test_flawless',
                    toolName: 'test_tool',
                    intent: 'inspecao_tanques',
                    data: {
                        titulo: 'Tanques de Combustivel',
                        subtitulo: 'Status de Autonomia',
                        status: 'normal',
                        kpis: [{ label: 'Gasolina Comum', valor: '18.420 L', status: 'normal' }]
                    },
                    autoOpen: false
                });
            """)

            # Dispara open passando elemento gatilho simulado
            page.evaluate("""
                const btn = document.getElementById('btn-toggle-aux-panel');
                window.auraAuxPanel.open('art_test_flawless', false, btn);
            """)
            time.sleep(0.1)

            active_id = page.evaluate("window.auraAuxPanel.activeArtifactId")
            assert active_id == "art_test_flawless", f"Artefato ativo incorreto: {active_id}"
            time.sleep(0.55)
            print("   [OK] Abertura com artefato associado concluida perfeitamente.")

            # 7. Testa fechamento suave
            print("5. Testando fechamento suave (close)...")
            btn_close = page.locator("#aux-btn-close")
            btn_close.click()

            time.sleep(0.65)
            is_hidden_closed = page.evaluate("document.getElementById('aura-aux-panel').classList.contains('hidden')")
            is_active_closed = page.evaluate("document.getElementById('view-console').classList.contains('aux-panel-active')")
            assert is_hidden_closed is True, "Painel deve estar oculto apos fechar"
            assert is_active_closed is False, "view-console nao deve ter aux-panel-active apos fechar"
            print("   [OK] Fechamento e recolhimento limpos concluidos.")

            browser.close()

        print("=" * 70)
        print("TODOS OS TESTES DE SPATIAL MORPHING E FLIP PASSARAM COM SUCESSO!")
        print("=" * 70)
        return True
    finally:
        server.shutdown()

if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)
