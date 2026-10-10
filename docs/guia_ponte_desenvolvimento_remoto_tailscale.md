# 🌉 Guia Completo: Ponte Tailscale para Desenvolvimento Remoto (Notebook ↔ PC de Casa)

> **Projeto**: Ai.la - IA Especialista do Posto de Combustíveis & PDV  
> **Repositório GitHub**: [https://github.com/marlonhms/IA-Local](https://github.com/marlonhms/IA-Local)  
> **Topologia**: Notebook (Servidor de Banco de Dados) ↔ PC de Casa (Estação de Desenvolvimento)  
> **Data de Atualização**: Março/2026  

---

## 1. Visão Geral e Arquitetura da Solução

O objetivo desta integração é permitir que você continue desenvolvendo, testando e expandindo o **Ai.la** a partir do seu **Computador de Casa**, consumindo diretamente a base transacional do ERP e o banco vetorial semântico que já estão hospedados e populados no **Notebook**, utilizando a malha privada do **Tailscale (VPN Mesh WireGuard)**.

Essa evolução representa o primeiro passo concreto no desacoplamento do projeto da máquina local única (*full local*), estabelecendo uma arquitetura cliente/servidor aderente aos cenários reais de redes de postos e filiais remotas.

```
┌─────────────────────────────────────────────────────────────┐
│                    PC DE CASA (Dev Station)                 │
│                 IP Tailscale: 100.89.108.95                 │
│                 Hostname: desktop-d0hv5co                   │
│                                                             │
│   • VS Code / Cursor / CLI                                  │
│   • Código Ai.la (.env apontando para o Notebook)           │
│   • Executa main.py / scripts consumindo APIs remotas       │
└──────────────────────────────┬──────────────────────────────┘
                               │
            🔒 Rede Mesh Tailscale (100.64.0.0/10)
            🚀 Suporte a MagicDNS (ex: marlonh-supwp)
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    NOTEBOOK (Database Host)                 │
│                 IP Tailscale: 100.77.164.17                 │
│                 Hostname Tailscale: marlonh-supwp           │
│                                                             │
│   • PostgreSQL 16 ERP (Windows Service)  ───► Porta 5433    │
│   • pgvector Nativo (Base posto_ai)      ───► Porta 5433    │
│   • AURA Web Cockpit & API               ───► Porta 8000    │
│   • Firewall do Windows restrito a Tailscale e 100.64.0.0/10│
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Ajustes Realizados no Notebook (Servidor)

Todas as configurações de escuta e segurança foram implementadas e validadas no Notebook:

### 2.1. Escuta do PostgreSQL 16 ERP (`postgresql.conf`)
- **Arquivo**: `C:\Program Files\PostgreSQL\16\data\postgresql.conf`
- **Configuração**:
  ```ini
  listen_addresses = '*'
  port = 5433
  ```
- **Status**: O PostgreSQL está configurado para escutar conexões de todas as interfaces de rede (`0.0.0.0` e `::`).

### 2.2. Autorização de Rede no `pg_hba.conf`
- **Arquivo**: `C:\Program Files\PostgreSQL\16\data\pg_hba.conf`
- **Regra Adicionada**:
  ```ini
  # Conexoes remotas seguras via Tailscale VPN (Rede Mesh de Casa / Filiais):
  host    all             all             100.64.0.0/10           md5
  ```
- **Explicação**: A faixa `100.64.0.0/10` é o espaço CGNAT reservado pelo Tailscale para toda a malha VPN. Qualquer dispositivo autenticado na sua conta Tailscale tem permissão para autenticar via senha MD5/SCRAM.

### 2.3. Validade da Senha do Usuário `suporte`
- O usuário `suporte` no banco ERP possuía expiração configurada para o final do dia anterior (`2026-10-02 23:59:59`).
- O papel foi atualizado com validade permanente para o ambiente de desenvolvimento:
  ```sql
  ALTER ROLE suporte WITH PASSWORD '899007' VALID UNTIL 'infinity';
  ALTER ROLE postgres WITH PASSWORD '123456' VALID UNTIL 'infinity';
  ```

### 2.4. Exposição do Docker `pgvector-posto`
- **Container**: `pgvector-posto` (imagem `pgvector/pgvector:pg16`).
- **Mapeamento**: `0.0.0.0:5434->5432/tcp`.
- **Status**: O container escuta em modo dual-stack em todas as interfaces, estando 100% acessível pelo IP Tailscale `100.77.164.17:5434` ou pelo MagicDNS `marlonh-supwp:5434`.

### 2.5. Liberação do Firewall do Windows no Notebook
Para garantir que o Firewall do Windows não descarte pacotes vindos do PC de casa, criamos scripts automatizados de liberação no repositório:
- **`liberar_firewall_tailscale.bat`** (no diretório raiz do projeto - com auto-elevação UAC)
- **`scripts\configurar_ponte_tailscale.ps1`**

#### O que o script faz:
1. Detecta automaticamente o IP e o adaptador de rede Tailscale (`Tailscale` no Windows, equivalente a `tailscale0` no Linux).
2. Cria ou atualiza regras no Windows Defender Firewall restritas à interface e à rede Tailscale (`100.64.0.0/10`):
   - `AiLa-PostgreSQL-ERP-5433` (TCP 5433)
   - `AiLa-Docker-pgvector-5434` (TCP 5434)
   - `AiLa-PostgreSQL-Dev-5435` (TCP 5435)
3. Garante que o serviço Windows `postgresql-x64-16` e o container Docker `pgvector-posto` estejam rodando.

> 💡 **Como executar no Notebook**: Basta dar um duplo clique em `liberar_firewall_tailscale.bat`. O script solicitará elevação de Administrador automaticamente se necessário.

---

## 3. Comparativo Estratégico de Fluxos de Trabalho

Apresentamos as duas melhores formas de trabalhar de casa:

| Critério | Opção 1: Git Clone Local no PC de Casa | Opção 2: VS Code Remote Tunnels / SSH |
| :--- | :--- | :--- |
| **Onde o código roda** | No Python do PC de Casa | No Python do Notebook |
| **Onde os arquivos ficam** | No SSD do PC de Casa (sincronizados via Git) | No SSD do Notebook |
| **Configuração no PC Casa** | Necessário Python 3.12 + `pip install` | Nenhuma (só o VS Code instalado) |
| **Latência do Editor** | **Nativa / Instantânea** (zero lag de digitação) | Depende da estabilidade da rede |
| **Resiliência a oscilações** | **Alta**: continua editando mesmo se a net cair | Média: desconecta o editor se a net oscilar |
| **Mentalidade de Produção** | **Excelente**: já desacopla cliente de servidor | Mantém tudo rodando acoplado no note |
| **Recomendação** | ⭐ **Recomendada para evolução sólida do Ai.la** | ⚡ **Excelente para sessões rápidas/sem setup** |

---

## 4. Passo a Passo: Opção 1 (Git Clone Local no PC de Casa - Recomendada)

Esta abordagem desacopla a aplicação do banco de dados, permitindo que seu PC de casa seja uma estação de desenvolvimento ágil e veloz.

### Passo 1: Obter o IP ou Nome Tailscale do Notebook
No Notebook, abra o PowerShell ou terminal e execute:
```powershell
tailscale ip -4
# Exemplo retornado: 100.77.164.17
```
> 💡 **Dica MagicDNS**: Você também pode utilizar o hostname Tailscale do notebook diretamente: `marlonh-supwp`.

### Passo 2: Clonar o Repositório no PC de Casa
No Computador de Casa, abra o PowerShell e execute:
```powershell
git clone https://github.com/marlonhms/IA-Local.git "C:\Users\Marlon\Documents\IA-Local"
cd "C:\Users\Marlon\Documents\IA-Local"
```

### Passo 3: Criar o Ambiente Virtual e Instalar Dependências
```powershell
# Se o PowerShell bloquear a ativação do venv, libere para o usuário atual:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Passo 4: Configurar o `.env` no PC de Casa
Copie o `.env.example` para `.env`:
```powershell
Copy-Item .env.example .env
```
Edite o arquivo `.env` para apontar os hosts para o IP do Notebook (`100.77.164.17` ou `marlonh-supwp`):
```ini
# Google Gemini API
GEMINI_API_KEY=sua_chave_gemini_aqui

# Banco ERP Transacional (Apontando para o Notebook via Tailscale)
ERP_DB_HOST=100.77.164.17
ERP_DB_PORT=5433
ERP_DB_NAME=posto
ERP_DB_USER=suporte
ERP_DB_PASSWORD=899007
ERP_DB_CONNECT_TIMEOUT=5

# Banco Vetorial Semântico (PostgreSQL 16 Nativo do Notebook via Tailscale)
VECTOR_DB_HOST=100.77.164.17
VECTOR_DB_PORT=5433
VECTOR_DB_NAME=posto_ai
VECTOR_DB_USER=postgres
VECTOR_DB_PASSWORD=123456
VECTOR_DB_CONNECT_TIMEOUT=5

# Modelos do Gemini
DEFAULT_EMBEDDING_MODEL=models/gemini-embedding-001
DEFAULT_LLM_MODEL=models/gemini-3.1-flash-lite
```

*(Nota: Você pode substituir `100.77.164.17` por `marlonh-supwp` caso o MagicDNS esteja ativo).*

### Passo 5: Testar a Conexão com o Diagnóstico Automático
Execute o script de teste de conectividade no PC de Casa. Você pode testar sem argumentos (usando o `.env`) ou passando o host diretamente pela linha de comando:
```powershell
# Opção A: Usando valores do .env
python scripts/test_ponte_tailscale.py

# Opção B: Testando um IP ou hostname diretamente via CLI
python scripts/test_ponte_tailscale.py 100.77.164.17
# ou:
python scripts/test_ponte_tailscale.py marlonh-supwp
```
**Resultado Esperado**:
```
============================================================================
 🔍 DIAGNÓSTICO DA PONTE TAILSCALE - AI.LA (BANCO LOCAL & REMOTO)
============================================================================
[1/2] Testando Conexão com Banco ERP (100.77.164.17:5433)...
  [OK] Conectado com sucesso em 48.0ms [SLA EXCELENTE - Ideal para desenvolvimento interativo]
   - Database: posto | User: suporte | Porta Server: 5433
   - Tabela 'produtos': 250 registros encontrados no ERP

[2/2] Testando Conexão com Banco Vetorial (100.77.164.17:5433)...
  [OK] Conectado com sucesso em 40.5ms [SLA EXCELENTE - Ideal para desenvolvimento interativo]
   - Database: posto_ai | User: postgres | Porta Server: 5433
   - Extensão pgvector: v0.8.6
   - Tabela 'produtos_vetores': 250 embeddings indexados

============================================================================
🎉 SUCESSO TOTAL: A ponte de rede está 100% operacional!
   Você pode executar e codar o projeto normalmente nesta máquina.
============================================================================
```

### Passo 6: Acessar o Painel Web da AURA no PC de Casa
Se você iniciar o painel no notebook via `iniciar_painel.bat`, você pode abrir diretamente o navegador no PC de Casa e acessar:
- **Painel Executivo da AURA**: `http://100.77.164.17:8000` (ou `http://marlonh-supwp:8000`)
- **Documentação Swagger/OpenAPI**: `http://100.77.164.17:8000/docs`

### Passo 7: Executar a AURA / Ai.la no PC de Casa
```powershell
python main.py
# ou para abrir o servidor web da AURA localmente:
python server.py
```
O agente iniciará normalmente, autenticando no ERP do Notebook e carregando a telemetria SRE e filial remota.

---

## 5. Passo a Passo: Opção 2 (VS Code Remote Tunnels / SSH)

Se você não quiser instalar Python, bibliotecas ou clonar nada no PC de casa, pode programar no PC de casa utilizando os recursos de computação do Notebook:

### Método A: VS Code Remote Tunnels (Sem necessidade de configurar SSH)
1. **No Notebook**:
   - Abra o terminal do VS Code na pasta do projeto e execute:
     ```powershell
     code tunnel service install
     ```
     *(Isso instala o túnel do VS Code como serviço em background no Windows, mantendo o acesso disponível mesmo se a janela do VS Code for fechada).*
   - Caso prefira a interface gráfica: pressione `Ctrl+Shift+P` no VS Code, digite `Remote Tunnels: Turn on Remote Tunnel Access...` e faça login com sua conta GitHub/Microsoft.
2. **No PC de Casa**:
   - Abra o VS Code.
   - Instale a extensão **Remote - Tunnels** da Microsoft.
   - Faça login com a mesma conta GitHub/Microsoft.
   - Conecte-se ao túnel do notebook.
   - Pronto: você edita o código e roda os terminais diretamente no notebook com zero latência de banco de dados.

### Método B: VS Code Remote SSH via Tailscale
1. O Tailscale possui o recurso nativo **Tailscale SSH**.
2. No notebook, ative o Tailscale SSH:
   ```powershell
   tailscale set --ssh
   ```
3. No PC de Casa, no VS Code, instale a extensão **Remote - SSH**.
4. Conecte via SSH no endereço `marlon@100.77.164.17` (ou `marlon@marlonh-supwp`).

---

## 6. Checklist de Solução de Problemas (Troubleshooting)

Se algum teste falhar, siga este checklist rápido:

### 1. `socket.timeout` ou `Tempo Limite Esgotado`
- **Causa**: Firewall do Windows no Notebook bloqueando as portas.
- **Solução**: No Notebook, execute o arquivo `liberar_firewall_tailscale.bat`. O script possui auto-elevação UAC e configurará as regras associadas ao adaptador Tailscale.

### 2. `Connection Refused` (Conexão Recusada)
- **Causa**: O serviço do PostgreSQL ou o Docker não está rodando no Notebook.
- **Solução**: No Notebook, abra o Docker Desktop (para a porta 5434) e inicie o serviço do Windows `postgresql-x64-16` (ou rode `iniciar.bat` / `liberar_firewall_tailscale.bat`).

### 3. `FATAL: senha expirada para o usuário suporte`
- **Causa**: O ERP do posto aplicou data de validade na credencial.
- **Solução**: Execute no Notebook:
  ```powershell
  python -c "import psycopg2; conn = psycopg2.connect(host='localhost', port=5433, dbname='posto', user='postgres'); cur = conn.cursor(); cur.execute('''ALTER ROLE suporte WITH PASSWORD '899007' VALID UNTIL 'infinity';'''); conn.commit(); conn.close(); print('Papel atualizado!')"
  ```

### 4. `ExecutionPolicy` no PowerShell do PC de Casa
- **Causa**: Política de execução restritiva do Windows impede ativação do `venv`.
- **Solução**: Execute no PowerShell do PC de Casa:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### 5. Mudança de IP do Tailscale
- **Observação**: Os IPs do Tailscale (`100.x.y.z`) são **estáticos** para cada nó da sua conta Tailscale. Além disso, o hostname MagicDNS (`marlonh-supwp`) resolve automaticamente para o IP correto independente de trocas de rede.

---

## 7. Próximos Passos na Evolução da Arquitetura

Essa ponte Tailscale não resolve apenas a sua necessidade imediata de programar de casa: ela estabelece as bases para o **desprendimento de infraestrutura do Ai.la**:

1. **Prontidão Multi-Filial**: O sistema agora já suporta operar com host de banco remoto via variável de ambiente, permitindo que a IA rode em um servidor central (Cloud/VPS) conectando aos bancos dos postos via Tailscale Subnet Router.
2. **Separação de Camadas**: A separação física entre quem executa a IA (LLM/Agente) e quem armazena os dados transacionais (ERP legado) reduz drasticamente os riscos de corrupção de dados e facilita manutenções e backups.
