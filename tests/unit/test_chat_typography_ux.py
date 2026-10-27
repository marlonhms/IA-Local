"""
Suite de Testes Unitarios de Tipografia Cognitiva e UX Textual do Chat (Apendice B - Fase 4).
Valida ergonomia tipografica (Bringhurst 68ch, .aura-data-token, .aura-chat-disclosure, tabular-nums),
auto-tokenizacao de valores operacionais e fiscais, regra de Progressive Disclosure,
sinteses deterministicas concisas (genui_active=True vs False), sincronizacao com dist/
e ausencia absoluta de travessoes Unicode (\\u2014 e \\u2013).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

from config.settings import BASE_DIR
from core.aura_engine import AuraEngine, AuraSessionMemory


@pytest.mark.unit
class TestChatTypographyUX:
    """Suite de testes para a Fase 4 do Apendice B de UX Textual do Chat."""

    @classmethod
    def setup_class(cls) -> None:
        """Configuracao de caminhos e infraestrutura de teste."""
        cls.web_dir = BASE_DIR / "web"
        cls.css_file = cls.web_dir / "css" / "aura.css"
        cls.js_file = cls.web_dir / "js" / "aura-chat.js"
        cls.html_file = cls.web_dir / "index.html"
        cls.dist_web_dir = BASE_DIR / "dist" / "AuraBackend" / "_internal" / "web"

        mem = AuraSessionMemory(db_path=":memory:")
        cls.engine = AuraEngine(
            tenant_id="tenant_ux_test",
            filial_id="posto_ux_test",
            session_memory=mem,
        )

    # -------------------------------------------------------------------------
    # a) Presenca das classes e regras ergonomicas em web/css/aura.css
    # -------------------------------------------------------------------------
    def test_css_ergonomic_and_typography_rules(self) -> None:
        """Valida que web/css/aura.css contem as regras de ergonomia tipografica da Fase 1 e 4."""
        assert self.css_file.exists(), f"Arquivo CSS ausente: {self.css_file}"
        css_content = self.css_file.read_text(encoding="utf-8")

        # 1. Regra de Bringhurst: largura otima de leitura 68ch
        assert "max-width: 68ch" in css_content, "Regra max-width: 68ch ausente em web/css/aura.css"

        # 2. Micro-tokens semanticos de dados
        assert ".aura-data-token" in css_content, "Classe .aura-data-token ausente em web/css/aura.css"
        assert "tabular-nums" in css_content, "Propriedade tabular-nums ausente em web/css/aura.css"

        # 3. Progressive disclosure no chat
        assert ".aura-chat-disclosure" in css_content, (
            "Classe .aura-chat-disclosure ausente em web/css/aura.css"
        )

        # 4. Modo de conforto de leitura (Fase 4: fonte 0.96rem)
        assert "0.96rem" in css_content, "Regra font-size: 0.96rem ausente para modo de conforto de leitura"
        assert "reading-mode-comfort" in css_content or "aura-reading-comfort" in css_content, (
            "Classe de modo de conforto de leitura ausente em web/css/aura.css"
        )

    # -------------------------------------------------------------------------
    # b) Tokenizacao automatica de valores operacionais e fiscais
    # -------------------------------------------------------------------------
    def test_auto_tokenization_operational_and_fiscal_values(self) -> None:
        """Valida a auto-tokenizacao de valores operacionais e fiscais em .aura-data-token."""
        test_cases = [
            # Valores monetarios (R$)
            ("Total de R$ 1.500,00 faturado", '<span class="aura-data-token">R$ 1.500,00</span>'),
            ("Preco de R$ 45,90 por item", '<span class="aura-data-token">R$ 45,90</span>'),
            ("Ajuste de R$ -120,50 no caixa", '<span class="aura-data-token">R$ -120,50</span>'),
            # Volumes e vazoes (L, L/min, litros)
            ("Volume de 15.000 L de diesel", '<span class="aura-data-token">15.000 L</span>'),
            ("Vazao de 35 L/min no bico", '<span class="aura-data-token">35 L/min</span>'),
            ("Capacidade de 500 litros", '<span class="aura-data-token">500 litros</span>'),
            # Percentuais e desvios (%)
            ("Variacao de +12.5% no mes", '<span class="aura-data-token">+12.5%</span>'),
            ("Tolerancia de -0.6% da ANP", '<span class="aura-data-token">-0.6%</span>'),
            ("Margem de 15% na pista", '<span class="aura-data-token">15%</span>'),
            # Codigos fiscais e operacionais (CFOP, CST, Rejeicao, cStat)
            ("Operacao sob CFOP 5929", '<span class="aura-data-token">CFOP 5929</span>'),
            ("Regime Monofasico CST 61", '<span class="aura-data-token">CST 61</span>'),
            ("Aliquota zero CST 04", '<span class="aura-data-token">CST 04</span>'),
            ("Classificacao NCM 27101259", '<span class="aura-data-token">NCM 27101259</span>'),
            ("Falha por Rejeicao 778", '<span class="aura-data-token">Rejeicao 778</span>'),
            ("Retorno SEFAZ cStat = 100", '<span class="aura-data-token">cStat = 100</span>'),
        ]

        js_script = """
        const fs = require('fs');
        const { AuraChatController } = require('./web/js/aura-chat.js');
        const controller = new AuraChatController();
        const inputs = JSON.parse(fs.readFileSync(0, 'utf-8'));
        const results = inputs.map(text => controller.applySmartTypographyTokens(text));
        console.log(JSON.stringify(results));
        """

        raw_inputs = [tc[0] for tc in test_cases]
        proc = subprocess.run(
            ["node", "-e", js_script],
            input=json.dumps(raw_inputs),
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        rendered_outputs = json.loads(proc.stdout)

        for (raw_input, expected_token_html), actual_html in zip(test_cases, rendered_outputs):
            assert expected_token_html in actual_html, (
                f"Tokenizacao falhou para '{raw_input}'. Esperado conter '{expected_token_html}', obtido: '{actual_html}'"
            )

    def test_auto_tokenization_respects_code_blocks(self) -> None:
        """Garante que numeros dentro de <code> ou <pre> nao sejam encapsulados por .aura-data-token."""
        js_script = """
        const { AuraChatController } = require('./web/js/aura-chat.js');
        const controller = new AuraChatController();
        const snippet = '<pre><code>SELECT * FROM vendas WHERE total = 1500 AND cfop = 5929;</code></pre>';
        console.log(controller.applySmartTypographyTokens(snippet));
        """
        proc = subprocess.run(["node", "-e", js_script], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        output = proc.stdout.strip()
        assert "aura-data-token" not in output, (
            f"Bloco de codigo nao deveria receber .aura-data-token: {output}"
        )

    def test_auto_tokenization_with_preexisting_tokens_and_multiple_blocks(self) -> None:
        """Garante que a presenca de .aura-data-token existente nao bloqueie a tokenizacao subsequente."""
        js_script = """
        const { AuraChatController } = require('./web/js/aura-chat.js');
        const controller = new AuraChatController();
        const snippet = '<span class="aura-data-token">R$ 100,00</span> e depois 50 litros';
        console.log(controller.applySmartTypographyTokens(snippet));
        """
        proc = subprocess.run(["node", "-e", js_script], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        output = proc.stdout.strip()
        assert '<span class="aura-data-token">R$ 100,00</span>' in output, "Token previo deve ser mantido"
        assert '<span class="aura-data-token">50 litros</span>' in output, "Token subsequente deve ser encapsulado"

    # -------------------------------------------------------------------------
    # c) Regra de Progressive Disclosure quando mensagem longa possui tool card
    # -------------------------------------------------------------------------
    def test_progressive_disclosure_has_tool_card_rule(self) -> None:
        """Valida que mensagens com mais de 3 blocos recebem disclosure apenas com tool card ativo."""
        four_blocks = "<p>Paragrafo 1</p><p>Paragrafo 2</p><p>Paragrafo 3</p><p>Paragrafo 4</p>"

        js_script = f"""
        const {{ AuraChatController }} = require('./web/js/aura-chat.js');
        const controller = new AuraChatController();
        const html = '{four_blocks}';

        const withToolCard = controller.applyProgressiveDisclosure(html, false, true);
        const withoutToolCard = controller.applyProgressiveDisclosure(html, false, false);
        const whileStreaming = controller.applyProgressiveDisclosure(html, true, true);

        console.log(JSON.stringify({{
            withToolCard,
            withoutToolCard,
            whileStreaming
        }}));
        """
        proc = subprocess.run(["node", "-e", js_script], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)

        # 1. Com tool card ativo (hasToolCard === true) -> Encapsula blocos complementares em disclosure
        assert "aura-chat-disclosure" in data["withToolCard"], (
            "Progressive disclosure deveria estar ativo quando hasToolCard=true e blocos > 3"
        )
        assert "<p>Paragrafo 1</p>" in data["withToolCard"], "Primeiro bloco deve permanecer visivel no topo"
        assert "<p>Paragrafo 2</p>" in data["withToolCard"], "Segundo bloco deve permanecer visivel no topo"

        # 2. Sem tool card (hasToolCard === false) -> Nao deve encapsular
        assert "aura-chat-disclosure" not in data["withoutToolCard"], (
            "Progressive disclosure nao deve ser acionado quando hasToolCard=false"
        )

        # 3. Durante streaming (isStillStreaming === true) -> Nao deve encapsular prematuramente
        assert "aura-chat-disclosure" not in data["whileStreaming"], (
            "Progressive disclosure nao deve ser acionado enquanto o streaming ainda estiver ativo"
        )

    # -------------------------------------------------------------------------
    # Toggle de Conforto de Leitura (concise vs comfort)
    # -------------------------------------------------------------------------
    def test_reading_density_toggle_and_modes(self) -> None:
        """Valida o funcionamento do toggle de conforto de leitura (concise vs comfort)."""
        # 1. Valida presenca do botao no HTML
        html_content = self.html_file.read_text(encoding="utf-8")
        assert 'id="btn-chat-reading-density"' in html_content, (
            "Botao #btn-chat-reading-density nao encontrado no cabecalho de web/index.html"
        )
        assert "Aa" in html_content, "Icone tipografico 'Aa' ausente no botao de densidade de leitura"

        # 2. Valida transicao de estados e atributo 'open' no disclosure via Node
        js_script = """
        const { AuraChatController } = require('./web/js/aura-chat.js');
        const c = new AuraChatController();
        const html = '<p>B1</p><p>B2</p><p>B3</p><p>B4</p>';

        const defaultMode = c.getReadingMode();
        c.setReadingMode('concise');
        const conciseOutput = c.applyProgressiveDisclosure(html, false, true);

        c.setReadingMode('comfort');
        const comfortMode = c.getReadingMode();
        const comfortOutput = c.applyProgressiveDisclosure(html, false, true);

        c.toggleReadingMode();
        const toggledMode = c.getReadingMode();

        console.log(JSON.stringify({
            defaultMode,
            conciseHasOpen: conciseOutput.includes(' open>'),
            conciseHasDisclosure: conciseOutput.includes('aura-chat-disclosure'),
            comfortMode,
            comfortHasOpen: comfortOutput.includes(' open>'),
            toggledMode
        }));
        """
        proc = subprocess.run(["node", "-e", js_script], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)

        assert res["defaultMode"] == "concise", "Modo padrao inicial deve ser 'concise'"
        assert res["conciseHasDisclosure"] is True, "Modo conciso deve conter container disclosure"
        assert res["conciseHasOpen"] is False, "Modo conciso nao deve ter o atributo 'open' no disclosure"
        assert res["comfortMode"] == "comfort", "Modo conforto deve reportar 'comfort'"
        assert res["comfortHasOpen"] is True, "Modo conforto deve abrir o disclosure com atributo 'open'"
        assert res["toggledMode"] == "concise", "Toggle a partir de conforto deve retornar para 'concise'"

    # -------------------------------------------------------------------------
    # d) Sinteses deterministicas concisas (genui_active=True vs False)
    # -------------------------------------------------------------------------
    def test_deterministic_contingency_synthesis_dual_channel(self) -> None:
        """Valida que _gerar_sintese_contingencia_ferramenta enxuga o texto quando genui_active=True."""
        # Teste 1: roi_diagnostic
        roi_sample = {
            "status": "success",
            "summary": {
                "total_monthly_loss_brl": 18500.0,
                "estimated_monthly_recovery_brl": 14200.0,
                "roi_90_days_net_brl": 38000.0,
                "roi_multiple": 4.2,
                "guarantee_3x_met": True,
            },
            "breakdown": {
                "lmc_and_tank_shrinkage": 4200.0,
                "convenience_and_pos_cancellations": 3500.0,
                "cashier_shift_discrepancies": 2800.0,
                "pricing_and_carreta_arbitrage": 5200.0,
                "working_capital_selic_cost": 2800.0,
            },
        }

        sintese_roi_gui = self.engine._gerar_sintese_contingencia_ferramenta(
            "roi_diagnostic", roi_sample, "qual o roi?", genui_active=True
        )
        sintese_roi_txt = self.engine._gerar_sintese_contingencia_ferramenta(
            "roi_diagnostic", roi_sample, "qual o roi?", genui_active=False
        )

        assert sintese_roi_gui is not None
        assert sintese_roi_txt is not None
        # Sintese com GUI deve ser enxuta e referenciar o painel lateral
        assert "painel lateral" in sintese_roi_gui
        assert len(sintese_roi_gui.splitlines()) < len(sintese_roi_txt.splitlines())
        # Sintese somente texto deve conter o detalhamento completo dos 5 vetores
        assert "Detalhamento dos 5 Vetores de Perdas" in sintese_roi_txt
        assert "Variacao LMC & Tanques" in sintese_roi_txt

        # Teste 2: pos_audit
        pos_sample = {
            "status": "success",
            "total_operators_analyzed": 8,
            "anomalous_operators_count": 1,
            "cashier_shift_audit": {"status": "CONCILIADO", "discrepancy_brl": 0.0},
            "operators_analysis": [
                {"operator_id": "OP_01", "cancellation_rate_pct": 8.5, "z_score": 2.8, "is_anomaly": True},
                {"operator_id": "OP_02", "cancellation_rate_pct": 1.2, "z_score": 0.3, "is_anomaly": False},
            ],
        }

        sintese_pos_gui = self.engine._gerar_sintese_contingencia_ferramenta(
            "pos_audit", pos_sample, "auditoria pos", genui_active=True
        )
        sintese_pos_txt = self.engine._gerar_sintese_contingencia_ferramenta(
            "pos_audit", pos_sample, "auditoria pos", genui_active=False
        )

        assert sintese_pos_gui is not None
        assert sintese_pos_txt is not None
        assert "painel lateral" in sintese_pos_gui
        assert "Ranking de Operadores" in sintese_pos_txt

        # Teste 3: conciliacao_turno
        turno_sample = {
            "status": "success",
            "metrics": {
                "difference": 0.0,
                "automation_revenue": 45000.0,
                "pos_revenue": 45000.0,
                "automation_volume_liters": 8200.0,
            },
        }

        sintese_turno_gui = self.engine._gerar_sintese_contingencia_ferramenta(
            "conciliacao_turno", turno_sample, "como fechou o turno?", genui_active=True
        )
        sintese_turno_txt = self.engine._gerar_sintese_contingencia_ferramenta(
            "conciliacao_turno", turno_sample, "como fechou o turno?", genui_active=False
        )

        assert sintese_turno_gui is not None
        assert sintese_turno_txt is not None
        assert "painel lateral" in sintese_turno_gui
        assert len(sintese_turno_gui.splitlines()) <= len(sintese_turno_txt.splitlines())

        # Teste 4: lmc_anp
        lmc_sample = {
            "status": "success",
            "resumo_executivo": {
                "status_geral_anp": "CONFORME_ANP",
                "variacao_total_litros": -12.5,
                "variacao_media_pct": -0.15,
            },
        }
        sintese_lmc_gui = self.engine._gerar_sintese_contingencia_ferramenta(
            "lmc_anp", lmc_sample, "como esta o lmc?", genui_active=True
        )
        sintese_lmc_txt = self.engine._gerar_sintese_contingencia_ferramenta(
            "lmc_anp", lmc_sample, "como esta o lmc?", genui_active=False
        )
        assert sintese_lmc_gui is not None
        assert sintese_lmc_txt is not None
        assert "painel lateral" in sintese_lmc_gui
        assert "Portaria 26/1992" in sintese_lmc_txt

    # -------------------------------------------------------------------------
    # e) Sincronizacao 100% identica entre web/ e dist/AuraBackend/_internal/web/
    # -------------------------------------------------------------------------
    def test_dist_web_synchronization(self) -> None:
        """Valida que todos os arquivos web essenciais em dist/ estao presentes e 100% identicos."""
        if not self.dist_web_dir.exists():
            pytest.skip(f"Diretorio {self.dist_web_dir} nao existe no ambiente de teste")

        critical_files = [
            "index.html",
            "css/aura.css",
            "js/aura-chat.js",
            "js/aura-genui-widgets.js",
            "js/aura-triggers.js",
        ]

        for rel in critical_files:
            src = self.web_dir / rel
            dst = self.dist_web_dir / rel
            assert src.exists(), f"Fonte ausente: {src}"
            assert dst.exists(), f"Destino dist ausente: {dst}"
            src_bytes = src.read_bytes()
            dst_bytes = dst.read_bytes()
            assert src_bytes == dst_bytes, (
                f"Dessincronizacao detectada entre {src} ({len(src_bytes)} bytes) e {dst} ({len(dst_bytes)} bytes)"
            )

    # -------------------------------------------------------------------------
    # f) Ausencia absoluta de travessoes Unicode (\u2014 e \u2013)
    # -------------------------------------------------------------------------
    def test_zero_unicode_dashes_strict(self) -> None:
        """Garante a regra inegociavel de ZERO travessoes (\\u2014 e \\u2013) em todo o codigo do projeto."""
        files_to_check = [
            self.web_dir / "index.html",
            self.web_dir / "css" / "aura.css",
            self.web_dir / "js" / "aura-chat.js",
            BASE_DIR / "core" / "aura_engine.py",
            BASE_DIR / "core" / "prompts" / "system_prompts.py",
            Path(__file__),
        ]

        if self.dist_web_dir.exists():
            files_to_check.extend([
                self.dist_web_dir / "index.html",
                self.dist_web_dir / "css" / "aura.css",
                self.dist_web_dir / "js" / "aura-chat.js",
            ])

        # Varredura completa em todos os modulos de codigo do projeto
        for folder_name in ["core", "web", "tests", "scripts", "config", "adapters"]:
            folder = BASE_DIR / folder_name
            if folder.exists():
                for p in folder.rglob("*"):
                    if p.is_file() and p.suffix in (".py", ".js", ".html", ".css"):
                        if "__pycache__" not in str(p) and "node_modules" not in str(p):
                            files_to_check.append(p)

        forbidden = ["\u2014", "\u2013"]
        unique_files = list({f.resolve(): f for f in files_to_check}.values())

        for file_path in unique_files:
            assert file_path.exists(), f"Arquivo para verificacao ausente: {file_path}"
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for ch in forbidden:
                codepoint = f"\\u{ord(ch):04x}"
                assert ch not in content, (
                    f"Travessao proibido {codepoint} detectado no arquivo: {file_path}"
                )
