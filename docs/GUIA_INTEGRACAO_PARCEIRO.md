# GUIA DE INTEGRACAO TECNICA: PARCEIRO BI E AURA PARTNER API GATEWAY
## Manual de Implementacao, Especificacao de Contratos e Prompt Mestre para Agente de IA

> **Classificacao:** Especificacao Tecnica de Integracao e Arquitetura de Software  
> **Versao:** 1.0.0-PRO  
> **Status:** Pronto para Producao / Branch: `feature/partner-api-gateway`  
> **Regra Estrita de Estilo:** Zero travessoes em todo o documento (uso exclusivo de hifens normais, dois pontos ou parenteses)  
> **Publico-Alvo:** Equipe de Engenharia do Parceiro e Agentes de IA Autonomos (Cursor, Claude, Copilot, Windsurf, ChatGPT)  

---

## SUMARIO EXECUTIVO

Este documento estabelece o padrao definitivo de integracao entre a plataforma de BI do Parceiro e o ecossistema AURA (Agente Autonomo de Inteligencia Operacional para Postos de Combustiveis).

A integracao permite que o Parceiro:
1. Sincronize dados brutos operacionais de postos que utilizam o ERP WebPosto (`tanques`, `fechabomba`, `fechacaixa`, `pedido`, `itemped`) diretamente para o staging isolado da AURA via API REST segura.
2. Incorpore o assistente conversacional corporativo da AURA dentro do portal ou aplicativo de BI do Parceiro em modo texto puro de alta performance com streaming SSE (Server-Sent Events).
3. Preserve 100% da estabilidade, codigo e arquitetura do BI existente do Parceiro, operando atraves de um modulo estritamente isolado sem qualquer escrita no banco de dados operacional.

---

## SECAO 1: PROMPT MESTRE PARA O AGENTE DE IA DO PARCEIRO

> **Instrucao para o Desenvolvedor / Lider Tecnico do Parceiro:**  
> Copie o bloco delimitado abaixo integralmente e cole-o no seu agente de IA (como regra de projeto em `.cursorrules`, instrucoes de projeto no Claude, System Prompt no Windsurf ou chat do Copilot). O prompt foi calibrado tecnicamente para evitar alucinacoes, forcar isolamento arquitetural e blindar o sistema contra quebras.

```markdown
# PROMPT DE DIRETRIZES DE ENGENHARIA PARA INTEGRACAO COM AURA GATEWAY

Voce e um Engenheiro de Software Senior e Arquiteto de Integracao Corporativa especializado em sistemas de Business Intelligence (BI) e integracao de APIs de alta confiabilidade.

Sua missao e implementar a integracao do nosso sistema com o AURA Partner API Gateway (versao 1.0.0, branch `feature/partner-api-gateway`).

---

### REGRAS DE OURO (DIRETRIZES ABSOLUTAS E IRREVOGAVEIS)

1. PRINCIPIO DA NAO-QUEBRA (ZERO DOWNTIME / ZERO REGRESSAO):
   - Voce JAMAIS devera modificar, refatorar, renomear ou excluir models, controllers, dashboards, relatorios, tabelas ou rotinas de sincronizacao de BI existentes no nosso projeto.
   - O funcionamento habitual do nosso BI tem prioridade absoluta. Caso haja qualquer conflito de bibliotecas ou dependencias, a integracao da AURA devera se adaptar ao nosso ambiente.

2. ARQUITETURA ESTREITAMENTE ISOLADA:
   - Todo e qualquer codigo novo desta integracao devera residir EXCLUSIVAMENTE em um diretorio novo e isolado:
     `integrations/aura/` (ou `services/aura/` se o projeto usar padrao de servicos).
   - Nenhuma classe interna do nosso BI deve depender diretamente do modulo da AURA. Se a AURA for desativada ou removida, o BI devera continuar rodando como se nada tivesse acontecido.

3. CONSULTAS SQL SOMENTE-LEITURA E CONEXAO SEGURA:
   - As consultas para extracao das tabelas do WebPosto (`tanques`, `fechabomba`, `fechacaixa`, `pedido`, `itemped`) devem ser estritamente SELECT.
   - E expressamente proibido executar operacoes de escrita (INSERT, UPDATE, DELETE, ALTER, DROP, LOCK) no banco do WebPosto ou no banco do nosso BI.
   - Suporte tanto pool de conexoes (ex: psycopg2 `getconn()` / `putconn()`) quanto conexao direta de forma segura, com liberacao garantida no bloco finally.
   - Utilize sempre modo READ ONLY seguro com limites claros de busca (LIMIT / clausula de intervalo temporal) para nao sobrecarregar o banco de dados.

4. DEGRADACAO GRACIOSA, RECONEXAO E RESILIENCIA (CIRCUIT BREAKER):
   - Se o servidor da AURA estiver indisponivel, lento ou retornando erros transientes (HTTP 500, 502, 503, 504 ou timeout de rede), o nosso sistema NAO PODE travar.
   - Implemente reconexao automatica com backoff exponencial (ate 3 tentativas) para falhas de rede no chat e na sincronizacao.
   - Erros de configuracao (HTTP 400, 401, 422) NAO devem ser retentados: falhe imediatamente com log explicativo.
   - O chat devera exibir uma mensagem amigavel ao usuario: "O copiloto inteligente esta temporariamente indisponivel. O painel de BI segue operando normalmente."

5. PROTOCOLO DE CHAT EM TEXTO PURO (SEM GENUI / SEM ELEMENTOS INTERNOS):
   - O AURA Partner Gateway opera em modo texto puro (`enable_genui=False`).
   - No streaming SSE do chat (`POST /api/v1/partner/chat`), filtre e processe EXCLUSIVAMENTE eventos com tipo `delta` (acumulando o texto do token recebido em `data.text`) e finalize no evento `done`.
   - Se algum evento interno for recebido (`intent`, `tool_start`, `tool_result`, `telemetry`), ignore-o silenciosamente.

6. CONFORMIDADE DE ESTILO:
   - Proibido o uso de travessoes Unicode (\u2014 e \u2013). Use hifens normais (-), dois pontos (:) ou parenteses.

---

### CONTRATOS TECNICOS DO AURA PARTNER API GATEWAY

#### A. Configuracoes e Credenciais (via Variaveis de Ambiente):
- `AURA_API_BASE_URL`: URL base do gateway (ex: `http://100.x.y.z:8000` via Tailscale ou `https://aura-edge.internal:8000`).
- `AURA_PARTNER_KEY`: Chave secreta de autenticacao de parceiro.
- `AURA_STATION_ID`: Identificador da filial ou posto (ex: `posto_01`, `filial_matriz`).

#### B. Sincronizacao de Dados em Staging (Raw Sync):
- Rota: `POST {AURA_API_BASE_URL}/api/v1/partner/stations/{station_id}/raw-sync`
- Headers Obrigatorios:
  - `X-Partner-Key: {AURA_PARTNER_KEY}`
  - `X-Station-ID: {station_id}` (deve ser identico ao da URL)
  - `Content-Type: application/json`
- Corpo (JSON aceito em dois formatos: aninhado ou direto na raiz):
  ```json
  {
    "station_id": "posto_01",
    "sync_timestamp": "2026-10-25T10:00:00Z",
    "tables": {
      "tanques": [
        {
          "codtan": "1",
          "prl_ds_produto_lmc": "Gasolina Comum",
          "codlmc": "1001",
          "ultima_leitura": "2026-10-25T10:00:00",
          "volume": 12500.0,
          "volume_agua": 0.0,
          "temperatura": 24.5,
          "capacidade": 15000.0,
          "iniciodia": 13000.0,
          "tan_vl_quantidade_fim": 12500.0
        }
      ],
      "fechabomba": [
        {
          "ilha": "1",
          "codbom": "1",
          "codtan": "1",
          "codpro": "GAS_COMUM",
          "turno": "1",
          "codpdv": "1",
          "dtmov": "2026-10-25T10:00:00",
          "encltsa": 1000.0,
          "enclts": 1500.0,
          "qtdeaf": 0.0,
          "preco": 5.89,
          "encdinh": 2945.0
        }
      ],
      "fechacaixa": [
        {
          "cai_cd_caixa": "1",
          "codpdv": "1",
          "fechado": "S",
          "matricula": "OPERADOR_101",
          "turno": "1",
          "dtmov": "2026-10-25T10:00:00",
          "cai_ts_abertura": "2026-10-25T06:00:00",
          "cai_ts_fechamento": "2026-10-25T14:00:00",
          "valrefcai": 200.0,
          "valdinh": 1500.0,
          "valcart": 2325.55,
          "valnotpra": 0.0,
          "venda_combustivel": 3825.55,
          "venda_produtos": 0.0,
          "litros": 649.5,
          "valtot": 3825.55
        }
      ],
      "pedido": [
        {
          "codi": "PED1001",
          "pdv": "1",
          "dtem": "2026-10-25T09:30:00",
          "valortotal": 150.0,
          "situ": "A",
          "vendedor": "OPERADOR_101",
          "ven_tx_motivo_cancelamento": null,
          "formapg": "1"
        }
      ],
      "itemped": [
        {
          "controle": "1",
          "pedido": "PED1001",
          "codpec": "GAS_COMUM",
          "valunit": 5.89,
          "quant": 25.466,
          "valitem": 150.0
        }
      ]
    }
  }
  ```
- DICIONARIO DE CAMPOS RECONHECIDOS (NAO ALUCINAR NOMES DE COLUNAS):
  - `tanques`: `codtan`, `prl_ds_produto_lmc`, `codlmc`, `ultima_leitura`, `volume`, `volume_agua`, `temperatura`, `capacidade`, `iniciodia`, `tan_vl_quantidade_fim`
  - `fechabomba`: `ilha`, `codbom`, `codtan`, `codpro`, `turno`, `codpdv`, `dtmov`, `encltsa`, `enclts`, `qtdeaf`, `preco`, `encdinh`
  - `fechacaixa`: `cai_cd_caixa`, `codpdv`, `fechado`, `matricula`, `turno`, `dtmov`, `cai_ts_abertura`, `cai_ts_fechamento`, `valrefcai`, `valdinh`, `valcart`, `valnotpra`, `venda_combustivel`, `venda_produtos`, `litros`, `valtot`
  - `pedido`: `codi`, `pdv`, `dtem`, `valortotal`, `situ`, `vendedor`, `ven_tx_motivo_cancelamento`, `formapg`
  - `itemped`: `controle`, `pedido`, `codpec`, `valunit`, `quant`, `valitem`

#### C. Chat Corporativo em Streaming SSE:
- Rota: `POST {AURA_API_BASE_URL}/api/v1/partner/chat`
- Headers:
  - `X-Partner-Key: {AURA_PARTNER_KEY}`
  - `X-Station-ID: {station_id}`
  - `Content-Type: application/json`
- Corpo (JSON):
  ```json
  {
    "query": "Pergunta do usuario do posto",
    "stream": true,
    "session_id": "sessao_unica_do_usuario",
    "station_id": "posto_01",
    "tenant_id": "rede_cliente_opcional"
  }
  ```
- Resposta: `Content-Type: text/event-stream`.
  - Formato de cada chunk:
    `event: delta`
    `data: {"chunk_type": "delta", "text": "fragmento de texto", "session_id": "..."}`
  - Formato de conclusao:
    `event: done`
    `data: {"chunk_type": "done", "text": "", "session_id": "..."}`

---

### ETAPAS DE IMPLEMENTACAO SOLICITADAS:
1. Crie o modulo `integrations/aura/` com o carregamento seguro de configuracoes de ambiente.
2. Implemente o cliente HTTP `AuraClient` com controle de timeouts, reconexao com backoff e tratamento de erros (401, 400, 422, 500).
3. Crie a rotina de extracao somente-leitura dos dados do WebPosto em lotes controlados (batch size maximo de 500 a 1000 registros).
4. Implemente o consumidor SSE para streaming de respostas no chat com suporte a reconexao.
5. Crie testes automatizados unitarios isolados cobrindo cenarios de sucesso e indisponibilidade da AURA.
6. Execute a suite de testes original do nosso BI para comprovar que nenhuma funcionalidade foi impactada.
```

---

## SECAO 2: ARQUITETURA DA SOLUCAO NO LADO DO PARCEIRO

### 2.1 Visao Geral de Componentes e Fluxo de Dados

A integracao e desenhada segundo o principio de "Acoplamento Zero" (Zero-Coupling Architecture). O sistema existente do Parceiro permanece inalterado, e o modulo da AURA atua como um servico satelite.

```
+-----------------------------------------------------------------------------------+
|                            ECOSSISTEMA DO PARCEIRO                                |
|                                                                                   |
|  +--------------------+         (Somente-Leitura)        +---------------------+  |
|  | Banco de Dados ERP | <============================== | DataExtractor       |  |
|  | WebPosto (PG/SQL)  |   SELECT * FROM tanques, ...    | (Conexao Read-Only) |  |
|  +--------------------+                                 +----------+----------+  |
|                                                                    |              |
|  +--------------------+                                 +----------v----------+  |
|  | Dashboards e BI    | (Inalterados, operacao normal)  | SyncJob (Agendador) |  |
|  | Existente          |                                 | (Em Lotes Seguros)  |  |
|  +--------------------+                                 +----------+----------+  |
|                                                                    |              |
|  +--------------------+       Eventos SSE (delta/done)  +----------v----------+  |
|  | Frontend / Portal  | <============================== | AuraClient /        |  |
|  | Widget Chat Puro   |   Stream de Texto Conversa      | ChatService         |  |
|  +--------------------+                                 +----------+----------+  |
|                                                                    |              |
+--------------------------------------------------------------------+--------------+
                                                                     |
                     Rede Segura (Tailscale Mesh / HTTPS TLS)        |
                                                                     v
+-----------------------------------------------------------------------------------+
|                        AURA PARTNER GATEWAY (BORDA / NUVEM)                       |
|                                                                                   |
|  POST /api/v1/partner/stations/{id}/raw-sync  -->  Staging Isolado por Posto      |
|                                                    (Persistencia Segura)          |
|                                                                                   |
|  POST /api/v1/partner/chat                    -->  AuraEngine (Modo Texto Puro)   |
|                                                    (Streaming SSE: delta + done)  |
+-----------------------------------------------------------------------------------+
```

### 2.2 Estrutura de Diretorios Recomendada

O modulo deve ser criado dentro do backend do Parceiro na seguinte estrutura padronizada:

```
integrations/aura/
├── __init__.py                # Ponto de entrada do pacote isolado
├── config.py                  # Validacao de variaveis de ambiente
├── client.py                  # Cliente HTTP da AURA (httpx / requests)
├── extractor.py               # Extracao SQL somente-leitura do WebPosto
├── sync_job.py                # Rotina de lote (batch) para o endpoint raw-sync
├── sse_parser.py              # Parser robusto para eventos text/event-stream
├── chat_service.py            # Servico de orquestracao do chat
└── tests/
    ├── __init__.py
    ├── test_client.py         # Testes de comunicacao e autenticacao
    ├── test_extractor.py      # Testes de extracao com mocks
    └── test_sse_parser.py     # Testes de parsing de eventos delta e done
```

*(Caso o backend do Parceiro seja em Node.js / TypeScript, crie a pasta equivalente `src/integrations/aura/` contendo `config.ts`, `AuraClient.ts`, `DataExtractor.ts`, `SyncJob.ts`, `SseParser.ts`, `ChatService.ts`).*

### 2.3 Principios de Nao-Interferencia e Seguranca

1. **Pool de Conexao Separado:** O `DataExtractor` deve utilizar um pool de conexao de banco de dados proprio com o parametro de sessao `default_transaction_read_only = on` (ou conexao via usuario de banco sem privilegios de gravacao).
2. **Isolamento de Memoria:** Nenhum objeto do BI existente e compartilhado por referencia mutavel com o modulo da AURA.
3. **Tratamento de Timeouts Rigidos:** Todas as chamadas para o gateway da AURA devem ter limite de conexao configurado para 5 segundos e limite de leitura para 30 segundos (ou 60 segundos no chat).
4. **Comportamento diante de Quedas:** Caso a AURA caia, a fila de sync descarta lotes antigos acumulados ou retem apenas a foto mais recente do estado do posto para evitar tempestade de sincronizacao (thundering herd).

---

## SECAO 3: CONTRATO DE SINCRONIZACAO DE DADOS (RAW-SYNC)

### 3.1 Especificacao do Endpoint

- **Metodo:** `POST`
- **Rota:** `/api/v1/partner/stations/{station_id}/raw-sync`
- **Parametro de Rota (`station_id`):** Identificador alfanumerico da filial do posto (limite de 64 caracteres; apenas letras, numeros, hifens e sublinhados). Exemplo: `posto_matriz_01`.

#### Headers HTTP:
| Header | Tipo | Obrigatorio | Descricao |
| :--- | :--- | :--- | :--- |
| `X-Partner-Key` | String | Sim | Chave de parceiro fornecida pela AURA |
| `X-Station-ID` | String | Sim | Identificador da estacao (deve bater com `station_id` da URL) |
| `Content-Type` | String | Sim | Valor fixo: `application/json` |

*(Alternativa aceita de autenticacao: `Authorization: Bearer <chave_de_parceiro>`)*

### 3.2 Formato do Payload JSON

O gateway da AURA aceita duas estruturas:
1. **Estrutura Aninhada Oficial:** Dicionario com metadados e chave `tables`.
2. **Estrutura Direta:** Tabelas posicionadas diretamente no topo do corpo JSON.

#### Exemplo Oficial Completo (Estrutura Aninhada):
```json
{
  "station_id": "posto_matriz_01",
  "sync_timestamp": "2026-10-25T13:45:00Z",
  "tables": {
    "tanques": [
      {
        "codtan": "1",
        "prl_ds_produto_lmc": "Gasolina Comum",
        "codlmc": "1001",
        "ultima_leitura": "2026-10-25T13:30:00",
        "volume": 14250.50,
        "volume_agua": 0.0,
        "temperatura": 24.8,
        "capacidade": 15000.0,
        "iniciodia": 14900.0,
        "tan_vl_quantidade_fim": 14250.50
      },
      {
        "codtan": "2",
        "prl_ds_produto_lmc": "Etanol Hidratado",
        "codlmc": "1002",
        "ultima_leitura": "2026-10-25T13:30:00",
        "volume": 8100.0,
        "volume_agua": 1.5,
        "temperatura": 25.2,
        "capacidade": 10000.0,
        "iniciodia": 8900.0,
        "tan_vl_quantidade_fim": 8100.0
      }
    ],
    "fechabomba": [
      {
        "ilha": "1",
        "codbom": "1",
        "codtan": "1",
        "codpro": "GAS_COMUM",
        "turno": "1",
        "codpdv": "1",
        "dtmov": "2026-10-25T13:30:00",
        "encltsa": 10500.0,
        "enclts": 11149.5,
        "qtdeaf": 0.0,
        "preco": 5.89,
        "encdinh": 3825.55
      }
    ],
    "fechacaixa": [
      {
        "cai_cd_caixa": "1",
        "codpdv": "1",
        "fechado": "S",
        "matricula": "OPERADOR_JOAO",
        "turno": "1",
        "dtmov": "2026-10-25T13:30:00",
        "cai_ts_abertura": "2026-10-25T06:00:00",
        "cai_ts_fechamento": "2026-10-25T13:30:00",
        "valrefcai": 200.0,
        "valdinh": 1500.0,
        "valcart": 2325.55,
        "valnotpra": 0.0,
        "venda_combustivel": 3825.55,
        "venda_produtos": 0.0,
        "litros": 649.5,
        "valtot": 3825.55
      }
    ],
    "pedido": [
      {
        "codi": "PED_20261025_001",
        "pdv": "1",
        "dtem": "2026-10-25T13:10:00",
        "valortotal": 150.0,
        "situ": "A",
        "vendedor": "OPERADOR_JOAO",
        "ven_tx_motivo_cancelamento": null,
        "formapg": "CARTAO_CREDITO"
      }
    ],
    "itemped": [
      {
        "controle": "1",
        "pedido": "PED_20261025_001",
        "codpec": "GAS_COMUM",
        "valunit": 5.89,
        "quant": 25.466,
        "valitem": 150.0
      }
    ]
  }
}
```

### 3.3 Dicionario de Dados das Tabelas WebPosto

Abaixo constam as colunas reconhecidas e mapeadas automaticamente pelo adaptador canonico AUPS da AURA (`generic_postgres.yaml`):

#### 1. Tabela `tanques` (Inventario e Medicacao Fisica Subterranea):
- `codtan` (string/int): Identificador fisico do tanque.
- `prl_ds_produto_lmc` (string): Descricao do combustivel (ex: "Gasolina Comum", "Etanol Hidratado", "Diesel S10").
- `codlmc` (string/int): Codigo fiscal do produto no Livro de Movimentacao de Combustiveis.
- `ultima_leitura` (string ISO): Data/hora da ultima leitura volumetrica da sonda.
- `volume` (float/string): Volume atual em litros no tanque.
- `volume_agua` (float/string): Altura de agua no fundo do tanque em milimetros ou litros.
- `temperatura` (float/string): Temperatura do combustivel em graus Celsius.
- `capacidade` (float/string): Capacidade geometrica nominal em litros.
- `iniciodia` (float/string): Volume de combustivel na abertura do dia.
- `tan_vl_quantidade_fim` (float/string): Volume de combustivel no encerramento.

#### 2. Tabela `fechabomba` (Encerrantes de Bicos Medidores):
- `ilha` (string/int): Identificador da ilha ou equipamento concentrador.
- `codbom` (string/int): Identificador do bico medidor.
- `codtan` (string/int): Identificador do tanque que alimenta o bico.
- `codpro` (string): Codigo do produto comercializado.
- `turno` (string): Identificador do turno de operacao.
- `codpdv` (string/int): Identificador do PDV associado.
- `dtmov` (string ISO): Data e hora do registro do movimento.
- `encltsa` (float/string): Leitura do encerrante inicial em litros.
- `enclts` (float/string): Leitura do encerrante final em litros.
- `qtdeaf` (float/string): Volume de afericao volumetrica (sem venda fiscal).
- `preco` (float/string): Preco unitario praticado na bomba.
- `encdinh` (float/string): Valor total faturado no bico.

#### 3. Tabela `fechacaixa` (Fechamento e Prestacao de Turno):
- `cai_cd_caixa` (string/int): Chave primaria do fechamento de caixa.
- `codpdv` (string/int): Identificador do ponto de venda.
- `fechado` (string): "S" para caixa encerrado, "N" para aberto.
- `matricula` (string): Identificacao do operador / frentista.
- `turno` (string): Turno de trabalho.
- `dtmov` (string ISO): Data do movimento contabil.
- `cai_ts_abertura` (string ISO): Data e hora de abertura do caixa.
- `cai_ts_fechamento` (string ISO): Data e hora de fechamento (ou null).
- `valrefcai` (float/string): Fundo de reserva / troco inicial.
- `valdinh` (float/string): Valor declarado em dinheiro.
- `valcart` (float/string): Valor declarado em cartao de debito/credito.
- `valnotpra` (float/string): Valor declarado a prazo (faturado/convenio).
- `venda_combustivel` (float/string): Subtotal faturado em combustiveis.
- `venda_produtos` (float/string): Subtotal faturado em loja de conveniencia / lubrificantes.
- `litros` (float/string): Total de litros faturados no turno.
- `valtot` (float/string): Total geral consolidado do fechamento.

#### 4. Tabela `pedido` (Cabecalho de Vendas / Cupons Fiscais):
- `codi` (string/int): Identificador unico do pedido / cupom fiscal.
- `pdv` (string/int): Identificador do PDV emissor.
- `dtem` (string ISO): Data e hora da emissao.
- `valortotal` (float/string): Valor total liquido da venda.
- `situ` (string): Situacao do cupom ("A" para ativo/aprovado, "C" para cancelado).
- `vendedor` (string): Matricula ou nome do frentista.
- `ven_tx_motivo_cancelamento` (string): Motivo do cancelamento se cancelado.
- `formapg` (string): Codigo ou descricao da condicao de pagamento.

#### 5. Tabela `itemped` (Itens de Venda do Cupom):
- `controle` (string/int): Sequencial do item dentro do pedido.
- `pedido` (string/int): Chave estrangeira referenciando `pedido.codi`.
- `codpec` (string): Codigo de barras ou SKU do produto/combustivel.
- `valunit` (float/string): Preco unitario cobrado.
- `quant` (float/string): Quantidade vendida (litros ou unidades).
- `valitem` (float/string): Valor total do item.

### 3.4 Sanitizacao e Limites de Lote (Batch Sizing)

1. **Formatacao Numerica:** O gateway da AURA possui sanitizador inteligente nativo que converte automaticamente formatos monetarios brasileiros (ex: `"1.250,50"` vira `1250.5` e `"5,89"` vira `5.89`). No entanto, o envio em formato numerico `float` padrao e altamente recomendado para melhor performance.
2. **Janela Temporal e Frequencia:**
   - Dados de `tanques` e `fechabomba`: Enviar a foto atual (estado mais recente) a cada 5 a 15 minutos.
   - Dados de `fechacaixa`: Enviar fechamentos das ultimas 24 a 48 horas.
   - Dados de `pedido` e `itemped`: Enviar vendas emitidas nas ultimas 12 a 24 horas em lotes limitados a no maximo 500 pedidos por sincronizacao.
3. **Limite Seguro de Carga:** Nao envie lotes com mais de 5.000 itens totais por requisicao HTTP. Se houver historico acumulado, segmente o envio em multiplas requisicoes sequenciais com intervalo de 500ms entre elas.

### 3.5 Exemplo Completo de Extracao Segura em Python

```python
"""
Modulo: integrations/aura/extractor.py
Extracao somente-leitura e envio em lote para o AURA Partner Gateway.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
import requests

logger = logging.getLogger("integrations.aura")


class AuraSyncJob:
    """Job responsavel por extrair dados do WebPosto e sincronizar com a AURA."""

    def __init__(
        self,
        base_url: str,
        partner_key: str,
        station_id: str,
        db_connection_pool: Any,
        timeout_seconds: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.partner_key = partner_key
        self.station_id = station_id
        self.pool = db_connection_pool
        self.timeout = timeout_seconds

    def _get_connection(self) -> tuple[Any, bool]:
        """Obtem conexao de forma compativel com Pool (psycopg2) ou Conexao direta."""
        if hasattr(self.pool, "getconn"):
            return self.pool.getconn(), True
        elif hasattr(self.pool, "connect"):
            return self.pool.connect(), False
        return self.pool, False

    def _query_readonly(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executa consulta com garantia de isolamento somente-leitura."""
        conn, is_pool = self._get_connection()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute("SET TRANSACTION READ ONLY;")
                except Exception:
                    pass
                cursor.execute(sql, params)
                if not cursor.description:
                    return []
                columns = [desc[0].lower() for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        finally:
            if is_pool and hasattr(self.pool, "putconn"):
                self.pool.putconn(conn)

    def extract_recent_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extrai dados recentes das tabelas padrao sem onerar o banco de dados."""
        # O WebPosto opera no horario local brasileiro (America/Sao_Paulo)
        # O uso do datetime local previne corte indevido de 3 horas por descompasso UTC
        limit_date = datetime.now() - timedelta(hours=24)
        limit_date_str = limit_date.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Tanques (Estado mais recente)
        tanques_sql = """
            SELECT codtan, prl_ds_produto_lmc, codlmc, ultima_leitura,
                   volume, volume_agua, temperatura, capacidade, iniciodia, tan_vl_quantidade_fim
            FROM tanques
            ORDER BY codtan ASC;
        """
        tanques = self._query_readonly(tanques_sql)

        # 2. Encerrantes de Bomba (Ultimas 24h)
        bomba_sql = """
            SELECT ilha, codbom, codtan, codpro, turno, codpdv, dtmov,
                   encltsa, enclts, qtdeaf, preco, encdinh
            FROM fechabomba
            WHERE dtmov >= %s
            ORDER BY dtmov DESC
            LIMIT 200;
        """
        fechabomba = self._query_readonly(bomba_sql, (limit_date_str,))

        # 3. Fechamentos de Caixa (Ultimas 48h)
        caixa_sql = """
            SELECT cai_cd_caixa, codpdv, fechado, matricula, turno, dtmov,
                   cai_ts_abertura, cai_ts_fechamento, valrefcai, valdinh, valcart,
                   valnotpra, venda_combustivel, venda_produtos, litros, valtot
            FROM fechacaixa
            WHERE dtmov >= %s
            ORDER BY dtmov DESC
            LIMIT 50;
        """
        fechacaixa = self._query_readonly(caixa_sql, (limit_date_str,))

        # 4. Pedidos / Cupons Recentes (Limite seguro de 500 registros)
        pedido_sql = """
            SELECT codi, pdv, dtem, valortotal, situ, vendedor,
                   ven_tx_motivo_cancelamento, formapg
            FROM pedido
            WHERE dtem >= %s AND COALESCE(situ, '') != 'C'
            ORDER BY dtem DESC
            LIMIT 500;
        """
        pedidos = self._query_readonly(pedido_sql, (limit_date_str,))

        # 5. Itens dos pedidos extraidos
        pedido_ids = [p["codi"] for p in pedidos if "codi" in p]
        itens: List[Dict[str, Any]] = []
        if pedido_ids:
            format_strings = ",".join(["%s"] * len(pedido_ids))
            item_sql = f"""
                SELECT controle, pedido, codpec, valunit, quant, valitem
                FROM itemped
                WHERE pedido IN ({format_strings})
                ORDER BY controle ASC;
            """
            itens = self._query_readonly(item_sql, tuple(pedido_ids))

        return {
            "tanques": tanques,
            "fechabomba": fechabomba,
            "fechacaixa": fechacaixa,
            "pedido": pedidos,
            "itemped": itens,
        }

    def execute_sync(self, max_retries: int = 3) -> bool:
        """Executa extracao e envio para o AURA Partner Gateway com reconexao e circuit breaker."""
        try:
            tables_data = self.extract_recent_data()
            url = f"{self.base_url}/api/v1/partner/stations/{self.station_id}/raw-sync"
            headers = {
                "X-Partner-Key": self.partner_key,
                "X-Station-ID": self.station_id,
                "Content-Type": "application/json",
            }
            payload = {
                "station_id": self.station_id,
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                "tables": tables_data,
            }

            for attempt in range(1, max_retries + 1):
                try:
                    response = requests.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout,
                    )
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(
                            "AURA Sync: Sucesso para estacao %s. Contagens: %s",
                            self.station_id,
                            result.get("record_counts"),
                        )
                        return True
                    elif response.status_code in (400, 401, 422):
                        # Erro de configuracao/payload: nao retentar
                        logger.error(
                            "AURA Sync: Erro de validacao AURA (HTTP %d): %s",
                            response.status_code,
                            response.text,
                        )
                        return False
                    else:
                        logger.warning(
                            "AURA Sync: Tentativa %d/%d retornou HTTP %d. Resposta: %s",
                            attempt,
                            max_retries,
                            response.status_code,
                            response.text,
                        )
                except requests.exceptions.RequestException as req_exc:
                    logger.warning(
                        "AURA Sync: Tentativa %d/%d falha de rede: %s",
                        attempt,
                        max_retries,
                        req_exc,
                    )

            logger.error("AURA Sync: Esgotadas todas as tentativas. O BI segue operacional.")
            return False

        except Exception as exc:
            logger.error("AURA Sync: Erro inesperado na rotina de extracao: %s", exc)
            return False
```

---

## SECAO 4: CONTRATO DO CHAT CONVERSACIONAL

### 4.1 Especificacao do Endpoint

- **Metodo:** `POST`
- **Rota:** `/api/v1/partner/chat`

#### Headers HTTP Obrigatorios:
| Header | Tipo | Descricao |
| :--- | :--- | :--- |
| `X-Partner-Key` | String | Chave de autenticacao de parceiro |
| `X-Station-ID` | String | Identificador da estacao do posto |
| `Content-Type` | String | `application/json` |

#### Corpo da Requisicao (`PartnerChatRequest`):
```json
{
  "query": "Como estao as vendas de Gasolina Comum hoje em relacao a media?",
  "stream": true,
  "session_id": "sessao_usr_987654",
  "station_id": "posto_matriz_01",
  "tenant_id": "rede_norte",
  "context": {
    "usuario_cargo": "Gerente de Pista",
    "origem": "portal_bi_web"
  }
}
```

- `query` (string, obrigatorio): Pergunta em linguagem natural enviada pelo usuario.
- `stream` (boolean, default: `true`): Se `true`, a resposta e enviada via Server-Sent Events (SSE). Se `false`, retorna JSON consolidado apos conclusao.
- `session_id` (string, opcional): Identificador persistente da conversa para preservar contexto.
- `station_id` (string, opcional): Deve coincidir com o header `X-Station-ID` se informado.
- `tenant_id` (string, opcional): Codigo da rede de postos para segmentacao corporativa.
- `context` (objeto, opcional): Metadados complementares.

---

### 4.2 Protocolo de Streaming SSE Filtrado

O endpoint de parceiros da AURA foi projetado exclusivamente para transmissao em texto puro.
Internamente, a IA do posto gera calculos, intencoes e telemetria, porem o gateway filtra tudo e emite exclusivamente dois tipos de eventos para o parceiro:

1. **`event: delta`**: Emitido continuamente com os fragmentos do texto final sintetizado.
2. **`event: done`**: Emitido no encerramento da geracao da resposta.

#### Exemplo do Fluxo de Linhas Recebido na Conexao SSE:
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
X-Station-ID: posto_matriz_01
X-GenUI-Enabled: 0

event: delta
data: {"chunk_type":"delta","text":"A Gasolina Comum registrou ","session_id":"sessao_usr_987654"}

event: delta
data: {"chunk_type":"delta","text":"um volume de 1.250 litros ate as 13h, ","session_id":"sessao_usr_987654"}

event: delta
data: {"chunk_type":"delta","text":"representando um crescimento de 8,4% frente a media dos ultimos 4 dias.","session_id":"sessao_usr_987654"}

event: done
data: {"chunk_type":"done","text":"","session_id":"sessao_usr_987654"}

```

---

### 4.3 Implementacao do Cliente Consumidor SSE em TypeScript / JavaScript

O codigo abaixo utiliza a API padrao `fetch` com `ReadableStream`, decodificacao UTF-8, controle de timeouts via `AbortController` e reconexao automatica com backoff exponencial. Compativel com React, Vue, Angular, Next.js ou Node.js (v18+).

```typescript
/**
 * Modulo: integrations/aura/auraChatClient.ts
 * Consumidor robusto de SSE para o chat AURA em modo texto puro com reconexao e timeout.
 */

export interface ChatChunk {
  chunk_type: "delta" | "done" | "error";
  text?: string;
  session_id?: string;
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onComplete: (fullText: string) => void;
  onError: (errorMsg: string) => void;
}

export interface AuraChatConfig {
  baseUrl: string;
  partnerKey: string;
  stationId: string;
  timeoutMs?: number; // Padrao: 60000ms (60s)
  maxRetries?: number; // Padrao: 3 tentativas
}

export async function streamAuraChat(
  query: string,
  sessionId: string,
  config: AuraChatConfig,
  callbacks: StreamCallbacks
): Promise<void> {
  const endpoint = `${config.baseUrl.replace(/\/$/, "")}/api/v1/partner/chat`;
  const maxRetries = config.maxRetries ?? 3;
  const timeoutMs = config.timeoutMs ?? 60000;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    let accumulatedText = "";
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "X-Partner-Key": config.partnerKey,
          "X-Station-ID": config.stationId,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
          stream: true,
          session_id: sessionId,
          station_id: config.stationId,
        }),
      });

      clearTimeout(timeoutId);

      // Erros de cliente (4xx) nao sao transientes: falha imediata sem retry
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("Chave de parceiro AURA nao autorizada (HTTP 401). Verifique AURA_PARTNER_KEY.");
        }
        if (response.status === 400) {
          throw new Error("Requisicao invalida ou conflito de station_id (HTTP 400).");
        }
        if (response.status === 422) {
          throw new Error("Payload rejeitado pela AURA (HTTP 422).");
        }

        // Erros de servidor (5xx): lanca erro para acionar retry se houver tentativas
        if (response.status >= 500 && attempt < maxRetries) {
          const waitTime = Math.pow(2, attempt - 1) * 1000;
          await new Promise((resolve) => setTimeout(resolve, waitTime));
          continue;
        }

        throw new Error(`Erro retornado pelo servidor AURA: HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Resposta sem corpo de streaming legivel.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // O protocolo SSE separa eventos por duas quebras de linha (\n\n)
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          const trimmed = block.trim();
          if (!trimmed) continue;

          let eventType = "message";
          let dataPayload = "";

          const lines = trimmed.split(/\r?\n/);
          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const chunk = line.slice(5).trim();
              dataPayload = dataPayload ? `${dataPayload}\n${chunk}` : chunk;
            }
          }

          if (eventType === "delta" && dataPayload) {
            try {
              const parsed: ChatChunk = JSON.parse(dataPayload);
              if (parsed.text) {
                accumulatedText += parsed.text;
                callbacks.onToken(parsed.text);
              }
            } catch {
              // Em caso de fragmento json incompleto, prossegue
            }
          } else if (eventType === "done") {
            if (dataPayload) {
              try {
                const parsed: ChatChunk = JSON.parse(dataPayload);
                if (parsed.text) {
                  accumulatedText += parsed.text;
                  callbacks.onToken(parsed.text);
                }
              } catch {
                // Ignora parsing de erro no chunk de finalizacao
              }
            }
            callbacks.onComplete(accumulatedText);
            return;
          }
        }
      }

      // Se o stream fechou sem evento explicito de done
      callbacks.onComplete(accumulatedText);
      return;

    } catch (error: any) {
      clearTimeout(timeoutId);

      // Nao retenta se for erro de autenticacao/validacao (4xx)
      const isClientError = error?.message?.includes("HTTP 40") || error?.message?.includes("HTTP 422");
      if (isClientError || attempt >= maxRetries) {
        const message = error?.name === "AbortError"
          ? `Timeout de ${timeoutMs / 1000}s esgotado na resposta da AURA.`
          : (error?.message || "Erro de comunicacao com a AURA.");
        callbacks.onError(message);
        return;
      }

      // Backoff exponencial para reconexao em falhas de rede (1s, 2s, 4s)
      const waitTime = Math.pow(2, attempt - 1) * 1000;
      await new Promise((resolve) => setTimeout(resolve, waitTime));
    }
  }
}
```

---

### 4.4 Implementacao do Cliente Consumidor SSE em Python

```python
"""
Modulo: integrations/aura/chat_service.py
Consumidor assincrono de SSE para backend Python utilizando httpx com reconexao e resiliencia.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator
import httpx

logger = logging.getLogger("integrations.aura.chat")


async def stream_aura_chat_response(
    base_url: str,
    partner_key: str,
    station_id: str,
    query: str,
    session_id: str | None = None,
    max_retries: int = 3,
    connect_timeout: float = 5.0,
    read_timeout: float = 60.0,
) -> AsyncGenerator[str, None]:
    """
    Consome o endpoint /api/v1/partner/chat e gera tokens textuais (deltas).
    Implementa reconexao com backoff exponencial para falhas transientes de rede.
    Descarta silenciosamente qualquer outro tipo de evento interno.
    """
    url = f"{base_url.rstrip('/')}/api/v1/partner/chat"
    headers = {
        "X-Partner-Key": partner_key,
        "X-Station-ID": station_id,
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "stream": True,
        "session_id": session_id or f"sess_{station_id}",
        "station_id": station_id,
    }

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(connect=connect_timeout, read=read_timeout, write=10.0, pool=5.0)

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    # Erros de cliente (4xx) nao sao transientes: falha imediata sem retry
                    if response.status_code in (400, 401, 422):
                        error_body = await response.aread()
                        raise ValueError(
                            f"Erro de configuracao/autenticacao AURA (HTTP {response.status_code}): {error_body.decode('utf-8')}"
                        )

                    # Erros de servidor (5xx): lanca erro para acionar retry se houver tentativas
                    if response.status_code >= 500:
                        error_body = await response.aread()
                        raise httpx.HTTPStatusError(
                            f"Servidor AURA retornou HTTP {response.status_code}: {error_body.decode('utf-8')}",
                            request=response.request,
                            response=response,
                        )

                    current_event = None
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip()
                        if not line:
                            current_event = None
                            continue

                        # Parsing seguro sem corromper conteudo interno
                        if line.startswith("event:"):
                            current_event = line[6:].strip()
                        elif line.startswith("data:"):
                            data_str = line[5:].strip()
                            if current_event == "delta":
                                try:
                                    payload_json = json.loads(data_str)
                                    token = payload_json.get("text", "")
                                    if token:
                                        yield token
                                except json.JSONDecodeError:
                                    continue
                            elif current_event == "done":
                                if data_str:
                                    try:
                                        payload_json = json.loads(data_str)
                                        token = payload_json.get("text", "")
                                        if token:
                                            yield token
                                    except json.JSONDecodeError:
                                        pass
                                return

            # Fluxo completado com sucesso
            return

        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            if attempt < max_retries:
                wait_time = 2 ** (attempt - 1)
                logger.warning(
                    f"AURA Chat SSE: Tentativa {attempt}/{max_retries} falhou ({exc}). Reconectando em {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"AURA Chat SSE: Esgotadas todas as {max_retries} tentativas de conexao: {exc}")
                raise
```

---

### 4.5 Modo Sincrono (`stream: false`)

Caso o Parceiro prefira consultar o chat via requisicao HTTP padrao (sem streaming), basta passar `"stream": false`.

#### Resposta HTTP 200 Sincrona:
```json
{
  "session_id": "sessao_usr_987654",
  "station_id": "posto_matriz_01",
  "query": "Qual o saldo atual do tanque 1?",
  "response_text": "O tanque 1 (Gasolina Comum) esta com volume atual de 14.250 litros, operando a 95% da capacidade.",
  "intent": "tanques",
  "confidence": 0.98
}
```

---

### 4.6 Tratamento de Erros, Codigos de Retorno e Politica de Reconexao

| Codigo HTTP | Causa Raiz | Politica de Retry | Como o Parceiro Deve Tratar |
| :--- | :--- | :--- | :--- |
| `401 Unauthorized` | Cabecalho `X-Partner-Key` ausente ou incorreto | **NAO Retentar** | Verificar variavel de ambiente `AURA_PARTNER_KEY` |
| `400 Bad Request` | Conflito de `station_id` entre Header e URL/Corpo | **NAO Retentar** | Garantir que o valor em `X-Station-ID` seja identico ao parametro da URL e do JSON |
| `422 Unprocessable` | JSON malformado ou payload sem tabelas validas | **NAO Retentar** | Validar esquema antes do envio (verificar nomes de campos) |
| `500 Internal Error` | Falha interna no motor de processamento AURA | **Retentar 3x** | Backoff exponencial (1s, 2s, 4s); se persistir, circuit breaker |
| `502 / 503 / 504` | Gateway reiniciando ou sobrecarregado | **Retentar 3x** | Backoff exponencial (1s, 2s, 4s); exibir aviso amigavel |
| `Timeout de Rede` | Servidor da AURA offline ou conexao congelada | **Retentar 3x** | Circuit breaker: cancelar chamada e manter BI 100% operacional |

---

## SECAO 5: SEGURANCA E CONFIGURACAO DE AMBIENTE

### 5.1 Variaveis de Ambiente Recomendadas

O Parceiro deve configurar os seguintes parametros no arquivo `.env` do backend ou no cofre de segredos (Vault / AWS Secrets Manager):

```ini
# =============================================================================
# CONFIGURACOES DE INTEGRACAO AURA PARTNER GATEWAY
# =============================================================================

# URL base do gateway AURA (IP Tailscale ou Dominio Seguro HTTPS)
AURA_API_BASE_URL=https://marlonh-supwp.tail6cf59f.ts.net

# Chave secreta compartilhada fornecida pela equipe AURA
AURA_PARTNER_KEY=aura_pk_live_LJOztb9MVhTu2d0UErvDPZeCFfOMU7uawlWJ9YNEuvM

# Identificador unico padrao do posto ou filial atual
AURA_STATION_ID=posto_matriz_01

# Timeouts de comunicacao em segundos
AURA_CONNECT_TIMEOUT=5
AURA_READ_TIMEOUT=30
AURA_CHAT_TIMEOUT=60

# Intervalo do Job de Sincronizacao em minutos
AURA_SYNC_INTERVAL_MINUTES=10

# Habilitar recurso de Chat no Portal de BI (true/false)
AURA_CHAT_ENABLED=true
```

### 5.2 Topologia de Rede e Conexao

1. **Conexao Direta via Tailscale Mesh (Recomendado):**
   - O servidor da AURA e o servidor de BI do Parceiro conectam-se atraves de uma rede privada virtual WireGuard gerenciada pelo Tailscale.
   - Vantagens: Criptografia ponta a ponta sem necessidade de expor portas publicas na internet nem configurar IP fixo no posto revendedor.
2. **Conexao via Proxy Reverso HTTPS:**
   - Caso a comunicacao ocorra via internet publica, a AURA devera estar protegida atras de um proxy reverso (Nginx, Traefik ou Cloudflare) com TLS 1.3 ativado.
   - O cabecalho `X-Partner-Key` deve trafegar exclusivamente sob conexao segura HTTPS.

---

## SECAO 6: PLANO DE TESTES E HOMOLOGACAO PASSO A PASSO

O Agente de IA do Parceiro devera seguir estritamente o roteiro de validacao abaixo para garantir o funcionamento correto antes de solicitar publicacao.

### Passo 1: Validacao de Conectividade e Healthcheck
Verificar se o gateway esta respondendo adequadamente:

```bash
curl -X GET "https://marlonh-supwp.tail6cf59f.ts.net/api/v1/partner/health"
```
**Resposta esperada (HTTP 200):**
```json
{
  "status": "online",
  "service": "AURA Partner Gateway (Opcao A)",
  "protocol_version": "1.0.0"
}
```

---

### Passo 2: Teste de Seguranca e Autenticacao
Garantir que chamadas nao autenticadas sejam barradas:

```bash
# Tentativa 1: Sem cabecalho de chave (deve retornar 401)
curl -s -o /dev/null -w "%{http_code}\n" -X GET "https://marlonh-supwp.tail6cf59f.ts.net/api/v1/partner/stations/posto_teste/status"
# Saida esperada: 401

# Tentativa 2: Com chave valida
curl -s -X GET "https://marlonh-supwp.tail6cf59f.ts.net/api/v1/partner/stations/posto_teste/status" \
  -H "X-Partner-Key: aura_pk_live_LJOztb9MVhTu2d0UErvDPZeCFfOMU7uawlWJ9YNEuvM"
# Saida esperada: HTTP 200 com status "ready" ou "empty"
```

---

### Passo 3: Envio de Lote Piloto de Dados (`raw-sync`)
Realizar uma sincronizacao com dados de teste:

```bash
curl -X POST "https://marlonh-supwp.tail6cf59f.ts.net/api/v1/partner/stations/posto_teste/raw-sync" \
  -H "Content-Type: application/json" \
  -H "X-Partner-Key: aura_pk_live_LJOztb9MVhTu2d0UErvDPZeCFfOMU7uawlWJ9YNEuvM" \
  -H "X-Station-ID: posto_teste" \
  -d '{
    "station_id": "posto_teste",
    "tables": {
      "tanques": [
        {
          "codtan": "1",
          "prl_ds_produto_lmc": "Gasolina Comum",
          "volume": 12000.0,
          "capacidade": 15000.0
        }
      ],
      "fechabomba": [
        {
          "ilha": "1",
          "codbom": "1",
          "codtan": "1",
          "codpro": "GAS_COMUM",
          "dtmov": "2026-10-25T10:00:00",
          "encltsa": 1000.0,
          "enclts": 1200.0
        }
      ]
    }
  }'
```
**Resposta esperada (HTTP 200):**
```json
{
  "status": "success",
  "station_id": "posto_teste",
  "tables_stored": ["tanques", "fechabomba"],
  "record_counts": {
    "tanques": 1,
    "fechabomba": 1
  }
}
```

---

### Passo 4: Verificacao do Mapeamento Canonico AUPS
Confirmar que os dados brutos foram mapeados com precisao:

```bash
curl -X GET "https://marlonh-supwp.tail6cf59f.ts.net/api/v1/partner/stations/posto_teste/tanks" \
  -H "X-Partner-Key: aura_pk_live_LJOztb9MVhTu2d0UErvDPZeCFfOMU7uawlWJ9YNEuvM"
```
**Resposta esperada (HTTP 200):**
```json
{
  "station_id": "posto_teste",
  "count": 1,
  "tanks": [
    {
      "identificador_tanque": "1",
      "combustivel": "Gasolina Comum",
      "volume_atual_litros": 12000.0,
      "capacidade_nominal_litros": 15000.0
    }
  ]
}
```

---

### Passo 5: Teste do Chat Conversacional Sincrono
Validar o processamento em texto puro sem streaming:

```bash
curl -X POST "https://marlonh-supwp.tail6cf59f.ts.net/api/v1/partner/chat" \
  -H "Content-Type: application/json" \
  -H "X-Partner-Key: aura_pk_live_LJOztb9MVhTu2d0UErvDPZeCFfOMU7uawlWJ9YNEuvM" \
  -H "X-Station-ID: posto_teste" \
  -d '{
    "query": "Qual o status do tanque 1?",
    "stream": false,
    "station_id": "posto_teste"
  }'
```
**Resposta esperada:** JSON contendo `response_text` e `intent`.

---

### Passo 6: Teste do Streaming SSE
Validar a recepcao dos eventos de streaming no terminal:

```bash
curl -N -X POST "https://marlonh-supwp.tail6cf59f.ts.net/api/v1/partner/chat" \
  -H "Content-Type: application/json" \
  -H "X-Partner-Key: aura_pk_live_LJOztb9MVhTu2d0UErvDPZeCFfOMU7uawlWJ9YNEuvM" \
  -H "X-Station-ID: posto_teste" \
  -d '{
    "query": "Resuma a situacao dos tanques",
    "stream": true,
    "station_id": "posto_teste"
  }'
```
**Comportamento esperado:** O terminal devera receber sucessivos blocos `event: delta` contendo os fragmentos da resposta e finalizar com o bloco `event: done`.

---

### Passo 7: Validacao de Nao-Regressao do BI Existente
Execute a suite de testes automatizados do projeto do Parceiro:

```bash
# Exemplo para projetos em Python (pytest):
pytest tests/ -v

# Exemplo para projetos em Node.js (jest / vitest):
npm test
```
**Criterio obrigatorio de aceite:** 100% dos testes do BI do parceiro devem continuar passando com zero falhas e zero modificacoes nos testes existentes.

---

## SECAO 7: PERGUNTAS FREQUENTES E RESOLUCAO DE PROBLEMAS (FAQ)

#### P1: Por que o chat nao retorna graficos GenUI ou cartoes visuais?
**R:** A API de parceiros opera intencionalmente em modo texto puro corporativo (`enable_genui=False`). Isso foi definido para garantir compatibilidade imediata com qualquer interface de usuario do parceiro (web, mobile, bot de mensageria), evitando que o parceiro precise implementar renderizadores complexos de micro-frontends.

#### P2: O que acontece se a sincronizacao de dados falhar no meio do dia?
**R:** O staging da AURA mantem os dados persistidos no arquivo `raw_data.json` da estacao. Quando o proximo lote for sincronizado com sucesso, ele atualizara a foto dos dados. Caso ocorra queda temporaria na rede, a AURA respondera as perguntas dos operadores com base no ultimo estado armazenado.

#### P3: O identificador `station_id` precisa ser numerico?
**R:** Nao. O `station_id` e uma string de ate 64 caracteres. Recomendamos usar padroes como `posto_01`, `filial_centro` ou o proprio CNPJ sem pontuacao do posto (ex: `12345678000199`). Evite espacos e caracteres especiais (utilize apenas letras, numeros, hifens e sublinhados).

#### P4: Como evitar que o processo de extracao trave o banco de dados do posto?
**R:** Execute a conexao explicitamente em modo somente-leitura (`SET TRANSACTION READ ONLY`), limite o intervalo de busca para as ultimas 24 ou 48 horas e utilize a clausula `LIMIT` nas consultas de cupons e itens. Nao crie indices nem altere o esquema do banco WebPosto.

---

> **AURA Partner Engineering - Todos os direitos reservados.**  
> Em caso de duvidas tecnicas durante o processo de integracao, acione diretamente a equipe de engenharia responsavel pelo gateway.
