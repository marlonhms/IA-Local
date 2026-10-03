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
    server = ServerThread(port=8000)
    server.start()
    time.sleep(1.5)

    artifact_dir = Path(r"C:\Users\Marlon\.gemini\antigravity\brain\94da55fc-9aa9-4fa4-a1ff-8e151407b516")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    cockpit_png = artifact_dir / "painel_aura_cockpit.png"
    radar_png = artifact_dir / "painel_aura_radar.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850}, device_scale_factor=2)
        page = context.new_page()
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        time.sleep(1.5)

        # 1. Click on Cockpit Operacional Tab
        try:
            tab_cockpit = page.locator("button[data-tab='cockpit']")
            if tab_cockpit.is_visible():
                tab_cockpit.click()
                time.sleep(2.0)
                page.screenshot(path=str(cockpit_png))
                print(f"[OK] Cockpit screenshot saved: {cockpit_png}")
        except Exception as e:
            print(f"[WARN] Failed cockpit: {e}")

        # 2. Click on Radar 1-Clique Tab
        try:
            tab_radar = page.locator("button[data-tab='triggers']")
            if tab_radar.is_visible():
                tab_radar.click()
                time.sleep(2.0)
                # Click on LMC ANP card
                card_lmc = page.locator("button:has-text('LMC Oficial ANP')").first
                if card_lmc.is_visible():
                    card_lmc.click()
                    time.sleep(1.5)
                page.screenshot(path=str(radar_png))
                print(f"[OK] Radar screenshot saved: {radar_png}")
        except Exception as e:
            print(f"[WARN] Failed radar: {e}")

        context.close()
        browser.close()

    server.stop()
    print("[OK] All screenshots captured!")

if __name__ == "__main__":
    capture()
