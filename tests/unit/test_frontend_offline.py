"""
Testes Unitarios do Frontend 100% Offline-First (Fase P0-5).
Valida que todos os assets essenciais (Tailwind, Lucide, Marked, CSS) estao
embarcados localmente em web/static/vendor/, que nao ha nenhuma dependencia
de CDNs publicas (unpkg, cdn.tailwindcss, googleapis, jsdelivr), que as rotas
FastAPI servem os arquivos estaticos corretamente e que a regra inegociavel
de ZERO travessoes e respeitada.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config.settings import BASE_DIR
from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory


@pytest.mark.unit
class TestFrontendOfflineFirst:
    """Suite de testes para garantia de Frontend 100% Offline-First."""

    @classmethod
    def setup_class(cls) -> None:
        """Inicializa caminhos e cliente de teste FastAPI."""
        cls.web_dir = BASE_DIR / "web"
        cls.vendor_dir = cls.web_dir / "static" / "vendor"
        cls.css_dir = cls.web_dir / "css"
        cls.scripts_dir = BASE_DIR / "scripts"

        mem = AuraSessionMemory(db_path=":memory:")
        engine = AuraEngine(tenant_id="test_offline", filial_id="posto_test", session_memory=mem)
        cls.app = create_aura_app(engine)
        cls.client = TestClient(cls.app)

    def test_vendor_assets_exist_and_non_empty(self) -> None:
        """Valida que todos os arquivos vendor existem em web/static/vendor/ com tamanho compativel."""
        assert self.vendor_dir.exists(), f"Diretorio vendor nao encontrado: {self.vendor_dir}"

        expected_assets = {
            "tailwind.min.js": 350_000,  # min ~350 KB
            "lucide.min.js": 350_000,    # min ~350 KB
            "marked.min.js": 30_000,     # min ~30 KB
        }

        for filename, min_bytes in expected_assets.items():
            file_path = self.vendor_dir / filename
            assert file_path.exists(), f"Asset offline ausente: {file_path}"
            file_size = file_path.stat().st_size
            assert file_size >= min_bytes, (
                f"Asset {filename} parece incompleto: tamanho {file_size} bytes (minimo esperado: {min_bytes})"
            )

    def test_index_html_has_zero_remote_cdn_scripts(self) -> None:
        """Valida que web/index.html nao carrega nenhum script ou stylesheet de CDNs remotas."""
        index_file = self.web_dir / "index.html"
        assert index_file.exists(), f"Arquivo index.html nao encontrado: {index_file}"
        content = index_file.read_text(encoding="utf-8")

        # Verifica tags <script src="...">
        script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for src in script_srcs:
            assert not src.startswith("http://") and not src.startswith("https://") and not src.startswith("//"), (
                f"index.html carrega script de CDN remota proibida: {src}"
            )
            assert not any(cdn in src.lower() for cdn in ["unpkg.com", "cdn.tailwindcss", "jsdelivr.net", "cdnjs"]), (
                f"index.html contem referencia de CDN: {src}"
            )

        # Verifica tags <link rel="stylesheet" href="...">
        css_hrefs = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for href in css_hrefs:
            assert not href.startswith("http://") and not href.startswith("https://") and not href.startswith("//"), (
                f"index.html carrega stylesheet de CDN remota proibida: {href}"
            )
            assert not any(cdn in href.lower() for cdn in ["googleapis.com", "gstatic.com", "jsdelivr.net"]), (
                f"index.html contem referencia a fontes ou estilos remotos: {href}"
            )

    def test_showcase_html_has_zero_remote_cdn_scripts(self) -> None:
        """Valida que web/showcase.html nao carrega nenhum script ou estilo de CDNs remotas."""
        showcase_file = self.web_dir / "showcase.html"
        assert showcase_file.exists(), f"Arquivo showcase.html nao encontrado: {showcase_file}"
        content = showcase_file.read_text(encoding="utf-8")

        # Verifica tags <script src="...">
        script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for src in script_srcs:
            assert not src.startswith("http://") and not src.startswith("https://") and not src.startswith("//"), (
                f"showcase.html carrega script de CDN remota proibida: {src}"
            )
            assert not any(cdn in src.lower() for cdn in ["unpkg.com", "cdn.tailwindcss", "jsdelivr.net", "cdnjs"]), (
                f"showcase.html contem referencia de CDN: {src}"
            )

        # Verifica tags <link href="...">
        link_hrefs = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for href in link_hrefs:
            assert not href.startswith("http://") and not href.startswith("https://") and not href.startswith("//"), (
                f"showcase.html carrega recurso remoto proibido: {href}"
            )
            assert not any(cdn in href.lower() for cdn in ["googleapis.com", "gstatic.com", "jsdelivr.net"]), (
                f"showcase.html contem referencia a CDN ou fontes remotas: {href}"
            )

    def test_aura_css_has_zero_remote_imports(self) -> None:
        """Valida que web/css/aura.css nao possui @import de fontes ou estilos externos."""
        css_file = self.css_dir / "aura.css"
        assert css_file.exists(), f"Arquivo aura.css nao encontrado: {css_file}"
        content = css_file.read_text(encoding="utf-8")

        # Verifica se ha @import de URLs externas
        import_matches = re.findall(r'@import\s+(?:url\()?["\']?([^"\'\)\s]+)', content, re.IGNORECASE)
        for imp in import_matches:
            assert not imp.startswith("http://") and not imp.startswith("https://") and not imp.startswith("//"), (
                f"aura.css contem @import externo proibido: {imp}"
            )

    def test_build_showcase_page_script_offline_first(self) -> None:
        """Valida que scripts/build_showcase_page.py nao injeta links de CDNs publicas."""
        script_file = self.scripts_dir / "build_showcase_page.py"
        assert script_file.exists(), f"Script build_showcase_page.py nao encontrado: {script_file}"
        content = script_file.read_text(encoding="utf-8")

        # Proibicao de CDNs externas no gerador
        assert "cdn.tailwindcss.com" not in content, "build_showcase_page.py ainda referencia cdn.tailwindcss.com"
        assert "unpkg.com" not in content, "build_showcase_page.py ainda referencia unpkg.com"
        assert "fonts.googleapis.com" not in content, "build_showcase_page.py ainda referencia fonts.googleapis.com"
        assert "fonts.gstatic.com" not in content, "build_showcase_page.py ainda referencia fonts.gstatic.com"

        # Presenca obrigatoria de referencias locais aos vendors
        assert "/static/vendor/tailwind.min.js" in content
        assert "/static/vendor/lucide.min.js" in content

    def test_fastapi_serves_static_vendor_assets(self) -> None:
        """Valida que a aplicacao FastAPI serve os assets offline com status 200 e content-type correto."""
        resp_tailwind = self.client.get("/static/vendor/tailwind.min.js")
        assert resp_tailwind.status_code == 200
        assert len(resp_tailwind.content) > 350_000

        resp_lucide = self.client.get("/static/vendor/lucide.min.js")
        assert resp_lucide.status_code == 200
        assert len(resp_lucide.content) > 350_000

        resp_marked = self.client.get("/static/vendor/marked.min.js")
        assert resp_marked.status_code == 200
        assert len(resp_marked.content) > 30_000

        resp_css = self.client.get("/static/css/aura.css")
        assert resp_css.status_code == 200
        assert "text/css" in resp_css.headers.get("content-type", "")

    def test_zero_travessoes_in_frontend_offline_files(self) -> None:
        """Garante a regra inegociavel de ZERO travessoes (\u2014 e \u2013) nos arquivos afetados."""
        files_to_check = [
            Path(__file__),
            self.scripts_dir / "build_showcase_page.py",
            self.web_dir / "index.html",
            self.web_dir / "showcase.html",
        ]

        for file_path in files_to_check:
            content = file_path.read_text(encoding="utf-8")
            assert "\u2014" not in content, f"Travessao em-dash (\u2014) encontrado no arquivo: {file_path}"
            assert "\u2013" not in content, f"Travessao en-dash (\u2013) encontrado no arquivo: {file_path}"
