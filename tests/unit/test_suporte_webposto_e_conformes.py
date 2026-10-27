"""
Suite de Testes Unitarios: Experiencia Profissional do Gestor Fiscal (AURA Shield)
Valida:
1. Eliminacao de instrucoes de edicao manual de XML/banco pelo cliente.
2. Direcionamento profissional para Suporte webPosto e acoes reais do ERP.
3. Ocultacao de cards de conformidade da Visao Gestor com accordion compacto.
4. Botao e payload de geracao de chamado para WhatsApp do Suporte webPosto.
5. Zero travessoes Unicode em todos os arquivos.
"""
from decimal import Decimal
from pathlib import Path
import pytest

from core.fiscal_engine import (
    auditar_matematica_item,
    auditar_totais_documento,
    StatusApontamento,
    GravidadeApontamento,
)


def get_project_root() -> Path:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "web" / "index.html").exists():
            return current
        if (current / "ia-banco-local" / "web" / "index.html").exists():
            return current / "ia-banco-local"
        current = current.parent
    return Path.cwd()


class TestSuporteWebpostoEConformes:
    def test_zero_manual_xml_instructions_in_fiscal_engine(self):
        """Garante que nenhuma regra fiscal instrua o gestor a editar tags XML ou campos de banco."""
        root = get_project_root()
        fiscal_file = root / "core" / "fiscal_engine.py"
        content = fiscal_file.read_text(encoding="utf-8")

        # Termos proibidos que denotam amadorismo operacional
        prohibited = [
            "Zerar vOutro e transferir o valor para vDesc",
            "Ajustar a tag <vProd>",
            "Ajustar o total <vNF>",
            "Transferir o valor do cupom ou desconto para o campo vDesc",
        ]
        for term in prohibited:
            assert term not in content, f"Instrucao manual proibida encontrada: '{term}'"

    def test_val_neg_item_directs_to_webposto_support(self):
        """Valida que o valor monetario negativo no item direciona para suporte webPosto."""
        ok, finding = auditar_matematica_item(
            n_item=1,
            c_prod="001",
            x_prod="GASOLINA COMUM",
            q_com=Decimal("10.00"),
            v_un_com=Decimal("5.00"),
            v_prod=Decimal("50.00"),
            v_outro=Decimal("-10.00"),
        )
        assert ok is False
        assert finding is not None
        assert finding.status == StatusApontamento.INVALID
        assert finding.gravidade == GravidadeApontamento.CRITICAL
        assert "Bloqueio de Emissao" in finding.titulo
        assert "suporte" in finding.acoes_recomendadas[0].lower()
        assert "webposto" in finding.acoes_recomendadas[0].lower()

    def test_val_neg_totais_directs_to_webposto_support(self):
        """Valida que totais com valor negativo direcionam para suporte webPosto."""
        findings = auditar_totais_documento(
            v_prod_total_declarado=Decimal("100.00"),
            itens_v_prod=[Decimal("100.00")],
            v_nf_declarado=Decimal("90.00"),
            v_outro=Decimal("-10.00"),
        )
        invalids = [f for f in findings if f.regra_id == "SEFAZ-VAL-NEG"]
        assert len(invalids) == 1
        finding = invalids[0]
        assert "Bloqueio de Emissao" in finding.titulo
        assert "suporte" in finding.acoes_recomendadas[0].lower()
        assert "webposto" in finding.acoes_recomendadas[0].lower()

    def test_genui_widgets_contains_pro_support_and_conformes_separation(self):
        """Valida a presenca da logica de suporte webPosto e separacao de conformes no JS."""
        root = get_project_root()
        widgets_file = root / "web" / "js" / "aura-genui-widgets.js"
        content = widgets_file.read_text(encoding="utf-8")

        # 1. Separacao de pendencias e conformes
        assert "const isConformeItem" in content
        assert "const pendencias = rawFindings.filter" in content
        assert "const conformes = rawFindings.filter" in content

        # 2. Accordion compacto para conformes
        assert "finding-conformes-box" in content
        assert "btn-toggle-conformes" in content
        assert "container-conformes-list" in content

        # 3. Botao de chamado WhatsApp e payload estruturado
        assert "btn-suporte-webposto" in content
        assert "Copiar Chamado Suporte webPosto (WhatsApp)" in content
        assert "Abertura de Chamado Suporte webPosto" in content
        assert "navigator.clipboard.writeText" in content

    def test_zero_unicode_dashes(self):
        """Garante ausencia total de travessoes Unicode em todos os arquivos modificados."""
        root = get_project_root()
        files = [
            root / "core" / "fiscal_engine.py",
            root / "core" / "aura_engine.py",
            root / "web" / "js" / "aura-genui-widgets.js",
            root / "tests" / "unit" / "test_suporte_webposto_e_conformes.py",
        ]
        forbidden = ["\u2014", "\u2013"]
        for f in files:
            assert f.exists(), f"Arquivo {f} deve existir"
            content = f.read_text(encoding="utf-8")
            for char in forbidden:
                assert char not in content, f"Travessao proibido {repr(char)} em {f.name}"
