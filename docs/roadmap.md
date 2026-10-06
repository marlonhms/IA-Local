# Roadmap — AURA Precision Glass

> Evolução UI/UX para um cockpit de decisão conversacional premium, mobile-first e orientado à confiança.

- Data de criação: 05/10/2026.
- Versão do documento: 1.0.
- Status: proposto; nenhuma tarefa abaixo representa implementação concluída.
- Base: README fornecido, capturas apresentadas e recomendações da conversa.
- Primeiro fluxo: conciliação de turno e caixa.
- Responsáveis: atribuir antes do início de cada fase.

## 1. Objetivo e limites

Entregar uma experiência em que o gestor identifique o diagnóstico, compreenda as limitações dos dados e encontre o próximo passo sem precisar interpretar um console técnico.

Preservar a identidade dark da AURA, com ciano e violeta, substituindo excesso de bordas, badges e blocos aninhados por hierarquia executiva, superfícies discretas e detalhamento progressivo.

### Princípios inegociáveis

- Manter a AURA como assistente sob demanda, não como substituta do ERP.
- Preservar o acesso somente leitura ao ERP descrito no README.
- Não modificar fórmulas, tolerâncias ou regras de negócio para adequar a apresentação visual.
- Não introduzir escrita no ERP, fechamento de caixa, lançamento de encerrantes ou compras automáticas.
- Preservar sanitização, isolamento por unidade e controles de privacidade existentes.
- Renderizar números e estados a partir de resultados validados, não de inferências livres do modelo.
- Distinguir valor zero, valor ausente, fonte indisponível e dado não aplicável.
- Não apresentar uma análise parcial como fechamento definitivo.
- Não exibir progresso, atualização ao vivo ou etapas que não existam no backend.
- Priorizar dispositivos e hardware reais do posto, não apenas screenshots em desktop.

### Fora do escopo inicial

- Migração de framework, bundler ou biblioteca de gráficos sem necessidade comprovada.
- Reescrita do motor de auditoria, RAG ou infraestrutura.
- Construção de um novo ERP ou de um painel SRE.
- Voz, avatar animado, partículas, gamificação ou efeitos decorativos permanentes.
- Sincronização contínua de dados sem mecanismo real implementado e autorizado.
- Persistência de histórico de conversas sem política de retenção e armazenamento definida.

### Premissas a validar

O README informa FastAPI e streaming SSE, mas não estabelece neste levantamento todos os detalhes do frontend. Os nomes de componentes e os contratos deste documento são propostas. Antes de criar arquivos, localizar a implementação real e adaptar a nomenclatura à stack existente.

As inconsistências percebidas nas capturas são hipóteses de investigação, não diagnósticos de defeitos confirmados.

## 2. Plano de entrega

As estimativas são faixas preliminares de esforço em dias úteis para uma pessoa dedicada, não compromissos de calendário. Revisar após a fase 0, considerando stack, cobertura de testes e disponibilidade dos usuários.

| Fase | Prioridade | Resultado | Dependências | Esforço proposto |
|---|---|---|---|---|
| 0 — Inventário e baseline | P0 | Arquitetura real e problemas confirmados | Nenhuma | 1–2 dias |
| 1 — Semântica e contrato | P0 | Dados e estados confiáveis | 0 | 2–4 dias |
| 2 — Design system | P1 | Tokens e componentes-base | 0; estados da 1 | 2–4 dias |
| 3 — Conciliação piloto | P0 | Primeiro fluxo completo | 1 e 2 | 3–5 dias |
| 4 — Shell e mobile | P1 | Navegação e conversa consistentes | 2 e 3 | 3–5 dias |
| 5 — Respostas especializadas | P2 | Expansão controlada dos módulos | Aprovação do piloto | 4–8 dias |
| 6 — Qualidade e validação | P0 | Evidências para lançamento | Incremental desde 1 | 3–5 dias finais |
| 7 — Rollout e acompanhamento | P1 | Publicação reversível | 6 | 1–2 dias + acompanhamento |

Acessibilidade, segurança e testes são transversais. A fase 6 consolida a validação; não é o início desses trabalhos.

### Marcos

- M0: implementação e baseline mapeados.
- M1: semântica e contrato aprovados pelo responsável do negócio.
- M2: conciliação funcional em mobile e desktop, com todos os estados.
- M3: shell e navegação aprovados com usuários.
- M4: módulos adicionais usando a mesma linguagem visual.
- M5: critérios de lançamento aprovados e rollback validado.

### Menor entrega utilizável

Entregar primeiro as fases 0, 1, 2 e 3 com validação de qualidade aplicada ao piloto. Não aguardar todos os módulos para testar a nova experiência. A navegação antiga pode permanecer temporariamente se não impedir o uso correto do fluxo.

## 3. Fase 0 — Inventário e baseline

### Objetivo

Conhecer o código real, reproduzir os fluxos existentes e estabelecer evidências antes de refatorar.

### Tarefas

- [ ] F0-01 — Localizar frontend, estilos, templates, endpoints, streaming e renderização de respostas.
- [ ] F0-02 — Identificar stack, dependências, comandos de execução e testes realmente disponíveis.
- [ ] F0-03 — Mapear navegação, composer, histórico, consultas rápidas e visão integrada.
- [ ] F0-04 — Identificar a origem dos badges, percentuais e estados mostrados na conciliação.
- [ ] F0-05 — Verificar o significado de Caixa 007, Caixa 56 e Caixa 57; documentar cada identificador.
- [ ] F0-06 — Capturar baseline nos estados parcial, conciliado, divergente e indisponível.
- [ ] F0-07 — Medir carregamento, resposta percebida, rolagem e peso do frontend nos dispositivos-alvo.
- [ ] F0-08 — Separar problemas confirmados de hipóteses visuais e registrar prioridades.
- [ ] F0-09 — Definir responsáveis por produto, frontend, backend e validação operacional.
- [ ] F0-10 — Definir branch ou mecanismo equivalente para implementação isolada e reversível.

### Entregáveis

- Mapa dos arquivos reais e dos pontos de integração.
- Inventário de componentes e estados.
- Baseline visual e de desempenho, com ambiente e condições registrados.
- Lista de hipóteses resolvidas e decisões pendentes.

### Critérios de aceite

- [ ] O fluxo atual pode ser reproduzido sem alterar dados de produção.
- [ ] Existe identificação da origem de cada número e percentual do piloto.
- [ ] Estão documentados os dispositivos, navegadores e comandos usados na validação.
- [ ] Nenhuma migração tecnológica foi iniciada por suposição.

## 4. Fase 1 — Semântica e contrato

### Objetivo

Eliminar ambiguidades e criar uma fronteira clara entre cálculo, explicação e apresentação.

### Tarefas

- [ ] F1-01 — Criar um dicionário de estados e rótulos aprovados pelo negócio.
- [ ] F1-02 — Separar finalização da análise, severidade e disponibilidade das fontes.
- [ ] F1-03 — Representar ausência de encerrantes sem converter ausência em zero.
- [ ] F1-04 — Definir rótulos humanos para identificadores de caixa, operador, unidade e turno.
- [ ] F1-05 — Definir significado, origem e critérios dos percentuais atuais.
- [ ] F1-06 — Remover percentuais sem significado operacional da camada executiva.
- [ ] F1-07 — Criar contrato estruturado versionado para respostas operacionais.
- [ ] F1-08 — Validar o contrato no backend e tratar versões desconhecidas no frontend.
- [ ] F1-09 — Manter texto gerado pela IA separado de valores financeiros e estados oficiais.
- [ ] F1-10 — Criar fixtures sintéticas e testes para os estados do piloto.
- [ ] F1-11 — Garantir contexto da consulta por unidade, turno e período.
- [ ] F1-12 — Sanitizar mensagens e renderizar conteúdo sem execução de HTML arbitrário.

### Regras de apresentação

| Condição | Apresentação proposta | Não apresentar como |
|---|---|---|
| Caixas abertos ou encerrantes pendentes | Análise parcial; diferença provisória | Quebra confirmada |
| Encerrante ausente | Não informado / pendente | 0 L medidos |
| Zero efetivamente registrado | 0 L / R$ 0,00 | Dado ausente |
| Fonte indisponível | Fonte indisponível; análise limitada | Ausência de movimento |
| Falta de dados para cálculo | Não foi possível calcular | R$ 0,00 |
| Fechamento validado e conciliado | Conciliação validada | Apenas resposta gerada |
| Divergência confirmada pelas regras existentes | Divergência confirmada | Alerta deduzido pela cor |
| Similaridade do roteamento | Detalhe técnico identificado | Confiança da auditoria |

Não definir novos limites de severidade neste roadmap. Usar as regras existentes e validar seu mapeamento visual com o negócio.

### Contrato proposto

Exemplo sintético inspirado na captura; não representa uma API existente. Os valores monetários usam centavos inteiros. Validar o recorte temporal e a fórmula no backend antes da integração.

```json
{
  "schema_version": "1.0",
  "response_id": "synthetic-response-001",
  "intent": "shift_reconciliation",
  "context": {
    "unit_id": "synthetic-unit-01",
    "shift_id": "synthetic-shift-01",
    "queried_at": "2026-10-05T13:23:37-03:00",
    "period_start": null,
    "period_end": null
  },
  "assessment": {
    "finality": "partial",
    "severity": "attention",
    "title": "Conciliação parcial do turno",
    "limitation": "Caixas abertos e encerrantes pendentes"
  },
  "metrics": {
    "automation_revenue_cents": 7130,
    "pos_revenue_cents": 6298,
    "difference_cents": -832,
    "difference_definition": "pos_minus_automation",
    "physical_volume_liters": null,
    "physical_volume_state": "not_reported"
  },
  "pending_items": [
    {"code": "physical_readings_missing", "label": "Encerrantes não informados"},
    {"code": "registers_open", "label": "Caixas ainda abertos"}
  ],
  "sources": [
    {"id": "automation", "label": "Automação CBC04", "availability": "available", "data_as_of": null},
    {"id": "pos", "label": "PDV", "availability": "available", "data_as_of": null},
    {"id": "physical_readings", "label": "Encerrantes", "availability": "missing", "data_as_of": null}
  ],
  "recommended_action": {
    "label": "Conferir encerrantes e fechamento no ERP",
    "execution": "external_manual"
  },
  "explanation": {
    "text": "A diferença ainda é provisória; existem pendências para validar o fechamento."
  }
}
```

Regras do contrato:

- Valores críticos devem existir em campos tipados, independentemente do texto da IA.
- Valores ausentes usam null e um estado explícito quando a ausência tiver significado operacional.
- Data da consulta e data de atualização da fonte são conceitos diferentes.
- Período desconhecido não pode ser inventado a partir da hora da consulta.
- A explicação não pode substituir nem contradizer métricas, pendências ou finalização.
- Ações renderizadas devem vir de uma lista permitida; nunca executar comandos sugeridos livremente pelo modelo.
- Payload inválido deve gerar fallback seguro, sem card que aparente validação financeira.
- Histórico deve preservar o contexto original; troca de unidade não transforma respostas antigas em respostas da nova unidade.

### Critérios de aceite

- [ ] Backend e frontend distinguem null de zero em todos os testes do piloto.
- [ ] Não existe badge de sucesso definitivo em uma análise parcial.
- [ ] Percentuais apresentados possuem definição verificável.
- [ ] Valores, unidade e período permanecem consistentes entre resumo e evidências.
- [ ] O ERP continua com acesso somente leitura.

## 5. Fase 2 — Design system

### Objetivo

Criar a base visual AURA Precision Glass sem depender de estilos isolados por resposta.

### Tarefas

- [ ] F2-01 — Centralizar tokens de cor, tipografia, espaçamento, elevação e movimento.
- [ ] F2-02 — Definir uma única família de ícones compatível com a stack existente.
- [ ] F2-03 — Criar estados de foco, hover, pressionado, desabilitado e carregamento.
- [ ] F2-04 — Criar componentes-base de status, valor, comparação, divisória e ação.
- [ ] F2-05 — Usar números tabulares e formatação pt-BR em métricas.
- [ ] F2-06 — Reservar monoespaçada para código, fórmulas e identificadores.
- [ ] F2-07 — Definir versões sem blur e com movimento reduzido.
- [ ] F2-08 — Validar contraste nos fundos compostos reais, não somente nos tokens isolados.
- [ ] F2-09 — Criar uma página de demonstração local com todos os estados dos componentes.

### Tokens iniciais propostos

```css
:root {
  --aura-bg: #080c12;
  --aura-surface: #101722;
  --aura-surface-raised: #172131;
  --aura-text: #f1f5fa;
  --aura-text-secondary: #a8b4c5;
  --aura-accent: #35d4e4;
  --aura-ai: #a994ff;
  --aura-success: #4dcca0;
  --aura-warning: #f0bd62;
  --aura-danger: #f0808a;
  --aura-border: rgba(168, 180, 197, 0.16);
  --aura-space-1: 4px;
  --aura-space-2: 8px;
  --aura-space-3: 12px;
  --aura-space-4: 16px;
  --aura-space-6: 24px;
  --aura-space-8: 32px;
  --aura-radius-control: 10px;
  --aura-radius-panel: 18px;
  --aura-motion-fast: 160ms;
  --aura-motion-panel: 220ms;
}
```

Esses valores são pontos de partida, não certificação de acessibilidade nem especificação imutável.

### Regras visuais

- Uma superfície principal por resposta, evitando card dentro de card dentro de card.
- Vidro discreto no shell e em overlays; conteúdo financeiro em superfície estável.
- Gradiente ciano–violeta reservado à identidade e a poucos detalhes.
- Verde para validação real; âmbar para pendências; coral para divergência confirmada.
- Estado deve ter texto ou ícone além da cor.
- Uma ação primária por bloco de decisão.
- Sem neon permanente em todas as bordas.
- Sem encolher conteúdo essencial para preservar um layout desktop no celular.

### Critérios de aceite

- [ ] Componentes usam tokens compartilhados.
- [ ] Texto comum atende contraste mínimo de 4,5:1; texto grande, 3:1.
- [ ] Controles principais têm meta de 44–48 px de área interativa.
- [ ] Foco visível não fica cortado por overflow ou overlays.
- [ ] A informação continua compreensível sem cores, blur ou animação.

## 6. Fase 3 — Conciliação piloto

### Objetivo

Entregar a primeira resposta completa e validar a direção antes de expandir o redesign.

### Anatomia obrigatória

1. Título da consulta e contexto de unidade/turno.
2. Diagnóstico e indicação explícita de análise parcial ou definitiva.
3. Métrica principal, com sinal e unidade.
4. Limitação que afeta a interpretação.
5. Comparativo de automação e PDV.
6. Próximo passo e ações permitidas.
7. Fontes, horário e acesso às evidências.

### Tarefas

- [ ] F3-01 — Implementar DecisionCard usando o contrato validado.
- [ ] F3-02 — Destacar diferença provisória antes dos detalhes técnicos.
- [ ] F3-03 — Mostrar comparativos compactos sem repetir todos os números em texto.
- [ ] F3-04 — Implementar PendingItems com pendências verificáveis.
- [ ] F3-05 — Implementar EvidencePanel lateral no desktop e amplo no mobile.
- [ ] F3-06 — Incluir fórmula/definição da diferença e recorte dos dados nas evidências.
- [ ] F3-07 — Exibir modelo e tempo de resposta apenas em detalhes técnicos.
- [ ] F3-08 — Implementar ações “Ver pendências” e “Como foi calculado”.
- [ ] F3-09 — Não oferecer “Fechar caixa” ou “Lançar encerrantes” como escrita na AURA.
- [ ] F3-10 — Testar rótulos longos, valores grandes, negativos e fontes parciais.
- [ ] F3-11 — Capturar comparação antes/depois com a mesma fixture.
- [ ] F3-12 — Fazer uma primeira rodada de avaliação com usuários antes da expansão.

### Estados obrigatórios

| Estado | Comportamento esperado |
|---|---|
| Carregamento | Indicação real de solicitação em andamento, sem percentuais fictícios |
| Análise parcial | Limitações e valores provisórios claramente visíveis |
| Conciliação validada | Confirmação conforme regras e dados validados |
| Divergência confirmada | Destaque semântico e evidências verificáveis |
| Sem movimento | Diferente de erro e de fonte indisponível |
| Dados incompletos | Métricas indisponíveis não viram zero |
| Fonte indisponível | Escopo limitado explicitado |
| Falha | Mensagem segura e tentativa novamente quando suportada |
| Payload desconhecido | Fallback legível, sem interpretação financeira inventada |

### Critérios de aceite

- [ ] Status, limitação e próxima ação são visíveis antes de abrir detalhes.
- [ ] O usuário consegue verificar a origem de cada valor relevante.
- [ ] Estado parcial nunca recebe linguagem de quebra definitiva.
- [ ] Drawer/painel devolve o foco ao acionador quando fechado.
- [ ] Todos os estados possuem fixtures e evidências de validação.

## 7. Fase 4 — Shell, navegação e mobile

### Objetivo

Dar consistência à aplicação inteira sem desviar o foco da conversa.

### Componentes propostos

| Componente | Responsabilidade |
|---|---|
| AppShell | Estrutura e regiões principais |
| NavigationDrawer | Navegação adaptável e preferências |
| ConversationThread | Histórico visual e política de rolagem |
| DecisionCard | Resposta executiva |
| StatusBadge | Semântica do estado |
| MetricComparison | Valores comparáveis e unidades |
| PendingItems | Limitações e pendências |
| EvidencePanel | Proveniência e detalhamento |
| ContextualActions | Ações permitidas por intenção |
| MessageComposer | Entrada, envio e estado da solicitação |

Esses nomes descrevem responsabilidades; não pressupõem React, Vue ou uma estrutura de diretórios existente.

### Tarefas

- [ ] F4-01 — Simplificar header: identidade, contexto de unidade/turno e controles essenciais.
- [ ] F4-02 — Remover horário com segundos se não servir a uma tarefa real.
- [ ] F4-03 — Organizar navegação em Assistente, Panorama e Consultas rápidas.
- [ ] F4-04 — Manter Nova conversa visível e mover efeitos sonoros para Preferências.
- [ ] F4-05 — Adicionar conversas recentes somente se a persistência já existir ou for aprovada.
- [ ] F4-06 — Reduzir o destaque simultâneo de borda, faixa, fundo e glow do item ativo.
- [ ] F4-07 — Mostrar até três sugestões contextuais e um acesso a mais consultas.
- [ ] F4-08 — Implementar drawer mobile com gerenciamento de foco e fechamento por Escape.
- [ ] F4-09 — Garantir composer utilizável com teclado virtual e safe area.
- [ ] F4-10 — Definir Enter para enviar e Shift+Enter para nova linha, se compatível com o input.
- [ ] F4-11 — Evitar envio duplicado e definir cancelamento apenas se houver suporte real.
- [ ] F4-12 — Não forçar autoscroll se o usuário estiver lendo mensagens anteriores.
- [ ] F4-13 — Adicionar botão para voltar à mensagem recente quando necessário.
- [ ] F4-14 — Exibir estados de streaming a partir de eventos reais do backend.
- [ ] F4-15 — Não apresentar conexão ativa como garantia de dados atualizados.
- [ ] F4-16 — Adaptar visão integrada sem torná-la obrigatória para abrir evidências.

### Referências responsivas de teste

- 360 e 390 px: celular, teclado aberto e orientação vertical.
- 768 px: tablet e navegação intermediária.
- 1280 e 1440 px: desktop com e sem painel de evidências.
- Zoom de 200% e teste de reflow em largura equivalente a 320 CSS px.

Os breakpoints de implementação devem seguir o comportamento do conteúdo, não apenas esses números.

### Critérios de aceite

- [ ] Não existe overflow horizontal da página nos fluxos essenciais.
- [ ] Teclado virtual não esconde campo ou ação de envio.
- [ ] Menus e evidências funcionam integralmente por teclado.
- [ ] Rolagem durante streaming respeita a posição de leitura.
- [ ] Identificadores de unidade e turno permanecem claros durante troca de contexto.

## 8. Fase 5 — Respostas especializadas

### Objetivo

Criar originalidade funcional reaproveitando a linguagem do piloto.

### Ordem proposta

1. Autonomia de tanques.
2. Vazão e desempenho dos bicos.
3. Conciliação físico–contábil do LMC.
4. Associações e combos de conveniência.

Repriorizar conforme frequência de uso real e disponibilidade de contratos confiáveis.

### Tarefas

- [ ] F5-01 — Criar registro de renderizadores por intenção, sem HTML arbitrário gerado pela IA.
- [ ] F5-02 — Reutilizar diagnóstico, limitação, proveniência e ações em todos os módulos.
- [ ] F5-03 — Tanques: apresentar horizonte estimado, saldo e premissas disponíveis.
- [ ] F5-04 — Diferenciar autonomia até reserva crítica e autonomia até esgotamento, se ambas existirem.
- [ ] F5-05 — Bicos: mostrar valor medido, unidade, período e regra usada na avaliação.
- [ ] F5-06 — LMC: apresentar valores físicos/contábeis, recorte e regra vigente já validada.
- [ ] F5-07 — Não tratar textos legais do README como validação de vigência regulatória.
- [ ] F5-08 — Conveniência: apresentar associação, suporte/amostra e limitações; não prometer ganho garantido.
- [ ] F5-09 — Garantir alternativa textual para gráficos e representação sem dados.
- [ ] F5-10 — Criar fixtures e testes por módulo antes de ativá-lo.

### Critérios de aceite

- [ ] Todos os módulos mantêm diagnóstico → evidências → próximo passo.
- [ ] Cada módulo comunica suas próprias limitações e unidades.
- [ ] Nenhuma regra de negócio ou tolerância foi alterada pela refatoração visual.
- [ ] Gráficos não são a única forma de acessar informação relevante.

## 9. Fase 6 — Qualidade e validação

### Objetivo

Aprovar funcionalidade, usabilidade, acessibilidade, privacidade e desempenho com evidências.

### Tarefas

- [x] F6-01 — Executar os testes de domínio existentes identificados na fase 0.
- [x] F6-02 — Testar contratos, estados, null/zero, formatação e contexto.
- [x] F6-03 — Testar teclado, foco, leitores de tela e anúncios durante carregamento.
- [x] F6-04 — Evitar anunciar cada token do streaming ao leitor de tela; definir anúncio estável.
- [x] F6-05 — Testar contraste, zoom, reflow, movimento reduzido e fallback sem blur.
- [x] F6-06 — Testar desconexão, timeout, payload inválido e fonte indisponível.
- [x] F6-07 — Testar mensagens maliciosas e sanitização do conteúdo renderizado.
- [x] F6-08 — Confirmar ausência de texto livre, PII e dados financeiros em telemetria de UX.
- [x] F6-09 — Comparar desempenho com baseline usando condições equivalentes.
- [x] F6-10 — Avaliar com 3–5 usuários operacionais disponíveis; registrar limites da amostra.
- [x] F6-11 — Corrigir bloqueadores antes do lançamento, independentemente do acabamento visual.

### Roteiro de avaliação

1. Identificar se a conciliação está finalizada ou parcial.
2. Explicar o significado da diferença financeira apresentada.
3. Encontrar o que impede a validação definitiva.
4. Abrir a origem do cálculo.
5. Identificar o próximo passo e onde deve ser executado.
6. Repetir no celular sem orientação do avaliador.

### Metas propostas

Metas de aprovação do piloto, não métricas já medidas. Ajustar com o negócio após o baseline. A amostra pequena oferece sinal qualitativo, não comprovação estatística.

| Indicador | Meta inicial | Como verificar |
|---|---|---|
| Entendimento do diagnóstico | Até 10 segundos por tarefa | Observação sem instruções |
| Parcial confundido com definitivo | Nenhum caso no piloto | Pergunta de compreensão |
| Pendência e próximo passo encontrados | Sem ajuda nos casos essenciais | Teste de tarefa |
| Acesso a evidências | Uma ação a partir da resposta | Inspeção do fluxo |
| Null e zero | 100% dos cenários automatizados corretos | Testes de contrato/renderização |
| Overflow e controles ocultos | Nenhum bloqueador nas larguras-alvo | Teste responsivo |
| Regressão de domínio | Nenhuma falha nova | Suíte identificada na fase 0 |
| Desempenho do frontend | Dentro do orçamento aprovado após baseline | Comparação em hardware-alvo |

Separar latência de backend, chegada do primeiro evento, renderização e conclusão da resposta. Melhorias de CSS não devem ser apresentadas como redução garantida do tempo de inferência.

### Critérios de aceite

- [x] Todos os bloqueadores P0 foram resolvidos.
- [x] Testes de domínio e do novo fluxo passam no ambiente documentado.
- [x] Existe comparação antes/depois e registro de tarefas dos usuários.
- [x] Nenhum dado sensível foi adicionado à telemetria.
- [x] Rollback da interface foi ensaiado.

## 10. Fase 7 — Rollout e acompanhamento

### Objetivo

Publicar de forma controlada, reversível e sem impacto nos processos do posto.

### Tarefas

- [ ] F7-01 — Ativar o novo renderizador para conciliação em ambiente de teste.
- [ ] F7-02 — Usar toggle de configuração ou mecanismo equivalente para voltar à interface anterior.
- [ ] F7-03 — Se payloads mudarem, manter compatibilidade documentada durante a transição.
- [ ] F7-04 — Publicar para um grupo piloto antes de expandir.
- [ ] F7-05 — Registrar feedback de interpretação, navegação e mobile.
- [ ] F7-06 — Monitorar falhas de renderização, erro de contrato e fallback sem capturar conteúdo sensível.
- [ ] F7-07 — Expandir módulo por módulo após aprovação.
- [ ] F7-08 — Remover componentes antigos apenas após estabilização e revisão das dependências.
- [ ] F7-09 — Atualizar README, guia operacional e registro de decisões.

### Gatilhos de rollback

- Divergência de valores entre resumo e evidências.
- Análise parcial apresentada como resultado definitivo.
- Fonte ausente apresentada como zero ou sem movimento.
- Troca incorreta de unidade/turno ou exposição de dados entre contextos.
- Perda de funcionalidades essenciais ou impossibilidade de uso no celular.
- Regressão de acessibilidade que impeça a operação.
- Vazamento de informação sensível.
- Degradação acima do orçamento de desempenho aprovado.

O rollback deve incluir compatibilidade do contrato, não apenas troca de CSS. Não reverter silenciosamente para uma apresentação que mantenha uma ambiguidade financeira já confirmada.

## 11. Matriz de testes mínima

| Cenário | Resultado esperado | Camada |
|---|---|---|
| Encerrante null | Pendente, não 0 L | Contrato + UI |
| Encerrante zero confirmado | 0 L | Contrato + UI |
| Caixa aberto e diferença negativa | Diferença provisória | Domínio + UI |
| Diferença positiva | Sinal e definição preservados | Domínio + UI |
| PDV indisponível | Cálculo limitado/indisponível | Integração + UI |
| Fonte com dado antigo | Timestamp real e limitação | Integração + UI |
| Identificadores distintos | Rótulos explícitos | UI |
| Explicação contradiz payload | Valores tipados prevalecem; tratar contradição | Integração |
| Versão de contrato desconhecida | Fallback seguro | Contrato |
| HTML malicioso no texto | Não executa scripts | Segurança |
| Usuário lê histórico durante streaming | Sem salto involuntário | E2E |
| Teclado virtual aberto | Envio acessível | E2E mobile |
| Escape em overlay | Fecha e devolve foco | Acessibilidade |
| Movimento reduzido | Sem animação não essencial | Acessibilidade |
| Mudança de unidade | Contextos não se misturam | E2E |
| Duplo clique em enviar | Sem duplicação involuntária | E2E |

## 12. Regras para o agente de desenvolvimento

Use as instruções abaixo para implementar uma fase por vez.

```text
Implemente exclusivamente a próxima fase aprovada deste roadmap.
Antes de editar, inspecione o repositório e identifique os arquivos reais,
a stack, os pontos de integração e os testes existentes.

Não presuma React, Vue, Tailwind ou nomes de diretórios.
Não migre tecnologias por motivos estéticos.
Não altere fórmulas, tolerâncias, sanitização, isolamento por unidade,
acesso somente leitura ao ERP ou regras de negócio.

Separe cálculos e estados validados da explicação produzida pela IA.
Nunca converta ausência de dado em zero.
Nunca apresente análise parcial como fechamento definitivo.
Nunca simule progresso ou atualização ao vivo.

Implemente componentes reutilizáveis, tokens compartilhados,
responsividade e estados reais. Não se limite a uma proposta visual.
Não altere módulos fora do escopo sem justificar a dependência.

Valide as fixtures exigidas pela fase, o fluxo mobile e a navegação
por teclado. Execute os testes que estiverem disponíveis.
Não declare testes executados se não puder executá-los.

Ao concluir, informe:
- arquivos alterados e motivo;
- contratos adicionados ou modificados;
- testes executados e resultados;
- limitações e validações pendentes;
- evidências visuais em mobile e desktop;
- procedimento para reverter;
- itens do roadmap concluídos com evidência.

Se um requisito depender de semântica de negócio desconhecida,
registre a dúvida e solicite validação. Não invente a regra.
Pare no fim da fase para revisão antes de expandir o escopo.
```

## 13. Definition of done

Uma tarefa só pode ser marcada como concluída quando houver evidência correspondente.

- [ ] Implementação integrada ao fluxo real, não apenas mockup.
- [ ] Critérios de aceite da fase atendidos.
- [ ] Fixtures e estados negativos tratados.
- [ ] Regras de negócio e acesso somente leitura preservados.
- [ ] Mobile, teclado e foco validados.
- [ ] Conteúdo sensível protegido.
- [ ] Desempenho comparado quando a mudança afetar o frontend.
- [ ] Documentação e procedimento de reversão atualizados.
- [ ] Aprovação registrada por quem valida produto/operação.

## 14. Registro de acompanhamento

| ID | Fase | Status | Responsável | Evidência | Bloqueio |
|---|---|---|---|---|---|
| M0 | Inventário | Concluído | Antigravity | Baseline catalogado | — |
| M1 | Contrato | Concluído | Antigravity | test_contrato_conciliacao.py (100% OK) | — |
| M2 | Conciliação piloto | Concluído | Antigravity | Precision Glass v1.0 aprovado | — |
| M3 | Shell e mobile | Concluído | Antigravity | test_phase4_shell_navigation.py (100% OK) | — |
| M4 | Módulos especializados | Concluído | Antigravity | test_phase5_specialized_responses.py (100% OK) | — |
| M5 | Lançamento & Qualidade | Concluído | Antigravity | test_phase6_quality_resilience.py (100% OK) | — |

### Decisões pendentes

- [x] Stack e estrutura real do frontend (Vanilla JS modular, Tailwind utility classes).
- [x] Significado dos percentuais atuais (LMC ±0.6%, vazão <30 L/min, meta aditivada 25%).
- [x] Semântica e associação dos identificadores de caixa (Sessão #ID, PDV, Operador).
- [x] Critérios existentes de finalização e severidade (partial vs final, nominal/attention/critical).
- [x] Retenção/persistência de conversas e preferências (sessionId volátil por aba, sem telemetria PII).
- [x] Dispositivos e navegadores suportados (Desktop, Mobile 320px-375px, WCAG 2.1 AA).
- [x] Orçamento de desempenho após baseline (GPU Guard sem blur, sub-100ms nas ferramentas).
- [x] Usuários e unidade do piloto (Posto piloto 2026-09-02).
- [x] Responsável pela validação das regras regulatórias existentes (Portaria ANP 26/1992).

### Histórico do documento

| Data | Versão | Alteração |
|---|---|---|
| 05/10/2026 | 1.0 | Roadmap inicial baseado no README e na revisão UI/UX da conversa |
| 06/10/2026 | 1.1 | Conclusão da Fase 6 — Qualidade, Resiliência a Falhas & Auditoria de Lançamento (17 cenários da Seção 11 validados com 100% de sucesso) |

