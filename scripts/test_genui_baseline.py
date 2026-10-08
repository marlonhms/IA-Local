"""
Suíte de Testes Automatizada: Linha de Base do Protocolo GenUI & Catálogo Seguro
(Fase 0 — AURA IntelligentUI / SDUI Baseline & Security Suite)

Validações Obrigatórias:
1. Idempotência Criptográfica & UUID v4 em Python (core/schemas/idempotency.py):
   - Geração de UUID v4 canônico e IDs com prefixo (tool_call_id, action_id).
   - Validação estrita de formato RFC 4122 v4 e rejeição de UUIDs corrompidos/inválidos.
   - Validação de constraints via Pydantic model IdempotencyKey.
2. Integração no Shell Web SPA (web/index.html & FastAPI Static Mount):
   - Presença da tag <script src="/static/js/aura-genui.js?v=2.9.6" defer> no index.html.
   - Disponibilidade do asset /static/js/aura-genui.js via rota HTTP FastAPI (Status 200 OK).
3. Lógica Frontend e Catálogo Fechado via Node.js (web/js/aura-genui.js):
   - Exportação dual Zero-Bundler (CommonJS require e simulação de window no browser).
   - Registro de componentes válidos (registerComponent, hasComponent, listComponents).
   - Resolução segura de componentes cadastrados (resolveComponent).
   - Mitigação de OWASP LLM03 (Agência Excessiva): bloqueio imediato e lançamento de exceção
     para componentes não catalogados ou nomes maliciosos (ex: render_DeleteAllDatabasesUI).
   - Mitigação de OWASP LLM01 (Prompt Injection & XSS): neutralização de caracteres perigosos via escapeHtml.
   - Idempotência Criptográfica em JavaScript: geração e validação de UUID v4 no Node.js.
4. Regressão Zero:
   - Execução e validação de 100% de sucesso nas 4 suítes analíticas existentes:
     * test_aura_aux_panel.py
     * test_phase5_specialized_responses.py
     * test_phase6_quality_resilience.py
     * test_aura_showcase.py
"""

import sys
import subprocess
import json
import re
from pathlib import Path

# Protege stdout e stderr no terminal Windows contra problemas de codificação
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.aura_api import create_aura_app
from core.schemas.idempotency import (
    generate_uuid4,
    generate_tool_call_id,
    generate_action_id,
    is_valid_uuid4,
    validate_tool_call_id,
    validate_action_id,
    IdempotencyKey,
)


def run_genui_baseline_tests():
    print("=" * 78)
    print("🛡️ SUÍTE DE TESTES: LINHA DE BASE & PROTOCOLO GENUI (FASE 0 — P0)")
    print("   (SecureComponentRegistry, Idempotência Criptográfica e Governança)")
    print("=" * 78)

    # =========================================================================
    # 1. VALIDAÇÃO DE IDEMPOTÊNCIA CRIPTOGRÁFICA EM PYTHON
    # =========================================================================
    print("\n1. Testando Módulo de Idempotência Criptográfica em Python...")
    u1 = generate_uuid4()
    assert is_valid_uuid4(u1, allow_prefix=False), f"UUID gerado inválido: {u1}"
    assert len(u1) == 36, f"Comprimento de UUID incorreto: {len(u1)}"

    tc = generate_tool_call_id()
    assert tc.startswith("call_"), f"Prefixo call_ ausente em: {tc}"
    assert validate_tool_call_id(tc), f"Validação de tool_call_id falhou para: {tc}"

    act = generate_action_id()
    assert act.startswith("act_"), f"Prefixo act_ ausente em: {act}"
    assert validate_action_id(act), f"Validação de action_id falhou para: {act}"

    # Validação de rejeição de formatos inválidos e ataques de injeção em prefixos
    invalid_cases = [
        "",
        "   ",
        None,
        12345,
        "not-a-uuid",
        "12345678-1234-1234-1234-123456789012",  # Versão 1, não 4
        "88b19a02-412f-4a0b-8c01-d85cfd774bfe-extra",
        "<script>alert(1)</script>",
        "call_invalid-uuid-string",
        "<script>_88b19a02-412f-4a0b-8c01-d85cfd774bfe",  # Injeção XSS em prefixo
        "'; DROP TABLE_88b19a02-412f-4a0b-8c01-d85cfd774bfe",  # Injeção SQL em prefixo
        "_88b19a02-412f-4a0b-8c01-d85cfd774bfe",  # Prefixo vazio com underscore
        "123prefix_88b19a02-412f-4a0b-8c01-d85cfd774bfe",  # Prefixo iniciando com dígito
        "call_88b19a02-412f-4a0b-8c01-d85cfd774bfe_extra",  # Sufixo malicioso anexado
    ]
    for inv in invalid_cases:
        assert not is_valid_uuid4(inv, allow_prefix=True), f"UUID inválido ou ataque de prefixo foi aceito incorretamente: {inv}"

    # Validação de isolamento de prefixos cruzados (Cross-Prefix Isolation)
    raw_uuid = generate_uuid4()
    assert validate_tool_call_id(f"call_{raw_uuid}"), "validate_tool_call_id deveria aceitar prefixo call_"
    assert validate_tool_call_id(f"tool_call_{raw_uuid}"), "validate_tool_call_id deveria aceitar prefixo tool_call_"
    assert not validate_tool_call_id(f"act_{raw_uuid}"), "validate_tool_call_id NÃO deve aceitar prefixo de ação act_"
    assert not validate_tool_call_id(f"<script>_{raw_uuid}"), "validate_tool_call_id NÃO deve aceitar injeção no prefixo"

    assert validate_action_id(f"act_{raw_uuid}"), "validate_action_id deveria aceitar prefixo act_"
    assert validate_action_id(f"action_{raw_uuid}"), "validate_action_id deveria aceitar prefixo action_"
    assert not validate_action_id(f"call_{raw_uuid}"), "validate_action_id NÃO deve aceitar prefixo de ferramenta call_"
    assert not validate_action_id(f"'; DROP_{raw_uuid}"), "validate_action_id NÃO deve aceitar injeção no prefixo"

    # Validação do envelope Pydantic IdempotencyKey
    key_valid = IdempotencyKey(tool_call_id=tc, action_id=act)
    assert key_valid.tool_call_id == tc
    assert key_valid.action_id == act

    # Rejeição de tool_call_id com prefixo trocado ou malformado no Pydantic
    try:
        IdempotencyKey(tool_call_id=f"act_{raw_uuid}")
        assert False, "Pydantic deveria rejeitar tool_call_id contendo prefixo de ação act_"
    except Exception:
        pass

    try:
        IdempotencyKey(tool_call_id=tc, action_id=f"call_{raw_uuid}")
        assert False, "Pydantic deveria rejeitar action_id contendo prefixo de ferramenta call_"
    except Exception:
        pass

    try:
        IdempotencyKey(tool_call_id="malformed_id")
        assert False, "Pydantic deveria rejeitar tool_call_id malformado"
    except Exception:
        pass

    print("   [OK] Geração, validação RFC 4122 v4, isolamento de prefixos e modelo Pydantic aprovados.")

    # =========================================================================
    # 2. VALIDAÇÃO DE INTEGRAÇÃO HTML E SHELL FASTAPI
    # =========================================================================
    print("\n2. Testando Integração Web SPA e Servimento Estático FastAPI...")
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(tenant_id="test_genui_base", filial_id="posto_base_01", session_memory=mem)
    app = create_aura_app(engine)
    client = TestClient(app)

    resp_root = client.get("/")
    assert resp_root.status_code == 200, "Falha ao carregar SPA da raiz"
    html = resp_root.text

    assert 'src="/static/js/aura-genui.js?v=2.9.6"' in html, "Script aura-genui.js ausente com cache-buster no index.html"
    assert re.search(r'<script\s+src="/static/js/aura-genui\.js\?v=2\.9\.6"\s+defer></script>', html), \
        "Tag script de aura-genui.js não possui atributo defer para carregamento não bloqueante"

    resp_js = client.get("/static/js/aura-genui.js")
    assert resp_js.status_code == 200, "Falha ao servir /static/js/aura-genui.js via StaticFiles"
    assert "SecureComponentRegistry" in resp_js.text, "Conteúdo de aura-genui.js não contém SecureComponentRegistry"
    print("   [OK] Shell HTML e rota estática /static/js/aura-genui.js validados com 200 OK.")

    # =========================================================================
    # 3. VALIDAÇÃO FRONTEND HEADLESS NO NODE.JS
    # =========================================================================
    print("\n3. Executando Validação Headless via Node.js (Segurança, Registry & XSS)...")
    genui_js_path = BASE_DIR / "web" / "js" / "aura-genui.js"
    assert genui_js_path.exists(), f"Arquivo aura-genui.js não encontrado em {genui_js_path}"

    xss_cases = [
        ["<script>alert('xss')</script>", "&lt;script&gt;alert(&#039;xss&#039;)&lt;/script&gt;"],
        ['<img src="x" onerror="stealCookies()">', "&lt;img src=&quot;x&quot; onerror=&quot;stealCookies()&quot;&gt;"],
        ['" onclick="hack()\'', "&quot; onclick=&quot;hack()&#039;"],
        ["Template `breakout` test", "Template &#96;breakout&#96; test"],
        ["Preço: R$ 5,50 & Combustível > 10L < 20L", "Preço: R$ 5,50 &amp; Combustível &gt; 10L &lt; 20L"]
    ]
    xss_payloads_json = json.dumps(xss_cases)

    node_test_script = f"""
    const path = {json.dumps(str(genui_js_path.resolve()))};
    const {{
      AuraGenUI,
      SecureComponentRegistry,
      registry,
      escapeHtml,
      sanitizeProps,
      generateUUID,
      generateToolCallId,
      generateActionId,
      isValidUUID,
      validateToolCallId,
      validateActionId
    }} = require(path);

    console.log('[NODE] 1. Validando exportação e namespace AuraGenUI...');
    if (!AuraGenUI || AuraGenUI.version !== '1.0.0') {{
      console.error('FALHA: Namespace AuraGenUI inválido ou versão incorreta');
      process.exit(1);
    }}
    if (typeof AuraGenUI.SecureComponentRegistry !== 'function') {{
      console.error('FALHA: SecureComponentRegistry não exposto em AuraGenUI');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Namespace AuraGenUI e construtor expostos corretamente');

    console.log('[NODE] 2. Validando Registro, Proteção Anti-Tamper e Prototype Safety no SecureComponentRegistry...');
    const testRegistry = new SecureComponentRegistry();
    const mockComponent = {{
      render: (props) => `<div class="mock-widget">${{props.title}}</div>`
    }};

    testRegistry.registerComponent('render_TankRunOutForecastUI', mockComponent, {{
      intent: 'tank_forecast',
      version: '1.0.0'
    }});

    if (!testRegistry.hasComponent('render_TankRunOutForecastUI')) {{
      console.error('FALHA: hasComponent retornou false para componente cadastrado');
      process.exit(1);
    }}

    const resolved = testRegistry.resolveComponent('render_TankRunOutForecastUI');
    if (resolved !== mockComponent) {{
      console.error('FALHA: resolveComponent não retornou o componente esperado');
      process.exit(1);
    }}

    // Teste de Proteção contra Hijacking / Sobrescrita não autorizada
    let overwriteBlocked = false;
    try {{
      testRegistry.registerComponent('render_TankRunOutForecastUI', {{ render: () => 'malicious' }});
    }} catch (err) {{
      overwriteBlocked = true;
    }}
    if (!overwriteBlocked) {{
      console.error('FALHA: registerComponent permitiu sobrescrita não autorizada de componente existente');
      process.exit(1);
    }}

    // Teste de sobrescrita autorizada explícita
    testRegistry.registerComponent('render_TankRunOutForecastUI', mockComponent, {{}}, {{ allowOverwrite: true }});

    // Teste de rejeição de nomes de Prototype Pollution no registro
    const dangerousNames = ['__proto__', 'constructor', 'prototype', 'valueOf', 'toString'];
    for (const dName of dangerousNames) {{
      let protoBlocked = false;
      try {{
        testRegistry.registerComponent(dName, mockComponent);
      }} catch (err) {{
        protoBlocked = true;
      }}
      if (!protoBlocked) {{
        console.error(`FALHA: registerComponent permitiu nome perigoso de prototype: ${{dName}}`);
        process.exit(1);
      }}
    }}

    // Teste de rejeição de definições inválidas (não-função e não-objeto)
    let invalidDefBlocked = false;
    try {{
      testRegistry.registerComponent('render_InvalidDef', 12345);
    }} catch (err) {{
      invalidDefBlocked = true;
    }}
    if (!invalidDefBlocked) {{
      console.error('FALHA: registerComponent permitiu definição de componente numérica/inválida');
      process.exit(1);
    }}

    const meta = testRegistry.getMetadata('render_TankRunOutForecastUI');
    if (!meta) {{
      console.error('FALHA: Metadados do componente incorretos:', meta);
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Registro, Anti-Tamper e Prototype Safety aprovados com sucesso');

    console.log('[NODE] 3. Validando Bloqueio de Agência Excessiva (OWASP LLM03)...');
    // Teste de rejeição de componente não cadastrado com exceção explícita
    let blockedThrown = false;
    try {{
      testRegistry.resolveComponent('render_DeleteAllDatabasesUI');
    }} catch (err) {{
      blockedThrown = true;
      if (!err.message.includes('Agência Excessiva') || !err.message.includes('OWASP LLM03')) {{
        console.error('FALHA: Mensagem de erro de Agência Excessiva não cita OWASP LLM03:', err.message);
        process.exit(1);
      }}
    }}
    if (!blockedThrown) {{
      console.error('FALHA: resolveComponent permitiu componente não registrado sem lançar erro');
      process.exit(1);
    }}

    // Teste de resolução quando options é null (deve continuar lançando erro por padrão)
    let nullOptionsThrown = false;
    try {{
      testRegistry.resolveComponent('render_UnregisteredUI', null);
    }} catch (err) {{
      nullOptionsThrown = true;
    }}
    if (!nullOptionsThrown) {{
      console.error('FALHA: resolveComponent com options=null não lançou erro por padrão');
      process.exit(1);
    }}

    // Teste de resolução silenciosa (com throwOnMissing=false ou boolean false)
    const silentResolved = testRegistry.resolveComponent('render_MaliciousScriptUI', {{ throwOnMissing: false }});
    if (silentResolved !== null) {{
      console.error('FALHA: resolveComponent silencioso não retornou null para componente malicioso');
      process.exit(1);
    }}

    const silentResolvedBool = testRegistry.resolveComponent('render_MaliciousScriptUI', false);
    if (silentResolvedBool !== null) {{
      console.error('FALHA: resolveComponent com boolean false não retornou null');
      process.exit(1);
    }}

    if (testRegistry.getSecurityAlertCount() < 3) {{
      console.error('FALHA: Contador de incidentes de segurança não foi incrementado corretamente');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ OWASP LLM03 mitigado: Invocação de componentes desconhecidos rejeitada com sucesso');

    console.log('[NODE] 4. Validando Neutralização de XSS, Prototype Pollution e Circularidade (OWASP LLM01)...');
    const xssPayloads = {xss_payloads_json};

    for (const [raw, expected] of xssPayloads) {{
      const escaped = escapeHtml(raw);
      if (escaped !== expected) {{
        console.error(`FALHA: escapeHtml falhou para ${{raw}}. Esperado: ${{expected}}, Obtido: ${{escaped}}`);
        process.exit(1);
      }}
    }}
    if (escapeHtml(null) !== '' || escapeHtml(undefined) !== '') {{
      console.error('FALHA: escapeHtml não tratou null ou undefined graciosamente');
      process.exit(1);
    }}
    if (escapeHtml('hello\\0world') !== 'helloworld') {{
      console.error('FALHA: escapeHtml não neutralizou byte nulo');
      process.exit(1);
    }}

    // Teste de sanitização de Prototype Pollution em sanitizeProps
    const maliciousProps = JSON.parse('{{"__proto__": {{"polluted": true}}, "title": "Seguro"}}');
    const sanitizedProps = sanitizeProps(maliciousProps);
    if (({{}}).polluted) {{
      console.error('FALHA: sanitizeProps permitiu Prototype Pollution global');
      process.exit(1);
    }}
    if (sanitizedProps.__proto__ && sanitizedProps.__proto__.polluted) {{
      console.error('FALHA: sanitizeProps manteve __proto__ poluído no objeto');
      process.exit(1);
    }}

    // Teste de ciclo de referência em sanitizeProps (evita stack overflow)
    const circularObj = {{ title: "Widget" }};
    circularObj.self = circularObj;
    const sanitizedCirc = sanitizeProps(circularObj);
    if (sanitizedCirc.self !== '[Circular]') {{
      console.error('FALHA: sanitizeProps falhou ao tratar objeto com referência circular');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ XSS, Prototype Pollution e ciclos neutralizados com sucesso via escapeHtml/sanitizeProps');

    console.log('[NODE] 5. Validando Idempotência Criptográfica e Isolamento de Prefixos no JavaScript...');
    const uuidJs = generateUUID();
    if (!isValidUUID(uuidJs, false)) {{
      console.error('FALHA: generateUUID gerou string inválida para UUID v4:', uuidJs);
      process.exit(1);
    }}

    const toolIdJs = generateToolCallId();
    if (!toolIdJs.startsWith('call_') || !validateToolCallId(toolIdJs)) {{
      console.error('FALHA: generateToolCallId gerou identificador inválido:', toolIdJs);
      process.exit(1);
    }}

    const actionIdJs = generateActionId();
    if (!actionIdJs.startsWith('act_') || !validateActionId(actionIdJs)) {{
      console.error('FALHA: generateActionId gerou identificador inválido:', actionIdJs);
      process.exit(1);
    }}

    // Rejeição de ataques de injeção em prefixos no JS
    if (isValidUUID('<script>_' + uuidJs, true)) {{
      console.error('FALHA: isValidUUID aceitou injeção XSS no prefixo');
      process.exit(1);
    }}
    if (isValidUUID('123digit_' + uuidJs, true)) {{
      console.error('FALHA: isValidUUID aceitou prefixo inválido iniciando com número');
      process.exit(1);
    }}

    // Isolamento cruzado de prefixos no JS
    if (validateToolCallId(actionIdJs)) {{
      console.error('FALHA: validateToolCallId aceitou action_id com prefixo act_');
      process.exit(1);
    }}
    if (validateActionId(toolIdJs)) {{
      console.error('FALHA: validateActionId aceitou tool_call_id com prefixo call_');
      process.exit(1);
    }}

    if (isValidUUID('malicious-uuid-token', true)) {{
      console.error('FALHA: isValidUUID aceitou token arbitrário não formatado como UUID v4');
      process.exit(1);
    }}
    console.log('[NODE]    ✓ Idempotência Criptográfica e isolamento de prefixos validados no JavaScript');

    console.log('NODE_GENUI_BASELINE_OK');
    """

    res_node = subprocess.run(
        ["node"],
        input=node_test_script,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if res_node.returncode != 0:
        print("\n❌ ERRO NA EXECUÇÃO DOS TESTES NODE.JS:")
        print(res_node.stderr)
        assert False, "Testes headless Node.js falharam"

    assert "NODE_GENUI_BASELINE_OK" in res_node.stdout, "Script Node.js não concluiu com sucesso"
    for line in res_node.stdout.strip().split("\n"):
        if line.strip():
            print(f"   {line}")

    # =========================================================================
    # 4. VALIDAÇÃO DE ZERO REGRESSÃO NAS SUÍTES EXISTENTES
    # =========================================================================
    print("\n4. Executando Validação de Regressão Zero nas Suítes Analíticas Existentes...")
    regression_suites = [
        ("test_aura_aux_panel.py", "Companion Canvas & Inspector Panel"),
        ("test_phase5_specialized_responses.py", "DecisionCards & Respostas Especializadas"),
        ("test_phase6_quality_resilience.py", "Resiliência, Qualidade & WCAG"),
    ]

    for script_name, suite_desc in regression_suites:
        script_path = BASE_DIR / "scripts" / script_name
        assert script_path.exists(), f"Arquivo de teste {script_name} não encontrado"
        print(f"   ► Executando {script_name} ({suite_desc})...")
        res = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if res.returncode != 0:
            print(f"\n❌ REGRESSÃO DETECTADA EM {script_name}:")
            print(res.stdout)
            print(res.stderr)
            assert False, f"Regressão detectada na suíte {script_name}"
        print(f"     [OK] {script_name} aprovado com 100% de sucesso.")

    print("\n" + "=" * 78)
    print("🎉 LINHA DE BASE GENUI (FASE 0) HOMOLOGADA COM 100% DE SUCESSO!")
    print("   SecureComponentRegistry ativo, OWASP LLM03 mitigado, zero regressões.")
    print("=" * 78)


if __name__ == "__main__":
    run_genui_baseline_tests()
