"""
Suite de Testes Unitarios de Sinergia Dual-Channel, Nitidez Optica e Coreografia (Apendice C).
Valida nitidez optica no Windows (ClearType subpixel antialiasing, ausencia de transform residual),
escala de contraste e legibilidade (.prose-aura >= #e2e8f0, lead #f8fafc, tamanho 0.935rem),
eliminacao de text-xs em fluxos textuais, desativacao de autoOpen apressado,
remocao de disclosure duplicado com Canvas ativo, contrato Zero Repeticao no backend e prompts,
limpeza de redundancia interna no Canvas (cockpit de pista e dupla persona adaptativa),
paridade com dist/ e zero travessoes Unicode.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
import pytest

from config.settings import BASE_DIR


@pytest.mark.unit
class TestSinergiaDualChannelPhase1:
    """Suite de testes para a Fase 1 do Apendice C: Nitidez Optica e Renderizacao Cristalina."""

    @classmethod
    def setup_class(cls) -> None:
        """Caminhos dos artefatos estaticos de frontend."""
        cls.web_dir = BASE_DIR / "web"
        cls.dist_web_dir = BASE_DIR / "dist" / "AuraBackend" / "_internal" / "web"
        cls.css_file = cls.web_dir / "css" / "aura.css"
        cls.dist_css_file = cls.dist_web_dir / "css" / "aura.css"
        cls.js_file = cls.web_dir / "js" / "aura-chat.js"
        cls.dist_js_file = cls.dist_web_dir / "js" / "aura-chat.js"
        cls.html_file = cls.web_dir / "index.html"
        cls.dist_html_file = cls.dist_web_dir / "index.html"

    # -------------------------------------------------------------------------
    # 1. Nitidez Optica e Restauracao de Subpixel ClearType em aura.css
    # -------------------------------------------------------------------------
    def test_subpixel_antialiasing_and_gpu_cleanup(self) -> None:
        """Valida que o CSS restaura subpixel-antialiased e elimina transforms residuais."""
        assert self.css_file.exists(), f"Arquivo CSS ausente: {self.css_file}"
        css = self.css_file.read_text(encoding="utf-8")

        # 1.1 html e body devem usar subpixel-antialiased
        assert "subpixel-antialiased" in css, "subpixel-antialiased ausente em aura.css"

        # 1.2 Bolhas de chat (.chat-bubble-aura e .chat-bubble-user) com subpixel e sem transform
        assert ".chat-bubble-aura" in css, ".chat-bubble-aura ausente em aura.css"
        assert ".chat-bubble-user" in css, ".chat-bubble-user ausente em aura.css"

        # 1.3 Verificar que nao ha antialiased em escala de cinza forcado no html/body ou bolhas
        match_aura = re.search(r"\.chat-bubble-aura\s*\{([^}]+)\}", css)
        assert match_aura is not None, "Bloco .chat-bubble-aura nao localizado"
        aura_body = match_aura.group(1)
        assert "-webkit-font-smoothing: subpixel-antialiased" in aura_body, (
            ".chat-bubble-aura deve usar -webkit-font-smoothing: subpixel-antialiased"
        )
        assert "transform: none !important" in aura_body, (
            ".chat-bubble-aura deve ter transform: none !important para evitar rasterizacao borrada"
        )
        assert "will-change: auto !important" in aura_body, (
            ".chat-bubble-aura deve ter will-change: auto !important"
        )

        match_user = re.search(r"\.chat-bubble-user\s*\{([^}]+)\}", css)
        assert match_user is not None, "Bloco .chat-bubble-user nao localizado"
        user_body = match_user.group(1)
        assert "-webkit-font-smoothing: subpixel-antialiased" in user_body, (
            ".chat-bubble-user deve usar -webkit-font-smoothing: subpixel-antialiased"
        )
        assert "transform: none !important" in user_body, (
            ".chat-bubble-user deve ter transform: none !important"
        )

    # -------------------------------------------------------------------------
    # 2. Elevacao de Contraste e Escala Modular Anti-Embacamento
    # -------------------------------------------------------------------------
    def test_contrast_and_modular_font_scale(self) -> None:
        """Valida que a cor base e #e2e8f0, lead e #f8fafc e fonte do chat e 0.935rem."""
        css = self.css_file.read_text(encoding="utf-8")

        # 2.1 prose-aura com fonte 0.935rem e cor #e2e8f0
        match_prose = re.search(r"\.prose-aura\s*\{([^}]+)\}", css)
        assert match_prose is not None, "Bloco .prose-aura nao localizado"
        prose_body = match_prose.group(1)
        assert "font-size: 0.935rem" in prose_body, (
            ".prose-aura deve ter font-size: 0.935rem para ergonomia e nitidez"
        )
        assert "color: #e2e8f0" in prose_body, (
            ".prose-aura base deve ter color: #e2e8f0 (Slate-200) para contraste otico"
        )
        assert "line-height: 1.65" in prose_body, (
            ".prose-aura deve ter line-height: 1.65 para ritmo vertical confortavel"
        )

        # 2.2 Lead paragraph (.prose-aura > p:first-of-type) com cor #f8fafc e 0.96rem
        match_lead = re.search(r"\.prose-aura\s*>\s*p:first-of-type\s*\{([^}]+)\}", css)
        assert match_lead is not None, "Bloco .prose-aura > p:first-of-type nao localizado"
        lead_body = match_lead.group(1)
        assert "color: #f8fafc" in lead_body, (
            "Paragrafo lead do chat deve ter color: #f8fafc (Slate-50)"
        )
        assert "font-size: 0.96rem" in lead_body, (
            "Paragrafo lead do chat deve ter font-size: 0.96rem"
        )

    # -------------------------------------------------------------------------
    # 3. Proibicao de text-xs em Fluxos de Leitura
    # -------------------------------------------------------------------------
    def test_elimination_of_text_xs_in_disclosure_reading_flows(self) -> None:
        """Valida que o disclosure no chat e CSS nao utilizam text-xs (12px) para leitura."""
        css = self.css_file.read_text(encoding="utf-8")
        js = self.js_file.read_text(encoding="utf-8")

        # 3.1 CSS: regras de disclosure devem manter 0.935rem e cor #e2e8f0
        assert ".aura-chat-disclosure" in css, ".aura-chat-disclosure ausente no CSS"
        match_disc = re.search(r"\.aura-chat-disclosure\s+\.prose-aura[^{]*\{([^}]+)\}", css)
        assert match_disc is not None, "Regra de nitidez para texto dentro de disclosure ausente"
        disc_body = match_disc.group(1)
        assert "font-size: 0.935rem" in disc_body, (
            "Texto do disclosure deve manter font-size: 0.935rem"
        )
        assert "color: #e2e8f0" in disc_body, (
            "Texto do disclosure deve manter color: #e2e8f0"
        )

        # 3.2 JS: containers internos de disclosure nao devem ter text-xs com text-slate-300
        assert "text-xs text-slate-300" not in js, (
            "aura-chat.js ainda contem text-xs text-slate-300 em fluxo de leitura"
        )
        assert "text-[0.935rem]" in js, (
            "aura-chat.js deve aplicar text-[0.935rem] no container do disclosure"
        )

    # -------------------------------------------------------------------------
    # 4. Paridade 100% com dist/
    # -------------------------------------------------------------------------
    def test_dist_web_synchronization(self) -> None:
        """Garante sincronizacao byte a byte entre web/ e dist/AuraBackend/_internal/web/."""
        assert self.dist_css_file.exists(), f"CSS em dist ausente: {self.dist_css_file}"
        assert self.dist_js_file.exists(), f"JS em dist ausente: {self.dist_js_file}"
        assert self.dist_html_file.exists(), f"HTML em dist ausente: {self.dist_html_file}"

        web_css = self.css_file.read_text(encoding="utf-8")
        dist_css = self.dist_css_file.read_text(encoding="utf-8")
        assert web_css == dist_css, "web/css/aura.css difere de dist/.../aura.css"

        web_js = self.js_file.read_text(encoding="utf-8")
        dist_js = self.dist_js_file.read_text(encoding="utf-8")
        assert web_js == dist_js, "web/js/aura-chat.js difere de dist/.../aura-chat.js"

        web_html = self.html_file.read_text(encoding="utf-8")
        dist_html = self.dist_html_file.read_text(encoding="utf-8")
        assert web_html == dist_html, "web/index.html difere de dist/.../index.html"

    # -------------------------------------------------------------------------
    # 5. Conformidade Estrita: ZERO Travessoes Unicode
    # -------------------------------------------------------------------------
    def test_zero_unicode_dashes_phase1(self) -> None:
        """Valida a regra de ZERO travessoes Unicode (\\u2014 e \\u2013) nos arquivos da Fase 1."""
        files_to_check = [
            self.css_file,
            self.dist_css_file,
            self.js_file,
            self.dist_js_file,
            self.html_file,
            self.dist_html_file,
            Path(__file__),
            BASE_DIR / "scripts" / "apply_phase1_sinergia.py",
        ]
        for fpath in files_to_check:
            content = fpath.read_text(encoding="utf-8")
            c_em = content.count("\u2014")
            c_en = content.count("\u2013")
            assert c_em == 0, f"Arquivo {fpath} contem {c_em} ocorrencias de em-dash (\\u2014)"
            assert c_en == 0, f"Arquivo {fpath} contem {c_en} ocorrencias de en-dash (\\u2013)"


@pytest.mark.unit
class TestSinergiaDualChannelPhase2:
    """Suite de testes para a Fase 2 do Apendice C: Coreografia Sequencial e Card de Ponte."""

    @classmethod
    def setup_class(cls) -> None:
        """Caminhos dos artefatos estaticos de frontend."""
        cls.web_dir = BASE_DIR / "web"
        cls.dist_web_dir = BASE_DIR / "dist" / "AuraBackend" / "_internal" / "web"
        cls.chat_js = cls.web_dir / "js" / "aura-chat.js"
        cls.dist_chat_js = cls.dist_web_dir / "js" / "aura-chat.js"
        cls.aux_js = cls.web_dir / "js" / "aura-aux-panel.js"
        cls.dist_aux_js = cls.dist_web_dir / "js" / "aura-aux-panel.js"

    # -------------------------------------------------------------------------
    # 1. Desativacao do autoOpen Apressado do Canvas
    # -------------------------------------------------------------------------
    def test_auto_open_disabled_on_streaming_and_default(self) -> None:
        """Valida que autoOpen e false como padrao para permitir leitura previa no chat."""
        chat_content = self.chat_js.read_text(encoding="utf-8")
        aux_content = self.aux_js.read_text(encoding="utf-8")

        # 1.1 aura-aux-panel.js default parameter
        assert "autoOpen = false" in aux_content, (
            "projectArtifact em aura-aux-panel.js deve ter parametro default autoOpen = false"
        )

        # 1.2 hydrateGenUISlot e renderToolInlineWidget passam autoOpen: false
        assert "autoOpen: false" in chat_content, (
            "aura-chat.js deve configurar autoOpen: false ao projetar artefatos"
        )
        # Nao deve haver chamadas com autoOpen: true em aura-chat.js
        assert "autoOpen: true" not in chat_content, (
            "aura-chat.js nao deve forcar autoOpen: true prematuramente"
        )

    # -------------------------------------------------------------------------
    # 2. Remocao do Accordion Conflitante +Detalhes em Respostas com Canvas
    # -------------------------------------------------------------------------
    def test_no_duplicate_disclosure_when_canvas_active(self) -> None:
        """Valida que mensagens com Canvas acoplado (hasToolCard=true) NAO geram disclosure no chat."""
        four_blocks = "<p>Paragrafo 1</p><p>Paragrafo 2</p><p>Paragrafo 3</p><p>Paragrafo 4</p>"

        js_script = f"""
        const {{ AuraChatController }} = require('./web/js/aura-chat.js');
        const controller = new AuraChatController();
        const html = '{four_blocks}';

        const withCanvas = controller.applyProgressiveDisclosure(html, false, true);
        const textOnly = controller.applyProgressiveDisclosure(html, false, false);
        const streaming = controller.applyProgressiveDisclosure(html, true, false);

        console.log(JSON.stringify({{
            withCanvasHasDisclosure: withCanvas.includes('aura-chat-disclosure'),
            textOnlyHasDisclosure: textOnly.includes('aura-chat-disclosure'),
            streamingHasDisclosure: streaming.includes('aura-chat-disclosure'),
        }}));
        """
        proc = subprocess.run(["node", "-e", js_script], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)

        # Com Canvas presente, a leitura e limpa e fluida (zero duplicacao de botoes de expansao)
        assert data["withCanvasHasDisclosure"] is False, (
            "Com Companion Canvas ativo, o chat NAO deve gerar accordion duplicado (+Detalhes)"
        )
        # Em texto puro longo sem Canvas, o progressive disclosure permanece ativo
        assert data["textOnlyHasDisclosure"] is True, (
            "Em respostas longas sem Canvas, o progressive disclosure deve proteger a ergonomia"
        )
        # Durante streaming, nao encapsula
        assert data["streamingHasDisclosure"] is False, (
            "Durante streaming nao deve encapsular em disclosure"
        )

    # -------------------------------------------------------------------------
    # 3. Card de Transicao Contextual (renderCompanionPortalCard)
    # -------------------------------------------------------------------------
    def test_companion_portal_card_invitation_button(self) -> None:
        """Valida que o card de transicao convida o usuario com 'Explorar no Canvas ->'."""
        chat_content = self.chat_js.read_text(encoding="utf-8")

        assert "Explorar no Canvas ->" in chat_content, (
            "Botao de acao do Companion Portal Card deve convidar o usuario com 'Explorar no Canvas ->'"
        )
        assert "aux-companion-portal-banner" in chat_content, (
            "Classe aux-companion-portal-banner ausente no card portal"
        )

    # -------------------------------------------------------------------------
    # 4. Sincronizacao de Distribuicao
    # -------------------------------------------------------------------------
    def test_dist_sync_phase2(self) -> None:
        """Garante sincronizacao byte a byte dos arquivos da Fase 2 com dist/."""
        assert self.dist_chat_js.exists(), f"Arquivo dist ausente: {self.dist_chat_js}"
        assert self.dist_aux_js.exists(), f"Arquivo dist ausente: {self.dist_aux_js}"

        assert self.chat_js.read_text(encoding="utf-8") == self.dist_chat_js.read_text(encoding="utf-8")
        assert self.aux_js.read_text(encoding="utf-8") == self.dist_aux_js.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # 5. Conformidade Estrita: ZERO Travessoes Unicode
    # -------------------------------------------------------------------------
    def test_zero_unicode_dashes_phase2(self) -> None:
        """Valida que todos os arquivos da Fase 2 possuem ZERO travessoes Unicode."""
        files = [
            self.chat_js,
            self.dist_chat_js,
            self.aux_js,
            self.dist_aux_js,
            BASE_DIR / "scripts" / "apply_phase2_sinergia.py",
            Path(__file__),
        ]
        for fpath in files:
            content = fpath.read_text(encoding="utf-8")
            assert content.count("\u2014") == 0, f"Arquivo {fpath} contem em-dash (\\u2014)"
            assert content.count("\u2013") == 0, f"Arquivo {fpath} contem en-dash (\\u2013)"


@pytest.mark.unit
class TestSinergiaDualChannelPhase3:
    """Suite de testes para a Fase 3 do Apendice C: Contrato Zero Repeticao no Backend e Prompts."""

    @classmethod
    def setup_class(cls) -> None:
        """Configuracao de engine e caminhos."""
        from core.aura_engine import AuraEngine, AuraSessionMemory

        cls.engine_file = BASE_DIR / "core" / "aura_engine.py"
        cls.prompts_file = BASE_DIR / "core" / "prompts" / "system_prompts.py"

        mem = AuraSessionMemory(db_path=":memory:")
        cls.engine = AuraEngine(
            tenant_id="tenant_p3_test",
            filial_id="posto_p3_test",
            session_memory=mem,
        )

    # -------------------------------------------------------------------------
    # 1. Prompts Sistemicos com Clausula Estrita de Zero Repeticao
    # -------------------------------------------------------------------------
    def test_system_prompts_zero_repetition_clause(self) -> None:
        """Valida a inclusao da regra de zero repeticao quando genui_active=True."""
        from core.prompts.system_prompts import build_fiscal_audit_prompt, build_system_prompt

        p_fiscal = build_fiscal_audit_prompt(
            pergunta_sanitizada="auditar xml de teste",
            contexto_sanitizado="{}",
            historico_formatado="",
            genui_active=True,
        )
        assert "REGRA ESTRITA DE ZERO REPETICAO" in p_fiscal
        assert "NUNCA descreva itens individuais" in p_fiscal

        p_system = build_system_prompt(
            pergunta_sanitizada="como estao os precos?",
            contexto_sanitizado="{}",
            historico_formatado="",
            intencao="precos_concorrencia",
            genui_active=True,
        )
        assert "REGRA ESTRITA DE ZERO REPETICAO" in p_system
        assert "NUNCA descreva itens individuais" in p_system

    # -------------------------------------------------------------------------
    # 2. Sintese Contingencial Deterministica sem Listagem de Itens
    # -------------------------------------------------------------------------
    def test_xml_contingency_synthesis_no_individual_items(self) -> None:
        """Valida que _gerar_sintese_contingencia_ferramenta clusteriza por causa raiz sem despejar itens."""
        xml_sample = {
            "tipo": "xml_documento",
            "resultado": {
                "valido": False,
                "erros_impeditivos": 1,
                "alertas_fiscais": 0,
                "modelo": "65",
                "emit_uf": "SP",
                "dest_uf": "SP",
                "apontamentos": [
                    {
                        "regra_id": "SEFAZ-VAL-NEG",
                        "status": "INVALID",
                        "titulo": "Valor Negativo no Item 2",
                        "explicacao_executiva": "Item 2 (CERVEJA HEINEKEN LATA 350ML): Campo 'vOutro' possui valor negativo (-12.50)",
                        "explicacao_tecnica": "Tag <vOutro> com valor negativo infringe MOC 7.0",
                        "base_legal": ["MOC 7.0"],
                    }
                ],
            },
        }

        sintese_gui = self.engine._gerar_sintese_contingencia_ferramenta(
            "auditoria_fiscal_sefaz", xml_sample, "auditar xml", genui_active=True
        )

        assert sintese_gui is not None
        # Deve ter a estrutura dos 4 blocos
        assert "Auditoria de Documento XML" in sintese_gui
        assert "Causa Raiz Geral" in sintese_gui
        assert "Resolucao no webPosto" in sintese_gui
        assert "Ponte Contextual" in sintese_gui
        assert "painel lateral" in sintese_gui

        # REGRA ESTRITA: Nao deve conter o nome do produto individual nem "Item 2" no chat
        assert "CERVEJA HEINEKEN" not in sintese_gui, (
            "Sintese no chat nao deve despejar produtos linha por linha quando o Canvas esta ativo"
        )
        assert "Item 2" not in sintese_gui, (
            "Sintese no chat nao deve referenciar linhas individuais de itens quando o Canvas esta ativo"
        )

    # -------------------------------------------------------------------------
    # 3. Insercao de Diretiva Dual-Channel em _resolver_contexto_ferramenta
    # -------------------------------------------------------------------------
    def test_resolver_contexto_ferramenta_dual_channel_directive(self) -> None:
        """Valida que o contexto para o LLM recebe a diretiva Dual-Channel quando genui_active=True."""
        ctx_gui, _, _, _, _ = self.engine._resolver_contexto_ferramenta(
            "auditar xml", "auditoria_fiscal_sefaz", genui_active=True
        )
        assert "[DIRETIVA DUAL-CHANNEL ATIVA]" in ctx_gui
        assert "NUNCA descreva itens individuais" in ctx_gui

        ctx_txt, _, _, _, _ = self.engine._resolver_contexto_ferramenta(
            "auditar xml", "auditoria_fiscal_sefaz", genui_active=False
        )
        assert "[DIRETIVA DUAL-CHANNEL ATIVA]" not in ctx_txt

    # -------------------------------------------------------------------------
    # 4. Conformidade Estrita: ZERO Travessoes Unicode
    # -------------------------------------------------------------------------
    def test_zero_unicode_dashes_phase3(self) -> None:
        """Valida que todos os arquivos da Fase 3 possuem ZERO travessoes Unicode."""
        files = [
            self.engine_file,
            self.prompts_file,
            BASE_DIR / "scripts" / "apply_phase3_sinergia.py",
            Path(__file__),
        ]
        for fpath in files:
            content = fpath.read_text(encoding="utf-8")
            assert content.count("\u2014") == 0, f"Arquivo {fpath} contem em-dash (\\u2014)"
            assert content.count("\u2013") == 0, f"Arquivo {fpath} contem en-dash (\\u2013)"


@pytest.mark.unit
class TestSinergiaDualChannelPhase4:
    """Suite de testes para a Fase 4 do Apendice C: Limpeza da Redundancia Interna no Canvas."""

    @classmethod
    def setup_class(cls) -> None:
        """Caminhos e infraestrutura para testes de componentes GenUI e backend."""
        cls.web_dir = BASE_DIR / "web"
        cls.dist_web_dir = BASE_DIR / "dist" / "AuraBackend" / "_internal" / "web"
        cls.widgets_js = cls.web_dir / "js" / "aura-genui-widgets.js"
        cls.dist_widgets_js = cls.dist_web_dir / "js" / "aura-genui-widgets.js"
        cls.engine_file = BASE_DIR / "core" / "aura_engine.py"

    # -------------------------------------------------------------------------
    # 1. Remocao do Bloco Repetitivo em persona_views["gestor"]
    # -------------------------------------------------------------------------
    def test_persona_views_gestor_pista_summary_no_finding_repetition(self) -> None:
        """Valida que persona_views.gestor resume o impacto da pista sem concatenar todos os bullets de findings."""
        from core.aura_engine import build_canonical_genui_envelope

        resultado_mock = {
            "valido": False,
            "erros_impeditivos": 1,
            "alertas_fiscais": 0,
            "modelo": "65",
            "emit_uf": "SP",
            "dest_uf": "SP",
            "apontamentos": [
                {
                    "regra_id": "SEFAZ-VAL-NEG",
                    "status": "INVALID",
                    "titulo": "Valor Negativo no Item 2",
                    "explicacao_executiva": "Item 2 (CERVEJA HEINEKEN LATA 350ML): Campo 'vOutro' possui valor negativo (-12.50)",
                    "explicacao_tecnica": "Tag <vOutro> com valor negativo infringe MOC 7.0",
                    "base_legal": ["MOC 7.0"],
                }
            ],
        }

        import uuid
        envelope = build_canonical_genui_envelope(
            intencao="auditoria_fiscal_sefaz",
            tool_call_id=str(uuid.uuid4()),
            resultado_bruto={"tipo": "xml_documento", "resultado": resultado_mock, "status": "sucesso"},
            executive_summary="Auditoria XML executada.",
        )

        assert envelope is not None
        props = envelope.props
        assert "persona_views" in props
        pv = props["persona_views"]
        gestor_text = pv.get("gestor", "")

        # Deve ser um resumo de impacto operacional
        assert "Impacto na Operacao" in gestor_text
        assert "Faturamento retido" in gestor_text

        # Nao deve duplicar o texto literal de explicacao_executiva do item no topo
        assert "Item 2 (CERVEJA HEINEKEN LATA 350ML)" not in gestor_text, (
            "persona_views.gestor nao deve conter o texto verbatim do finding individual"
        )
        assert pv.get("faturamento_status") is not None
        assert pv.get("tempo_retencao") is not None

    # -------------------------------------------------------------------------
    # 2. Renderizacao do Cockpit de Impacto da Pista no Canvas (Layer 1)
    # -------------------------------------------------------------------------
    def test_canvas_pista_impact_cockpit_rendering(self) -> None:
        """Valida que FiscalShieldInspectorUI renderiza o cockpit de impacto na pista em Layer 1."""
        widgets_content = self.widgets_js.read_text(encoding="utf-8")

        # 2.1 Verifica presenca do cockpit no renderLayer1
        assert "Resumo de Impacto na Pista" in widgets_content
        assert "Impacto no Faturamento:" in widgets_content
        assert "Tempo Estimado na Pista:" in widgets_content

        # 2.2 Verifica presenca das duas visualizacoes adaptativas em fiscal_findings_list
        assert "finding-view-gestor" in widgets_content
        assert "finding-view-contador" in widgets_content
        assert "Como destravar no webPosto" in widgets_content
        assert "Tags XML:" in widgets_content

    # -------------------------------------------------------------------------
    # 3. Sincronizacao de Distribuicao
    # -------------------------------------------------------------------------
    def test_dist_sync_phase4(self) -> None:
        """Garante sincronizacao byte a byte de aura-genui-widgets.js com dist/."""
        assert self.dist_widgets_js.exists(), f"Arquivo dist ausente: {self.dist_widgets_js}"
        assert self.widgets_js.read_text(encoding="utf-8") == self.dist_widgets_js.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # 4. Conformidade Estrita: ZERO Travessoes Unicode
    # -------------------------------------------------------------------------
    def test_zero_unicode_dashes_phase4(self) -> None:
        """Valida que todos os arquivos da Fase 4 possuem ZERO travessoes Unicode."""
        files = [
            self.widgets_js,
            self.dist_widgets_js,
            self.engine_file,
            BASE_DIR / "scripts" / "apply_phase4_sinergia.py",
            Path(__file__),
        ]
        for fpath in files:
            content = fpath.read_text(encoding="utf-8")
            assert content.count("\u2014") == 0, f"Arquivo {fpath} contem em-dash (\\u2014)"
            assert content.count("\u2013") == 0, f"Arquivo {fpath} contem en-dash (\\u2013)"


@pytest.mark.unit
class TestSinergiaDualChannelPhase5:
    """Suite de testes para a Fase 5 do Apendice C: Verificacao Integrada E2E e Sincronizacao Global."""

    @classmethod
    def setup_class(cls) -> None:
        """Configuracao de engine e caminhos estaticos."""
        from core.aura_engine import AuraEngine, AuraSessionMemory

        cls.web_dir = BASE_DIR / "web"
        cls.dist_web_dir = BASE_DIR / "dist" / "AuraBackend" / "_internal" / "web"

        mem = AuraSessionMemory(db_path=":memory:")
        cls.engine = AuraEngine(
            tenant_id="tenant_p5_test",
            filial_id="posto_p5_test",
            session_memory=mem,
        )

    # -------------------------------------------------------------------------
    # 1. Integracao Ponta a Ponta do Contrato Dual-Channel (Chat -> Canvas)
    # -------------------------------------------------------------------------
    def test_end_to_end_dual_channel_contract(self) -> None:
        """Valida a coreografia completa: chat sintetico por causa raiz + card portal + canvas sem redundancia."""
        from core.aura_engine import build_canonical_genui_envelope

        xml_mock = {
            "valido": False,
            "erros_impeditivos": 1,
            "alertas_fiscais": 0,
            "modelo": "65",
            "emit_uf": "SP",
            "dest_uf": "SP",
            "apontamentos": [
                {
                    "regra_id": "SEFAZ-VAL-NEG",
                    "status": "INVALID",
                    "titulo": "Valor Negativo no Item 2",
                    "explicacao_executiva": "Item 2 (CERVEJA HEINEKEN LATA 350ML): Campo 'vOutro' possui valor negativo (-12.50)",
                    "explicacao_tecnica": "Tag <vOutro> com valor negativo infringe MOC 7.0",
                    "base_legal": ["MOC 7.0"],
                    "campos_afetados": ["vOutro"],
                    "acoes_recomendadas": ["Mover o valor para a tag vDesc no webPosto."],
                }
            ],
        }

        # 1. Chat: Sintese deterministica contingencial clusterizada (SEM listagem do item 2)
        sintese = self.engine._gerar_sintese_contingencia_ferramenta(
            "auditoria_fiscal_sefaz",
            {"tipo": "xml_documento", "resultado": xml_mock},
            "auditar xml",
            genui_active=True,
        )
        assert "CERVEJA HEINEKEN" not in sintese
        assert "Item 2" not in sintese
        assert "Causa Raiz Geral" in sintese
        assert "Resolucao no webPosto" in sintese
        assert "Ponte Contextual" in sintese

        # 2. Envelope GenUI: Visao Gestor nao repete explicacao executiva verbatim
        import uuid
        envelope = build_canonical_genui_envelope(
            intencao="auditoria_fiscal_sefaz",
            tool_call_id=str(uuid.uuid4()),
            resultado_bruto={"tipo": "xml_documento", "resultado": xml_mock, "status": "sucesso"},
            executive_summary="Auditoria XML executada.",
        )
        assert envelope is not None
        gestor_text = envelope.props["persona_views"]["gestor"]
        assert "CERVEJA HEINEKEN" not in gestor_text
        assert "Impacto na Operacao" in gestor_text

        # 3. Frontend Chat: applyProgressiveDisclosure nao gera accordion concorrente quando hasToolCard=true
        js_script = """
        const { AuraChatController } = require('./web/js/aura-chat.js');
        const c = new AuraChatController();
        const html = '<p>Veredito</p><p>Causa Raiz</p><p>Resolucao</p><p>Ponte</p>';
        const withCard = c.applyProgressiveDisclosure(html, false, true);
        const cardHtml = c.renderCompanionPortalCard({
            artifactId: 'art_test',
            artifactTitle: 'Auditoria Fiscal',
            artifactSubtitle: '1 erro impeditivo',
            containerId: 'msg_test',
            widgetHtml: '<div>Canvas Widget</div>'
        });
        console.log(JSON.stringify({
            hasDisclosure: withCard.includes('aura-chat-disclosure'),
            hasButtonCanvas: cardHtml.includes('Explorar no Canvas ->')
        }));
        """
        proc = subprocess.run(["node", "-e", js_script], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        assert res["hasDisclosure"] is False, "Chat com Canvas nao deve ter accordion +Detalhes competindo"
        assert res["hasButtonCanvas"] is True, "Card deve conter botao 'Explorar no Canvas ->'"

    # -------------------------------------------------------------------------
    # 2. Integridade Global de Sincronizacao com dist/
    # -------------------------------------------------------------------------
    def test_complete_dist_web_integrity(self) -> None:
        """Garante paridade 100% byte a byte entre todos os arquivos web/ e dist/."""
        synced_files = [
            "css/aura.css",
            "js/aura-chat.js",
            "js/aura-aux-panel.js",
            "js/aura-genui-widgets.js",
            "index.html",
        ]
        for rel in synced_files:
            src = self.web_dir / rel
            dst = self.dist_web_dir / rel
            assert src.exists(), f"Arquivo fonte ausente: {src}"
            assert dst.exists(), f"Arquivo de distribuicao ausente: {dst}"
            assert src.read_text(encoding="utf-8") == dst.read_text(encoding="utf-8"), (
                f"Divergencia entre web/{rel} e dist/.../{rel}"
            )

    # -------------------------------------------------------------------------
    # 3. Auditoria Global de Travessoes Unicode em Todo o Apendice C
    # -------------------------------------------------------------------------
    def test_global_zero_unicode_dashes_dual_channel(self) -> None:
        """Audita zero travessoes Unicode em todos os arquivos tocados pelo Apendice C."""
        all_touched_files = [
            self.web_dir / "css" / "aura.css",
            self.web_dir / "js" / "aura-chat.js",
            self.web_dir / "js" / "aura-aux-panel.js",
            self.web_dir / "js" / "aura-genui-widgets.js",
            self.web_dir / "index.html",
            BASE_DIR / "core" / "aura_engine.py",
            BASE_DIR / "core" / "prompts" / "system_prompts.py",
            BASE_DIR / "docs" / "roadmap_apendice_sinergia_dual_channel.md",
            BASE_DIR / "docs" / "roadmap.md",
            BASE_DIR / "scripts" / "apply_phase1_sinergia.py",
            BASE_DIR / "scripts" / "apply_phase2_sinergia.py",
            BASE_DIR / "scripts" / "apply_phase3_sinergia.py",
            BASE_DIR / "scripts" / "apply_phase4_sinergia.py",
            Path(__file__),
        ]
        for fpath in all_touched_files:
            assert fpath.exists(), f"Arquivo ausente na auditoria: {fpath}"
            content = fpath.read_text(encoding="utf-8")
            c_em = content.count("\u2014")
            c_en = content.count("\u2013")
            assert c_em == 0, f"Arquivo {fpath} contem {c_em} ocorrencias de em-dash (\\u2014)"
            assert c_en == 0, f"Arquivo {fpath} contem {c_en} ocorrencias de en-dash (\\u2013)"
