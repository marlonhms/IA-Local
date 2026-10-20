"""
Testes unitarios para correcao de classificacao de benchmark de concorrencia,
ranking de postos mais baratos da ANP e eliminacao de embacamento no frontend.
"""

from pathlib import Path

from core.integrations.public_data.repository import PublicDataRepository
from core.semantic_router import classificar_intencao_heuristica
from core.tools import PostoTools


def test_intent_classification_postos_mais_baratos():
    """Valida que perguntas sobre postos mais baratos vao para benchmark_comparativo."""
    perguntas = [
        "Quais sao os 3 postos mais baratos de Gasolina Comum na minha cidade?",
        "Quais sao os postos mais baratos da cidade?",
        "Qual posto tem o menor preco de gasolina?",
        "Postos mais baratos de gasolina comum na cidade",
        "Ranking dos postos com menor preco na cidade",
        "Quem vende mais barato na cidade?",
    ]
    for q in perguntas:
        intencao = classificar_intencao_heuristica(q)
        assert intencao == "benchmark_comparativo", f"Falhou para: {q} (retornou {intencao})"


def test_public_data_repo_get_ranking_postos_mock():
    """Valida get_ranking_postos_anp retornando ordenado por preco."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")
    repo.init_schema()

    mock_records = [
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "POSTO ALPHA",
            "cnpj_revenda": "11.111.111/0001-11",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-14",
            "valor_venda": 5.79,
            "bandeira": "SHELL",
        },
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "POSTO BETA",
            "cnpj_revenda": "22.222.222/0001-22",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-14",
            "valor_venda": 5.49,
            "bandeira": "IPIRANGA",
        },
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "POSTO GAMA",
            "cnpj_revenda": "33.333.333/0001-33",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-14",
            "valor_venda": 5.59,
            "bandeira": "BRANCA",
        },
    ]
    repo.save_anp_precos_batch(mock_records)

    ranking = repo.get_ranking_postos_anp(
        municipio="CAMPINAS",
        produto="GASOLINA COMUM",
        limit=3,
        ordem="asc",
    )
    assert len(ranking) == 3
    # Primeiro deve ser o mais barato: POSTO BETA (5.49)
    assert ranking[0]["posto"] == "POSTO BETA"
    assert ranking[0]["preco"] == 5.49
    # Segundo deve ser POSTO GAMA (5.59)
    assert ranking[1]["posto"] == "POSTO GAMA"
    assert ranking[1]["preco"] == 5.59
    # Terceiro deve ser POSTO ALPHA (5.79)
    assert ranking[2]["posto"] == "POSTO ALPHA"
    assert ranking[2]["preco"] == 5.79


def test_tools_comparar_benchmark_includes_ranking():
    """Valida que comparar_benchmark_concorrencia inclui ranking_postos_anp."""
    repo = PublicDataRepository(use_sqlite_fallback=True, sqlite_db_path=":memory:")
    repo.init_schema()

    mock_records = [
        {
            "regiao": "SE",
            "estado_sigla": "SP",
            "municipio": "CAMPINAS",
            "revenda": "AUTO POSTO CENTRAL",
            "cnpj_revenda": "44.444.444/0001-44",
            "produto": "GASOLINA COMUM",
            "data_coleta": "2026-10-14",
            "valor_venda": 5.39,
            "bandeira": "VIBRA",
        }
    ]
    repo.save_anp_precos_batch(mock_records)

    tools = PostoTools(public_data_repo=repo)
    res = tools.comparar_benchmark_concorrencia(
        municipio="CAMPINAS",
        produto="GASOLINA COMUM",
        usar_cache_publico_anp=True,
    )
    assert "ranking_postos_anp" in res
    assert "gasolina_comum" in res["ranking_postos_anp"]
    postos = res["ranking_postos_anp"]["gasolina_comum"]
    assert len(postos) >= 1
    assert postos[0]["posto"] == "AUTO POSTO CENTRAL"
    assert postos[0]["preco"] == 5.39


def test_frontend_css_no_blur_on_chat_bubbles():
    """Valida que o CSS removeu backdrop-filter das bolhas para evitar texto embacado."""
    css_path = Path("web/css/aura.css")
    if not css_path.exists():
        css_path = Path("ia-banco-local/web/css/aura.css")
    css_text = css_path.read_text(encoding="utf-8")

    # Verifica blindagem contra embacamento nas bolhas
    assert "backdrop-filter: none !important;" in css_text
    assert ".chat-bubble-aura," in css_text
    assert "text-rendering: optimizeLegibility;" in css_text


def test_frontend_js_debug_chips_hidden():
    """Valida que chips tecnicos de intencao ficam ocultos para usuario final."""
    js_path = Path("web/js/aura-chat.js")
    if not js_path.exists():
        js_path = Path("ia-banco-local/web/js/aura-chat.js")
    js_text = js_path.read_text(encoding="utf-8")

    assert "window.AURA_DEBUG" in js_text
    assert "chip.classList.add('hidden');" in js_text


def test_ausencia_travessoes_novos_testes():
    """Garante ausencia de travessoes nos arquivos modificados."""
    arquivos = [
        "core/integrations/public_data/repository.py",
        "core/tools.py",
        "core/semantic_router.py",
        "core/aura_engine.py",
        "web/css/aura.css",
        "web/js/aura-chat.js",
    ]
    for arq_str in arquivos:
        p1 = Path(arq_str)
        p2 = Path("ia-banco-local") / arq_str
        arq = p1 if p1.exists() else p2
        texto = arq.read_text(encoding="utf-8")
        assert "\u2014" not in texto, f"Travessao em-dash encontrado em {arq}"
        assert "\u2013" not in texto, f"Travessao en-dash encontrado em {arq}"
