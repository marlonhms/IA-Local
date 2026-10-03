import sys
import os
import time
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from core.aura_api import create_aura_app

app = create_aura_app()

class ServerThread(threading.Thread):
    def __init__(self, host="127.0.0.1", port=8000):
        super().__init__(daemon=True)
        config = uvicorn.Config(app, host=host, port=port, log_level="error")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

def capture():
    server = ServerThread(port=8003)
    server.start()
    time.sleep(1.5)

    artifact_dir = Path(r"C:\Users\Marlon\.gemini\antigravity\brain\94da55fc-9aa9-4fa4-a1ff-8e151407b516")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    desktop_fx_png = artifact_dir / "painel_aura_desktop_fx.png"
    palette_png = artifact_dir / "painel_aura_command_palette.png"
    mobile_detected_png = artifact_dir / "painel_aura_mobile_detected.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # -------------------------------------------------------------
        # 1. Desktop Experience (1440x900) com Aurora Boreal & Glance Bar
        # -------------------------------------------------------------
        context_desktop = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            has_touch=False
        )
        page_desktop = context_desktop.new_page()
        page_desktop.goto("http://127.0.0.1:8003", wait_until="networkidle")
        time.sleep(2.0)

        # Move o mouse para acionar o efeito specular glance sobre um card
        page_desktop.mouse.move(500, 320)
        time.sleep(0.5)

        page_desktop.screenshot(path=str(desktop_fx_png))
        print(f"[OK] Desktop FX screenshot saved: {desktop_fx_png}")

        # -------------------------------------------------------------
        # 2. Command Palette Executiva (Ctrl+K)
        # -------------------------------------------------------------
        btn_palette = page_desktop.locator("#btn-open-palette")
        if btn_palette.is_visible():
            btn_palette.click()
        else:
            page_desktop.keyboard.press("Control+k")
        time.sleep(1.0)
        page_desktop.screenshot(path=str(palette_png))
        print(f"[OK] Command Palette screenshot saved: {palette_png}")

        context_desktop.close()

        # -------------------------------------------------------------
        # 3. Mobile Device Detection & Adaptive UX (412x915)
        # -------------------------------------------------------------
        context_mobile = browser.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=2,
            has_touch=True,
            is_mobile=True,
            user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page_mobile = context_mobile.new_page()
        page_mobile.goto("http://127.0.0.1:8003", wait_until="networkidle")
        time.sleep(2.0)

        page_mobile.screenshot(path=str(mobile_detected_png))
        print(f"[OK] Mobile Detected screenshot saved: {mobile_detected_png}")

        context_mobile.close()
        browser.close()

    server.stop()
    print("[OK] All FX screenshots captured successfully!")

if __name__ == "__main__":
    capture()
