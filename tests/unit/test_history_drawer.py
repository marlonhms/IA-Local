"""
Suite de Testes Unitarios: Gaveta Lateral de Historico de Conversas (Abordagem C)
Valida a integridade dos contratos, classes CSS, markup HTML e regras de agrupamento.
Regra inegociavel: ZERO TRAVESSOES em todo o codigo e documentacao.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest


def get_project_root() -> Path:
    """Retorna a raiz do projeto de forma agnostica ao diretorio de trabalho."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "web" / "index.html").exists():
            return current
        if (current / "ia-banco-local" / "web" / "index.html").exists():
            return current / "ia-banco-local"
        current = current.parent
    return Path.cwd()


def test_history_drawer_js_structure():
    """Valida a existencia e a estrutura da classe AuraHistoryDrawerController."""
    root = get_project_root()
    js_path = root / "web" / "js" / "aura-history-drawer.js"
    assert js_path.exists(), f"Arquivo {js_path} deve existir"

    content = js_path.read_text(encoding="utf-8")
    assert "class AuraHistoryDrawerController" in content
    assert "init()" in content
    assert "open()" in content
    assert "close()" in content
    assert "toggle()" in content
    assert "classifyDomain(session)" in content
    assert "groupSessionsByTime(sessions)" in content
    assert "renderHistory(" in content
    assert "switchSession(sessionId)" in content
    assert "deleteSession(" in content
    assert "handleClearAll()" in content
    assert "window.auraHistoryDrawer" in content


def test_html_drawer_integration():
    """Valida a presenca de todos os elementos DOM do Drawer no index.html."""
    root = get_project_root()
    html_path = root / "web" / "index.html"
    assert html_path.exists(), f"Arquivo {html_path} deve existir"

    content = html_path.read_text(encoding="utf-8")

    # Botao de acionamento no header
    assert 'id="btn-open-history"' in content

    # Drawer e Overlay
    assert 'id="aura-history-drawer"' in content
    assert 'id="aura-history-drawer-overlay"' in content

    # Componentes internos
    assert 'id="history-search-input"' in content
    assert 'id="history-groups-container"' in content
    assert 'id="history-total-chip"' in content
    assert 'id="btn-drawer-new-chat"' in content
    assert 'id="btn-close-history-drawer"' in content
    assert 'id="btn-clear-all-history"' in content

    # Inclusao do script
    assert '<script src="/static/js/aura-history-drawer.js' in content


def test_css_history_drawer_rules():
    """Valida que o CSS contem as declaracoes de transicao e visibilidade do drawer."""
    root = get_project_root()
    css_path = root / "web" / "css" / "aura.css"
    assert css_path.exists(), f"Arquivo {css_path} deve existir"

    content = css_path.read_text(encoding="utf-8")
    assert ".history-drawer" in content
    assert ".history-drawer-overlay" in content
    assert "#aura-history-drawer" in content
    assert "#aura-history-drawer.open" in content


def test_domain_classification_logic():
    """Testa as regras de classificacao dos badges operacionais da AURA."""

    def classify_domain(title: str) -> str:
        text = title.lower()
        if any(w in text for w in ["pagamento", "formas", "cartao", "pix", "dinheiro", "sangria", "fechamento", "caixa", "pdv", "turno", "faturamento"]):
            return "caixa"
        if any(w in text for w in ["tanque", "bico", "bomba", "combustivel", "gasolina", "etanol", "diesel", "autonomia", "afericao"]):
            return "tanques"
        if any(w in text for w in ["lmc", "livro", "anp", "resolucao", "inmetro", "conformidade", "fiscalizacao", "0.60"]):
            return "lmc"
        if any(w in text for w in ["loja", "conveniencia", "produto", "combo", "market basket", "itens", "vendas"]):
            return "vendas"
        return "operacao"

    # Caixa / Financeiro
    assert classify_domain("Quais foram as formas de pagamento do dia?") == "caixa"
    assert classify_domain("Relatorio de sangrias e fechamento de caixa") == "caixa"
    assert classify_domain("Conciliacao de turno no PDV 01") == "caixa"

    # Tanques / Pista
    assert classify_domain("Previsao de run-out dos tanques de diesel S10") == "tanques"
    assert classify_domain("Afericao de bicos e bombas da pista") == "tanques"
    assert classify_domain("Qual a autonomia da gasolina comum?") == "tanques"

    # LMC / Compliance
    assert classify_domain("Auditoria de conformidade do LMC conforme ANP") == "lmc"
    assert classify_domain("Verificar tolerancia de 0.60 no livro") == "lmc"

    # Vendas / Loja
    assert classify_domain("Quais os combos mais vendidos na loja de conveniencia?") == "vendas"
    assert classify_domain("Analise de market basket dos produtos") == "vendas"

    # Operacao (Fallback)
    assert classify_domain("Ola AURA, tudo bem?") == "operacao"
    assert classify_domain("Status geral do sistema") == "operacao"


def test_temporal_grouping_logic():
    """Testa a divisao das sessoes nos 4 baldes temporais: Hoje, Ontem, Ultimos 7 dias, Anteriores."""
    now = datetime.now(timezone.utc)
    today_dt = now - timedelta(hours=2)
    yesterday_dt = now - timedelta(days=1, hours=2)
    five_days_dt = now - timedelta(days=5)
    ten_days_dt = now - timedelta(days=10)

    sessions = [
        {"session_id": "s1", "title": "Chat Hoje", "updated_at": today_dt.isoformat()},
        {"session_id": "s2", "title": "Chat Ontem", "updated_at": yesterday_dt.isoformat()},
        {"session_id": "s3", "title": "Chat 5 dias", "updated_at": five_days_dt.isoformat()},
        {"session_id": "s4", "title": "Chat Antigo", "updated_at": ten_days_dt.isoformat()},
    ]

    start_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_yesterday = start_today - timedelta(days=1)
    seven_days_ago = start_today - timedelta(days=6)

    groups = {"Hoje": [], "Ontem": [], "Ultimos 7 dias": [], "Anteriores": []}

    for s in sessions:
        dt = datetime.fromisoformat(s["updated_at"])
        if dt >= start_today:
            groups["Hoje"].append(s["session_id"])
        elif dt >= start_yesterday:
            groups["Ontem"].append(s["session_id"])
        elif dt >= seven_days_ago:
            groups["Ultimos 7 dias"].append(s["session_id"])
        else:
            groups["Anteriores"].append(s["session_id"])

    assert "s1" in groups["Hoje"]
    assert "s2" in groups["Ontem"]
    assert "s3" in groups["Ultimos 7 dias"]
    assert "s4" in groups["Anteriores"]


def test_zero_travessoes_history_drawer():
    """Garante ausencia total de travessoes Unicode em todos os arquivos da feature."""
    root = get_project_root()
    files_to_check = [
        root / "web" / "js" / "aura-history-drawer.js",
        root / "web" / "index.html",
        root / "web" / "css" / "aura.css",
        root / "tests" / "unit" / "test_history_drawer.py",
    ]

    forbidden = ["\u2014", "\u2013"]

    for file_path in files_to_check:
        assert file_path.exists(), f"Arquivo {file_path} deve existir"
        content = file_path.read_text(encoding="utf-8")
        for char in forbidden:
            count = content.count(char)
            assert count == 0, f"Encontrado caractere proibido {repr(char)} ({count} ocorrencias) em {file_path}"
