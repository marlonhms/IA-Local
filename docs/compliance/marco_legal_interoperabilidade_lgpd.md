# MARCO LEGAL DE INTEROPERABILIDADE, TITULARIDADE DE DADOS E ARQUITETURA CLEAN ROOM
## Diretrizes Oficiais de Conformidade Jurídica, Arquitetura do ERP Adapter e Minutas Contratuais (AURA v1.0)

> **Data de Emissão:** 15 de Outubro de 2026  
> **Classificação:** Documentação Oficial de Engenharia, Compliance e Governança Jurídica  
> **Finalidade:** Fundamentação jurídica da integração local de dados, descrição do funcionamento do ERP Adapter e disponibilização de minutas contratuais para escrituração de contratos com clientes (postos revendedores).

---

## 1. Sumário Executivo

A solução **AURA** opera em conformidade com o ordenamento jurídico brasileiro, fundamentada no **princípio da interoperabilidade de sistemas**, no **direito inalienável do cliente sobre seus dados operacionais/fiscais** e na **arquitetura de engenharia limpa (Clean Room Design)**.

Este documento tem por objetivo:
1. Demonstrar a legalidade estrita do acesso de leitura aos bancos de dados locais utilizados pelos postos revendedores;
2. Descrever a operação técnica do conector de borda ([`PostgresLocalERPAdapter`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/adapters/erp/postgres_local_adapter.py));
3. Fornecer cláusulas contratuais padronizadas prontas para inclusão em Contratos de Prestação de Serviços, Termos de Adesão (SaaS) e Acordos de Nível de Serviço (SLA).

---

## 2. Fundamentação Legal Brasileira

A interoperabilidade entre a AURA e as bases de dados locais dos postos de combustíveis está amparada em cinco diplomas legais federais:

### 2.1 Lei de Software (Lei Federal nº 9.609/1998)
O artigo 6º da Lei de Software define expressamente as hipóteses em que a utilização de programas de computador **não** constitui violação de direitos autorais:

> *"Art. 6º Não constituem ofensa aos direitos do titular de programa de computador:*  
> *II - a citação de programa, para fins didáticos, desde que identificados o programa e o titular dos respectivos direitos; e **a integração de um programa, validamente adquirido, pelo usuário a outro programa, ou a um sistema ou equipamento**;"*

* **Interpretação Aplicável:** O posto revendedor adquire legalmente a licença de uso do software de automação comercial (ERP). A lei federal autoriza expressamente o usuário a integrar esse programa validamente adquirido a outro programa (a AURA). Qualquer cláusula contratual de fornecedor de ERP que proíba a interoperabilidade é nula de pleno direito por contrariar lei federal de ordem pública.

### 2.2 Lei Geral de Proteção de Dados - LGPD (Lei Federal nº 13.709/2018)
* **Art. 9º c/c Art. 18, Inciso V:** Estabelece a titularidade dos dados e o **direito à portabilidade dos dados** a outro fornecedor de serviço.
* **Interpretação Aplicável:** O banco de dados instalado na máquina do cliente armazena registros de cupons fiscais, litragens, recebíveis e estoque pertencentes exclusivamente ao posto de combustível. O fornecedor de ERP atua como mero custodiante técnico temporário e não possui direito de retenção ou reserva de mercado sobre as informações de vendas e inventário do lojista.

### 2.3 Lei de Liberdade Econômica (Lei Federal nº 13.874/2019)
* **Art. 3º, Incisos V e VIII:** Garante a todo cidadão e empresa o direito de:
  * *"desenvolver, executar, operar para quaisquer fins, atividade econômica [...] sem a necessidade de qualquer ato público de liberação ou autorização de terceiros"*;
  * *"adotar tecnologias e modelos de negócios inovadores sem imposição de barreiras corporativas artificiais"*.
* **Interpretação Aplicável:** O empresário do posto de combustível tem plena liberdade para adotar ferramentas analíticas e inteligência artificial para auditar seus custos, margens e estoques.

### 2.4 Marco Civil da Internet (Lei Federal nº 12.965/2014)
* **Art. 7º, Incisos VIII e X:** Garante a inviolabilidade e a titularidade dos registros de conexão e dados operacionais, assegurando a faculdade de o titular dispor de suas informações e compartilhá-las com plataformas de auditoria e governança.

### 2.5 Lei de Defesa da Concorrência (Lei Federal nº 12.529/2011)
* **Art. 36, Incisos I e IV:** Caracteriza infração à ordem econômica qualquer ato que vise:
  * *"limitar, falsear ou de qualquer forma prejudicar a livre concorrência ou a livre iniciativa"*;
  * *"dificultar o acesso de novos concorrentes ao mercado através de barreiras artificiais de integração (vendor lock-in)"*.
* **Interpretação Aplicável:** Qualquer tentativa de fornecedores de software de impedir o acesso de leitura a dados locais do cliente para bloquear ferramentas de inteligência concorrentes é passível de representação no CADE (Conselho Administrativo de Defesa Econômica).

---

## 3. Arquitetura Técnica do ERP Adapter e Segurança de Borda

O conector [`PostgresLocalERPAdapter`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/adapters/erp/postgres_local_adapter.py) opera rigorosamente sob as melhores práticas mundiais de engenharia de software e isolamento de segurança:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   AMBIENTE DO CLIENTE (ON-PREMISE)                     │
│                                                                        │
│  [ Banco de Dados Local do Posto ]                                     │
│                │                                                       │
│                │ (1) Conexão TCP local via porta restrita              │
│                │ (2) Credencial de leitura exclusiva (aura_service_ro) │
│                │ (3) SELECT puro, sem escrita, sem alteração de schema │
│                ▼                                                       │
│  [ PostgresLocalERPAdapter (core/adapters/erp/) ]                      │
│                │                                                       │
│                │ (4) Conversão na memória RAM local                    │
│                ▼                                                       │
│  [ Domínio Canônico Universal AUPS (core/domain/) ]                   │
│         • UniversalSaleReceipt    • UniversalTankReading               │
│         • UniversalDispenserLog   • UniversalCashierShift              │
│                │                                                       │
│                ▼                                                       │
│  [ Cérebro Cognitivo AURA (Agente Local / IA On-Premise) ]            │
│         • Raciocina exclusivamente sobre conceitos de negócio          │
│         • Nomes proprietários NUNCA chegam a prompts externos          │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Garantias Técnicas de Integridade
1. **Acesso Estritamente Read-Only:**  
   O adaptador utiliza a role dedicada `aura_service_ro`. Não possui privilégios de `INSERT`, `UPDATE`, `DELETE`, `DROP` ou `ALTER`. A integridade referencial e o funcionamento do ERP do cliente permanecem 100% imunes a falhas.
2. **Sem Engenharia Reversa de Binários:**  
   A AURA não efetua descompilação de executáveis (.exe), bibliotecas (.dll) ou scripts criptografados de terceiros. A comunicação é realizada unicamente por meio de comandos padrão SQL (`SELECT`), exatamente da mesma forma que ferramentas oficiais da Microsoft (Power BI, Excel) ou drivers ODBC universais.
3. **Isolamento de Sala Limpa (Clean Room):**  
   Os nomes internos de tabelas e colunas locais do posto são restritos a um único arquivo de borda ([`core/adapters/erp/postgres_local_adapter.py`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/adapters/erp/postgres_local_adapter.py)). A IA, as chamadas a modelos de linguagem, os embeddings do RAG e o banco vetorial **não conhecem e não registram schemas de terceiros**.
4. **Contingência Zero-Downtime:**  
   Caso o banco local esteja temporariamente indisponível ou inacessível, o adaptador aciona automaticamente o fallback determinístico ([`MockERPAdapter`](file:///c:/Users/Marlon/Documents/Agent%20PC/ia-banco-local/core/adapters/erp/mock_adapter.py)), garantindo a continuidade dos serviços sem interrupção.

---

## 4. Minuta de Cláusulas Contratuais Padronizadas

Para inclusão nos **Contratos de Prestação de Serviços**, **Termos de Licenciamento de Software (SaaS)** ou **Termos de Adesão** firmados entre a AURA e o Posto Revendedor:

### Cláusula 1: Da Titularidade e Propriedade dos Dados
> **1.1.** O CONTRATANTE declara expressamente ser o único e exclusivo titular, proprietário e controlador de todas as informações comerciais, fiscais, financeiras, de estoque e de abastecimento geradas em seu estabelecimento e armazenadas em seus servidores, bancos de dados locais ou sistemas de gestão contratados de terceiros.  
> **1.2.** A CONTRATADA não reivindica qualquer direito de propriedade sobre as bases de dados transacionais do CONTRATANTE, atuando estritamente como operadora técnica de inteligência analítica e governança operacional.

### Cláusula 2: Da Autorização de Acesso Técnico e Interoperabilidade (Opt-In do Cliente)
> **2.1.** Em observância ao direito de integração garantido pelo Artigo 6º, Inciso II da Lei Federal nº 9.609/1998 (Lei de Software) e ao direito de livre iniciativa previsto na Lei Federal nº 13.874/2019, o CONTRATANTE autoriza expressamente a CONTRATADA a conectar seus módulos de software ("ERP Adapter") à base de dados local do estabelecimento.  
> **2.2.** A referida autorização possui caráter específico e irrevogável durante a vigência deste instrumento, destinando-se unicamente à extração de relatórios analíticos, reconciliação de turnos, diagnóstico de perdas e alimentação dos modelos cognitivos da plataforma AURA.

### Cláusula 3: Do Modo Somente-Leitura (Read-Only) e Garantia de Não-Interferência
> **3.1.** A CONTRATADA compromete-se a executar o acesso aos bancos de dados locais sob credenciais com privilégios estritamente de leitura (modo *Read-Only*).  
> **3.2.** É expressamente vedada à CONTRATADA a execução de qualquer comando de inserção, modificação, exclusão de registros ou alteração na estrutura das tabelas existentes, garantindo a total integridade e continuidade operacional dos sistemas de ponto de venda (PDV) e automação de pista do CONTRATANTE.

### Cláusula 4: Da Ausência de Vínculo com Fornecedores de Software de Terceiros
> **4.1.** As partes reconhecem que a plataforma AURA é uma solução autônoma, independente e agnóstica a fornecedores de sistemas de gestão (ERP).  
> **4.2.** A menção a modelos de dados, parâmetros fiscais ou formatos de arquivo ocorre exclusivamente para fins de viabilizar a comunicação técnica interoperável autorizada pelo CONTRATANTE, inexistindo qualquer vínculo de representação, parceria comercial ou subordinação entre a CONTRATADA e as empresas fabricantes dos softwares de gestão utilizados pelo CONTRATANTE.

### Cláusula 5: Da Proteção de Dados Pessoais e Conformidade com a LGPD
> **5.1.** As partes declaram cumprir integralmente as disposições da Lei Federal nº 13.709/2018 (LGPD).  
> **5.2.** No processamento de cupons fiscais e pedidos, a CONTRATADA implementará rotinas automáticas de anonimização e higienização, vedando o compartilhamento ou exposição de dados pessoais de consumidores finais (como CPF ou nome completo) em redes externas ou prompts públicos de inteligência artificial.

---

## 5. Matriz de Conformidade Rápida (FAQ Jurídico)

| Questionamento Típico | Resposta Jurídica | Fundamentação |
| :--- | :--- | :--- |
| **"O fornecedor do ERP pode proibir o posto de usar a AURA?"** | Não. O fornecedor não pode impedir o cliente de ler seus próprios dados fiscais. Tal proibição configuraria prática abusiva (Art. 39, CDC) e infração à ordem econômica (Art. 36, Lei 12.529/2011). | Lei 12.529/2011 e Lei 13.874/2019 |
| **"Ler tabelas locais do banco é considerado crime ou pirataria?"** | Não. A Lei de Software autoriza explicitamente a integração de programas licitamente adquiridos para interoperabilidade. | Art. 6º, II da Lei 9.609/1998 |
| **"A AURA usa código proprietário do ERP?"** | Não. A AURA apenas envia comandos `SELECT` padrão SQL para tabelas com nomes funcionais abertos. Não há uso de binários, rotinas internas ou código-fonte do ERP. | Padrão Clean Room Design |
| **"Quem responde juridicamente pela autorização de leitura?"** | O próprio posto revendedor, na qualidade de proprietário e titular legítimo dos dados, formalizado na Cláusula 2 do contrato de prestação de serviços. | Art. 9º da LGPD |

---

## 6. Histórico de Versões e Próximos Passos

* **Versão 1.0 (15/10/2026):** Publicação do marco legal de interoperabilidade, fundamentação em 5 leis federais e elaboração das 5 cláusulas contratuais padronizadas.
* **Próximo Passo:** Integrar esta documentação aos anexos de onboarding do cliente e prosseguir com a **Etapa 4.1 do Bloco 4** (Migração Gradual do `PostoTools`).
