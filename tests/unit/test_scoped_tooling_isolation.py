"""
Testes Unitarios de Scoped Tooling e Isolamento de Contexto no AuraEngine.
Garante que ferramentas operacionais de pista/tanques nao sejam executadas em perguntas fiscais,
mesmo se o classificador preliminar retornar falsos positivos de mentoria.
Regra inegociavel: ZERO travessoes em todo o modulo.
"""

from unittest.mock import MagicMock
import pytest

from core.aura_engine import AuraEngine


@pytest.fixture
def mock_aura_engine():
    """Cria uma instancia de teste do AuraEngine com ferramentas mockadas."""
    engine = AuraEngine()
    engine._tools = MagicMock()
    return engine


def test_scoped_tooling_redireciona_falso_positivo_mentoria(mock_aura_engine):
    """Valida que pergunta fiscal com intencao preliminar mentoria_decisao e interceptada."""
    query = "Quais os pontos criticos de ICMS Monofasico CST 61, PIS/COFINS CST 04 na conveniencia e rejeicoes SEFAZ?"

    # Configura retorno da ferramenta fiscal
    mock_aura_engine.tools.auditar_documento_ou_chave_fiscal.return_value = {
        "status": "sucesso",
        "tipo": "consulta_rejeicao_fiscal",
        "resultados": [],
    }

    # Passa intencao erronea mentoria_decisao
    ctx_extra, bruto, telem, cache_hit, lat = mock_aura_engine._resolver_contexto_ferramenta(
        pergunta=query,
        intencao="mentoria_decisao",
        genui_active=False,
    )

    # Verifica que a ferramenta de mentoria/tanque NAO foi chamada
    assert not mock_aura_engine.tools.gerar_diagnostico_mentoria_executiva.called

    # Verifica que a ferramenta fiscal foi acionada
    assert mock_aura_engine.tools.auditar_documento_ou_chave_fiscal.called

    # Verifica que as Fichas Canonicas foram injetadas no contexto
    assert "GROUNDING FISCAL DETERMINISTICO" in ctx_extra
    assert "CST 61" in ctx_extra
    assert "CST 04" in ctx_extra


def test_scoped_tooling_preserva_perguntas_reais_de_tanques(mock_aura_engine):
    """Valida que perguntas legitimas de tanques e estoque continuam executando ferramentas normais."""
    query_tanque = "Quanto sobrou no tanque 1 de gasolina?"

    mock_aura_engine.tools.gerar_diagnostico_mentoria_executiva.return_value = {
        "status": "sucesso",
        "tanques": [{"tanque": 1, "produto": "GASOLINA COMUM"}],
    }

    ctx_extra, bruto, telem, cache_hit, lat = mock_aura_engine._resolver_contexto_ferramenta(
        pergunta=query_tanque,
        intencao="mentoria_decisao",
        genui_active=False,
    )

    # Verifica que a ferramenta de mentoria foi chamada normalmente
    assert mock_aura_engine.tools.gerar_diagnostico_mentoria_executiva.called
    assert not mock_aura_engine.tools.auditar_documento_ou_chave_fiscal.called
