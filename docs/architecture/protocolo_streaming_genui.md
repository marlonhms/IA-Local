# Especificação Formal do Protocolo de Streaming GenUI // AURA IntelligentUI

- **Documento:** Especificação Técnica do Protocolo SSE Multiplexado GenUI / Server-Driven UI
- **Versão:** 1.0.0 (Fase 0 — Linha de Base Arquitetural)
- **Data de Publicação:** 07/10/2026
- **Status:** Aprovado & Homologado
- **Repositório:** `ia-banco-local`
- **Módulos Vinculados:** `core/aura_engine.py`, `core/aura_api.py`, `core/schemas/idempotency.py`, `web/js/aura-genui.js`

---

## 1. Visão Geral & Objetivos Arquiteturais

O protocolo de streaming da **AURA IntelligentUI (GenUI / SDUI v1.0)** foi projetado para sustentar o posicionamento da AURA como **Mentor de Decisões Executivo de Borda (Executive Decision Mentor)** em operações de varejo e postos de combustíveis.

O protocolo resolve simultaneamente quatro desafios críticos de engenharia em sistemas Edge AI:
1. **Ultra-Baixa Latência Cognitiva (TTFT < 100ms):** Emissão instantânea do esqueleto visual (`ui_skeleton`) e dos primeiros tokens do Resumo Executivo (`delta`) antes do término de consultas analíticas volumosas.
2. **Determinismo Numérico Inabalável:** Isolamento absoluto entre a síntese textual probabilística do LLM e os números oficiais de faturamento, perdas e estoques apurados deterministicamente pelo backend Python e transmitidos em envelopes tipados (`ui_complete`).
3. **Mitigação Estrita de OWASP LLM03 (Agência Excessiva):** Proibição de tags arbitrárias geradas pelo modelo; execução vinculada exclusivamente ao catálogo fechado `SecureComponentRegistry` no frontend.
4. **Idempotência Criptográfica e Resiliência Transacional:** Uso obrigatório de UUID v4 para `tool_call_id` e `action_id`, prevenindo submissões duplicadas provocadas por instabilidade de rede ou duplo clique do operador.

---

## 2. Taxonomia dos Chunks SSE (Server-Sent Events)

O endpoint `/api/v1/aura/chat` opera via HTTP Server-Sent Events multiplexados. Abaixo está a especificação formal de todos os tipos canônicos de eventos:

```
+──────────────────────────────────────────────────────────────────────────────────────────+
|                               FLUXO TEMPORAL DE STREAMING SSE                            |
+──────────────────────────────────────────────────────────────────────────────────────────+
  [Requisição do Usuário]
         │
         ▼
  1. event: intent                ──> Classificação de intenção pelo SemanticRouter
  2. event: ui_skeleton           ──> Placeholder visual do componente alocado no feed (< 100ms)
  3. event: delta                 ──> Tokens em tempo real do Resumo Executivo (Camada 1)
  4. event: ui_delta (opcional)   ──> Fragmentos parciais de JSON de propriedades analíticas
  5. event: ui_complete           ──> Envelope estruturado canônico (GenUIEnvelope) para Camada 2 & 3
  6. event: telemetry             ──> Métricas SRE de latência e consumo de GPU
  7. event: done                  ──> Encerramento formal do stream
         │
         ▼ (Após interação do operador no botão da Camada 3)
  8. event: ui_action_feedback    ──> Confirmação da ação transacional com Action Voucher auditado
```

### 2.1 Especificação Detalhada por Tipo de Chunk

#### `delta`
- **Descrição:** Token ou fragmento textual livre emitido pelo LLM durante a síntese do Resumo Executivo (Camada 1).
- **Semântica de Apresentação:** Injetado diretamente no nó textual do chat via efeito progressivo (*typewriter*), fornecendo ancoragem cognitiva imediata ao operador.
- **Formato:**
  ```http
  event: delta
  data: {"chunk_type": "delta", "text": " Tanque 01 (Gasolina Comum) atingirá nível crítico em 4.2h.", "session_id": "sess_01"}
  ```

#### `ui_skeleton`
- **Descrição:** Sinal precursor emitido assim que o roteador semântico identifica a intenção analítica. Dispara a renderização do esqueleto animado do micro-widget antes de os cálculos do ERP estarem finalizados.
- **Objetivo UX:** Elimina a percepção de travamento (*system hang*) e reduz a latência percebida para menos de 100ms.
- **Formato:**
  ```http
  event: ui_skeleton
  data: {
    "chunk_type": "ui_skeleton",
    "tool_call_id": "call_a62b19cc-e872-448b-b8cf-dfff06869033",
    "component_name": "render_TankRunOutForecastUI",
    "title": "Analisando Autonomia de Tanques...",
    "session_id": "sess_01"
  }
  ```

#### `ui_delta`
- **Descrição:** Fragmentos progressivos de propriedades estruturadas (JSON sub-payload) gerados durante o streaming guiado (*guided decoding*).
- **Tratamento no Frontend:** Acumulado em buffer volátil (`string buffer`). Se descartado ou se a rede oscilar, o cliente aguarda o bloco consolidado `ui_complete`.
- **Formato:**
  ```http
  event: ui_delta
  data: {
    "chunk_type": "ui_delta",
    "tool_call_id": "call_a62b19cc-e872-448b-b8cf-dfff06869033",
    "delta_json": "{\"tanque\": \"01\", \"saldo_atual\": 420"
  }
  ```

#### `ui_complete`
- **Descrição:** Bloco consolidado, tipado e matematicamente validado contendo o envelope GenUI completo (`GenUIEnvelope`). 
- **Ação no Frontend:** Substitui o esqueleto (`ui_skeleton`) pelo widget interativo real registrado no `SecureComponentRegistry`, hidratando a Visualização Rica (Camada 2) e a Action Sheet Transacional (Camada 3).
- **Formato:**
  ```http
  event: ui_complete
  data: {
    "chunk_type": "ui_complete",
    "tool_call_id": "call_a62b19cc-e872-448b-b8cf-dfff06869033",
    "component_name": "render_TankRunOutForecastUI",
    "session_id": "sess_01",
    "data": {
      "envelope_version": "1.0",
      "tool_call_id": "call_a62b19cc-e872-448b-b8cf-dfff06869033",
      "component_name": "render_TankRunOutForecastUI",
      "client_component": "TankForecastWidget",
      "timestamp": "2026-10-07T19:00:00Z",
      "ttl_seconds": 900,
      "summary_text": "Tanque 01 com 4.2h de autonomia crítica.",
      "props": {
        "tanque": "01",
        "combustivel": "GASOLINA COMUM",
        "capacidade_litros": 15000,
        "saldo_atual_litros": 4200,
        "autonomia_critica_horas": 4.2,
        "espaco_livre_ullage_litros": 10800,
        "status_operacional": "CRÍTICO"
      },
      "actions": [
        {
          "action_id": "act_20367dea-9047-4a78-bc36-86b2d960fdf6",
          "label": "Pedir Carreta (10.000 L)",
          "action_type": "mutation",
          "requires_confirmation": true,
          "payload": {"tanque": "01", "litros": 10000}
        },
        {
          "action_id": "act_f48109ab-1294-4bca-9011-ccae991122aa",
          "label": "Projetar no Companion Canvas",
          "action_type": "inspection",
          "requires_confirmation": false,
          "payload": {"perspective": "tanques"}
        }
      ]
    }
  }
  ```

#### `ui_action_feedback`
- **Descrição:** Feedback assíncrono emitido após a submissão de uma ação transacional do operador via `POST /api/v1/aura/actions/execute` ou via canal de streaming reativo.
- **Mecanismo:** Fornece o status oficial da transação (`COMMITTED` ou `FAILED`), o número do **Action Voucher** emitido com assinatura HMAC-SHA256, ou dispara o rollback gracioso no frontend em caso de falha de conexão com a retaguarda do ERP.
- **Formato:**
  ```http
  event: ui_action_feedback
  data: {
    "chunk_type": "ui_action_feedback",
    "tool_call_id": "call_a62b19cc-e872-448b-b8cf-dfff06869033",
    "action_id": "act_20367dea-9047-4a78-bc36-86b2d960fdf6",
    "status": "COMMITTED",
    "voucher_id": "vch_77b1029c-502a-410a-9d21-f09c1234abcd",
    "signature": "hmac_sha256_3a91fbc...",
    "feedback_message": "Pedido de carreta #4912 homologado com sucesso no ERP local.",
    "timestamp": "2026-10-07T19:00:15Z"
  }
  ```

---

## 3. Padrão de Idempotência Criptográfica (UUID v4)

Para mitigar o risco de pedidos e transações duplicadas em cenários de alta latência ou cliques repetidos:
1. **`tool_call_id`:** Identificador canônico da execução analítica da ferramenta. Formato: `call_<UUIDv4>` (ex: `call_a62b19cc-e872-448b-b8cf-dfff06869033`).
2. **`action_id`:** Identificador único de cada ação proposta na Camada 3. Formato: `act_<UUIDv4>` (ex: `act_20367dea-9047-4a78-bc36-86b2d960fdf6`).
3. **Validação Criptográfica:** Implementada em Python (`core/schemas/idempotency.py`) e JavaScript (`web/js/aura-genui.js`) com conformidade estrita com RFC 4122 v4.

---

## 4. Governança e Mitigações de Segurança

### 4.1 OWASP LLM03 (Agência Excessiva / Excessive Agency)
- O motor de IA **não tem permissão para emitir código arbitrário ou nomes de tags HTML**.
- Todo componente renderizado deve existir previamente no catálogo fechado `SecureComponentRegistry`.
- Se o LLM alucinar ou tentar instanciar uma chave inexistente (ex: `render_ExecuteShellUI`), o frontend bloqueia a resolução imediatamente, incrementa o contador de incidentes de segurança (`_securityAlertCount`) e ativa fallback seguro sem executar código não homologado.

### 4.2 OWASP LLM01 (Prompt Injection & XSS)
- Todas as variáveis e strings injetadas no DOM passam obrigatoriamente pela sanitização via `escapeHtml()`.
- Valores numéricos são coercidos via `Number()` nativo antes de serem utilizados em larguras de barras ou gauges de SVG.

### 4.3 Isolamento Transacional Read-Only
- As 11 ferramentas analíticas do Python operam em modo **estritamente somente-leitura** no PostgreSQL local (`posto_ai:5433`).
- Nenhuma mutação de estoque, caixa ou preço ocorre diretamente pelo LLM. Qualquer mutação transacional requer o clique físico de um operador humano (*Human-in-the-Loop Gateway*) e a geração de um Action Voucher com trilha de auditoria.

---

## 5. Ciclo de Vida do Micro-Widget no Frontend

```
 [ui_skeleton] ──> SKELETON (Placeholder de baixa latência)
                         │
 [delta]       ──> STREAMING_TEXT (Resumo Executivo digitado em tempo real)
                         │
 [ui_complete] ──> HYDRATED (Props validadas montadas na Camada 2 & 3)
                         │
 [Clique Op.]  ──> STATE_LOCK + OPTIMISTIC UI (Botão desativado, spinner ativo)
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
          [Sucesso RPC]       [Falha/Timeout RPC]
               │                   │
         COMMITTED           ROLLBACK GRACIOSO
     (Voucher emitido,   (Restauração do botão original,
      role: 'tool' salva   toast de aviso sem reload)
      na memória AURA)
```
