"""
Testes Unitarios do Bloco 5: Higienizacao de Prompts, RAG e Telemetria (Clean Room).
Valida que nenhuma estrutura fisica de banco de dados, tabela relacional ou coluna
proprietaria do ERP e exposta aos prompts de sistema, base vetorial RAG ou labels analiticos.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from datetime import date
from pathlib import Path

from core.adapters.erp import MockERPAdapter
from core.aura_engine import AuraEngine
from core.prompts import build_help_prompt, build_system_prompt
from core.schemas.rca import RCAEvidenceItem
from core.tools import PostoTools
from scripts.seed_aura_conhecimento import CONHECIMENTO_CHUNKS

# Lista de termos fisicos e colunas proprietarias estritamente proibidas em prompts e RAG
FORBIDDEN_ERP_TOKENS = [
    "fechabomba",
    "fechacaixa",
    "itemped",
    "medicaotanques",
    "prazos",
    "enclts",
    "qtdeaf",
]


class TestPromptCleanRoom:
    """Suite de validacao de blindagem arquitetural de prompts e RAG."""

    def test_build_system_prompt_sanitization(self) -> None:
        """Garante que o system prompt da AURA nao vaza tabelas ou colunas fisicas."""
        prompt = build_system_prompt(
            pergunta_sanitizada="Como estao os tanques e fechamento de caixa de hoje?",
            contexto_sanitizado="Tanque 01 com 12.000 L de Gasolina Comum. Caixa 01 conciliado.",
            historico_formatado="Usuario: Ola\nAURA: Ola, gestor.",
            dados_filial={
                "idempresa": "00001",
                "nome": "POSTO PILOTO MODELO",
                "razao_social": "POSTO PILOTO MODELO LTDA",
                "cnpj": "12.345.678/0001-90",
            },
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 200

        # Validacao de ausencia de tabelas fisicas
        lower_prompt = prompt.lower()
        for token in FORBIDDEN_ERP_TOKENS:
            assert token not in lower_prompt, f"Token proibido '{token}' encontrado no system prompt!"

        # Validacao de diretrizes anti-alucinacao SQL
        assert "NUNCA gera queries SQL" in prompt
        assert "nao solicita comandos de banco de dados" in prompt
        assert "nao especifica nomes de tabelas relacionais internas" in prompt

    def test_build_help_prompt_sanitization(self) -> None:
        """Garante que o prompt de ajuda e navegacao nao vaza tabelas fisicas."""
        prompt = build_help_prompt(
            pergunta_sanitizada="Como funciona o cockpit operacional da AURA?",
            contexto_sanitizado="O cockpit consolida metricas de autonomia de tanques e turnos.",
            historico_formatado="",
            dados_filial={
                "idempresa": "00001",
                "nome": "POSTO PILOTO MODELO",
            },
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 200

        lower_prompt = prompt.lower()
        for token in FORBIDDEN_ERP_TOKENS:
            assert token not in lower_prompt, f"Token proibido '{token}' encontrado no prompt de ajuda!"

        # Validacao de diretrizes de blindagem
        assert "Nunca mencione comandos SQL" in prompt
        assert "nomes de tabelas relacionais" in prompt

    def test_build_system_prompt_routing_help(self) -> None:
        """Garante que build_system_prompt delega corretamente para help quando intencao e ajuda_sistema."""
        prompt = build_system_prompt(
            pergunta_sanitizada="Quais os atalhos de navegacao?",
            contexto_sanitizado="Atalhos: Ctrl+K abre a paleta de comandos.",
            historico_formatado="",
            intencao="ajuda_sistema",
        )

        assert "AUTO-CONHECIMENTO e EXPLICACAO EXECUTIVA" in prompt
        lower_prompt = prompt.lower()
        for token in FORBIDDEN_ERP_TOKENS:
            assert token not in lower_prompt, f"Token proibido '{token}' no prompt de ajuda roteado!"

    def test_aura_engine_prompt_methods_delegation(self) -> None:
        """Garante que AuraEngine utiliza os novos metodos desacoplados sem vazar tabelas fisicas."""
        engine = AuraEngine(erp_adapter=MockERPAdapter())

        prompt_sistema = engine._build_prompt_sistema(
            pergunta_sanitizada="Como esta a previsao de esgotamento de combustiveis?",
            contexto_sanitizado="Tanque 2 com autonomia de 36 horas.",
            historico_formatado="Sem historico.",
        )
        assert isinstance(prompt_sistema, str)
        lower_sistema = prompt_sistema.lower()
        for token in FORBIDDEN_ERP_TOKENS:
            assert token not in lower_sistema, f"Token proibido '{token}' em _build_prompt_sistema!"

        prompt_ajuda = engine._build_prompt_ajuda(
            pergunta_sanitizada="Como operar a conciliacao de turnos?",
            contexto_sanitizado="Conciliacao compara encerrantes de pista com caixas.",
            historico_formatado="Sem historico.",
        )
        assert isinstance(prompt_ajuda, str)
        lower_ajuda = prompt_ajuda.lower()
        for token in FORBIDDEN_ERP_TOKENS:
            assert token not in lower_ajuda, f"Token proibido '{token}' em _build_prompt_ajuda!"

    def test_seed_conhecimento_chunks_rag_sanitized(self) -> None:
        """Garante que os chunks oficiais de conhecimento RAG nao citam tabelas proprietarias do ERP."""
        assert len(CONHECIMENTO_CHUNKS) >= 10

        for chunk in CONHECIMENTO_CHUNKS:
            titulo = chunk.get("titulo", "")
            conteudo = chunk.get("conteudo", "")
            topico = chunk.get("topico", "")

            texto_completo = f"{titulo} {conteudo} {topico}".lower()

            for token in FORBIDDEN_ERP_TOKENS:
                assert token not in texto_completo, (
                    f"Token proibido '{token}' encontrado no chunk RAG '{titulo}'!"
                )

    def test_posto_tools_output_labels_and_sources_sanitized(self) -> None:
        """Garante que labels, fontes e diagnosticos de PostoTools nao vazam tabelas fisicas."""
        adapter = MockERPAdapter()
        tools = PostoTools(erp_adapter=adapter)

        # Conciliacao de turnos
        res_turno = tools.auditar_fechamento_turno(data=date(2026, 10, 15))
        assert res_turno.get("status") in ("ok", "sem_movimento", "divergencia")

        resumo = res_turno.get("resumo_executivo", {})
        origem_pista = resumo.get("origem_faturamento_pista", "")
        assert "fechabomba" not in origem_pista.lower()
        assert (
            "Encerrantes Fisicos de Pista" in origem_pista
            or "tempo real" in origem_pista
            or "Sem moviment" in origem_pista
        )

        sources = res_turno.get("sources", [])
        for src in sources:
            src_str = str(src).lower()
            for token in FORBIDDEN_ERP_TOKENS:
                assert token not in src_str, f"Token proibido '{token}' encontrado na fonte {src}!"

    def test_rca_evidence_item_supports_canonical_entities(self) -> None:
        """Garante que RCAEvidenceItem aceita entidades canonicas AUPS sem erro de validacao."""
        ev_pumps = RCAEvidenceItem(
            evidence_id="EV-TEST-001",
            pattern_type="divergencia_encerrante",
            source_table="dispenser_logs",
            description="Leitura de encerrante com divergencia apurada.",
        )
        assert ev_pumps.source_table == "dispenser_logs"

        ev_shifts = RCAEvidenceItem(
            evidence_id="EV-TEST-002",
            pattern_type="inversao_pagamento",
            source_table="cashier_shifts",
            description="Variacao de forma de pagamento no turno.",
        )
        assert ev_shifts.source_table == "cashier_shifts"

        ev_sales = RCAEvidenceItem(
            evidence_id="EV-TEST-003",
            pattern_type="estorno_descompassado",
            source_table="sales_receipts",
            description="Cupom de venda descompassado.",
        )
        assert ev_sales.source_table == "sales_receipts"

    def test_zero_travessoes_in_prompts_and_tests(self) -> None:
        """Garante a ausencia estrita de travessoes (em-dash e en-dash) nos modulos de prompts e testes."""
        files_to_check = [
            Path("core/prompts/__init__.py"),
            Path("core/prompts/system_prompts.py"),
            Path("tests/unit/test_prompt_clean_room.py"),
        ]

        em_dash = "\u2014"
        en_dash = "\u2013"

        for file_path in files_to_check:
            assert file_path.exists(), f"Arquivo {file_path} nao existe para verificacao!"
            content = file_path.read_text(encoding="utf-8")
            assert em_dash not in content, f"Travessao em-dash (\\u2014) detectado em {file_path}!"
            assert en_dash not in content, f"Travessao en-dash (\\u2013) detectado em {file_path}!"
