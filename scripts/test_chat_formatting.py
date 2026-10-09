"""
Suíte de Testes Automatizada: Formatações de Texto e Destaques Semânticos no Chat AURA
(Markdown rico, Negrito, Itálico, Sublinhado, Cores Semânticas Obsidian, Streaming Seguro e XSS Guard)

Validações:
1. Regras do System Prompt no Backend (core/aura_engine.py):
   - Orientação explícita sobre negrito, itálico e sublinhado.
   - 5 Cores Semânticas mapeadas aos contextos de posto de combustível e PDV:
     * Verde Esmeralda (text-emerald): Saldo positivo, conformidade ANP, metas batidas, lucro, economia.
     * Amarelo/Âmbar (text-amber): Atenção, alerta preventivo, estoque moderado, prazo de compra próximo.
     * Vermelho/Coral (text-rose): Tanque crítico (< 15%), furo/quebra de caixa, divergência de pista, fora da ANP.
     * Ciano (text-cyan): Métricas técnicas, litros, vazão de bicos L/min, encerrantes, telemetria.
     * Roxo (text-purple): Insights estratégicos, recomendações de combos de conveniência, Lift, ações gerenciais.
2. Folha de Estilos do Design System (web/css/aura.css):
   - Presença de classes text-*, badge-* e aura-hl-* para as 5 cores (incluindo aliases green, yellow, red).
   - Estilização de sublinhado (.aura-underline e .prose-aura u).
   - Estilização de negrito, itálico e cabeçalhos em .prose-aura.
3. Parser de Formatação do Frontend (web/js/aura-chat.js executado via Node.js):
   - Negrito (**negrito**).
   - Itálico (*itálico*).
   - Sublinhado (<u>texto</u>, [u]texto[/u] e __texto__ incluindo palavras compostas __meta_urgente__).
   - Tags BBCode de cores ([verde], [amarelo], [vermelho], [ciano], [roxo]).
   - Tags BBCode de badges ([badge-verde], [badge-amarelo], [badge-vermelho], [badge-ciano], [badge-roxo]).
   - Suporte a tags seguras HTML (<span class="text-emerald">, <span class="badge-amber">).
   - Resiliência em streaming token-a-token (balanceamento automático LIFO de tags não fechadas).
   - Sanitização estrita contra XSS (<script>, <img onerror>, atributos onclick, <svg/onload>, <body/onload>).
   - Preservação de comparações numéricas (< 15%, < 30 L/min) e citações ([26) durante streaming ativo e renderização final.
   - Proteção de blocos de código (``` e `) contra mutações e injeções acidentais.
   - Recursos completos do fallback autônomo (tabelas, listas ordenadas, blockquotes).
"""

import sys
import subprocess
import json
from pathlib import Path

# Protege stdout no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.aura_engine import AuraEngine, AuraSessionMemory


def test_system_prompt_rules():
    print("\n--- 1. Validando Regras de Formatação no System Prompt (core/aura_engine.py) ---")
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(tenant_id="teste_format", filial_id="posto_teste", session_memory=mem)

    # 1. Prompt Operacional Padrão
    prompt_op = engine._build_prompt_sistema(
        pergunta_sanitizada="Como está a situação do tanque de gasolina comum?",
        contexto_sanitizado="Tanque 01: 12% do volume, 14h de autonomia.",
        historico_formatado="",
        intencao="previsao_tanques",
    )

    # Verificações obrigatórias de formatação
    assert "**Negrito" in prompt_op or "**negrito" in prompt_op.lower(), "Faltou instrução de negrito"
    assert "*Itálico" in prompt_op or "*itálico" in prompt_op.lower(), "Faltou instrução de itálico"
    assert "Sublinhado" in prompt_op, "Faltou instrução de sublinhado"
    assert "<u>" in prompt_op and "__" in prompt_op, "Faltou sintaxe <u> ou __ para sublinhado"

    # Verificações das 5 cores semânticas e seus significados
    # 1. Verde Esmeralda
    assert "Verde Esmeralda" in prompt_op, "Faltou Verde Esmeralda no prompt"
    assert "text-emerald" in prompt_op or "[verde]" in prompt_op, "Faltou tag text-emerald ou [verde]"
    assert "ANP" in prompt_op and ("saldo positivo" in prompt_op.lower() or "conformidade" in prompt_op.lower()), "Faltou contexto de ANP/saldo no Verde"

    # 2. Amarelo / Âmbar
    assert "Amarelo" in prompt_op or "Âmbar" in prompt_op, "Faltou Amarelo/Âmbar no prompt"
    assert "text-amber" in prompt_op or "[amarelo]" in prompt_op, "Faltou tag text-amber ou [amarelo]"
    assert "atenção" in prompt_op.lower() or "alerta preventivo" in prompt_op.lower() or "estoque moderado" in prompt_op.lower(), "Faltou contexto de atenção no Amarelo"

    # 3. Vermelho / Coral
    assert "Vermelho" in prompt_op or "Coral" in prompt_op, "Faltou Vermelho/Coral no prompt"
    assert "text-rose" in prompt_op or "[vermelho]" in prompt_op, "Faltou tag text-rose ou [vermelho]"
    assert "crítico" in prompt_op.lower() or "furo" in prompt_op.lower() or "caixa" in prompt_op.lower(), "Faltou contexto crítico/quebra de caixa no Vermelho"

    # 4. Ciano
    assert "Ciano" in prompt_op, "Faltou Ciano no prompt"
    assert "text-cyan" in prompt_op or "[ciano]" in prompt_op, "Faltou tag text-cyan ou [ciano]"
    assert "litros" in prompt_op.lower() or "vazão" in prompt_op.lower() or "bicos" in prompt_op.lower(), "Faltou contexto de litros/vazão no Ciano"

    # 5. Roxo
    assert "Roxo" in prompt_op, "Faltou Roxo no prompt"
    assert "text-purple" in prompt_op or "[roxo]" in prompt_op, "Faltou tag text-purple ou [roxo]"
    assert "combos" in prompt_op.lower() or "conveniência" in prompt_op.lower() or "ações" in prompt_op.lower(), "Faltou contexto de combos/ações no Roxo"

    assert "JAMAIS gere /vermelho ou [ciano] soltos" in prompt_op, "Faltou diretriz de integridade de sintaxe no prompt operacional"
    assert "SEMPRE feche as tags" in prompt_op, "Faltou diretriz de fechamento obrigatório no prompt operacional"

    print(" [OK] System Prompt Operacional: Todas as 5 cores, negrito, itálico e sublinhado validados com sucesso.")

    # 2. Prompt de Ajuda do Sistema (ajuda_sistema)
    prompt_ajuda = engine._build_prompt_sistema(
        pergunta_sanitizada="Como funciona o cockpit?",
        contexto_sanitizado="Módulo Cockpit Operacional.",
        historico_formatado="",
        intencao="ajuda_sistema",
    )
    assert "[ciano]" in prompt_ajuda and "[roxo]" in prompt_ajuda and "[verde]" in prompt_ajuda, "Faltaram cores no prompt de ajuda_sistema"
    assert "JAMAIS gere /vermelho ou [ciano] soltos" in prompt_ajuda, "Faltou diretriz de integridade de sintaxe no prompt de ajuda_sistema"

    # 3. Teste do método dedicado _build_prompt_ajuda
    prompt_ajuda_metodo = engine._build_prompt_ajuda(
        pergunta_sanitizada="Como funciona o cockpit?",
        contexto_sanitizado="Módulo Cockpit Operacional.",
        historico_formatado="",
    )
    assert prompt_ajuda_metodo == prompt_ajuda, "Divergência entre _build_prompt_ajuda e _build_prompt_sistema"
    print(" [OK] System Prompt de Ajuda do Sistema: Diretrizes semânticas e integridade de sintaxe validadas.")


def test_css_classes():
    print("\n--- 2. Validando Classes CSS do Design System (web/css/aura.css) ---")
    css_path = BASE_DIR / "web" / "css" / "aura.css"
    assert css_path.exists(), "aura.css não encontrado"
    css_content = css_path.read_text(encoding="utf-8")

    # Classes de texto colorido
    cores_esperadas = ["text-emerald", "text-amber", "text-rose", "text-cyan", "text-purple", "text-green", "text-yellow", "text-red"]
    for cor in cores_esperadas:
        assert f".{cor}" in css_content, f"Classe .{cor} ausente em aura.css"

    # Classes de badges coloridos com glow
    badges_esperados = ["badge-emerald", "badge-amber", "badge-rose", "badge-cyan", "badge-purple", "badge-green", "badge-yellow", "badge-red"]
    for badge in badges_esperados:
        assert f".{badge}" in css_content, f"Classe .{badge} ausente em aura.css"

    # Classes de sublinhado e tipografia
    assert ".aura-underline" in css_content, "Classe .aura-underline ausente em aura.css"
    assert ".prose-aura u" in css_content, "Regra .prose-aura u ausente em aura.css"
    assert ".prose-aura strong" in css_content or ".prose-aura b" in css_content, "Regra para negrito ausente"
    assert ".prose-aura em" in css_content or ".prose-aura i" in css_content, "Regra para itálico ausente"

    print(" [OK] Design System CSS: Todas as classes text-*, badge-*, .aura-underline e .prose-aura presentes e estilizadas.")


def test_frontend_js_parser():
    print("\n--- 3. Validando Parser Frontend (web/js/aura-chat.js via Node.js) ---")

    node_script = r"""
    const { AuraChatController } = require('./web/js/aura-chat.js');
    const chat = new AuraChatController();

    const results = {};

    // 1. Negrito, Itálico e Sublinhado
    results.bold_italic = chat.formatMarkdown('**Texto Negrito** e *Texto Itálico*');
    results.underline_bbcode = chat.formatMarkdown('[u]Texto Sublinhado BBCode[/u]');
    results.underline_html = chat.formatMarkdown('<u>Texto Sublinhado HTML</u>');
    results.underline_md = chat.formatMarkdown('Prazo: __24 horas__');
    results.compound_underline = chat.formatMarkdown('Prazo: __meta_urgente__');

    // 2. Cores BBCode
    results.verde = chat.formatMarkdown('[verde]Saldo positivo de R$ 5.000[/verde]');
    results.amarelo = chat.formatMarkdown('[amarelo]Atenção preventivo[/amarelo]');
    results.vermelho = chat.formatMarkdown('[vermelho]Tanque 01 crítico (< 15%)[/vermelho]');
    results.ciano = chat.formatMarkdown('[ciano]Vazão de 32 L/min e 14.250 L[/ciano]');
    results.roxo = chat.formatMarkdown('[roxo]Combo Cerveja + Carvão (Lift 3.2x)[/roxo]');

    // 3. Badges BBCode
    results.badge_verde = chat.formatMarkdown('[badge-verde]CONFORME ANP[/badge-verde]');
    results.badge_amarelo = chat.formatMarkdown('[badge-amarelo]ESTOQUE MODERADO[/badge-amarelo]');
    results.badge_vermelho = chat.formatMarkdown('[badge-vermelho]DIVERGÊNCIA CBC04[/badge-vermelho]');
    results.badge_ciano = chat.formatMarkdown('[badge-ciano]TELEMETRIA[/badge-ciano]');
    results.badge_roxo = chat.formatMarkdown('[badge-roxo]AÇÃO GERENCIAL[/badge-roxo]');

    // 4. HTML Direto Seguro
    results.span_html = chat.formatMarkdown('<span class="text-emerald">Lucro Apurado</span> e <span class="badge-rose">Furo R$ 85,00</span>');

    // 5. Streaming com tags abertas (auto-balanceamento LIFO)
    results.stream_unclosed_bb = chat.formatMarkdown('🚨 **Atenção**: Tanque 1 [vermelho]crítico em 12%', true);
    results.stream_partial_token = chat.formatMarkdown('O operador iniciou o fechamento [verm', true);
    results.stream_unclosed_html = chat.formatMarkdown('Situação <span class="text-amber">em conferência', true);
    results.stream_lifo = chat.balanceStreamingText('**[verde]Texto', true);

    // 6. Blindagem de Segurança contra XSS
    results.xss_script = chat.formatMarkdown('Ataque: <script>alert("hacked")</script>');
    results.xss_img_onerror = chat.formatMarkdown('Imagem: <img src="x" onerror="alert(1)">');
    results.xss_onclick = chat.formatMarkdown('<span onclick="stealData()">Clique</span>');
    results.xss_svg_slash = chat.formatMarkdown('Ataque: <svg/onload=alert(1)>');
    results.xss_img_slash = chat.formatMarkdown('Ataque: <img/src/onerror=alert(1)>');
    results.xss_body_onload = chat.formatMarkdown('Ataque: <body/onload=alert(1)>');

    // 7. Menor que / Maior que matemáticos não devem quebrar tags
    results.math_operators = chat.formatMarkdown('Nível < 15% e vazão > 35 L/min');
    results.stream_math = chat.balanceStreamingText('Nível < 15');
    results.stream_citation = chat.balanceStreamingText('Portaria [26');

    // 8. Proteção de Blocos de Código e Inline Code contra Corrupção de Tags
    results.code_block = chat.formatMarkdown('```python\ndef __init__(self):\n    return "[verde]ok[/verde]"\n```');
    results.inline_code = chat.formatMarkdown('Use `__init__` e `[verde]texto[/verde]`');

    // 9. Recursos de Markdown Fallback (Tabelas, Listas Ordenadas, Blockquotes)
    results.fallback_table = chat.formatMarkdown('| Tanque | Nível |\n|---|---|\n| TQ 01 | 14.500 L |');
    results.fallback_ordered = chat.formatMarkdown('1. Passo um\n2. Passo dois');
    results.fallback_blockquote = chat.formatMarkdown('> Alerta operacional ANP');

    // 10. Variações Quebradas de Formatação
    results.broken_unclosed = chat.formatMarkdown('[ciano]15.000 L', false);
    results.broken_slash_close = chat.formatMarkdown('[vermelho]crítico /vermelho', false);
    results.broken_orphan_slash = chat.formatMarkdown('🚨 Alerta /vermelho na pista', false);
    results.broken_orphan_close = chat.formatMarkdown('Divergência de caixa [/vermelho]', false);
    results.broken_mixed_colors = chat.formatMarkdown('[verde]R$ 50,00[/verde] e [ciano]14h', false);

    console.log(JSON.stringify(results));
    """

    res = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
        encoding="utf-8",
    )

    if res.returncode != 0:
        print("Erro ao executar script Node.js:", res.stderr)
        assert False, f"Node.js falhou com código {res.returncode}: {res.stderr}"

    data = json.loads(res.stdout)

    # 1. Validação de Negrito, Itálico e Sublinhado
    assert "<strong>Texto Negrito</strong>" in data["bold_italic"], "Falha no negrito"
    assert "<em>Texto Itálico</em>" in data["bold_italic"], "Falha no itálico"
    assert '<u class="aura-underline">Texto Sublinhado BBCode</u>' in data["underline_bbcode"], "Falha no sublinhado [u]"
    assert '<u class="aura-underline">Texto Sublinhado HTML</u>' in data["underline_html"], "Falha no sublinhado <u>"
    assert '<u class="aura-underline">24 horas</u>' in data["underline_md"], "Falha no sublinhado __texto__"
    assert '<u class="aura-underline">meta_urgente</u>' in data["compound_underline"], "Falha no sublinhado composto __meta_urgente__"
    print(" [OK] Markdown Básico: Negrito, Itálico e Sublinhado (BBCode, HTML e __ composto) renderizados com sucesso.")

    # 2. Validação das Cores BBCode
    assert "text-emerald" in data["verde"] and "aura-hl-emerald" in data["verde"], "Falha na cor [verde]"
    assert "text-amber" in data["amarelo"] and "aura-hl-amber" in data["amarelo"], "Falha na cor [amarelo]"
    assert "text-rose" in data["vermelho"] and "aura-hl-rose" in data["vermelho"], "Falha na cor [vermelho]"
    assert "text-cyan" in data["ciano"] and "aura-hl-cyan" in data["ciano"], "Falha na cor [ciano]"
    assert "text-purple" in data["roxo"] and "aura-hl-purple" in data["roxo"], "Falha na cor [roxo]"
    print(" [OK] Destaques de Cor BBCode: 5 cores (verde, amarelo, vermelho, ciano, roxo) convertidas em spans estilizados.")

    # 3. Validação dos Badges BBCode
    assert "badge-emerald" in data["badge_verde"] and "CONFORME ANP" in data["badge_verde"], "Falha no badge verde"
    assert "badge-amber" in data["badge_amarelo"], "Falha no badge amarelo"
    assert "badge-rose" in data["badge_vermelho"], "Falha no badge vermelho"
    assert "badge-cyan" in data["badge_ciano"], "Falha no badge ciano"
    assert "badge-purple" in data["badge_roxo"], "Falha no badge roxo"
    print(" [OK] Badges Semânticos: [badge-*] para as 5 cores convertidos com classes e glow refinados.")

    # 4. Validação de Spans HTML Diretos
    assert '<span class="text-emerald">Lucro Apurado</span>' in data["span_html"], "Falha no span text-emerald direto"
    assert '<span class="badge-rose">Furo R$ 85,00</span>' in data["span_html"], "Falha no span badge-rose direto"
    print(" [OK] Spans HTML Diretos: Classes semânticas autorizadas preservadas.")

    # 5. Validação de Streaming com tags abertas
    assert "</span>" in data["stream_unclosed_bb"], "Falha no auto-balanceamento de BBCode no streaming"
    assert "<strong>" in data["stream_unclosed_bb"] and "</strong>" in data["stream_unclosed_bb"], "Falha no fechamento de ** no streaming"
    assert "[verm" not in data["stream_partial_token"], "Tag parcial não deveria ser renderizada no frame do streaming"
    assert "</span>" in data["stream_unclosed_html"], "Falha no auto-balanceamento de HTML no streaming"
    assert data["stream_lifo"] == "**[verde]Texto[/verde]**", "Falha no aninhamento LIFO do streaming"
    print(" [OK] Estabilidade de Streaming: Auto-balanceamento de tags LIFO e supressão suave de tokens incompletos validados.")

    # 6. Validação de Blindagem XSS
    assert "<script>" not in data["xss_script"] and "&lt;script&gt;" in data["xss_script"], "XSS por <script> não foi neutralizado"
    assert "<img" not in data["xss_img_onerror"] and "onerror" not in data["xss_img_onerror"], "XSS por <img> onerror não foi neutralizado"
    assert "onclick" not in data["xss_onclick"], "Atributo onclick não foi neutralizado"
    assert "<svg" not in data["xss_svg_slash"] and "&lt;svg" in data["xss_svg_slash"], "XSS por <svg/onload> não foi neutralizado"
    assert "<img" not in data["xss_img_slash"] and "&lt;img" in data["xss_img_slash"], "XSS por <img/src/onerror> não foi neutralizado"
    assert "<body" not in data["xss_body_onload"] and "&lt;body" in data["xss_body_onload"], "XSS por <body/onload> não foi neutralizado"
    print(" [OK] Blindagem de Segurança: Ataques XSS (<script>, <svg/onload>, <img/onerror>, <body/onload>, onclick) 100% neutralizados.")

    # 7. Validação de Operadores Matemáticos e Citações
    assert "&lt; 15%" in data["math_operators"] or "< 15%" in data["math_operators"], "Falha no operador matemático < 15%"
    assert data["stream_math"] == "Nível < 15", f"Operador '< 15' foi indevidamente apagado no streaming: {data['stream_math']}"
    assert data["stream_citation"] == "Portaria [26", f"Citação '[26' foi indevidamente apagada no streaming: {data['stream_citation']}"
    print(" [OK] Operadores Matemáticos & Citações: '< 15%' e '[26' preservados tanto no full render quanto no streaming ativo.")

    # 8. Validação de Proteção de Blocos de Código e Inline Code
    assert "<span class" not in data["code_block"] and "[verde]ok[/verde]" in data["code_block"], "Código dentro de bloco sofreu transformação indevida"
    assert "__init__" in data["code_block"], "__init__ dentro de bloco de código foi indevidamente sublinhado"
    assert "<u class" not in data["inline_code"] and "__init__" in data["inline_code"], "Inline code sofreu transformação indevida"
    print(" [OK] Integridade de Código: Blocos de código (```) e inline code (`) 100% preservados contra mutações indevidas.")

    # 9. Validação do Fallback Markdown
    assert "<table" in data["fallback_table"] and "TQ 01" in data["fallback_table"], "Falha na renderização de tabelas no fallback"
    assert "<ol" in data["fallback_ordered"] and "Passo um" in data["fallback_ordered"], "Falha na renderização de listas ordenadas no fallback"
    assert "<blockquote" in data["fallback_blockquote"] and "Alerta operacional ANP" in data["fallback_blockquote"], "Falha em blockquotes no fallback"
    print(" [OK] Fallback Autônomo: Tabelas, listas ordenadas, blockquotes e blocos com linguagem renderizados sem dependências.")

    # 10. Validação das Variações Quebradas de Formatação
    # 1. Tag aberta não fechada no render final: [ciano]15.000 L -> deve aplicar cor ciano (text-cyan) e não conter [ciano]
    assert "text-cyan" in data["broken_unclosed"] and "aura-hl-cyan" in data["broken_unclosed"], "Falha na cor ciano para tag aberta não fechada"
    assert "[ciano]" not in data["broken_unclosed"] and "[/ciano]" not in data["broken_unclosed"], "Tag [ciano] crua permaneceu no texto final"

    # 2. Tag com fechamento quebrado por barra: [vermelho]crítico /vermelho -> deve aplicar cor vermelha (text-rose) e não conter /vermelho
    assert "text-rose" in data["broken_slash_close"] and "aura-hl-rose" in data["broken_slash_close"], "Falha na cor vermelha para fechamento quebrado por barra"
    assert "/vermelho" not in data["broken_slash_close"] and "[vermelho]" not in data["broken_slash_close"], "Tag /vermelho crua permaneceu no texto"

    # 3. Tag órfã solta no texto: 🚨 Alerta /vermelho na pista -> deve higienizar /vermelho e exibir texto limpo
    assert "/vermelho" not in data["broken_orphan_slash"], "Tag órfã /vermelho não foi higienizada"
    assert "Alerta" in data["broken_orphan_slash"] and "na pista" in data["broken_orphan_slash"], "Texto limpo corrompido na higienização de barra solta"

    # 4. Tag de fechamento órfã: Divergência de caixa [/vermelho] -> deve higienizar [/vermelho]
    assert "[/vermelho]" not in data["broken_orphan_close"], "Tag órfã [/vermelho] não foi higienizada"
    assert "Divergência de caixa" in data["broken_orphan_close"], "Texto limpo corrompido na remoção de [/vermelho]"

    # 5. Múltiplas cores misturadas: [verde]R$ 50,00[/verde] e [ciano]14h -> ambas devem receber cores sem quebras
    assert "text-emerald" in data["broken_mixed_colors"] and "text-cyan" in data["broken_mixed_colors"], "Falha em cores misturadas"
    assert "[verde]" not in data["broken_mixed_colors"] and "[ciano]" not in data["broken_mixed_colors"], "Tags cruas em cores misturadas"
    print(" [OK] Variações Quebradas: Tags não fechadas, barras quebradas, tags órfãs e múltiplas cores 100% resolvidas.")


def test_backend_color_markup_normalization():
    print("\n--- 4. Validando Normalização de Markup no Backend (normalize_aura_color_markup) ---")
    from core.aura_engine import normalize_aura_color_markup

    # 1. Tag aberta não fechada
    norm1 = normalize_aura_color_markup("[ciano]15.000 L")
    assert norm1 == "[ciano]15.000 L[/ciano]", f"Falha na normalização 1: {norm1}"

    # 2. Tag com fechamento quebrado por barra
    norm2 = normalize_aura_color_markup("[vermelho]crítico /vermelho")
    assert norm2 == "[vermelho]crítico[/vermelho]", f"Falha na normalização 2: {norm2}"

    # 3. Tag órfã solta no texto
    norm3 = normalize_aura_color_markup("🚨 Alerta /vermelho na pista")
    assert "/vermelho" not in norm3 and "Alerta" in norm3 and "na pista" in norm3, f"Falha na normalização 3: {norm3}"

    # 4. Tag de fechamento órfã
    norm4 = normalize_aura_color_markup("Divergência de caixa [/vermelho]")
    assert norm4 == "Divergência de caixa", f"Falha na normalização 4: {norm4}"

    # 5. Múltiplas cores misturadas
    norm5 = normalize_aura_color_markup("[verde]R$ 50,00[/verde] e [ciano]14h")
    assert norm5 == "[verde]R$ 50,00[/verde] e [ciano]14h[/ciano]", f"Falha na normalização 5: {norm5}"

    # 6. Preservação de blocos de código
    code_input = "```python\ndef run():\n    return '/vermelho'\n```"
    norm_code = normalize_aura_color_markup(code_input)
    assert norm_code == code_input, "Código dentro de bloco foi indevidamente alterado"

    print(" [OK] Backend Markup Normalizer: Todas as 5 variações e proteção de código validadas com sucesso.")


def run_all_formatting_tests():
    print("=" * 75)
    print("🚀 SUÍTE DE TESTES: FORMATAÇÃO DE TEXTO E DESTAQUES DO CHAT AURA")
    print("   (Markdown, Cores Semânticas Obsidian, Badges, Streaming & XSS)")
    print("=" * 75)

    test_system_prompt_rules()
    test_backend_color_markup_normalization()
    test_css_classes()
    test_frontend_js_parser()

    print("\n" + "=" * 75)
    print("🎉 TODOS OS TESTES DE FORMATAÇÃO DO CHAT PASSARAM COM 100% DE SUCESSO!")
    print("=" * 75)


if __name__ == "__main__":
    run_all_formatting_tests()
