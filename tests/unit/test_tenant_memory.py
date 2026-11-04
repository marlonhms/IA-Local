"""
Suite de Testes Unitarios da Memoria Auditavel da Camada Tenant (Fase 7).
Valida ciclo de vida (pendente -> ativo -> rejeitado -> obsoleto), isolamento estrito
entre postos, precedencia cognitiva e ausencia total de travessoes Unicode.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from core.tenant_memory import TenantMemoryManager, TenantMemoryFact


@pytest.fixture
def memory_manager() -> TenantMemoryManager:
    """Instancia isolada em memoria para cada teste."""
    return TenantMemoryManager(db_path=":memory:")


def test_fact_lifecycle_creation_pending(memory_manager: TenantMemoryManager):
    """Garante que novo fato registrado nasce com status 'pendente'."""
    fact = memory_manager.learn_fact(
        tenant_id="posto_central",
        filial_id=1,
        categoria="apelido_produto",
        chave="coca lata",
        conteudo="Chamar 'coca lata' de REFRIGERANTE COCA COLA LATA 350ML",
        origem="chat",
    )
    assert fact.id.startswith("mem_")
    assert fact.tenant_id == "posto_central"
    assert fact.filial_id == 1
    assert fact.status == "pendente"
    assert fact.aprovado_por is None

    # Nao deve aparecer em memorias ativas
    active = memory_manager.get_active_memories(tenant_id="posto_central", filial_id=1)
    assert len(active) == 0


def test_fact_approval_promotion_to_active(memory_manager: TenantMemoryManager):
    """Garante promocao de fato para status 'ativo' apos aprovacao do gestor."""
    fact = memory_manager.learn_fact(
        tenant_id="posto_central",
        filial_id=1,
        categoria="rotina_operacional",
        chave="fechamento_turno",
        conteudo="Fechamento do turno 3 sempre ocorre as 22h",
        status="pendente",
    )
    approved = memory_manager.approve_fact(fact.id, approved_by="gestor_carlos")
    assert approved is not None
    assert approved.status == "ativo"
    assert approved.aprovado_por == "gestor_carlos"
    assert approved.aprovado_em is not None

    active = memory_manager.get_active_memories(tenant_id="posto_central", filial_id=1)
    assert len(active) == 1
    assert active[0].id == fact.id
    assert active[0].chave == "fechamento_turno"


def test_fact_rejection(memory_manager: TenantMemoryManager):
    """Garante marcacao de rejeicao com motivo gravado."""
    fact = memory_manager.learn_fact(
        tenant_id="posto_central",
        filial_id=1,
        categoria="regra_posto",
        chave="desconto_extra",
        conteudo="Dar 50% de desconto para amigos",
        status="pendente",
    )
    rejected = memory_manager.reject_fact(fact.id, reason="Regra nao permitida pela diretoria")
    assert rejected is not None
    assert rejected.status == "rejeitado"
    assert rejected.metadata.get("motivo_rejeicao") == "Regra nao permitida pela diretoria"

    active = memory_manager.get_active_memories(tenant_id="posto_central", filial_id=1)
    assert len(active) == 0


def test_fact_deletion_obsolete(memory_manager: TenantMemoryManager):
    """Garante que exclusao inativa marcando como obsoleto."""
    fact = memory_manager.learn_fact(
        tenant_id="posto_central",
        filial_id=1,
        categoria="regra_posto",
        chave="regra_antiga",
        conteudo="Regra temporaria",
        status="ativo",
    )
    assert memory_manager.delete_fact(fact.id) is True

    # Nao aparece nas ativas nem na listagem padrao
    active = memory_manager.get_active_memories(tenant_id="posto_central")
    assert len(active) == 0
    all_facts = memory_manager.list_facts(tenant_id="posto_central")
    assert len(all_facts) == 0


def test_strict_cross_tenant_isolation(memory_manager: TenantMemoryManager):
    """Garante isolamento matematico entre tenant_posto_a e tenant_posto_b."""
    # Fato ativo no Posto A
    memory_manager.learn_fact(
        tenant_id="posto_a",
        filial_id=1,
        categoria="regra_posto",
        chave="frentista_cheque",
        conteudo="Posto A nao aceita cheque",
        status="ativo",
    )

    # Fato ativo no Posto B
    memory_manager.learn_fact(
        tenant_id="posto_b",
        filial_id=1,
        categoria="regra_posto",
        chave="frentista_cheque",
        conteudo="Posto B aceita cheque sob consulta",
        status="ativo",
    )

    # Consulta do Posto A nunca pode ver dados do Posto B
    mem_a = memory_manager.get_active_memories(tenant_id="posto_a", filial_id=1)
    assert len(mem_a) == 1
    assert "Posto A nao aceita cheque" in mem_a[0].conteudo
    assert "Posto B" not in mem_a[0].conteudo

    # Consulta do Posto B nunca pode ver dados do Posto A
    mem_b = memory_manager.get_active_memories(tenant_id="posto_b", filial_id=1)
    assert len(mem_b) == 1
    assert "Posto B aceita cheque" in mem_b[0].conteudo
    assert "Posto A" not in mem_b[0].conteudo

    # Tentativa de aprovacao cross-tenant deve falhar
    assert memory_manager.approve_fact(mem_a[0].id, tenant_id="posto_b") is None


def test_format_memories_for_prompt(memory_manager: TenantMemoryManager):
    """Valida geracao do bloco cognitivo para o prompt do modelo com precedencia."""
    memory_manager.learn_fact(
        tenant_id="posto_demo",
        filial_id=1,
        categoria="apelido_produto",
        chave="coca zero",
        conteudo="COCA ZERO refere-se a REFRIGERANTE COCA COLA ZERO 600ML",
        status="ativo",
    )
    memory_manager.learn_fact(
        tenant_id="posto_demo",
        filial_id=1,
        categoria="regra_posto",
        chave="sangria",
        conteudo="Sangria obrigatoria quando caixa atingir R$ 800,00",
        status="ativo",
    )

    prompt_block = memory_manager.format_memories_for_prompt(tenant_id="posto_demo", filial_id=1)
    assert "[MEMORIA DO POSTO (PREFERENCIAS E REGRAS ATIVAS DO TENANT)]:" in prompt_block
    assert "COCA ZERO" in prompt_block
    assert "Sangria obrigatoria" in prompt_block


def test_detect_learning_opportunity(memory_manager: TenantMemoryManager):
    """Valida deteccao heuristica de aprendizado de regras e apelidos pelo operador."""
    # Apelido de produto
    op1 = memory_manager.detect_learning_opportunity("chame o diesel s10 de DIESEL B S10 COMUM")
    assert op1 is not None
    assert op1["categoria"] == "apelido_produto"
    assert op1["chave"].lower() == "diesel s10"

    # Regra explicita
    op2 = memory_manager.detect_learning_opportunity("grave que frentista nao pode receber nota de 200 sem conferir na luz")
    assert op2 is not None
    assert op2["categoria"] == "regra_posto"
    assert "nota de 200" in op2["conteudo"]

    # Rotina operacional
    op3 = memory_manager.detect_learning_opportunity("aqui no posto a sangria de caixa sempre ocorre as 14h e 22h")
    assert op3 is not None
    assert op3["categoria"] == "rotina_operacional"


def test_zero_unicode_dashes_in_tenant_memory_files():
    """Garante ausencia estrita de travessoes Unicode (U+2014 e U+2013)."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    for fname in ["core/tenant_memory.py", "tests/unit/test_tenant_memory.py"]:
        content = (base_dir / fname).read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao em {fname}"
        assert "\u2013" not in content, f"Meia-risca em {fname}"
