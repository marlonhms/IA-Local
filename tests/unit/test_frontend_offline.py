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
import subprocess
import sys
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
        cls.fonts_dir = cls.web_dir / "static" / "fonts"
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

    def test_local_variable_fonts_exist_and_non_empty(self) -> None:
        """Valida que as fontes variaveis locais Geist e Newsreader existem em web/static/fonts/."""
        assert self.fonts_dir.exists(), f"Diretorio de fontes nao encontrado: {self.fonts_dir}"

        expected_fonts = {
            "geist_variable.ttf": 150_000,       # ~169 KB
            "newsreader_variable.ttf": 400_000,  # ~451 KB
        }

        for filename, min_bytes in expected_fonts.items():
            font_path = self.fonts_dir / filename
            assert font_path.exists(), f"Arquivo de fonte ausente: {font_path}"
            file_size = font_path.stat().st_size
            assert file_size >= min_bytes, (
                f"Fonte {filename} parece incompleta: tamanho {file_size} bytes (minimo esperado: {min_bytes})"
            )

    def test_aura_css_declares_offline_font_face_and_tabular_nums(self) -> None:
        """Valida regras @font-face offline e suporte a tabular-nums em web/css/aura.css."""
        css_file = self.css_dir / "aura.css"
        assert css_file.exists(), f"Arquivo aura.css nao encontrado: {css_file}"
        css_content = css_file.read_text(encoding="utf-8")

        # Verifica @font-face para Geist e Newsreader
        assert "@font-face" in css_content
        assert "geist_variable.ttf" in css_content
        assert "newsreader_variable.ttf" in css_content
        assert "truetype-variations" in css_content

        # Verifica tokens de raiz
        assert "--font-sans: 'Geist'" in css_content
        assert "--font-serif: 'Newsreader'" in css_content
        assert "--font-mono: 'Geist Mono'" in css_content

        # Verifica alinhamento numerico tabular
        assert "tabular-nums" in css_content
        assert 'font-feature-settings: "tnum" 1' in css_content

    def test_fastapi_serves_local_variable_fonts(self) -> None:
        """Valida que a aplicacao FastAPI serve os arquivos de fontes TTF locais com status 200."""
        # Rota /static/fonts/
        resp_geist = self.client.get("/static/fonts/geist_variable.ttf")
        assert resp_geist.status_code == 200
        assert len(resp_geist.content) > 150_000

        resp_newsreader = self.client.get("/static/fonts/newsreader_variable.ttf")
        assert resp_newsreader.status_code == 200
        assert len(resp_newsreader.content) > 400_000

        # Rota direta /fonts/
        resp_geist_root = self.client.get("/fonts/geist_variable.ttf")
        assert resp_geist_root.status_code == 200
        assert len(resp_geist_root.content) > 150_000

        resp_newsreader_root = self.client.get("/fonts/newsreader_variable.ttf")
        assert resp_newsreader_root.status_code == 200
        assert len(resp_newsreader_root.content) > 400_000

    def test_showcase_html_uses_offline_font_system_and_tabular_nums(self) -> None:
        """Valida integracao offline de fontes, tailwind config e tabular-nums no showcase.html."""
        showcase_file = self.web_dir / "showcase.html"
        assert showcase_file.exists()
        content = showcase_file.read_text(encoding="utf-8")

        assert "aura.css" in content
        assert "Geist" in content
        assert "Newsreader" in content
        assert "tabular-nums" in content
        assert 'font-feature-settings: "tnum" 1' in content
        assert "/static/icon.svg" in content

    def test_variable_fonts_match_android_source(self) -> None:
        """Valida que as fontes web/static/fonts sao copias fieis das fontes do app Android."""
        android_font_dir = BASE_DIR / "Aura Assistance Android" / "app" / "src" / "main" / "res" / "font"
        if android_font_dir.exists():
            for fname in ["geist_variable.ttf", "newsreader_variable.ttf"]:
                android_file = android_font_dir / fname
                web_file = self.fonts_dir / fname
                assert android_file.exists(), f"Fonte Android ausente: {android_file}"
                assert web_file.exists(), f"Fonte Web ausente: {web_file}"
                assert android_file.read_bytes() == web_file.read_bytes(), (
                    f"Fonte {fname} difere entre Android e Web"
                )

    def test_service_worker_precaches_fonts_and_security(self) -> None:
        """Valida presenca das fontes e scripts criticos na lista PRECACHE_ASSETS do sw.js."""
        sw_file = self.web_dir / "sw.js"
        assert sw_file.exists()
        content = sw_file.read_text(encoding="utf-8")

        assert "/static/fonts/geist_variable.ttf" in content
        assert "/static/fonts/newsreader_variable.ttf" in content
        assert "/static/js/aura-security-architecture.js" in content

    def test_dist_web_is_synchronized_with_source(self) -> None:
        """Valida que todos os arquivos web essenciais em dist/ estao presentes e identicos aos fontes."""
        dist_web = BASE_DIR / "dist" / "AuraBackend" / "_internal" / "web"
        if dist_web.exists():
            critical_files = [
                "index.html",
                "showcase.html",
                "icon.svg",
                "manifest.json",
                "sw.js",
                "css/aura.css",
                "static/icon.svg",
                "static/fonts/geist_variable.ttf",
                "static/fonts/newsreader_variable.ttf",
                "js/aura-security-architecture.js",
                "js/aura-welcome-cockpit.js",
                "js/aura-chat.js",
                "js/aura-cockpit.js",
                "js/aura-api.js",
                "js/aura-app.js",
            ]
            for rel_path in critical_files:
                src_path = self.web_dir / rel_path
                dst_path = dist_web / rel_path
                assert dst_path.exists(), f"Arquivo ausente em dist: {dst_path}"
                assert src_path.read_bytes() == dst_path.read_bytes(), (
                    f"Arquivo dist/{rel_path} desatualizado em relacao a web/{rel_path}"
                )

    def test_header_navigation_architecture_and_seven_items_rule(self) -> None:
        """Valida que o header superior cumpre a Regra dos 7 Itens (5 a 7 ancoras) da Fase 2."""
        index_file = self.web_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text(encoding="utf-8")

        # 1. Extremo Esquerdo: Hamburguer e Identidade com Filial
        assert 'id="btn-toggle-sidebar"' in content
        assert 'id="hud-filial-name"' in content

        # 2. Centro: Badge de Prontidao com pulso verde esmeralda
        assert "Pronta para Atendimento" in content
        assert "Motor Local 100% Offline" in content
        assert "bg-auraEmerald animate-pulse" in content

        # 3. Extremo Direito: Grupo de Produtividade com exatamente 3 botoes visiveis
        assert 'id="header-productive-actions"' in content
        assert 'id="btn-open-palette"' in content
        assert 'id="btn-toggle-aux-panel"' in content
        assert 'id="aux-toggle-beacon"' in content
        assert 'id="btn-new-chat"' in content

        # Extrai o bloco do grupo de produtividade e valida que os botoes visiveis sao exatamente 3
        match_prod = re.search(
            r'<div id="header-productive-actions"[^>]*>([\s\S]*?)</div>\s*</div>\s*</header>',
            content
        )
        assert match_prod is not None, "Bloco header-productive-actions nao encontrado"
        prod_html = match_prod.group(1)

        # Separa os botoes visiveis (fora do bloco hidden)
        visible_part = prod_html.split('<div class="hidden"')[0]
        visible_buttons = re.findall(r'<button\s+id="([^"]+)"', visible_part)
        assert len(visible_buttons) == 3, f"Esperado 3 botoes visiveis no grupo de produtividade, encontrado: {visible_buttons}"
        assert set(visible_buttons) == {"btn-open-palette", "btn-toggle-aux-panel", "btn-new-chat"}

        # Touch targets no header com minimo de 44px
        for btn_id in visible_buttons:
            btn_match = re.search(rf'<button\s+id="{btn_id}"[^>]*class="([^"]*)"', visible_part)
            assert btn_match is not None, f"Botao {btn_id} nao encontrado com atributo class"
            btn_classes = btn_match.group(1)
            assert "min-h-[44px]" in btn_classes, f"Botao {btn_id} nao possui min-h-[44px]: {btn_classes}"

    def test_sidebar_drawer_semantic_clusters_and_quick_search(self) -> None:
        """Valida busca rapida e os 3 clusters semanticos no drawer lateral da Fase 2."""
        index_file = self.web_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text(encoding="utf-8")

        # Campo de busca rapida no topo do drawer
        assert 'id="sidebar-quick-search"' in content
        assert 'type="search"' in content

        # 3 Clusters Semanticos declarados
        assert 'data-cluster="operacao-pista"' in content
        assert 'data-cluster="acoes-rapidas"' in content
        assert 'data-cluster="governanca-sistema"' in content

        # Cluster 1: Operacao da Pista
        assert "Operacao da Pista (Rotina)" in content
        assert 'data-tab="console"' in content
        assert 'data-tab="cockpit"' in content
        assert "Fechamento de Turno" in content
        assert "Oportunidades da Loja" in content
        assert 'id="sidebar-btn-open-history"' in content

        # Cluster 2: Acoes Rapidas em 1-Clique
        assert "Acoes Rapidas em 1-Clique" in content
        assert 'data-tab="triggers"' in content
        assert "Conformidade ANP (LMC)" in content
        assert "Perdas & Quebras de Caixa" in content
        assert "Analitico de Faturamento" in content

        # Cluster 3: Governanca & Sistema
        assert "Governanca & Sistema" in content
        assert 'id="sidebar-btn-open-compliance"' in content
        assert 'id="sidebar-btn-open-security-arch"' in content
        assert 'id="sidebar-btn-open-telemetry"' in content
        assert 'id="sidebar-btn-toggle-modo-pista"' in content
        assert 'id="sidebar-btn-toggle-gpu-guard"' in content
        assert 'id="sidebar-btn-toggle-sfx"' in content
        assert 'id="sidebar-btn-open-automations"' in content

        # Touch targets no drawer com minimo de 48px em conformidade com WCAG 2.1 AA
        drawer_match = re.search(r'<aside id="aura-sidebar-drawer"[\s\S]*?</aside>', content)
        assert drawer_match is not None, "Drawer lateral nao encontrado"
        drawer_html = drawer_match.group(0)

        nav_item_matches = re.findall(r'<button[^>]*class="([^"]*sidebar-nav-item[^"]*)"', drawer_html)
        assert len(nav_item_matches) >= 10, "Menos botoes de navegacao no drawer do que o esperado"
        for classes in nav_item_matches:
            assert "min-h-[48px]" in classes, f"Elemento do drawer sem min-h-[48px]: {classes}"

        # Estado vazio de busca
        assert 'id="sidebar-search-empty"' in content, "Elemento de busca vazia #sidebar-search-empty ausente"

    def test_touch_targets_wcag_and_search_normalization(self) -> None:
        """Valida que o CSS contem regras de touch targets WCAG 2.1 AA (44px desktop / 48px mobile) e JS normaliza busca."""
        css_file = self.css_dir / "aura.css"
        assert css_file.exists()
        css_content = css_file.read_text(encoding="utf-8")

        # Regras de 44px desktop e 48px mobile
        assert "#btn-toggle-sidebar" in css_content
        assert "#sidebar-quick-search" in css_content
        assert "min-height: 44px" in css_content
        assert "@media (max-width: 767px)" in css_content
        assert "min-height: 48px !important" in css_content

        # Logica de normalizacao de busca no JS
        js_file = self.web_dir / "js" / "aura-app.js"
        assert js_file.exists()
        js_content = js_file.read_text(encoding="utf-8")

        assert "sidebar-quick-search" in js_content
        assert "normalizeText" in js_content
        assert "normalize('NFD')" in js_content
        assert "sidebar-search-empty" in js_content
        assert "input:not([disabled])" in js_content

    def test_welcome_readiness_cockpit_phase3(self) -> None:
        """Valida a presenca do Cockpit Ativo de Prontidao no index.html e aura-chat.js (Fase 3)."""
        index_file = self.web_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text(encoding="utf-8")

        # Container principal do cockpit de boas-vindas
        assert 'id="welcome-readiness-cockpit"' in content
        assert "welcome-cockpit" in content
        assert "welcome-cockpit-header" in content
        assert "Prontidao do posto agora" in content or "Prontidão do posto agora" in content
        assert 'id="welcome-cockpit-refresh"' in content
        assert "window.auraWelcomeCockpit.refresh" in content

        # 3 Mini-indicadores operacionais obrigatorios
        assert 'data-indicator="tanques"' in content
        assert "Reserva de Tanques" in content
        assert 'data-indicator="turno"' in content
        assert "Conciliação do Turno" in content or "Conciliacao do Turno" in content
        assert 'data-indicator="lmc"' in content
        assert "Conformidade LMC" in content

        # Estados de skeleton / shimmer e acoes rapidas
        assert "welcome-indicator-skeleton" in content
        assert "skeleton-shimmer" in content
        assert "welcome-indicator-body" in content
        assert "welcome-indicator-value" in content
        assert "welcome-indicator-detail" in content
        assert "window.auraChat.sendUserPrompt" in content

        # Validacao do script aura-welcome-cockpit.js
        cockpit_js = self.web_dir / "js" / "aura-welcome-cockpit.js"
        assert cockpit_js.exists()
        js_content = cockpit_js.read_text(encoding="utf-8")
        assert "AuraWelcomeCockpit" in js_content
        assert "evaluateTanques" in js_content
        assert "evaluateTurno" in js_content
        assert "evaluateLmc" in js_content
        assert "shellHtml" in js_content

        # Validacao do CSS tabular-nums e touch targets
        css_content = (self.css_dir / "aura.css").read_text(encoding="utf-8")
        assert ".welcome-cockpit" in css_content
        assert ".welcome-indicator" in css_content
        assert "tabular-nums" in css_content
        assert 'font-feature-settings: "tnum" 1' in css_content

        # Execucao profunda dos vetores analiticos do cockpit no Node.js
        node_script = """
        const cockpit = require('./web/js/aura-welcome-cockpit.js');

        // Vetor 1: Tanques em reserva e ok
        const t_ok = cockpit.evaluateTanques({ status: 'ok', detalhamento_tanques: [{ codtan: '1', combustivel: 'GC', status_operacional: 'OPERACIONAL', autonomia_critica_horas: 30.5 }] });
        if (t_ok.state !== 'ok' || !t_ok.value.includes('Acima de 24 h')) process.exit(1);

        const t_alert = cockpit.evaluateTanques({ status: 'ok', detalhamento_tanques: [{ codtan: '1', combustivel: 'GC', status_operacional: 'OPERACIONAL', autonomia_critica_horas: 10.0, alerta_critico: true }] });
        if (t_alert.state !== 'alert' || !t_alert.value.includes('reserva')) process.exit(2);

        const t_neutral = cockpit.evaluateTanques(null);
        if (t_neutral.state !== 'neutral' || !t_neutral.detail.includes('Aguardando')) process.exit(3);

        // Vetor 2: Turno conciliado, furo e em andamento
        const u_ok = cockpit.evaluateTurno({ status: 'ok', data_auditada: '2026-10-22', resumo_executivo: { status_conciliacao: 'CONCILIADO' } });
        if (u_ok.state !== 'ok' || u_ok.value !== 'Batido') process.exit(4);

        const u_alert = cockpit.evaluateTurno({ status: 'ok', data_auditada: '2026-10-22', resumo_executivo: { status_conciliacao: 'FURO_DE_CAIXA', diferenca_financeira_caixa: -150.0 } });
        if (u_alert.state !== 'alert' || u_alert.value !== 'Divergente') process.exit(5);

        const u_prog = cockpit.evaluateTurno({ status: 'ok', data_auditada: '2026-10-22', resumo_executivo: { status_conciliacao: 'TURNO_EM_ANDAMENTO', diferenca_financeira_caixa: -20.0 } });
        if (u_prog.state !== 'attention' || u_prog.value !== 'Em andamento') process.exit(6);

        const u_neutral = cockpit.evaluateTurno(null);
        if (u_neutral.state !== 'neutral' || !u_neutral.detail.includes('Aguardando')) process.exit(7);

        // Vetor 3: LMC conforme e fora da tolerancia
        const l_ok = cockpit.evaluateLmc({ status: 'ok', resumo_executivo: { status_geral_anp: 'CONFORME_ANP', total_tanques_analisados: 4, total_tanques_alerta: 0, variacao_volumetrica_geral_pct: 0.15 } });
        if (l_ok.state !== 'ok' || l_ok.value !== 'Conforme') process.exit(8);

        const l_alert = cockpit.evaluateLmc({ status: 'ok', resumo_executivo: { status_geral_anp: 'ALERTA_ANP', total_tanques_analisados: 4, total_tanques_alerta: 1, tanques_em_alerta: [{ tanque: '2', variacao_pct: -0.85 }] } });
        if (l_alert.state !== 'alert' || !l_alert.value.includes('fora')) process.exit(9);

        const l_neutral = cockpit.evaluateLmc(null);
        if (l_neutral.state !== 'neutral' || !l_neutral.detail.includes('Aguardando')) process.exit(10);
        """
        proc = subprocess.run(["node", "-e", node_script], cwd=str(BASE_DIR), capture_output=True, text=True)
        assert proc.returncode == 0, f"Falha na validacao profunda de vetores no Node.js: {proc.stderr}"

    def test_showcase_hero_problem_first_phase3(self) -> None:
        """Valida que o Hero no showcase.html e build_showcase_page.py adota abordagem Problem-First (Fase 3)."""
        showcase_file = self.web_dir / "showcase.html"
        assert showcase_file.exists()
        content = showcase_file.read_text(encoding="utf-8")

        # Validacao de sincronizacao exata com scripts/build_showcase_page.py
        if str(self.scripts_dir) not in sys.path:
            sys.path.insert(0, str(self.scripts_dir))
        import build_showcase_page
        generated_html = build_showcase_page.generate_showcase_html()
        assert generated_html == content, "scripts/build_showcase_page.py e web/showcase.html nao estao perfeitamente sincronizados"

        # Headline Problem-First universal (sem nichar em postos de combustivel)
        assert "Perdas financeiras invisíveis, furos de caixa e desvios de estoque custam caro para o seu negócio." in content
        assert "conectando a qualquer banco de dados sem trocar o seu sistema atual" in content
        assert "perda de combustível" not in content
        assert "multas da ANP" not in content
        for erp_brand in ("WebPosto", "Linx", "Totvs", "Sankhya", "Alterdata"):
            assert erp_brand not in content, f"Marca de ERP citada no showcase: {erp_brand}"

        # 3 Badges de Autoridade Tecnica
        assert "Zero gravação no sistema de gestão (100% somente leitura)" in content
        assert "Economia de até 95% em custos de IA" in content
        assert "Resposta local sub-100ms na rede da sua empresa" in content

        # CTAs Duplos
        assert "Testar Diagnóstico ao Vivo" in content
        assert "Inspecionar Script SQL Auditável" in content
        assert "window.auraTour.scrollToSection('sec-chat-graph')" in content
        assert "window.auraSecurityArchitecture.openModal()" in content

        # Blindagem de termos tecnicos no showcase e no gerador
        forbidden = [
            "postgresql", "postgres", "sqlite", "spacy", "pgvector",
            "transformers", "chromadb", "chroma", "ollama", "groq",
            "llama", "langchain", "huggingface"
        ]
        content_lower = content.lower()
        for term in forbidden:
            assert term not in content_lower, f"Termo proibido '{term}' vazado no showcase"
        gen_lower = generated_html.lower()
        for term in forbidden:
            assert term not in gen_lower, f"Termo proibido '{term}' vazado no build_showcase_page.py"

    def test_cache_and_precache_versions_phase3(self) -> None:
        """Valida incremento de versao de cache em index.html, showcase.html e sw.js (Fase 3)."""
        index_content = (self.web_dir / "index.html").read_text(encoding="utf-8")
        assert "v=2.10.22" in index_content

        showcase_content = (self.web_dir / "showcase.html").read_text(encoding="utf-8")
        assert "v=2.10.22" in showcase_content

        sw_content = (self.web_dir / "sw.js").read_text(encoding="utf-8")
        assert "aura-pwa-v18" in sw_content
        assert "/static/js/aura-welcome-cockpit.js" in sw_content

    def test_zero_travessoes_in_frontend_offline_files(self) -> None:
        """Garante a regra inegociavel de ZERO travessoes (\u2014 e \u2013) nos arquivos afetados."""
        files_to_check = [
            Path(__file__),
            self.scripts_dir / "build_showcase_page.py",
            self.scripts_dir / "verify_spatial_trajectory.py",
            self.web_dir / "index.html",
            self.web_dir / "showcase.html",
            self.css_dir / "aura.css",
            self.web_dir / "static" / "icon.svg",
            self.web_dir / "icon.svg",
            self.web_dir / "sw.js",
            self.web_dir / "js" / "aura-welcome-cockpit.js",
            self.web_dir / "js" / "aura-chat.js",
            self.web_dir / "js" / "aura-security-architecture.js",
            self.web_dir / "js" / "aura-cockpit.js",
            self.web_dir / "js" / "aura-api.js",
            self.web_dir / "js" / "aura-app.js",
            BASE_DIR / "core" / "aura_api.py",
            BASE_DIR / "docs" / "roadmap_uiux_inspiracao_lovable.md",
        ]

        for file_path in files_to_check:
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                assert "\u2014" not in content, f"Travessao em-dash (\u2014) encontrado no arquivo: {file_path}"
                assert "\u2013" not in content, f"Travessao en-dash (\u2013) encontrado no arquivo: {file_path}"


