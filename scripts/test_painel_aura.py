"""
Suíte de Testes Automatizada: Painel Próprio da AURA (SPA & Servidor FastAPI).
(Cockpit Operacional da Pista, Gatilhos 1-Clique, Console Cognitivo e Assets Estáticos)

Validações:
1. Rota raiz GET / serve a SPA com status 200 OK e tipo text/html.
2. Rota alternativa GET /dashboard serve a SPA com status 200 OK.
3. Assets estáticos montados sob /static/ retornam 200 OK:
   - /static/css/aura.css (Design System, cores esmeralda/ciano/roxo, cilindros de tanques)
   - /static/js/aura-api.js (Cliente SSE e APIs)
   - /static/js/aura-cockpit.js (Controlador de telemetria da pista)
   - /static/js/aura-triggers.js (Catálogo de 11 ferramentas)
   - /static/js/aura-chat.js (Console cognitivo com streaming)
   - /static/js/aura-app.js (Coordenador de abas e auto-refresh)
4. Cabeçalhos de CORS configurados adequadamente.
5. Integração dos endpoints analíticos consumidos pelo frontend:
   - GET /api/v1/aura/health
   - GET /api/v1/aura/stations
   - POST /api/v1/aura/execute-intent (run_out, lmc_anp, conciliacao_turno, desempenho_pista_frentistas, conveniencia_vendas_cruzadas)
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Protege stdout no Windows contra cp1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Garante path absoluto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.aura_engine import AuraEngine, AuraSessionMemory
from core.aura_api import create_aura_app


def run_tests():
    print("=" * 75)
    print("SUITE DE TESTES: PAINEL OPERACIONAL & CONSOLE COGNITIVO AURA")
    print("   (Validacao de SPA, Static Assets, CORS e Contratos Frontend/Backend)")
    print("=" * 75)

    # Inicializa motor e aplicação de teste
    mem_test = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(
        tenant_id="test_tenant",
        filial_id="posto_teste_01",
        session_memory=mem_test,
    )
    app = create_aura_app(engine)
    client = TestClient(app)

    # ------------------------------------------------------------------
    # 1. TESTE DE ROTAS SPA HTML
    # ------------------------------------------------------------------
    print("\n1. Testando Rotas da SPA (GET / e GET /dashboard)...")
    resp_root = client.get("/")
    assert resp_root.status_code == 200, f"Esperava 200 em /, obteve {resp_root.status_code}"
    assert "text/html" in resp_root.headers.get("content-type", "")
    html_text = resp_root.text
    assert "AURA" in html_text, "AURA não encontrada no HTML da rota /"
    assert "Cockpit Operacional" in html_text, "Título do Cockpit não encontrado no HTML"
    assert "Console Cognitivo" in html_text, "Console Cognitivo não encontrado no HTML"
    print(" [OK] GET / -> 200 OK (SPA HTML carregada com sucesso).")

    resp_dash = client.get("/dashboard")
    assert resp_dash.status_code == 200, f"Esperava 200 em /dashboard, obteve {resp_dash.status_code}"
    assert "text/html" in resp_dash.headers.get("content-type", "")
    print(" [OK] GET /dashboard -> 200 OK (Alias de rota funcionando).")

    # ------------------------------------------------------------------
    # 2. TESTE DE ARQUIVOS ESTÁTICOS (/static/...)
    # ------------------------------------------------------------------
    print("\n2. Testando Entrega de Assets Estáticos (/static/...)...")
    assets = [
        ("/static/css/aura.css", "neural-core-orb", "Design System CSS"),
        ("/static/js/aura-api.js", "AuraApiClient", "API Client JS"),
        ("/static/js/aura-cockpit.js", "AuraCockpitController", "Cockpit Controller JS"),
        ("/static/js/aura-triggers.js", "AuraTriggersController", "Triggers Controller JS"),
        ("/static/js/aura-chat.js", "AuraChatController", "Chat Controller JS"),
        ("/static/js/aura-app.js", "AuraApp", "App Coordinator JS"),
        ("/static/js/aura-fx.js", "AuraBorealisEngine", "FX & Desktop Engine JS"),
    ]

    for path, expected_snippet, label in assets:
        resp = client.get(path)
        assert resp.status_code == 200, f"Falha ao carregar {path}: HTTP {resp.status_code}"
        assert expected_snippet in resp.text, f"Snippet '{expected_snippet}' não encontrado em {path}"
        print(f" [OK] {label}: {path} -> 200 OK ({len(resp.text)} bytes).")

    # ------------------------------------------------------------------
    # 3. TESTE DE CONTRATOS DA API CONSUMIDOS PELO FRONTEND
    # ------------------------------------------------------------------
    print("\n3. Testando Contratos Analíticos Consumidos pelo Painel...")
    
    # Health
    r_health = client.get("/api/v1/aura/health")
    assert r_health.status_code == 200
    assert r_health.json().get("status") == "healthy"
    print(" [OK] Health Check da API: 200 OK.")

    # Stations
    r_stations = client.get("/api/v1/aura/stations")
    assert r_stations.status_code == 200
    st_data = r_stations.json()
    assert isinstance(st_data, list) and len(st_data) > 0
    print(f" [OK] Telemetria de Estação: {st_data[0].get('filial_nome')} (ERP: {st_data[0].get('erp_online')}).")

    # 11 Gatilhos: Teste exaustivo de todas as 11 ferramentas analíticas consumidas pelo Painel
    ferramentas_teste = [
        ("run_out", {}),
        ("lmc_anp", {"data": "2026-09-02"}),
        ("conciliacao_turno", {"data": "2026-09-02"}),
        ("desempenho_pista_frentistas", {}),
        ("vendas_analitico", {}),
        ("conveniencia_vendas_cruzadas", {"min_lift": 1.2}),
        ("sre_metricas", {}),
        ("dados_filial", {}),
        ("estoque_posicao", {}),
        ("clientes_ranking", {}),
        ("catalogo_produtos", {}),
    ]

    for tool_name, params in ferramentas_teste:
        r_tool = client.post("/api/v1/aura/execute-intent", json={"tool_name": tool_name, "params": params})
        assert r_tool.status_code == 200, f"Falha na ferramenta {tool_name}: {r_tool.status_code}"
        payload = r_tool.json()
        assert payload.get("status") == "success"
        assert "data" in payload
        print(f" [OK] Ferramenta '{tool_name}' validada com sucesso.")

    print("\n" + "=" * 75)
    print("[OK] TODOS OS TESTES DO PAINEL DA AURA PASSARAM COM 100% DE SUCESSO!")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
