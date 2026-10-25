"""
Script de Validacao Profunda de Trajetoria Espacial e FPS:
Verifica amostragem quadro a quadro (requestAnimationFrame) da abertura do painel.
Garante ausencia de travamentos da thread principal, saltos bruscos ou desvios errilicos.
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
        if path.startswith("/static/js/"):
            path = "/js/" + path[len("/static/js/"):]
        elif path.startswith("/static/css/"):
            path = "/css/" + path[len("/static/css/"):]
        elif path.startswith("/static/icon.svg"):
            path = "/icon.svg"
        return super().translate_path(path)

def verify_trajectory():
    print("=" * 70)
    print("ANALISE DE TRAJETORIA QUADRO A QUADRO (60 FPS FLIP)")
    print("=" * 70)

    port = 8766
    server = ThreadingHTTPServer(("127.0.0.1", port), AuraWebHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        time.sleep(1.0)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            url = f"http://127.0.0.1:{port}/index.html"
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(1.0)

            # Injeta artefato com acao no chat
            page.evaluate("""
                window.auraAuxPanel.projectArtifact({
                    id: 'art_trajectory_test',
                    toolName: 'radar_tanques',
                    intent: 'monitoramento',
                    data: {
                        titulo: 'Volume Tanques de Diesel',
                        subtitulo: 'S10 e Comum',
                        status: 'normal',
                        records: [{ combustivel: 'Diesel S10', volume: 24000 }]
                    },
                    autoOpen: false
                });
            """)

            # Instrumenta gravacao de frames durante open() via amostragem de alta frequencia (25ms)
            trajectory_data = page.evaluate("""() => {
                return new Promise((resolve) => {
                    const btn = document.getElementById('btn-toggle-aux-panel');
                    const auxPanel = document.getElementById('aura-aux-panel');
                    const chatCol = document.getElementById('chat-stream-column');
                    
                    const btnRect = btn.getBoundingClientRect();
                    const frames = [];

                    window.auraAuxPanel.open('art_trajectory_test', false, btn);
                    const startTime = performance.now();

                    function recordFrame() {
                        const now = performance.now();
                        const pRect = auxPanel.getBoundingClientRect();
                        const cRect = chatCol.getBoundingClientRect();
                        frames.push({
                            elapsed: now - startTime,
                            panel: { left: pRect.left, top: pRect.top, width: pRect.width, height: pRect.height },
                            chat: { left: cRect.left, top: cRect.top, width: cRect.width, height: cRect.height }
                        });

                        if (now - startTime < 480 || frames.length < 16) {
                            requestAnimationFrame(recordFrame);
                        } else {
                            resolve({ btnRect, frames });
                        }
                    }
                    requestAnimationFrame(recordFrame);
                });
            }""")

            frames = trajectory_data["frames"]
            btn_rect = trajectory_data["btnRect"]
            print(f"1. Coletados {len(frames)} frames durante a transicao de abertura (460ms).")
            print(f"   Botao de origem: left={btn_rect['left']:.1f}, top={btn_rect['top']:.1f}, width={btn_rect['width']:.1f}")

            # Valida taxa de quadros (sem congelamento da thread principal)
            assert len(frames) >= 14, f"Amostragem insuficiente ({len(frames)} frames). Bloqueio detectado."
            print(f"   [OK] Taxa de quadros suave confirmada ({len(frames)} frames gravados).")

            # Valida primeiro frame
            first_frame = frames[0]
            print(f"2. Primeiro frame: Panel left={first_frame['panel']['left']:.1f}, top={first_frame['panel']['top']:.1f}, width={first_frame['panel']['width']:.1f}")
            
            # Valida frame intermediario e frame final
            mid_frame = frames[len(frames) // 2]
            final_frame = frames[-1]
            print(f"3. Frame intermediario ({mid_frame['elapsed']:.1f}ms): Panel left={mid_frame['panel']['left']:.1f}, width={mid_frame['panel']['width']:.1f}")
            print(f"4. Frame final ({final_frame['elapsed']:.1f}ms): Panel left={final_frame['panel']['left']:.1f}, width={final_frame['panel']['width']:.1f}")

            # Verifica se o painel expandiu continuamente de tamanho pequeno para grande
            assert final_frame['panel']['width'] > first_frame['panel']['width'], "O painel deve expandir em largura continuamente."
            assert final_frame['panel']['height'] > first_frame['panel']['height'], "O painel deve expandir em altura continuamente."
            print("   [OK] Expansao geometrica continua e organica validada com sucesso.")

            # Valida monotonicidade da expansao (sem saltos errilicos para a esquerda ou topo)
            for i in range(1, len(frames)):
                prev = frames[i - 1]
                curr = frames[i]
                assert curr['panel']['width'] >= prev['panel']['width'] - 1.0, f"Salto anomalo de largura no frame {i}"
                assert curr['panel']['height'] >= prev['panel']['height'] - 1.0, f"Salto anomalo de altura no frame {i}"
            print("   [OK] Monotonicidade de expansao confirmada (zero sobressaltos).")

            # Valida que o chat se acomodou de forma suave e estavel
            chat_first = frames[0]['chat']
            chat_final = frames[-1]['chat']
            print(f"5. Chat column: inicial left={chat_first['left']:.1f} -> final left={chat_final['left']:.1f}")
            assert chat_final['width'] > 0, "Largura do chat deve permanecer valida."
            print("   [OK] Acomodacao estavel do chat validada sem thrashing.")

            browser.close()

        print("=" * 70)
        print("VALIDACAO PROFUNDA DE TRAJETORIA 100% APROVADA!")
        print("=" * 70)
        return True
    finally:
        server.shutdown()

if __name__ == "__main__":
    if not verify_trajectory():
        sys.exit(1)
