"""
Testes Unitarios do Bloco 6: Documento de Conformidade, Opt-In do Lojista e Clean Room.
Valida schemas de opt-in, manager de conformidade, integridade do termo juridico,
integracao com o AuraEngine e a regra inegociavel de ZERO travessoes.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config.settings import BASE_DIR
from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.compliance_manager import ComplianceManager
from core.schemas.compliance import (
    ComplianceOptInStatus,
    ComplianceVerificationResult,
)


@pytest.mark.unit
class TestComplianceOptIn:
    """Suite de testes unitarios de conformidade legal e opt-in tecnico."""

    def test_compliance_opt_in_status_schema(self) -> None:
        """Valida tipagem, validacao e imutabilidade do schema ComplianceOptInStatus."""
        now_iso = datetime.now(UTC).isoformat()
        status_obj = ComplianceOptInStatus(
            loja_cnpj="12.345.678/0001-90",
            razao_social="Auto Posto Central Ltda",
            aceite_interoperabilidade_em=now_iso,
            versao_termo="1.0",
            status="active",
            assinado_por="Carlos Eduardo - Diretor Operacional",
            hash_termo="a" * 64,
            metadata={"origem": "painel_onboarding_local", "ip": "127.0.0.1"},
        )

        assert status_obj.loja_cnpj == "12.345.678/0001-90"
        assert status_obj.cnpj_limpo == "12345678000190"
        assert status_obj.razao_social == "Auto Posto Central Ltda"
        assert status_obj.is_active is True
        assert status_obj.versao_termo == "1.0"
        assert status_obj.hash_termo == "a" * 64

        # Imutabilidade garantida por frozen=True
        with pytest.raises(ValidationError):
            status_obj.status = "revoked"

    def test_compliance_opt_in_datetime_coercion(self) -> None:
        """Garante que objetos datetime sao convertidos automaticamente para string ISO."""
        dt = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
        status_obj = ComplianceOptInStatus(
            loja_cnpj="98.765.432/0001-10",
            razao_social="Posto Exemplo S/A",
            aceite_interoperabilidade_em=dt,
            versao_termo="1.0",
            status="accepted",
            assinado_por="Mariana Souza",
            hash_termo="b" * 64,
        )
        assert isinstance(status_obj.aceite_interoperabilidade_em, str)
        assert "2026-10-15T12:00:00" in status_obj.aceite_interoperabilidade_em
        assert status_obj.is_active is True

    def test_term_document_integrity_and_legal_basis(self) -> None:
        """
        Valida que o documento oficial de conformidade existe e contem
        todas as fundamentacoes legais brasileiras exigidas e certificacoes tecnicas.
        """
        term_path = BASE_DIR / "docs" / "compliance" / "termo_interoperabilidade_lgpd.md"
        assert term_path.exists(), f"Termo nao encontrado em: {term_path}"

        content = term_path.read_text(encoding="utf-8")
        assert len(content) > 1000, "Conteudo do termo excessivamente curto"

        # 1. Fundamentacao Legal: LGPD (Lei 13.709/2018)
        assert "13.709/2018" in content
        assert "Art. 7, IX" in content or "Art. 7" in content
        assert "Art. 2" in content
        assert "Art. 18" in content
        assert "Legitimo Interesse" in content
        assert "Portabilidade" in content or "portabilidade" in content

        # 2. Fundamentacao Legal: Lei de Software (Lei 9.609/1998)
        assert "9.609/1998" in content
        assert "Art. 6" in content
        assert "interoperabilidade" in content or "Interoperabilidade" in content
        assert "copia de salvaguarda" in content or "salvaguarda" in content

        # 3. Fundamentacao Legal: Marco Civil da Internet (Lei 12.965/2014)
        assert "12.965/2014" in content
        assert "Art. 3" in content
        assert "Art. 4" in content
        assert "livre concorrencia" in content or "Livre Concorrencia" in content

        # 4. Vedacao ao Vendor Lock-in (CDC e Codigo Civil)
        assert "Vendor Lock-in" in content or "vendor lock-in" in content
        assert "Consumidor" in content
        assert "Codigo Civil" in content

        # 5. Certificacao Tecnica Clean Room & Read-Only
        assert "aura_service_ro" in content
        assert "READ ONLY" in content
        assert "INSERT" in content
        assert "UPDATE" in content
        assert "DELETE" in content
        assert "AUPS" in content
        assert "BaseERPAdapter" in content

    def test_compliance_manager_hash_computation(self) -> None:
        """Garante calculo de hash SHA-256 deterministico e robusto do termo."""
        manager = ComplianceManager(db_path=":memory:")
        term_hash = manager.compute_term_hash()

        assert isinstance(term_hash, str)
        assert len(term_hash) == 64
        # Determinismo: calculos sucessivos produzem o mesmo digest
        assert term_hash == manager.compute_term_hash()

        # Arquivo inexistente retorna string vazia
        missing_hash = manager.compute_term_hash(path="/caminho/falso/termo.md")
        assert missing_hash == ""

    def test_compliance_manager_opt_in_lifecycle(self, tmp_path: Path) -> None:
        """
        Valida o ciclo de vida completo de opt-in:
        registro, consulta por CNPJ formatado/limpo, consulta do mais recente e revogacao.
        """
        db_file = tmp_path / "test_compliance.db"
        json_file = tmp_path / "test_opt_in.json"

        manager = ComplianceManager(db_path=db_file, json_path=json_file)
        current_hash = manager.compute_term_hash()

        # 1. Registro do opt-in
        opt_in = manager.register_opt_in({
            "loja_cnpj": "11.222.333/0001-44",
            "razao_social": "Posto das Americas Ltda",
            "assinado_por": "Gestor Geral",
            "metadata": {"canal": "totem_local"},
        })

        assert opt_in.loja_cnpj == "11.222.333/0001-44"
        assert opt_in.status == "active"
        assert opt_in.hash_termo == current_hash
        assert opt_in.is_active is True

        # 2. Consulta por CNPJ exato
        retrieved = manager.get_opt_in("11.222.333/0001-44")
        assert retrieved is not None
        assert retrieved.razao_social == "Posto das Americas Ltda"

        # 3. Consulta por CNPJ desformatado (apenas digitos)
        retrieved_clean = manager.get_opt_in("11222333000144")
        assert retrieved_clean is not None
        assert retrieved_clean.loja_cnpj == "11.222.333/0001-44"

        # 4. Consulta sem parametros (retorna o mais recente)
        latest = manager.get_opt_in()
        assert latest is not None
        assert latest.loja_cnpj == "11.222.333/0001-44"

        # 5. Verificacao de validade
        assert manager.is_opt_in_valid("11.222.333/0001-44") is True

        # 6. Diagnostico completo
        verif = manager.verify_compliance("11.222.333/0001-44")
        assert isinstance(verif, ComplianceVerificationResult)
        assert verif.compliant is True
        assert verif.hash_confere is True
        assert verif.garantia_leitura_exclusiva is True
        assert verif.isolamento_aups is True

        # 7. Revogacao
        revoked = manager.revoke_opt_in("11.222.333/0001-44", reason="Troca de gestao")
        assert revoked is True

        after_revocation = manager.get_opt_in("11.222.333/0001-44")
        assert after_revocation is not None
        assert after_revocation.status == "revoked"
        assert manager.is_opt_in_valid("11.222.333/0001-44") is False

        verif_revoked = manager.verify_compliance("11.222.333/0001-44")
        assert verif_revoked.compliant is False

    def test_compliance_manager_hash_mismatch(self) -> None:
        """Garante rejeicao de opt-in quando o hash do termo assinado diverge do atual."""
        manager = ComplianceManager(db_path=":memory:")

        # Registra opt-in com hash adulterado ou desatualizado
        manager.register_opt_in({
            "loja_cnpj": "22.333.444/0001-55",
            "razao_social": "Posto Bandeira Branca",
            "assinado_por": "Administrador",
            "hash_termo": "0" * 64,
        })

        assert manager.is_opt_in_valid("22.333.444/0001-55", verify_hash=True) is False
        assert manager.is_opt_in_valid("22.333.444/0001-55", verify_hash=False) is True

        result = manager.verify_compliance("22.333.444/0001-55")
        assert result.compliant is False
        assert result.hash_confere is False
        assert "desatualizada ou modificada" in result.mensagem

    def test_compliance_manager_missing_opt_in(self) -> None:
        """Verifica diagnostico para CNPJ que nunca realizou opt-in."""
        manager = ComplianceManager(db_path=":memory:")
        result = manager.verify_compliance("99.999.999/9999-99")

        assert result.compliant is False
        assert result.status == "pending_opt_in"
        assert result.hash_confere is False
        assert "sem opt-in" in result.mensagem.lower()

    def test_aura_engine_check_compliance_opt_in_integration(self) -> None:
        """Valida a integracao do metodo check_compliance_opt_in diretamente no AuraEngine."""
        session_mem = AuraSessionMemory(db_path=":memory:")
        compliance_mgr = ComplianceManager(db_path=":memory:")

        engine = AuraEngine(
            tenant_id="tenant_teste",
            filial_id="posto_teste_01",
            session_memory=session_mem,
            compliance_manager=compliance_mgr,
        )

        # Sem opt-in cadastrado
        status_unregistered = engine.check_compliance_opt_in("33.444.555/0001-66")
        assert isinstance(status_unregistered, dict)
        assert status_unregistered["compliant"] is False
        assert status_unregistered["status"] == "pending_opt_in"

        # Registra opt-in no manager
        compliance_mgr.register_opt_in({
            "loja_cnpj": "33.444.555/0001-66",
            "razao_social": "Posto Integrado S/A",
            "assinado_por": "Gerente de TI",
        })

        # Consulta agora atraves da Engine
        status_registered = engine.check_compliance_opt_in("33.444.555/0001-66")
        assert status_registered["compliant"] is True
        assert status_registered["razao_social"] == "Posto Integrado S/A"
        assert status_registered["garantia_leitura_exclusiva"] is True
        assert status_registered["isolamento_aups"] is True

    def test_zero_travessoes_compliance_rule(self) -> None:
        """
        Regra inegociavel do projeto: ZERO TRAVESSOES (em-dash e en-dash).
        Valida que nenhum dos arquivos do Bloco 6 contem os caracteres '\\u2014' ou '\\u2013'.
        """
        files_to_check = [
            BASE_DIR / "docs" / "compliance" / "termo_interoperabilidade_lgpd.md",
            BASE_DIR / "docs" / "compliance" / "marco_legal_interoperabilidade_lgpd.md",
            BASE_DIR / "core" / "schemas" / "compliance.py",
            BASE_DIR / "core" / "compliance_manager.py",
            BASE_DIR / "tests" / "unit" / "test_compliance_opt_in.py",
            BASE_DIR / "docs" / "roadmap_blindagem_juridica_clean_room.md",
        ]

        forbidden_chars = ["\u2014", "\u2013"]
        for file_path in files_to_check:
            assert file_path.exists(), f"Arquivo nao encontrado para checagem: {file_path}"
            content = file_path.read_text(encoding="utf-8")
            for char in forbidden_chars:
                assert char not in content, (
                    f"Violacao da regra ZERO TRAVESSOES: caractere {char!r} encontrado em {file_path.name}"
                )

    def test_compliance_performance_sub_second(self) -> None:
        """Valida que todas as operacoes de conformidade executam em tempo sub-segundo (< 0.3s)."""
        manager = ComplianceManager(db_path=":memory:")

        t0 = time.perf_counter()
        # 1. Hashing do termo fisico
        _ = manager.compute_term_hash()

        # 2. Registro de 10 opt-ins
        for i in range(10):
            manager.register_opt_in({
                "loja_cnpj": f"10.000.000/0001-{i:02d}",
                "razao_social": f"Posto Celeridade {i}",
                "assinado_por": f"Diretor {i}",
            })

        # 3. Verificacao de conformidade
        for i in range(10):
            res = manager.verify_compliance(f"10.000.000/0001-{i:02d}")
            assert res.compliant is True

        elapsed = time.perf_counter() - t0
        assert elapsed < 0.3, f"Tempo de execucao excedeu o limite de 0.3s: {elapsed:.4f}s"

    def test_compliance_schema_validation_rejects_empty(self) -> None:
        """Garante que strings vazias ou apenas espacos sao rejeitadas no schema."""
        now_iso = datetime.now(UTC).isoformat()
        with pytest.raises(ValidationError):
            ComplianceOptInStatus(
                loja_cnpj="   ",
                razao_social="Posto Vazio",
                aceite_interoperabilidade_em=now_iso,
                assinado_por="Gestor",
                hash_termo="a" * 64,
            )

        with pytest.raises(ValidationError):
            ComplianceOptInStatus(
                loja_cnpj="11.222.333/0001-44",
                razao_social="   ",
                aceite_interoperabilidade_em=now_iso,
                assinado_por="Gestor",
                hash_termo="a" * 64,
            )

        with pytest.raises(ValidationError):
            ComplianceOptInStatus(
                loja_cnpj="11.222.333/0001-44",
                razao_social="Posto OK",
                aceite_interoperabilidade_em="   ",
                assinado_por="Gestor",
                hash_termo="a" * 64,
            )

    def test_compliance_manager_split_brain_prevention(self, tmp_path: Path) -> None:
        """
        Garante que o registro de CNPJ formatado seguido de desformatado
        nao gere registros duplicados nem estado inconsistente de revogacao.
        """
        db_file = tmp_path / "split_brain.db"
        json_file = tmp_path / "split_brain.json"
        manager = ComplianceManager(db_path=db_file, json_path=json_file)

        # 1. Registra com formatacao
        manager.register_opt_in({
            "loja_cnpj": "55.666.777/0001-88",
            "razao_social": "Posto Unificado",
            "assinado_por": "Gestor A",
        })

        # 2. Atualiza com o mesmo CNPJ porem desformatado
        manager.register_opt_in({
            "loja_cnpj": "55666777000188",
            "razao_social": "Posto Unificado Atualizado",
            "assinado_por": "Gestor B",
        })

        # Deve haver apenas 1 registro ativo e nao dois conflitantes
        opt_fmt = manager.get_opt_in("55.666.777/0001-88")
        assert opt_fmt is not None
        assert opt_fmt.razao_social == "Posto Unificado Atualizado"

        # Revogacao por CNPJ formatado revoga qualquer representacao
        manager.revoke_opt_in("55.666.777/0001-88", reason="Teste revogacao")
        verif = manager.verify_compliance("55666777000188")
        assert verif.compliant is False
        assert verif.status == "revoked"

    def test_compliance_manager_revoke_empty_or_whitespace_cnpj(self) -> None:
        """Garante que revogacao com CNPJ vazio ou invalido retorna False com seguranca."""
        manager = ComplianceManager(db_path=":memory:")
        assert manager.revoke_opt_in("") is False
        assert manager.revoke_opt_in("   ") is False
        assert manager.revoke_opt_in("invalido") is False

    def test_compliance_hash_newline_normalization(self, tmp_path: Path) -> None:
        """Garante determinismo do SHA-256 independentemente de quebras CRLF ou LF."""
        crlf_file = tmp_path / "termo_crlf.md"
        lf_file = tmp_path / "termo_lf.md"

        text = "# Termo de Teste\nLinha 1\nLinha 2\n"
        lf_file.write_bytes(text.encode("utf-8"))
        crlf_file.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

        manager = ComplianceManager(db_path=":memory:")
        hash_lf = manager.compute_term_hash(lf_file)
        hash_crlf = manager.compute_term_hash(crlf_file)

        assert hash_lf != ""
        assert hash_lf == hash_crlf

    def test_compliance_fastapi_endpoints(self) -> None:
        """Valida a consulta e registro de conformidade via endpoints HTTP da API FastAPI."""
        session_mem = AuraSessionMemory(db_path=":memory:")
        compliance_mgr = ComplianceManager(db_path=":memory:")
        engine = AuraEngine(session_memory=session_mem, compliance_manager=compliance_mgr)
        app = create_aura_app(engine=engine)
        client = TestClient(app)

        # 1. Consulta antes do opt-in
        res = client.get("/api/v1/aura/compliance/status?cnpj=44.555.666/0001-77")
        assert res.status_code == 200
        data = res.json()
        assert data["compliant"] is False
        assert data["status"] == "pending_opt_in"

        # 2. Registro formal de opt-in via POST
        post_res = client.post(
            "/api/v1/aura/compliance/opt-in",
            json={
                "loja_cnpj": "44.555.666/0001-77",
                "razao_social": "Auto Posto Alvorada Ltda",
                "assinado_por": "Renata Lima - Proprietaria",
                "metadata": {"ip": "192.168.1.50"},
            },
        )
        assert post_res.status_code == 200
        post_data = post_res.json()
        assert post_data["status"] == "ok"
        assert post_data["opt_in"]["loja_cnpj"] == "44.555.666/0001-77"
        assert post_data["verification"]["compliant"] is True

        # 3. Consulta subsequente apos opt-in
        res_after = client.get("/api/v1/aura/compliance/status?cnpj=44.555.666/0001-77")
        assert res_after.status_code == 200
        assert res_after.json()["compliant"] is True

    def test_driver_level_protection_options(self) -> None:
        """Garante que as opcoes de blindagem a prova de pericia tecnica estao ativas no driver PostgreSQL."""
        from config.settings import DB_ERP_CONFIG
        from core.adapters.erp.postgres_local_adapter import PostgresLocalERPAdapter

        options = str(DB_ERP_CONFIG.get("options", ""))
        assert "default_transaction_read_only=on" in options
        assert "statement_timeout=4000" in options
        assert "lock_timeout=1000" in options

        # Valida no ComplianceManager
        manager = ComplianceManager(db_path=":memory:")
        prot_status = manager.get_driver_protection_status()
        assert prot_status["read_only_enforced"] is True
        assert prot_status["statement_timeout_enforced"] is True
        assert prot_status["lock_timeout_enforced"] is True
        assert prot_status["forensic_safe"] is True

        # Valida no PostgresLocalERPAdapter
        adapter = PostgresLocalERPAdapter(force_offline=True)
        assert adapter.driver_options == options

    def test_term_v1_1_clauses_and_forensic_immunity(self) -> None:
        """Valida as clausulas especificas da versao 1.1: Art. 39 LGPD, Secao 3.2 e Clausula Quarta."""
        term_path = BASE_DIR / "docs" / "compliance" / "termo_interoperabilidade_lgpd.md"
        assert term_path.exists()
        content = term_path.read_text(encoding="utf-8")

        # Versao 1.1
        assert "Versao Oficial:** 1.1" in content or "1.1" in content

        # Art. 39 da LGPD (Enquadramento Controlador x Operador)
        assert "Art. 39" in content or "Artigo 39" in content
        assert "Controlador" in content
        assert "Operadora" in content

        # Secao 3.2 e Clausula Quarta (Isencao e Pericia Tecnica)
        assert "statement_timeout=4000" in content
        assert "lock_timeout=1000" in content
        assert "default_transaction_read_only=on" in content
        assert "pg_stat_activity" in content
        assert "Isencao de Responsabilidade" in content or "isencao" in content.lower()
