"""Testes Unitarios do AURA Universal Domain Schema (AUDS) e Domain Packs (Fase 1).

Valida:
1. Contratos canonicos universais (UniversalSaleTransaction, UniversalInventoryNode,
   UniversalEquipmentTelemetry, UniversalCashierSession, UniversalFinancialSettlement).
2. Aliases estritos de retrocompatibilidade com entidades AUPS legadas.
3. Comportamento de lot_multiple generico (5.000L vs 12 UN vs 100 CX).
4. Calculos deterministicos de taxas MDR, divergencias e liquidacao financeira.
5. Carga de Domain Packs declarativos em YAML (fuel, supermarket, wholesale).
6. Preservacao integral das 11 rotas originais e resolucao bidirecional no SemanticRouter.
7. Regra inegociavel de ZERO TRAVESSOES em todo o modulo.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import core.domain.cashier as cd_cashier
import core.domain.pumps as cd_pumps
import core.domain.sales as cd_sales
import core.domain.tanks as cd_tanks
from core.domain import (
    AUDSBaseModel,
    AUPSBaseModel,
    DomainPackConfig,
    UniversalCashierSession,
    UniversalCashierShift,
    UniversalDispenserLog,
    UniversalEquipmentTelemetry,
    UniversalFinancialSettlement,
    UniversalInventoryNode,
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
    UniversalSaleTransaction,
    UniversalTankReading,
    get_active_domain_pack,
    list_available_packs,
    load_all_domain_packs,
    load_domain_pack,
    reset_active_domain_pack,
    set_active_domain_pack,
)
from core.domain.domain_pack_loader import DEFAULT_DOMAIN_PACKS_DIR
from core.semantic_router import (
    INTENT_EXEMPLARS,
    UNIVERSAL_TO_LEGACY_INTENTS,
    SemanticRouter,
    classificar_intencao_universal,
)


class TestAUDSUniversalEntities:
    """Valida os contratos canônicos universais do AUDS e retrocompatibilidade."""

    def test_base_model_alias(self) -> None:
        """Garante equivalencia estrutural entre AUDSBaseModel e AUPSBaseModel."""
        assert AUDSBaseModel is AUPSBaseModel

    def test_universal_sale_transaction_and_alias(self) -> None:
        """Valida UniversalSaleTransaction e a equivalencia com UniversalSaleReceipt."""
        # Garantia de alias 1:1
        assert UniversalSaleReceipt is UniversalSaleTransaction

        # Instanciacao canonica universal
        tx = UniversalSaleTransaction(
            cupom_id="TX_1001",
            data_hora=datetime(2026, 10, 21, 14, 30, 0),
            pdv="CHECKOUT_03",
            total_reais=250.0,
            status="CONCLUIDA",
            operador="VENDEDOR_07",
            cliente_id="CLI_9988",
            canal_venda="B2B",
            desconto_reais=15.0,
            itens=[
                UniversalSaleItem(
                    sku="PROD_A",
                    descricao_produto="Item Atacado A",
                    preco_unitario_reais=50.0,
                    quantidade=5.0,
                    total_item_reais=250.0,
                )
            ],
            pagamentos=[
                UniversalPaymentMethod(
                    codigo_forma_pagamento="03",
                    descricao_forma="Boleto Bancario",
                    tipo="prazo",
                    valor_reais=250.0,
                )
            ],
        )

        assert tx.cupom_id == "TX_1001"
        assert tx.venda_id == "TX_1001"
        assert tx.id == "TX_1001"
        assert tx.id_cupom == "TX_1001"
        assert tx.id_pedido == "TX_1001"
        assert tx.pedido_id == "TX_1001"
        assert tx.transaction_id == "TX_1001"
        assert tx.cliente_id == "CLI_9988"
        assert tx.canal_venda == "B2B"
        assert tx.desconto_reais == 15.0
        assert tx.total_reais == 250.0
        assert len(tx.itens) == 1
        assert len(tx.pagamentos) == 1

        # Imutabilidade estrita
        with pytest.raises(ValidationError):
            tx.total_reais = 300.0

    def test_universal_inventory_node_and_alias(self) -> None:
        """Valida UniversalInventoryNode e a equivalencia com UniversalTankReading."""
        assert UniversalTankReading is UniversalInventoryNode

        # 1. Caso Combustivel (lote padrao 5.000L)
        node_combustivel = UniversalInventoryNode(
            identificador_node="1",
            nome_node="Tanque 1 Gasolina Comum",
            tipo_node="tanque",
            quantidade_atual=12000.0,
            capacidade_maxima=30000.0,
            quantidade_minima_seguranca=5000.0,
            unidade_medida="L",
            lot_multiple=5000.0,
            codigo_item="GAS_COM",
            descricao_item="Gasolina Comum",
        )
        assert node_combustivel.identificador_tanque == "1"
        assert node_combustivel.tanque_id == "1"
        assert node_combustivel.node_id == "1"
        assert node_combustivel.volume_atual_litros == 12000.0
        assert node_combustivel.capacidade_nominal_litros == 30000.0
        assert node_combustivel.capacidade_livre == 18000.0
        assert node_combustivel.ullage == 18000.0
        assert node_combustivel.percentual_ocupacao == 40.0
        assert node_combustivel.percentual_capacidade == 40.0
        # Espaco para carretas de 5.000L: cabem 3 lotes (15.000L)
        assert node_combustivel.calcular_espaco_para_lotes() == 3
        # Para repor 13.000L, sao necessarios 3 lotes de 5.000L
        assert node_combustivel.calcular_lotes_reposicao(13000.0) == 3

        # 2. Caso Supermercado (lote padrao 12 unidades)
        node_supermercado = UniversalInventoryNode(
            identificador_node="GOND_A12",
            nome_node="Gondola Cereais Matinais",
            tipo_node="gondola",
            quantidade_atual=14.0,
            capacidade_maxima=50.0,
            quantidade_minima_seguranca=10.0,
            unidade_medida="UN",
            lot_multiple=12.0,
            codigo_item="CER_77",
            descricao_item="Cereal Matinal 300g",
        )
        assert node_supermercado.identificador_node == "GOND_A12"
        assert node_supermercado.unidade_medida == "UN"
        assert node_supermercado.lot_multiple == 12.0
        assert node_supermercado.capacidade_livre == 36.0
        # 36 livres / 12 = cabem exatamente 3 caixas
        assert node_supermercado.calcular_espaco_para_lotes() == 3
        # Reposicao de 20 unidades requer 2 caixas de 12 (24 unidades)
        assert node_supermercado.calcular_lotes_reposicao(20.0) == 2

        # 3. Caso Atacado (lote padrao 100 caixas/palete)
        node_atacado = UniversalInventoryNode(
            identificador_node="GALPAO_DOCA_04",
            nome_node="Armazem Central Paletes",
            tipo_node="deposito",
            quantidade_atual=250.0,
            capacidade_maxima=1000.0,
            unidade_medida="CX",
            lot_multiple=100.0,
        )
        assert node_atacado.lot_multiple == 100.0
        assert node_atacado.capacidade_livre == 750.0
        assert node_atacado.calcular_espaco_para_lotes() == 7
        assert node_atacado.calcular_lotes_reposicao(250.0) == 3

    def test_universal_equipment_telemetry_and_alias(self) -> None:
        """Valida UniversalEquipmentTelemetry e a equivalencia com UniversalDispenserLog."""
        assert UniversalDispenserLog is UniversalEquipmentTelemetry

        # Registro canonico
        telem = UniversalEquipmentTelemetry(
            identificador_equipamento="BOMBA_02",
            identificador_componente="BICO_05",
            tipo_equipamento="bomba_combustivel",
            leitura_inicial=10000.0,
            leitura_final=10550.0,
            volume_aferido=20.0,
            total_faturado_reais=3120.0,
            codigo_item="DIESEL_S10",
            descricao_item="Diesel S10 Comum",
            identificador_origem="TANQUE_3",
            preco_unitario_reais=5.89,
            qtd_acionamentos=28,
        )

        assert telem.identificador_bomba == "BOMBA_02"
        assert telem.bomba_id == "BOMBA_02"
        assert telem.identificador_bico == "BICO_05"
        assert telem.bico_id == "BICO_05"
        assert telem.encerrante_inicial_litros == 10000.0
        assert telem.encerrante_final_litros == 10550.0
        assert telem.volume_aferido_litros == 20.0
        assert telem.delta_leitura == 550.0
        # Volume liquido vendido: 550 - 20 = 530
        assert telem.volume_vendido_litros == 530.0
        assert telem.volume_vendido == 530.0
        assert telem.qtd_abastecimentos == 28
        assert telem.codigo_combustivel == "DIESEL_S10"
        assert telem.descricao_combustivel == "Diesel S10 Comum"
        assert telem.identificador_tanque == "TANQUE_3"
        assert telem.tanque_id == "TANQUE_3"

    def test_universal_cashier_session_and_alias(self) -> None:
        """Valida UniversalCashierSession e a equivalencia com UniversalCashierShift."""
        assert UniversalCashierShift is UniversalCashierSession

        session = UniversalCashierSession(
            operador_id="OP_42",
            operador_nome="Marcos Operador",
            turno_descricao="TARDE",
            data_movimento=date(2026, 10, 21),
            pdv="POS_01",
            caixa_id="CX_01",
            fundo_troco_reais=100.0,
            total_declarado_reais=1450.0,
            total_sistema_reais=1500.0,
            dinheiro_declarado_reais=350.0,
            cartao_declarado_reais=800.0,
            pix_declarado_reais=300.0,
        )

        assert session.usuario_id == "OP_42"
        assert session.funcionario_id == "OP_42"
        assert session.nome_operador == "Marcos Operador"
        assert session.sessao_id == "CX_01"
        assert session.terminal_id == "CX_01"
        assert session.pix_declarado_reais == 300.0
        # 1450 declarado - 1500 sistema = quebra de -50.0
        assert session.quebra_sobra_reais == -50.0

    def test_universal_financial_settlement_reconciliation(self) -> None:
        """Valida calculos de MDR, reconciliacao de taxas e deteccao de divergencias."""
        # 1. Transacao sem divergencia (taxa contratada = 1.99%, taxa real = 1.99%)
        settle_ok = UniversalFinancialSettlement(
            liquidacao_id="DOC_55441",
            adquirente_ou_banco="Stone",
            bandeira="Mastercard",
            modalidade="debito",
            valor_bruto_reais=1000.0,
            taxa_mdr_contratada_pct=1.99,
            taxa_mdr_real_pct=1.99,
            prazo_dias_compensacao=1,
            status_liquidacao="LIQUIDADO",
        )
        assert settle_ok.desconto_taxa_reais == 19.90
        assert settle_ok.valor_liquido_reais == 980.10
        assert settle_ok.divergencia_taxa_reais == 0.0
        assert not settle_ok.taxa_divergente
        assert settle_ok.perda_divergencia_reais == 0.0

        # 2. Transacao com divergencia abusiva (contratado 2.50%, descontado 3.80%)
        settle_divergente = UniversalFinancialSettlement(
            liquidacao_id="DOC_99882",
            adquirente_ou_banco="Cielo",
            bandeira="Visa",
            modalidade="credito_vista",
            valor_bruto_reais=2000.0,
            taxa_mdr_contratada_pct=2.50,
            taxa_mdr_real_pct=3.80,
            prazo_dias_compensacao=30,
            status_liquidacao="PENDENTE",
        )
        # Desconto real: 2000 * 3.8% = 76.00
        assert settle_divergente.desconto_taxa_reais == 76.00
        # Desconto contratado: 2000 * 2.5% = 50.00
        # Perda: 76.00 - 50.00 = 26.00
        assert settle_divergente.divergencia_taxa_reais == 26.00
        assert settle_divergente.taxa_divergente
        assert settle_divergente.perda_divergencia_reais == 26.00
        assert settle_divergente.valor_liquido_reais == 1924.00

    def test_cross_module_canonical_type_identity(self) -> None:
        """Valida que todos os modulos de dominio compartilham as mesmas classes canonicas."""
        # Vendas / Faturamento
        assert cd_sales.UniversalSaleTransaction is UniversalSaleTransaction
        assert cd_sales.UniversalSaleReceipt is UniversalSaleReceipt
        # Estoque / Tanques
        assert cd_tanks.UniversalInventoryNode is UniversalInventoryNode
        assert cd_tanks.UniversalTankReading is UniversalTankReading
        # Equipamentos / Telemetria
        assert cd_pumps.UniversalEquipmentTelemetry is UniversalEquipmentTelemetry
        assert cd_pumps.UniversalDispenserLog is UniversalDispenserLog
        # Turnos / Caixa
        assert cd_cashier.UniversalCashierSession is UniversalCashierSession
        assert cd_cashier.UniversalCashierShift is UniversalCashierShift

    def test_universal_attributes_accessible_via_legacy_imports(self) -> None:
        """Garante acesso a atributos e comportamentos universais mesmo via imports legados."""
        # 1. Gondola em cd_tanks
        node_gondola = cd_tanks.UniversalInventoryNode(
            identificador_node="G_01",
            tipo_node="gondola",
            nome_node="Gondola Biscoitos",
            quantidade_atual=10.0,
            lot_multiple=12.0,
        )
        assert node_gondola.tipo_node == "gondola"
        assert node_gondola.nome_node == "Gondola Biscoitos"
        assert node_gondola.identificador_tanque == "G_01"

        # 2. Balanca em cd_pumps
        telem_balanca = cd_pumps.UniversalEquipmentTelemetry(
            identificador_equipamento="BAL_01",
            tipo_equipamento="balanca",
            leitura_inicial=0.0,
            leitura_final=15.5,
        )
        assert telem_balanca.tipo_equipamento == "balanca"
        assert telem_balanca.identificador_bomba == "BAL_01"
        assert telem_balanca.delta_leitura == 15.5

        # 3. Sessao de caixa em cd_cashier
        sessao = cd_cashier.UniversalCashierSession(
            caixa_id="CX_CENTRAL",
            operador_id="OP_99",
            pix_declarado_reais=250.0,
        )
        assert sessao.sessao_id == "CX_CENTRAL"
        assert sessao.terminal_id == "CX_CENTRAL"
        assert sessao.pix_declarado_reais == 250.0


class TestDomainPacksLoader:
    """Valida a estrutura dos arquivos YAML de Domain Packs e o modulo loader."""

    def test_domain_packs_directory_exists(self) -> None:
        """Garante existencia do diretorio oficial de Domain Packs."""
        assert DEFAULT_DOMAIN_PACKS_DIR.exists()
        assert DEFAULT_DOMAIN_PACKS_DIR.is_dir()

    def test_list_available_packs(self) -> None:
        """Garante que os 3 Domain Packs canônicos sao detectados."""
        packs = list_available_packs()
        assert "fuel_convenience" in packs
        assert "retail_supermarket" in packs
        assert "wholesale_distribution" in packs

    def test_load_all_domain_packs(self) -> None:
        """Garante carregamento integro dos 3 cartuchos simultaneamente."""
        all_packs = load_all_domain_packs()
        assert len(all_packs) >= 3
        assert "fuel_convenience" in all_packs
        assert "retail_supermarket" in all_packs
        assert "wholesale_distribution" in all_packs

    def test_load_pack_fuel_convenience(self) -> None:
        """Valida integridade do Domain Pack de Postos e Conveniencia."""
        pack = load_domain_pack("fuel_convenience")
        assert pack.pack_id == "fuel_convenience"
        assert pack.vertical == "fuel_retail"
        assert pack.vocabulary.get("inventory_node") == "tanque"
        assert pack.vocabulary.get("equipment") == "bomba"
        assert pack.vocabulary.get("component") == "bico"
        assert pack.vocabulary.get("operator") == "frentista"
        assert pack.vocabulary.get("stock_unit") == "L"

        # Tolerancias de pista
        assert pack.get_tolerance("regulatory_volume_tolerance_pct") == 0.60
        assert pack.get_tolerance("default_lot_multiple") == 5000.0
        assert pack.get_tolerance("min_pump_flow_rate_lpm") == 20.0
        assert pack.get_tolerance("water_alert_threshold_mm") == 5.0

        # Mapeamentos de intencoes
        assert pack.resolve_intent("auditoria_turno_caixa") == "auditoria_turno"
        assert pack.resolve_intent("previsao_runout_estoque") == "previsao_tanques"
        assert pack.resolve_intent("desempenho_equipe_conversao") == "desempenho_pista_frentistas"

        # Intencoes especificas
        specific_ids = [item.id for item in pack.specific_intents]
        assert "lmc_anp" in specific_ids
        assert "auditar_conformidade_lmc_anp" in specific_ids
        assert "custo_estoque_macro" in specific_ids

    def test_load_pack_retail_supermarket(self) -> None:
        """Valida integridade do Domain Pack de Varejo Geral e Supermercados."""
        pack = load_domain_pack("retail_supermarket")
        assert pack.pack_id == "retail_supermarket"
        assert pack.vertical == "supermarket_retail"
        assert pack.vocabulary.get("inventory_node") == "gondola"
        assert pack.vocabulary.get("equipment") == "checkout"
        assert pack.vocabulary.get("operator") == "operador_caixa"
        assert pack.vocabulary.get("stock_unit") == "UN"

        # Tolerancias de supermercado
        assert pack.get_tolerance("default_lot_multiple") == 12.0
        assert pack.get_tolerance("inventory_shrinkage_tolerance_pct") == 0.50
        assert pack.get_tolerance("perishability_alert_days") == 3.0
        assert pack.get_tolerance("min_shelf_availability_pct") == 95.0

        # Mapeamento para intencoes de varejo
        assert pack.resolve_intent("auditoria_turno_caixa") == "fechamento_checkout_varejo"
        assert pack.resolve_intent("previsao_runout_estoque") == "ruptura_gondola_perecibilidade"

        specific_ids = [item.id for item in pack.specific_intents]
        assert "ruptura_invisivel_gondola" in specific_ids
        assert "perdas_por_vencimento" in specific_ids
        assert "rentabilidade_por_secao" in specific_ids

    def test_load_pack_wholesale_distribution(self) -> None:
        """Valida integridade do Domain Pack de Atacado e Distribuicao."""
        pack = load_domain_pack("wholesale_distribution")
        assert pack.pack_id == "wholesale_distribution"
        assert pack.vertical == "wholesale_distribution"
        assert pack.vocabulary.get("inventory_node") == "deposito_galpao"
        assert pack.vocabulary.get("operator") == "vendedor_b2b"
        assert pack.vocabulary.get("stock_unit") == "CX"

        # Tolerancias de atacado
        assert pack.get_tolerance("default_lot_multiple") == 100.0
        assert pack.get_tolerance("default_credit_term_days") == 28.0
        assert pack.get_tolerance("overdue_tolerance_pct") == 2.0
        assert pack.get_tolerance("min_order_value_reais") == 500.0

        # Mapeamento para intencoes de atacado
        assert pack.resolve_intent("auditoria_turno_caixa") == "conciliacao_faturamento_diario"
        assert pack.resolve_intent("previsao_runout_estoque") == "giro_estoque_reposicao_cd"

        specific_ids = [item.id for item in pack.specific_intents]
        assert "inadimplencia_carteira_clientes" in specific_ids
        assert "curva_abc_produtos_clientes" in specific_ids
        assert "otimizacao_carga_frete" in specific_ids

    def test_get_active_domain_pack_default(self) -> None:
        """Garante que o Domain Pack padrao e o fuel_convenience."""
        active = get_active_domain_pack()
        assert active.pack_id == "fuel_convenience"

    def test_load_non_existent_pack_raises_error(self) -> None:
        """Garante que tentar carregar pack inexistente lanca FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_domain_pack("pack_inexistente_xyz_123")

    def test_get_active_domain_pack_preserves_custom_active_pack(self) -> None:
        """Garante que get_active_domain_pack sem argumentos preserva o cartucho ativo definido."""
        try:
            supermarket = load_domain_pack("retail_supermarket")
            set_active_domain_pack(supermarket)
            # Ao chamar sem parametros, deve retornar o pack customizado ativo
            active = get_active_domain_pack()
            assert active.pack_id == "retail_supermarket"
        finally:
            reset_active_domain_pack()
            # Apos reset, o padrao volta a ser fuel_convenience
            assert get_active_domain_pack().pack_id == "fuel_convenience"

    def test_domain_pack_tolerances_coercion_brazilian_format(self) -> None:
        """Valida que tolerancias com virgula brasileira ou porcentagem sao convertidas com seguranca."""
        pack = DomainPackConfig(
            pack_id="custom_pack",
            pack_name="Pack Customizado",
            vertical="custom_vertical",
            tolerances={
                "anp_tol": "0,60",
                "markup_pct": "28,5%",
                "lot_large": "5.000,00",
                "shrinkage": 0.5,
            },
        )
        assert pack.tolerances["anp_tol"] == 0.60
        assert pack.tolerances["markup_pct"] == 28.5
        assert pack.tolerances["lot_large"] == 5000.0
        assert pack.tolerances["shrinkage"] == 0.5

    def test_load_empty_or_invalid_yaml(self, tmp_path: Path) -> None:
        """Valida isolamento de erro ao carregar arquivo YAML vazio ou invalido."""
        empty_yaml = tmp_path / "empty_pack.yaml"
        empty_yaml.write_text("", encoding="utf-8")

        with pytest.raises((ValueError, TypeError)):
            load_domain_pack(empty_yaml, packs_dir=tmp_path)


class TestSemanticRouterDomainPacksIntegration:
    """Valida integracao do SemanticRouter com os Domain Packs e nao-regressao das 11 rotas."""

    def test_eleven_original_routes_preserved(self) -> None:
        """Garante que as 11 rotas originais continuam presentes no catalogo de exemplares."""
        original_eleven = [
            "lmc_anp",
            "auditoria_turno",
            "investigar_causa_raiz",
            "mentoria_decisao",
            "previsao_tanques",
            "desempenho_pista_frentistas",
            "vendas_analitico",
            "estoque_posicao",
            "clientes_ranking",
            "sre_metricas",
            "dados_filial",
        ]
        for route in original_eleven:
            assert route in INTENT_EXEMPLARS, f"Rota original '{route}' ausente em INTENT_EXEMPLARS"
            assert len(INTENT_EXEMPLARS[route]["exemplos"]) >= 5

    def test_six_universal_intents_registered_in_exemplars(self) -> None:
        """Garante presenca das 6 novas intencoes universais AUDS no catalogo."""
        universal_six = [
            "auditoria_turno_caixa",
            "previsao_runout_estoque",
            "desempenho_equipe_conversao",
            "market_basket_cross_sell",
            "erosao_financeira_tef_selic",
            "raio_x_causal_margem",
        ]
        for intent in universal_six:
            assert intent in INTENT_EXEMPLARS, f"Intencao universal '{intent}' ausente no catalogo"
            assert len(INTENT_EXEMPLARS[intent]["exemplos"]) >= 5

    def test_bidirectional_intent_resolution(self) -> None:
        """Garante traducao perfeita nos dois sentidos entre rotas universais e legadas."""
        router = SemanticRouter()

        for univ, leg in UNIVERSAL_TO_LEGACY_INTENTS.items():
            assert router.resolve_legacy_intent(univ) == leg
            assert router.resolve_universal_intent(leg) == univ

        # Rota nao mapeada deve retornar a si mesma
        assert router.resolve_universal_intent("lmc_anp") == "lmc_anp"
        assert router.resolve_legacy_intent("lmc_anp") == "lmc_anp"

    def test_router_domain_pack_loading_and_intent_dispatch(self) -> None:
        """Valida a carga de Domain Packs no SemanticRouter e resolucao contextual."""
        router = SemanticRouter()
        assert router.active_domain_pack is None

        # Carrega cartucho de varejo/supermercado
        pack_retail = router.load_domain_pack("retail_supermarket")
        assert pack_retail is not None
        assert pack_retail.pack_id == "retail_supermarket"
        assert router.active_domain_pack is not None
        assert router.active_domain_pack.pack_id == "retail_supermarket"

        # Rota universal mapeada para o contexto de supermercado
        assert router.resolve_active_pack_intent("auditoria_turno_caixa") == "fechamento_checkout_varejo"
        assert router.resolve_active_pack_intent("previsao_runout_estoque") == "ruptura_gondola_perecibilidade"

        # Carrega cartucho de postos
        router.load_domain_pack("fuel_convenience")
        assert router.active_domain_pack.pack_id == "fuel_convenience"
        assert router.resolve_active_pack_intent("auditoria_turno_caixa") == "auditoria_turno"
        assert router.resolve_active_pack_intent("previsao_runout_estoque") == "previsao_tanques"

    def test_classificar_intencao_universal_helper(self) -> None:
        """Valida helper deterministico de classificacao universal."""
        # Frases de fechamento de caixa
        intencao_univ = classificar_intencao_universal("Como fechou o primeiro turno hoje?")
        assert intencao_univ == "auditoria_turno_caixa"

        # Frases de runout / tanques
        intencao_univ_tanque = classificar_intencao_universal("Qual a previsão de run-out dos tanques?")
        assert intencao_univ_tanque == "previsao_runout_estoque"

        # Frases de frentistas / equipe
        intencao_univ_equipe = classificar_intencao_universal("Qual frentista vendeu mais aditivada hoje?")
        assert intencao_univ_equipe == "desempenho_equipe_conversao"

        # Frases de cross-sell
        intencao_univ_basket = classificar_intencao_universal("Quais produtos vendem juntos na cesta de compras?")
        assert intencao_univ_basket == "market_basket_cross_sell"


class TestZeroTravessoesAUDSCompliance:
    """Valida a regra inegociavel de ZERO TRAVESSOES nos arquivos criados na Fase 1."""

    def test_zero_travessoes_in_all_auds_files(self) -> None:
        """Garante que nenhum caractere em-dash ou en-dash existe nos novos artefatos."""
        root = Path(__file__).resolve().parent.parent.parent

        files_to_verify = [
            root / "core" / "domain" / "universal_entities.py",
            root / "core" / "domain" / "domain_pack_loader.py",
            root / "core" / "domain" / "__init__.py",
            root / "core" / "domain" / "base.py",
            root / "core" / "domain" / "sales.py",
            root / "core" / "domain" / "tanks.py",
            root / "core" / "domain" / "pumps.py",
            root / "core" / "domain" / "cashier.py",
            root / "config" / "domain_packs" / "pack_fuel_convenience.yaml",
            root / "config" / "domain_packs" / "pack_retail_supermarket.yaml",
            root / "config" / "domain_packs" / "pack_wholesale_distribution.yaml",
            root / "core" / "semantic_router.py",
            root / "docs" / "dossie_tecnico.md",
            root / "docs" / "roadmap.md",
            Path(__file__).resolve(),
        ]

        forbidden_dashes = ["\u2014", "\u2013"]
        for path in files_to_verify:
            assert path.exists(), f"Arquivo nao encontrado para verificacao: {path}"
            content = path.read_text(encoding="utf-8")
            for char in forbidden_dashes:
                assert char not in content, (
                    f"Violacao de ZERO TRAVESSOES: caractere {char!r} encontrado em {path.name}"
                )
