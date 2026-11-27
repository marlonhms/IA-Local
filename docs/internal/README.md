# Documentacao Interna de Engenharia e Operacao: AURA

> **Escopo:** Documentos internos de arquitetura, auditorias, runbooks operacionais, migracoes e roadmaps de engenharia.  
> **Regra:** Conteudo sob `docs/internal/` NAO deve ser publicado em portais externos. Tudo que for voltado a parceiros e clientes deve residir em [`../public/`](../public/README.md).

---

## 1. Mapa de Documentacao Interna

| Area | Documento | Escopo |
| :--- | :--- | :--- |
| **Runbook Fases 1 a 4B** | [`runbook-simulacao-memoria-migracoes.md`](runbook-simulacao-memoria-migracoes.md) | Esquema `0003_simulation_memory`, modulos Python/Android, comandos de teste e troubleshooting de servico. |
| **Auditoria Core** | [`../AUDITORIA_CARBON_CORE.md`](../AUDITORIA_CARBON_CORE.md) | Diagnostico e hardening do core Python/FastAPI. |
| **Auditoria Web UI** | [`../AUDITORIA_CARBON_UI.md`](../AUDITORIA_CARBON_UI.md) | Tokens Obsidian, Zero-CLS e SDK Web. |
| **Auditoria Android** | [`../AUDITORIA_CARBON_ANDROID.md`](../AUDITORIA_CARBON_ANDROID.md) | Paridade Android Compose, Keystore/TEE e streaming SSE. |
| **Arquitetura GenUI** | [`../architecture/Arquitetura GenUI para Edge AI.md`](../architecture/Arquitetura%20GenUI%20para%20Edge%20AI.md) | Pipeline de renderizacao generativa na borda. |
| **Protocolo SSE GenUI** | [`../architecture/protocolo_streaming_genui.md`](../architecture/protocolo_streaming_genui.md) | Contrato de eventos SSE (`ui_skeleton`, `ui_delta`, `ui_complete`, `stream_reset`). |
| **Plano Super Inteligencia** | [`../guides/PLANO_IMPLEMENTACAO_SUPER_INTELIGENCIA_UNIVERSAL.md`](../guides/PLANO_IMPLEMENTACAO_SUPER_INTELIGENCIA_UNIVERSAL.md) | Plano diretor das Fases 1 a 4 (Core, Profiler, Backtest e UI). |
| **Guias Operacionais** | [`../guides/guia_deploy_posto.md`](../guides/guia_deploy_posto.md), [`../guides/guia_ativacao_cerebro_central_vps_multitenant.md`](../guides/guia_ativacao_cerebro_central_vps_multitenant.md), [`../guides/guia_ponte_desenvolvimento_remoto_tailscale.md`](../guides/guia_ponte_desenvolvimento_remoto_tailscale.md) | Deploy local, VPS multi-tenant e tunel Tailscale. |

---

## 2. Convencao para Novos Documentos (Portal Publico vs. Interno)

1. **Fronteira `docs/public/` vs. `docs/internal/`:**
   - Se o documento explica **como o produto funciona**, **como integrar via API/SDK** ou **garantias LGPD/seguranca** para clientes e parceiros, crie ou atualize dentro de `docs/public/`.
   - Se o documento trata de **runbooks internos, detalhes de banco local, servico Windows, Tailscale, auditorias de codigo ou roadmaps**, coloque em `docs/internal/` (ou nos diretorios internos ja indexados).
2. **Estilo Diataxis em `docs/public/`:**
   - `01-conceitos/`: explicacoes conceituais (o que e e por que existe).
   - `02-funcionalidades/`: guias de uso e fluxo funcional.
   - `03-integracao-parceiros/`: passo a passo pratico para integradores.
   - `04-referencia-api/`: contratos HTTP/JSON exatos.
   - `05-seguranca-lgpd/`: controles de seguranca e conformidade.
3. **Checklist pre-publicacao para `docs/public/`:**
   - Zero travessoes Unicode (`\u2014` ou `\u2013`).
   - Zero segredos, chaves, IPs internos, nomes de bancos locais ou caminhos locais de maquina.
   - Todos os links relativos validados.
