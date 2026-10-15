# TERMO FORMAL DE INTEROPERABILIDADE, TITULARIDADE DE DADOS E OPT-IN DO LOJISTA
## Instrumento Juridico de Autorizacao, Seguranca e Certificacao Tecnica Clean Room (AURA v1.0)

> **Data da Versao:** 15 de Outubro de 2026  
> **Versao Oficial:** 1.0  
> **Classificacao:** Instrumento Juridico Vinculante e Certificacao Tecnica de Conformidade  
> **Finalidade:** Declaracao de titularidade de dados pelo estabelecimento revendedor, autorizacao expressa de interoperabilidade de leitura local, certificacao de nao-interferencia (Clean Room) e enquadramento regulatorio completo (LGPD, Lei de Software, Marco Civil da Internet e Codigo de Defesa do Consumidor).

---

## 1. Preambulo e Qualificacao das Partes

Pelo presente instrumento juridico e termo de adesao tecnica:

1. **ESTABELECIMENTO CONTROLADOR (LOJISTA / POSTO REVENDEDOR):**
   Pessoa juridica de direito privado, devidamente qualificada no Quadro de Formalizacao de Opt-In anexo a este instrumento, na qualidade de proprietaria, controladora e legitima titular de todo o acervo de dados gerados por sua atividade comercial, incluindo registros fiscais, movimentacoes de combustiveis, transacoes de ponto de venda (PDV), leituras de encerrantes, medicoes de tanques e conciliacoes de caixas.

2. **PLATAFORMA AURA (OPERADORA TECNICA DE INTELIGENCIA):**
   Solucao de inteligencia artificial, analise preditiva e governanca de dados operacionais para postos de combustiveis e lojas de conveniencia, operando em arquitetura distribuida de borda (Edge AI / On-Premise) com processamento desacoplado.

As partes celebram o presente **Termo de Interoperabilidade, Titularidade de Dados e Opt-In**, sujeitando-se integralmente as clausulas e condicoes a seguir expostas.

---

## 2. Fundamentacao Legal Brasileira Completa

A integracao, leitura e processamento analitico de dados operacionais pela plataforma AURA estao estritamente fundamentados na legislacao federal brasileira vigente:

### 2.1 Lei Geral de Protecao de Dados Pessoais - LGPD (Lei Federal 13.709/2018)
* **Art. 2 (Fundamentos da Protecao de Dados):** O tratamento de dados no ecossistema AURA observa como principios fundantes a livre iniciativa, a livre concorrencia, o desenvolvimento economico e tecnologico e a defesa do consumidor.
* **Art. 7, IX (Legitimo Interesse do Controlador):** O acesso aos dados transacionais para fins de auditoria de quebras de caixa, prevencao a fraudes de pista, conciliacao fiscal e gestao de estoques e realizado com base no legitimo interesse do controlador (o lojista), com o objetivo de apoiar e promover as atividades legitimas do estabelecimento.
* **Art. 18, V (Direito de Acesso e Portabilidade dos Dados pelo Titular):** Garante ao titular e controlador o direito inalienavel de portabilidade de seus registros de dados a outro prestador de servicos, assegurando que os dados gerados pela atividade do posto pertencem a ele e nao podem ser bloqueados pelo fornecedor de software ou custodiante tecnologico.

### 2.2 Lei de Software (Lei Federal 9.609/1998)
* **Art. 6, I e II (Exclusao de Infracao a Direitos Autorais):**
  A legislacao brasileira de protecao a propriedade intelectual de software e categorica ao estabelecer:
  > *"Art. 6. Nao constituem ofensa aos direitos do titular de programa de computador:*  
  > *I - a reproducao, em um so exemplar, de copia legitimamente adquirida, desde que se destine a copia de salvaguarda ou armazenamento de seguranca;*  
  > *II - a citacao de programa, para fins didaticos, desde que identificados o programa e o titular dos respectivos direitos; e a integracao de um programa, validamente adquirido, pelo usuario a outro programa, ou a um sistema ou equipamento."*
* **Aplicacao Direta:** O posto revendedor adquiriu validamente a licenca de uso de seu sistema de gestao (ERP). O Artigo 6, Inciso II confere ao usuario o direito irrevogavel de integrar esse software a outro sistema (a AURA). Nenhuma disposicao contratual de terceiro pode sobrepor-se a norma federal de ordem publica.

### 2.3 Marco Civil da Internet (Lei Federal 12.965/2014)
* **Art. 3 e Art. 4 (Principios e Objetivos de Interoperabilidade e Livre Concorrencia):**
  * O Marco Civil estabelece expressamente a promocao da interoperabilidade entre plataformas atraves de padroes abertos e a preservacao do carater colaborativo da rede como principio norteador.
  * O Artigo 4, Incisos II e III, determina expressamente como objetivo o estimulo a livre concorrencia, a inovacao tecnologica e a adocao de padroes e tecnologias abertas de comunicacao entre solucoes de software.

### 2.4 Codigo de Defesa do Consumidor (Lei Federal 8.078/1990) e Codigo Civil (Lei Federal 10.406/2002)
* **Vedacao Expressa ao "Vendor Lock-in" Abusivo:**
  * O Artigo 39 do Codigo de Defesa do Consumidor veda expressamente condutas de fornecedores que criem amarras artificiais, restrinjam a liberdade de contratacao ou imponham obstaculos tecnicos unilaterais para aprisionar clientes ("Vendor Lock-in").
  * O Artigo 36 da Lei Federal 12.529/2011 (Defesa da Concorrencia) enquadra como infracao a ordem economica qualquer ato que crie barreiras artificiais de entrada ou impeca o acesso de concorrentes a servicos complementares de tecnologia.
  * Os Artigos 421 e 422 do Codigo Civil estabelecem que a liberdade contratual deve ser exercida nos limites da funcao social do contrato e da boa-fe objetiva, assegurando que o titular dos dados operacionais e o estabelecimento comercial.
* **Propriedade Inalienavel dos Dados do Estabelecimento:**
  * Todos os cupons fiscais, arquivos XML de NF-e e NFC-e, registros do Livro de Movimentacao de Combustiveis (LMC da ANP), valores de caixa e cadastros pertencem exclusivamente ao estabelecimento comercial revendedor e nao a empresa desenvolvedora do ERP.

---

## 3. Certificacao Tecnica de Nao-Interferencia (Clean Room & Read-Only)

A plataforma AURA foi integralmente concebida e implementada sob estrita metodologia de Engenharia de Sala Limpa (Clean Room Software Engineering), assegurando as seguintes garantias tecnicas:

### 3.1 Operacao Estritamente Somente-Leitura (Read-Only)
1. **Role de Servico com Privilegios Exclusivos de Leitura:**
   * A conexao ao banco de dados relacional local do estabelecimento e realizada sob a credencial tecnica restrita `aura_service_ro`.
   * A role possui permissao exclusiva de `SELECT` para tabelas de negocio necessarias a auditoria.
   * Sao expressamente revogados todos os comandos de mutacao de dados (`INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`) e de modificacao de estrutura (`DROP`, `ALTER`, `CREATE`).
2. **Transacoes com Isolamento Read-Only em Nivel de Driver:**
   * Todas as sessoes abertas pelo adaptador de banco de dados definem explicitamente o parametro transacional `READ ONLY` no protocolo de comunicacao (`default_transaction_read_only = on`).
   * E tecnicamente impossivel a AURA alterar, corromper, bloquear ou substituir qualquer registro no banco de dados do posto.
3. **Inexistencia de Alteracao em Executaveis, DLLs ou Schemas:**
   * A AURA nao realiza descompilacao ou engenharia reversa de bibliotecas de enlace dinamico (arquivos `.dll`), binarios executaveis (`.exe`) ou scripts protegidos do ERP.
   * A comunicacao e estritamente externa, passiva e declarativa via consultas SQL padrao emitidas atraves do conector local ([`PostgresLocalERPAdapter`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/adapters/erp/postgres_local_adapter.py)).

### 3.2 Isolamento Local Atraves do AUPS (AURA Universal Posto Schema)
1. **Contrato Canonico Universal:**
   * A camada de borda traduz imediatamente os dados brutos recebidos da conexao local para as entidades de dominio canonicamente abertas do AUPS ([`UniversalSaleReceipt`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/domain/sales.py), [`UniversalTankReading`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/domain/tanks.py), [`UniversalDispenserLog`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/domain/pumps.py) e [`UniversalCashierShift`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/domain/cashier.py)).
   * Todo o processamento analitico, motor cognitivo, roteamento semantico e geracao de linguagem natural operam exclusivamente sobre o AUPS.
2. **Portas Abstratas de ERP:**
   * A integracao com o banco de dados segue a interface abstrata aberta [`BaseERPAdapter`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/adapters/erp/base.py), desacoplando totalmente a logica de negocio do posto em relacao a marcas especificas de ERP (Petros, Linx, WebPosto, XPert, LBC).
3. **Nenhum Dado Proprietario Exposto a IA ou Prompts Externos:**
   * Nenhum nome proprietario de tabela ou coluna interna do ERP transita para provedores de LLM externos, vetores de RAG ou telemetria em nuvem.
   * Todos os prompts e meta-estruturas utilizam terminologia conceitual de negocios e modelos do AUPS, cumprindo 100% dos requisitos de isolamento Clean Room.

---

## 4. Cláusulas Vinculantes de Opt-In do Lojista

### Clausula Primeira: Da Declaracao de Titularidade
O estabelecimento comercial declara sob as penas da lei que e o unico titular, possuidor e controlador dos dados fiscais, operacionais e financeiros gerados no exercicio de sua atividade comercial, tendo plena autoridade legal para autorizar a integracao e o tratamento analitico desses dados.

### Clausula Segunda: Da Autorizacao Expressa de Leitura Local (Opt-In)
O estabelecimento comercial autoriza expressamente a AURA a executar conexoes locais em modo estritamente somente-leitura em seus servidores locais para as seguintes finalidades especificas:
* Reconciliacao e auditoria de fechamento de turnos de caixas;
* Previsao preditiva de esgotamento de combustiveis em tanques fisicos;
* Auditoria do Livro de Movimentacao de Combustiveis (LMC padrao ANP);
* Detecao de anomalias de frentistas e encerrantes de bombas de abastecimento;
* Analise cruzada de vendas da loja de conveniencia (cesta de compras e market basket);
* Identificacao e diagnostico de causas-raiz (RCA forense) para prevencao de perdas e quebras financeiras.

### Clausula Terceira: Da Revogabilidade e Seguranca
1. O presente consentimento de interoperabilidade podera ser revogado a qualquer momento pelo estabelecimento comercial mediante atualizacao de status no sistema de conformidade da AURA.
2. A AURA compromete-se a manter rotinas automatizadas de sanitizacao e mascaramento de dados sensiveis (como CPF de consumidores finais) conforme preve o Artigo 18 da LGPD.

---

## 5. Quadro de Formalizacao de Opt-In Tecnico

Este quadro formaliza os dados cadastrais e o aceite assinado pelo responsavel legal da unidade:

| Campo de Conformidade | Identificador Tecnico | Valor Formalizado |
| :--- | :--- | :--- |
| **CNPJ do Estabelecimento** | `loja_cnpj` | Preenchimento no Onboarding / Configuracao Local |
| **Razao Social** | `razao_social` | Razao Social do Posto Revendedor |
| **Data e Hora do Aceite** | `aceite_interoperabilidade_em` | Timestamp ISO-8601 do Registro |
| **Versao do Termo** | `versao_termo` | 1.0 |
| **Status do Consentimento** | `status` | active |
| **Responsavel Legal / Assinante** | `assinado_por` | Nome do Titular ou Administrador Legal |
| **Hash Criptografico SHA-256** | `hash_termo` | Assinatura SHA-256 Calculada do Conteudo do Termo |

---

## 6. Integridade e Autenticidade Criptografica

A integridade deste documento e verificavel pelo modulo tecnico [`ComplianceManager`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/compliance_manager.py) atraves do calculo automatizado do digest criptografico SHA-256 de seu conteudo, garantindo que qualquer alteracao posterior no texto seja imediatamente identificada como violacao de versao.
