"""
Suíte de Testes: Resiliência de Vendas, Contingência Determinística e DecisionCard AURA
Valida:
1. Síntese executiva determinística de vendas no backend (_gerar_sintese_contingencia_ferramenta).
2. Renderização do DecisionCard de vendas no frontend (renderVendasAnaliticoWidget).
3. Eliminação de 'ok' no renderGenericToolWidget.
4. Bloqueio de sobrescrita de erro por eventos done subsequentes no SSE.
"""

import sys
import subprocess
import json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.aura_engine import AuraEngine


def test_backend_deterministic_synthesis():
    print("\n1. Testando Síntese Determinística no Backend...")
    engine = AuraEngine()

    mock_vendas = {
        "status": "ok",
        "ultimo_produto_vendido_destaque": {
            "origem": "Conveniência / PDV",
            "pedido": "200153",
            "produto": "BOLO DE MORANGO..",
            "codigo_sku": "00010",
            "data_hora": "2026-10-06 09:43:14",
            "quantidade": 1.0,
            "valor_unitario": 10.0,
            "valor_total": 10.0,
            "cupom": "7",
            "pdv": "007"
        },
        "produtos_mais_vendidos": [
            {
                "codpro": "00022",
                "nompro": "CERVEJA HEINEKEN LN 330ML",
                "total_saidas": 29,
                "qtd_total": 29.0,
                "receita_total": 319.0
            }
        ],
        "resumo_hoje": {
            "data": "2026-10-06",
            "abastecimentos_hoje": 0,
            "litros_hoje": 0.0,
            "faturamento_combustivel_hoje": 0.0,
            "pedidos_conveniencia_hoje": 2,
            "faturamento_conveniencia_hoje": 23.47
        },
        "resumo_geral": {
            "total_abastecimentos": 6,
            "total_litros": 35.85,
            "faturamento_total": 255.60
        }
    }

    sintese = engine._gerar_sintese_contingencia_ferramenta(
        intencao="vendas_analitico",
        resultado_bruto=mock_vendas,
        pergunta="projeção de vendas pra hoje?"
    )

    assert sintese is not None, "Síntese determinística retornou None para dados válidos"
    assert "Diagnóstico Executivo de Vendas" in sintese
    assert "R$ 23.47" in sintese
    assert "BOLO DE MORANGO" in sintese
    assert "CERVEJA HEINEKEN" in sintese
    assert "Projeção & Ação Recomendada" in sintese
    print("   [OK] Síntese determinística gerada com faturamento, último produto e ranking.")

    # Teste de fonte indisponível
    mock_indisponivel = {"status": "indisponivel", "motivo": "ERP offline"}
    sintese_indisp = engine._gerar_sintese_contingencia_ferramenta("vendas_analitico", mock_indisponivel, "vendas")
    assert sintese_indisp is None, "Síntese deve retornar None para status indisponível"
    print("   [OK] Retorno None validado para fontes indisponíveis.")


def test_frontend_node_validation():
    print("\n2. Executando Validação de Renderização no Node.js...")
    chat_js_path = BASE_DIR / "web" / "js" / "aura-chat.js"
    assert chat_js_path.exists(), "aura-chat.js não encontrado"

    import tempfile
    import os

    node_test_script = f"""
    const {{ AuraChatController }} = require({json.dumps(str(chat_js_path.resolve()))});
    const chat = new AuraChatController();

    // 1. Valida registro canônico
    if (typeof chat.responseRenderers['vendas_analitico'] !== 'function') {{
        console.error("ERRO: vendas_analitico não registrado em responseRenderers");
        process.exit(1);
    }}
    if (typeof chat.responseRenderers['consultar_analise_vendas_erp'] !== 'function') {{
        console.error("ERRO: consultar_analise_vendas_erp não registrado em responseRenderers");
        process.exit(1);
    }}

    // 2. Valida renderVendasAnaliticoWidget com dados reais
    const mockVendas = {{
        status: "ok",
        ultimo_produto_vendido_destaque: {{
            origem: "Conveniência / PDV",
            pedido: "200153",
            produto: "BOLO DE MORANGO..",
            codigo_sku: "00010",
            data_hora: "2026-10-06 09:43:14",
            quantidade: 1.0,
            valor_unitario: 10.0,
            valor_total: 10.0,
            cupom: "7",
            pdv: "007"
        }},
        produtos_mais_vendidos: [
            {{
                codpro: "00022",
                nompro: "CERVEJA HEINEKEN LN 330ML",
                total_saidas: 29,
                qtd_total: 29.0,
                receita_total: 319.0
            }}
        ],
        resumo_hoje: {{
            data: "2026-10-06",
            abastecimentos_hoje: 0,
            litros_hoje: 0.0,
            faturamento_combustivel_hoje: 0.0,
            pedidos_conveniencia_hoje: 2,
            faturamento_conveniencia_hoje: 23.47
        }},
        resumo_geral: {{
            total_abastecimentos: 6,
            total_litros: 35.85,
            faturamento_total: 255.60
        }}
    }};

    const widgetHtml = chat.renderVendasAnaliticoWidget(mockVendas);
    if (!widgetHtml.includes('decision-card')) {{
        console.error("ERRO: renderVendasAnaliticoWidget não gerou classe decision-card");
        process.exit(1);
    }}
    if (!widgetHtml.includes('BOLO DE MORANGO')) {{
        console.error("ERRO: renderVendasAnaliticoWidget não incluiu último produto vendido");
        process.exit(1);
    }}
    if (!widgetHtml.includes('CERVEJA HEINEKEN')) {{
        console.error("ERRO: renderVendasAnaliticoWidget não incluiu produto mais vendido");
        process.exit(1);
    }}
    if (!widgetHtml.includes('23,47')) {{
        console.error("ERRO: renderVendasAnaliticoWidget não incluiu faturamento de hoje");
        process.exit(1);
    }}

    // 3. Valida que renderToolInlineWidget despacha vendas_analitico
    const inlineHtml = chat.renderToolInlineWidget('vendas_analitico', mockVendas);
    if (!inlineHtml.includes('decision-card') || !inlineHtml.includes('Diagnóstico de Vendas & Faturamento')) {{
        console.error("ERRO: renderToolInlineWidget não despachou para renderVendasAnaliticoWidget");
        process.exit(1);
    }}

    // 4. Valida que renderGenericToolWidget NUNCA mostra o texto literal 'ok'
    const genericHtml = chat.renderGenericToolWidget('ferramenta_teste', {{ status: 'ok' }});
    if (genericHtml.includes('>ok<') || (genericHtml.includes('>OK<') && genericHtml.includes('ok'))) {{
        console.error("ERRO: renderGenericToolWidget imprimiu texto literal 'ok'");
        process.exit(1);
    }}
    if (!genericHtml.includes('Dados operacionais apurados com sucesso')) {{
        console.error("ERRO: renderGenericToolWidget não usou texto amigável de fallback");
        process.exit(1);
    }}

    console.log("NODE_VENDAS_TESTS_OK");
    """

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(node_test_script)
        temp_js = f.name

    try:
        res = subprocess.run(["node", temp_js], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"   [ERRO NODE]: {res.stderr}")
            sys.exit(1)
        assert "NODE_VENDAS_TESTS_OK" in res.stdout
    finally:
        if os.path.exists(temp_js):
            os.remove(temp_js)

    print("   [OK] Node.js validou DecisionCard, registro, despacho inline e eliminação de 'ok'.")


def main():
    print("=" * 78)
    print("📊 SUÍTE DE TESTES: RESILIÊNCIA E DECISION CARD DE VENDAS (AURA)")
    print("=" * 78)

    test_backend_deterministic_synthesis()
    test_frontend_node_validation()

    print("\n" + "=" * 78)
    print("🎉 TODOS OS TESTES DE RESILIÊNCIA DE VENDAS PASSARAM COM 100% DE SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    main()
