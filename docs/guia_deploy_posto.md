# ⛽ Guia de Implantação e Onboarding em Novos Postos (Fase 2.5)

> **Documento Operacional de Campo**  
> **Versão:** 1.0.0-PRO  
> **Status:** Ativo / Homologado  
> **Branch de Referência:** `main`  
> Zero travessões em todo o documento.

---

## 📌 1. Visão Geral da Arquitetura de Borda (Edge AI)

A **AURA** foi projetada para operar diretamente na retaguarda física de postos de combustíveis e lojas de conveniência sem exigir substituição ou upgrade no ERP legado do cliente.

### 🛡️ Princípio Inegociável Zero-Disruption
- **ERP Legado Intacto:** O banco transacional do posto (PostgreSQL 9.5 a 16) permanece operando na sua porta original (`5432` ou `5433`), acessado pela AURA em modo **estritamente somente-leitura** através da role técnica [`aura_service_ro`](file:///C:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/scripts/provisionar_usuario_leitura_erp.sql).
- **Banco Vetorial Isolado:** A base de embeddings, RAG híbrido e classificador semântico opera em uma instância dedicada de PostgreSQL 16 com a extensão `pgvector` na **porta 5434**, provisionada automaticamente via container Docker Compose ou serviço nativo.
- **Zero Locks e Zero Writes:** Risco zero de travar bombas, bicos Companytec CBC04 ou emissão de notas fiscais (NFC-e).

---

## 🧭 2. Matriz de Portas de Rede Locais

| Componente | Porta Padrão | Protocolo | Permissão AURA | Função Operacional |
| :--- | :---: | :---: | :---: | :--- |
| **ERP do Posto** | `5432` / `5433` | PostgreSQL | `SELECT` exclusivo | Dados transacionais de abastecimentos, faturamento e caixas. |
| **pgvector AURA** | `5434` | PostgreSQL 16 | Leitura e Escrita | Embeddings de produtos, cache semântico e meta-RAG. |
| **FastAPI Core** | `8000` | HTTP / SSE | Serviço da AURA | API REST e streaming conversacional com interface web. |
| **WhatsApp Gateway** | `5678` / `8080` | HTTP Webhook | Despacho assíncrono | Notificações opcionais via n8n e Evolution API. |

---

## 📋 3. Pré-Requisitos de Instalação na Máquina do Posto

Antes de iniciar a instalação no computador de retaguarda, confirme os seguintes requisitos:
1. **Sistema Operacional:** Windows 10 Pro / Enterprise ou Windows 11 (64 bits).
2. **Hardware Recomendado:** Processador Intel Core i3/i5 ou AMD Ryzen, mínimo 8 GB de memória RAM e 10 GB de espaço livre em disco SSD.
3. **Software Base:**
   - Python 3.10, 3.11 ou 3.12 instalado com a opção *"Add Python to PATH"* habilitada.
   - Docker Desktop ativo com WSL 2 (ou PostgreSQL 16 com pgvector nativo instalado na porta 5433/5434).
   - Acesso com privilégios de Administrador no Windows.

---

## 🚀 4. Passo a Passo de Instalação em 1-Clique

### Passo 4.1: Clonar o Repositório ou Copiar a Pasta do Projeto
Copie a pasta completa do projeto `ia-banco-local` para a máquina de retaguarda do posto (ex: `C:\AURA\ia-banco-local`).

### Passo 4.2: Executar o Script Automatizado de Onboarding
Abra o **PowerShell como Administrador** na pasta do projeto e execute:

```powershell
# Execucao padrao com Docker ativo
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_posto.ps1

# Ou informando a porta do ERP legado manualmente (ex: 5433)
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_posto.ps1 -ERPPort 5433

# Se a maquina ja tiver PostgreSQL 16 nativo (sem Docker):
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_posto.ps1 -SkipDocker -ERPPort 5433
```

O script executa automaticamente as seguintes 6 etapas:
1. **Ambiente Python:** Detecta interpretador e instala dependências de [`requirements.txt`](file:///C:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/requirements.txt).
2. **Segurança:** Cria o arquivo `.env` com chaves HMAC aleatórias de 32 bytes para blindagem de vouchers e API Key.
3. **Banco Vetorial:** Sobe o contêiner [`docker-compose.yml`](file:///C:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/docker-compose.yml) (`pgvector/pgvector:pg16`) na porta isolada `5434`.
4. **Conectividade:** Testa a comunicação TCP com o ERP legado.
5. **Migração:** Executa [`scripts/init_posto_database.py`](file:///C:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/scripts/init_posto_database.py), instalando a extensão `vector` e criando as tabelas com índices HNSW.
6. **Finalização:** Exibe o banner executivo de prontidão operacional.

---

## 🔒 5. Provisionamento da Role Somente-Leitura no ERP

Para garantir que a AURA tenha acesso matemático restrito a `SELECT` no ERP do posto, execute o script SQL de provisionamento:

```powershell
# No PowerShell ou CMD
psql -h localhost -p 5432 -U postgres -d posto -f .\scripts\provisionar_usuario_leitura_erp.sql
```

O script aplica as permissões:
```sql
CREATE ROLE aura_service_ro WITH LOGIN PASSWORD 'sua_senha_segura';
GRANT CONNECT ON DATABASE posto TO aura_service_ro;
GRANT USAGE ON SCHEMA public TO aura_service_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO aura_service_ro;
REVOKE CREATE, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM aura_service_ro;
```

---

## ⚙️ 6. Instalação do Serviço Windows 24/7 (NSSM)

Para que a AURA opere em segundo plano sem necessidade de manter janelas pretas de terminal abertas:

```cmd
# Executar como Administrador
.\scripts\iniciar_servico_nssm.bat
```

- **Nome do Serviço:** `AURA_Core_Engine`
- **Comportamento:** Inicia com o Windows (`SERVICE_AUTO_START`), recupera-se automaticamente de falhas em 5 segundos e grava logs estruturados em `logs/aura_service.log`.
- **Desinstalação:** Se necessário remover, execute `.\scripts\desinstalar_servico_nssm.bat`.

---

## 🩺 7. Checklist de Homologação de Campo

Após o deploy, valide os seguintes pontos no navegador do posto:
- [ ] Acessar `http://localhost:8000/api/v1/aura/health` e receber status `healthy`.
- [ ] Acessar `http://localhost:8000/` e visualizar a interface dark glass da AURA.
- [ ] Clicar no botão **"Automações"** no topo da tela e confirmar que o painel abre com toggles configuráveis.
- [ ] Executar o diagnóstico de tanques: *"Qual a previsão de esgotamento e a autonomia estimada dos tanques?"*.
- [ ] Executar a conciliação de turno: *"Como fechou o último turno? Teve quebra de caixa?"*.
- [ ] Conferir o status do serviço no Gerenciador de Serviços do Windows (`services.msc`).
