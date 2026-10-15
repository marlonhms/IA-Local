"""Driver PostgreSQL Local - Data Mapper (AUPS Bloco 3).

AURA Universal Posto Schema (AUPS): Bloco 3 (Driver de Borda Isolado).
Unico modulo do ecossistema AURA a conhecer as queries SQL e tabelas do ERP local.
Conecta-se exclusivamente com a role de leitura restrita aura_service_ro.
Mapeia dados relacionais brutos para entidades universais de core/domain/.
Inclui fallback offline automatico para MockERPAdapter em caso de desconexao.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from datetime import time as dt_time
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from config.settings import ERP_USER
from core.adapters.erp.base import (
    BaseERPAdapter,
    ERPConnectionError,
    ERPQueryError,
    normalize_date_filter,
)
from core.adapters.erp.mock_adapter import MockERPAdapter
from core.db_pool import get_erp_connection
from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog
from core.domain.sales import (
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.domain.tanks import UniversalTankReading

logger = logging.getLogger("PostgresLocalERPAdapter")


class PostgresLocalERPAdapter(BaseERPAdapter):
    """Driver PostgreSQL de Borda com Data Mapping para AUPS.

    Isola todos os comandos SQL proprietarios em um unico ponto de contato.
    Emite exclusivamente objetos de dominio canonico universal (core/domain/).
    Opera em modo estritamente somente-leitura com a role aura_service_ro.
    """

    def __init__(
        self,
        fallback_adapter: BaseERPAdapter | None = None,
        fallback_on_error: bool = True,
        force_offline: bool = False,
    ) -> None:
        """Inicializa o adaptador PostgreSQL local.

        Args:
            fallback_adapter: Instancia de adaptador substituto para modo offline.
            fallback_on_error: Se True, aciona o fallback em caso de erro no banco.
            force_offline: Se True, forca o uso imediato do fallback sem tocar no banco.
        """
        self._fallback_adapter = fallback_adapter or MockERPAdapter()
        self._fallback_on_error = fallback_on_error
        self._force_offline = force_offline
        self._db_role = ERP_USER

    @property
    def adapter_name(self) -> str:
        """Nome identificador do adaptador ERP."""
        return "Postgres Local ERP Adapter (Data Mapper)"

    @property
    def db_role(self) -> str:
        """Role de seguranca somente-leitura utilizada na conexao."""
        return self._db_role

    @property
    def fallback_adapter(self) -> BaseERPAdapter:
        """Instancia do adaptador de contingencia offline."""
        return self._fallback_adapter

    @property
    def fallback_on_error(self) -> bool:
        """Indica se fallback automatico em excecoes esta habilitado."""
        return self._fallback_on_error

    @property
    def force_offline(self) -> bool:
        """Indica se o modo offline forcado esta ativado."""
        return self._force_offline

    @force_offline.setter
    def force_offline(self, val: bool) -> None:
        self._force_offline = bool(val)

    @property
    def is_connected(self) -> bool:
        """Verifica se a conexao fisica com o banco local esta ativa."""
        if self._force_offline:
            return False
        try:
            with get_erp_connection(timeout=2) as conn, conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            return True
        except (psycopg2.Error, RuntimeError, OSError):
            return False

    def connect(self) -> bool:
        """Verifica prontidao da conexao com o banco de dados local."""
        if self._force_offline:
            return False
        try:
            with get_erp_connection(timeout=3) as conn, conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            return True
        except (psycopg2.Error, RuntimeError, OSError) as exc:
            if self._fallback_on_error:
                logger.warning("Falha ao conectar no PostgreSQL local (%s): modo offline.", exc)
                return False
            raise ERPConnectionError(f"Falha de conexao com PostgreSQL ERP local: {exc}") from exc

    def disconnect(self) -> None:
        """Finaliza recursos (devolucao garantida gerenciada pelo db_pool)."""

    def _execute_query(
        self,
        query: str,
        params: tuple[Any, ...] | list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Executa consulta SQL estritamente somente-leitura com RealDictCursor."""
        with get_erp_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_recent_sales(
        self,
        start_date: str | date | datetime | None = None,
        end_date: str | date | datetime | None = None,
        limit: int = 100,
    ) -> list[UniversalSaleReceipt]:
        """Recupera transacoes de venda e cupons do PDV mapeados para AUPS.

        Consulta tabelas locais: pedido, itemped, produtos e prazos.
        Aplica filtro de nulos: COALESCE(p.situ, '') != 'C' e p.dtcanc IS NULL.
        """
        if self._force_offline:
            return self._fallback_adapter.get_recent_sales(start_date, end_date, limit)

        dt_ini = normalize_date_filter(start_date)
        dt_fim = normalize_date_filter(end_date)
        lim = max(1, int(limit))

        where_clauses = [
            "COALESCE(p.situ, '') != 'C'",
            "p.dtcanc IS NULL",
        ]
        params: list[Any] = []

        if dt_ini:
            where_clauses.append("p.dtem >= %s")
            params.append(dt_ini)
        if dt_fim:
            where_clauses.append("p.dtem <= %s")
            params.append(dt_fim)

        where_sql = " AND ".join(where_clauses)

        query = f"""
            WITH sub_pedidos AS (
                SELECT p.codi
                FROM pedido p
                WHERE {where_sql}
                ORDER BY COALESCE(p.ven_ts_venda, (p.dtem + p.hsmov)::timestamp, p.dtem::timestamp) DESC NULLS LAST, p.codi DESC
                LIMIT %s
            )
            SELECT 
                TRIM(p.codi) AS pedido_id,
                TRIM(COALESCE(p.cupom, p.codi)) AS cupom,
                TRIM(COALESCE(p.pdv, '1')) AS pdv,
                p.dtem AS data_emissao,
                p.hsmov AS hora_emissao,
                p.ven_ts_venda AS data_hora_venda,
                ROUND(COALESCE(p.valortotal, 0)::numeric, 2) AS total_reais,
                COALESCE(NULLIF(TRIM(p.situ), ''), 'CONCLUIDA') AS status_venda,
                COALESCE(NULLIF(TRIM(p.vendedor), ''), NULLIF(TRIM(p.clie), ''), 'SISTEMA') AS operador,
                TRIM(COALESCE(p.formapg, '0')) AS cod_forma,
                COALESCE(NULLIF(TRIM(prz.nompra), ''), NULLIF(TRIM(prz.tpprazo), ''), 'OUTROS') AS desc_forma,
                TRIM(COALESCE(prz.tpprazo, '')) AS tipo_prazo,
                i.controle AS item_controle,
                TRIM(COALESCE(i.codpec, 'SEM_CODIGO')) AS item_sku,
                COALESCE(NULLIF(TRIM(pr.nompro), ''), 'PRODUTO ' || TRIM(COALESCE(i.codpec, 'DIVERSO'))) AS item_descricao,
                COALESCE(NULLIF(TRIM(g.grupo), ''), 'GERAL') AS item_grupo,
                ROUND(COALESCE(i.valunit, pr.valvenda, 0)::numeric, 2) AS item_preco,
                ROUND(COALESCE(i.quant, 1)::numeric, 3) AS item_quantidade,
                ROUND(COALESCE(i.valitem, (COALESCE(i.valunit, pr.valvenda, 0) * COALESCE(i.quant, 1)), 0)::numeric, 2) AS item_total
            FROM sub_pedidos sp
            JOIN pedido p ON p.codi = sp.codi
            LEFT JOIN itemped i ON TRIM(i.pedido) = TRIM(p.codi)
            LEFT JOIN produtos pr ON TRIM(pr.codpro) = TRIM(i.codpec)
            LEFT JOIN grupos g ON TRIM(g.codi) = TRIM(pr.codgru)
            LEFT JOIN prazos prz ON TRIM(prz.codpra) = TRIM(p.formapg)
            ORDER BY COALESCE(p.ven_ts_venda, (p.dtem + p.hsmov)::timestamp, p.dtem::timestamp) DESC NULLS LAST, p.codi DESC, i.controle ASC NULLS LAST;
        """

        try:
            query_params = list(params) + [lim]
            rows = self._execute_query(query, query_params)
        except (psycopg2.Error, RuntimeError, OSError, ValueError, KeyError) as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_recent_sales no Postgres (%s): usando fallback.", exc)
                return self._fallback_adapter.get_recent_sales(start_date, end_date, limit)
            raise ERPQueryError(f"Erro ao consultar vendas recentes no PostgreSQL: {exc}") from exc

        if not rows:
            return []

        # Agrupa itens e pagamentos por pedido_id preservando ordem de insercao
        receipts_map: dict[str, dict[str, Any]] = {}
        for r in rows:
            ped_id = r["pedido_id"]
            if ped_id not in receipts_map:
                dt_venda = r["data_hora_venda"]
                if not dt_venda:
                    d_em = r["data_emissao"] or date.today()
                    h_em = r["hora_emissao"] or dt_time(0, 0)
                    dt_venda = datetime.combine(d_em, h_em)

                pm = UniversalPaymentMethod(
                    codigo_forma_pagamento=str(r["cod_forma"]),
                    descricao_forma=str(r["desc_forma"]),
                    tipo=r["tipo_prazo"] or r["desc_forma"],
                    valor_reais=float(r["total_reais"]),
                )
                receipts_map[ped_id] = {
                    "cupom_id": r["cupom"] or ped_id,
                    "data_hora": dt_venda,
                    "pdv": str(r["pdv"]),
                    "total_reais": float(r["total_reais"]),
                    "status": str(r["status_venda"]),
                    "operador": str(r["operador"]),
                    "itens": [],
                    "pagamentos": [pm],
                }

            if r.get("item_controle") is not None or (r.get("item_sku") and r["item_sku"] != "SEM_CODIGO"):
                item = UniversalSaleItem(
                    sku=str(r["item_sku"]),
                    descricao_produto=str(r["item_descricao"]),
                    grupo_comercial=str(r["item_grupo"]),
                    preco_unitario_reais=float(r["item_preco"]),
                    quantidade=float(r["item_quantidade"]),
                    total_item_reais=float(r["item_total"]),
                )
                receipts_map[ped_id]["itens"].append(item)

        results: list[UniversalSaleReceipt] = []
        for data in receipts_map.values():
            receipt = UniversalSaleReceipt(
                cupom_id=data["cupom_id"],
                data_hora=data["data_hora"],
                pdv=data["pdv"],
                total_reais=data["total_reais"],
                status=data["status"],
                operador=data["operador"],
                itens=data["itens"],
                pagamentos=data["pagamentos"],
            )
            results.append(receipt)

        return results[:lim]

    def get_tank_inventory(self) -> list[UniversalTankReading]:
        """Recupera telemetria atual de estoque e regua dos tanques.

        Consulta tabelas locais: tanques e medicaotanques.
        Calcula capacidade, volume atual, nivel de agua, temperatura e percentual.
        """
        if self._force_offline:
            return self._fallback_adapter.get_tank_inventory()

        query = """
            SELECT 
                TRIM(t.codtan) AS identificador_tanque,
                COALESCE(t.ultima_leitura, CURRENT_TIMESTAMP) AS timestamp_leitura,
                ROUND(COALESCE(t.volume, t.qtdeat, 0)::numeric, 2) AS volume_atual_litros,
                ROUND(COALESCE(t.volume_agua, 0)::numeric, 2) AS volume_agua_mm,
                ROUND(COALESCE(t.temperatura, 25.0)::numeric, 1) AS temperatura_celsius,
                ROUND(COALESCE(t.capacidade, 0)::numeric, 2) AS capacidade_nominal_litros
            FROM tanques t
            ORDER BY t.codtan;
        """

        try:
            rows = self._execute_query(query)
        except (psycopg2.Error, RuntimeError, OSError, ValueError, KeyError) as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_tank_inventory no Postgres (%s): usando fallback.", exc)
                return self._fallback_adapter.get_tank_inventory()
            raise ERPQueryError(f"Erro ao consultar inventario de tanques no PostgreSQL: {exc}") from exc

        readings: list[UniversalTankReading] = []
        for r in rows:
            vol = float(r["volume_atual_litros"])
            cap = float(r["capacidade_nominal_litros"])
            pct = round((vol / cap * 100.0), 2) if cap > 0 else 0.0

            reading = UniversalTankReading(
                identificador_tanque=str(r["identificador_tanque"]),
                timestamp_leitura=r["timestamp_leitura"],
                volume_atual_litros=vol,
                volume_agua_mm=float(r["volume_agua_mm"]),
                temperatura_celsius=float(r["temperatura_celsius"]),
                percentual_capacidade=pct,
            )
            readings.append(reading)

        return readings

    def get_pump_dispenses(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        limit: int = 100,
    ) -> list[UniversalDispenserLog]:
        """Recupera medicoes de encerrantes de bicos dispensadores.

        Consulta tabelas locais: fechabomba e abastecimentos.
        Garante mapeamento para UniversalDispenserLog com encerrantes e faturamento.
        """
        if self._force_offline:
            return self._fallback_adapter.get_pump_dispenses(start_date, end_date, limit)

        dt_ini = normalize_date_filter(start_date)
        dt_fim = normalize_date_filter(end_date)
        lim = max(1, int(limit))

        where_fb = []
        params_fb: list[Any] = []
        if dt_ini:
            where_fb.append("fb.dtmov >= %s")
            params_fb.append(dt_ini)
        if dt_fim:
            where_fb.append("fb.dtmov <= %s")
            params_fb.append(dt_fim)

        where_fb_sql = ("WHERE " + " AND ".join(where_fb)) if where_fb else ""

        query_fb = f"""
            SELECT 
                COALESCE(TRIM(fb.ilha::text), TRIM(fb.codbom)) AS identificador_bomba,
                TRIM(fb.codbom) AS identificador_bico,
                fb.dtmov::timestamp AS timestamp_registro,
                ROUND(COALESCE(fb.encltsa, 0)::numeric, 3) AS encerrante_inicial_litros,
                ROUND(COALESCE(fb.enclts, 0)::numeric, 3) AS encerrante_final_litros,
                ROUND(COALESCE(fb.qtdeaf, 0)::numeric, 3) AS volume_aferido_litros,
                ROUND(COALESCE(fb.encdinh, ((COALESCE(fb.enclts, 0) - COALESCE(fb.encltsa, 0) - COALESCE(fb.qtdeaf, 0)) * COALESCE(fb.preco, 0)), 0)::numeric, 2) AS total_faturado_reais
            FROM fechabomba fb
            {where_fb_sql}
            ORDER BY fb.dtmov DESC, fb.codbom ASC
            LIMIT %s;
        """

        try:
            rows = self._execute_query(query_fb, params_fb + [lim])
        except (psycopg2.Error, RuntimeError, OSError, ValueError, KeyError) as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_pump_dispenses no fechabomba (%s): tentando abastecimentos.", exc)
                rows = []
            else:
                raise ERPQueryError(f"Erro ao consultar fechabomba no PostgreSQL: {exc}") from exc

        has_meaningful_dispenses = any(
            float(r.get("encerrante_final_litros") or 0) > 0
            or float(r.get("total_faturado_reais") or 0) > 0
            for r in rows
        )

        # Se fechabomba nao tiver registros ou contiver apenas linhas zeradas sem medicao real,
        # consulta a tabela abastecimentos da automacao Companytec/CBC
        if (not rows or not has_meaningful_dispenses) and not self._force_offline:
            where_ab = ["a.abt_bl_venda_cancelada IS NOT TRUE"]
            params_ab: list[Any] = []
            if dt_ini:
                where_ab.append("a.data >= %s")
                params_ab.append(dt_ini)
            if dt_fim:
                where_ab.append("a.data <= %s")
                params_ab.append(dt_fim)

            where_ab_sql = "WHERE " + " AND ".join(where_ab)

            query_ab = f"""
                SELECT 
                    COALESCE(TRIM(b.ilha::text), TRIM(a.bomba)) AS identificador_bomba,
                    TRIM(a.bomba) AS identificador_bico,
                    COALESCE(a.abt_ts_abastecimento, (a.data + a.hora)::timestamp, a.data::timestamp) AS timestamp_registro,
                    ROUND(COALESCE(MIN(a.ei), 0)::numeric, 3) AS encerrante_inicial_litros,
                    ROUND(COALESCE(MAX(a.encerrante), 0)::numeric, 3) AS encerrante_final_litros,
                    0.0 AS volume_aferido_litros,
                    ROUND(COALESCE(SUM(a.total), 0)::numeric, 2) AS total_faturado_reais
                FROM abastecimentos a
                LEFT JOIN bombas b ON TRIM(b.codbom) = TRIM(a.bomba)
                {where_ab_sql}
                GROUP BY b.ilha, a.bomba, a.abt_ts_abastecimento, a.data, a.hora
                ORDER BY COALESCE(a.abt_ts_abastecimento, (a.data + a.hora)::timestamp, a.data::timestamp) DESC
                LIMIT %s;
            """
            try:
                ab_rows = self._execute_query(query_ab, params_ab + [lim])
                if ab_rows:
                    rows = ab_rows
            except (psycopg2.Error, RuntimeError, OSError, ValueError, KeyError) as exc:
                if self._fallback_on_error:
                    logger.warning("Falha em get_pump_dispenses no abastecimentos (%s): usando fallback.", exc)
                    return self._fallback_adapter.get_pump_dispenses(start_date, end_date, limit)
                raise ERPQueryError(f"Erro ao consultar abastecimentos no PostgreSQL: {exc}") from exc

        logs: list[UniversalDispenserLog] = []
        for r in rows:
            log_item = UniversalDispenserLog(
                identificador_bomba=str(r["identificador_bomba"]),
                identificador_bico=str(r["identificador_bico"]),
                timestamp_registro=r["timestamp_registro"],
                encerrante_inicial_litros=float(r["encerrante_inicial_litros"]),
                encerrante_final_litros=float(r["encerrante_final_litros"]),
                volume_aferido_litros=float(r["volume_aferido_litros"]),
                total_faturado_reais=float(r["total_faturado_reais"]),
            )
            logs.append(log_item)

        return logs

    def get_cashier_shifts(
        self,
        target_date: str | date | None = None,
        limit: int = 50,
    ) -> list[UniversalCashierShift]:
        """Recupera fechamentos de turno de caixa e frentistas.

        Consulta tabelas locais: fechacaixa e funcionarios.
        Mapeia operador, turno, fundo de troco, total declarado, sistema e quebra/sobra.
        """
        if self._force_offline:
            return self._fallback_adapter.get_cashier_shifts(target_date, limit)

        dt_alvo = normalize_date_filter(target_date)
        lim = max(1, int(limit))

        where_clauses = []
        params: list[Any] = []
        if dt_alvo:
            where_clauses.append("fc.dtmov = %s")
            params.append(dt_alvo)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        query = f"""
            SELECT 
                TRIM(COALESCE(fc.matricula, '0')) AS operador_id,
                COALESCE(TRIM(f.nome), 'OPERADOR NÃO INFORMADO') AS operador_nome,
                COALESCE(TRIM(fc.turno), 'GERAL') AS turno_descricao,
                fc.dtmov AS data_movimento,
                COALESCE(fc.cai_ts_abertura, fc.dtmov::timestamp) AS timestamp_abertura,
                CASE 
                    WHEN fc.cai_ts_fechamento > '1900-01-01' THEN fc.cai_ts_fechamento 
                    ELSE NULL 
                END AS timestamp_fechamento,
                ROUND(COALESCE(fc.valrefcai, fc.suprimentodinheiro, 0)::numeric, 2) AS fundo_troco_reais,
                ROUND(COALESCE(fc.valtot, (COALESCE(fc.valdinh, 0) + COALESCE(fc.valcart, 0) + COALESCE(fc.valnotpra, 0) + COALESCE(fc.valcheconv, 0) + COALESCE(fc.valchevis, 0) + COALESCE(fc.valchepre, 0)))::numeric, 2) AS total_declarado_reais,
                ROUND((COALESCE(fc.venda_combustivel, 0) + COALESCE(fc.venda_produtos, 0))::numeric, 2) AS total_sistema_reais
            FROM fechacaixa fc
            LEFT JOIN funcionarios f ON TRIM(f.matr) = TRIM(fc.matricula)
            {where_sql}
            ORDER BY fc.dtmov DESC, fc.cai_cd_caixa DESC
            LIMIT %s;
        """

        try:
            rows = self._execute_query(query, params + [lim])
        except (psycopg2.Error, RuntimeError, OSError, ValueError, KeyError) as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_cashier_shifts no Postgres (%s): usando fallback.", exc)
                return self._fallback_adapter.get_cashier_shifts(target_date, limit)
            raise ERPQueryError(f"Erro ao consultar fechacaixa no PostgreSQL: {exc}") from exc

        shifts: list[UniversalCashierShift] = []
        for r in rows:
            tot_decl = float(r["total_declarado_reais"])
            tot_sist = float(r["total_sistema_reais"])
            quebra_sobra = round(tot_decl - tot_sist, 2)

            shift = UniversalCashierShift(
                operador_id=str(r["operador_id"]),
                operador_nome=str(r["operador_nome"]),
                turno_descricao=str(r["turno_descricao"]),
                data_movimento=r["data_movimento"],
                timestamp_abertura=r["timestamp_abertura"],
                timestamp_fechamento=r["timestamp_fechamento"],
                fundo_troco_reais=float(r["fundo_troco_reais"]),
                total_declarado_reais=tot_decl,
                total_sistema_reais=tot_sist,
                quebra_sobra_reais=quebra_sobra,
            )
            shifts.append(shift)

        return shifts

    def get_product_catalog(
        self,
        filter_term: str | None = None,
        category: str | None = None,
        limit: int = 100,
    ) -> list[UniversalSaleItem]:
        """Recupera itens e combustiveis cadastrados no catalogo do ERP.

        Consulta tabelas locais: produtos e grupos.
        Filtra por termo de busca no SKU/nome ou grupo comercial.
        """
        if self._force_offline:
            return self._fallback_adapter.get_product_catalog(filter_term, category, limit)

        lim = max(1, int(limit))
        where_clauses = ["p.nompro IS NOT NULL"]
        params: list[Any] = []

        if filter_term and filter_term.strip():
            term = f"%{filter_term.strip()}%"
            where_clauses.append("(p.codpro ILIKE %s OR p.nompro ILIKE %s)")
            params.extend([term, term])

        if category and category.strip():
            cat = f"%{category.strip()}%"
            where_clauses.append("g.grupo ILIKE %s")
            params.append(cat)

        where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT 
                TRIM(p.codpro) AS sku,
                COALESCE(NULLIF(TRIM(p.nompro), ''), 'PRODUTO ' || TRIM(p.codpro)) AS descricao_produto,
                COALESCE(NULLIF(TRIM(g.grupo), ''), 'GERAL') AS grupo_comercial,
                ROUND(COALESCE(p.valvenda, 0)::numeric, 2) AS preco_unitario_reais,
                1.0 AS quantidade,
                ROUND(COALESCE(p.valvenda, 0)::numeric, 2) AS total_item_reais
            FROM produtos p
            LEFT JOIN grupos g ON TRIM(g.codi) = TRIM(p.codgru)
            {where_sql}
            ORDER BY p.codpro ASC
            LIMIT %s;
        """

        try:
            rows = self._execute_query(query, params + [lim])
        except (psycopg2.Error, RuntimeError, OSError, ValueError, KeyError) as exc:
            if self._fallback_on_error:
                logger.warning("Falha em get_product_catalog no Postgres (%s): usando fallback.", exc)
                return self._fallback_adapter.get_product_catalog(filter_term, category, limit)
            raise ERPQueryError(f"Erro ao consultar catalogo de produtos no PostgreSQL: {exc}") from exc

        items: list[UniversalSaleItem] = []
        for r in rows:
            item = UniversalSaleItem(
                sku=str(r["sku"]),
                descricao_produto=str(r["descricao_produto"]),
                grupo_comercial=str(r["grupo_comercial"]),
                preco_unitario_reais=float(r["preco_unitario_reais"]),
                quantidade=float(r["quantidade"]),
                total_item_reais=float(r["total_item_reais"]),
            )
            items.append(item)

        return items

    def check_health(self) -> dict[str, Any]:
        """Verifica conectividade real, latencia em ms e contagem de registros locais."""
        def _get_fallback_counts(fh: dict[str, Any]) -> dict[str, int]:
            return {
                "pedidos": int(fh.get("sales_count") or len(getattr(self._fallback_adapter, "_sales", []))),
                "tanques": int(fh.get("tank_readings_count") or len(getattr(self._fallback_adapter, "_tanks", []))),
                "bombas": int(fh.get("pump_dispenses_count") or len(getattr(self._fallback_adapter, "_pumps", []))),
                "fechamentos": int(fh.get("cashier_shifts_count") or len(getattr(self._fallback_adapter, "_shifts", []))),
                "produtos": int(fh.get("catalog_items_count") or len(getattr(self._fallback_adapter, "_catalog", []))),
            }

        if self._force_offline:
            fallback_h = self._fallback_adapter.check_health()
            return {
                "status": "offline_fallback",
                "adapter": self.adapter_name,
                "connected": False,
                "is_connected": False,
                "mode": "offline_fallback",
                "latency_ms": fallback_h.get("latency_ms", 0.5),
                "db_role": self._db_role,
                "record_counts": _get_fallback_counts(fallback_h),
                "error": "Modo offline forcado ativado",
            }

        t0 = time.perf_counter()
        try:
            with get_erp_connection(timeout=3) as conn, conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()

                # Contagem de registros nas principais tabelas
                cur.execute("SELECT COUNT(*) FROM pedido;")
                cnt_pedidos = int(cur.fetchone()[0])

                cur.execute("SELECT COUNT(*) FROM tanques;")
                cnt_tanques = int(cur.fetchone()[0])

                cur.execute("SELECT COUNT(*) FROM fechabomba;")
                cnt_bombas = int(cur.fetchone()[0])

                cur.execute("SELECT COUNT(*) FROM fechacaixa;")
                cnt_fechamentos = int(cur.fetchone()[0])

                cur.execute("SELECT COUNT(*) FROM produtos;")
                cnt_produtos = int(cur.fetchone()[0])

            latency_ms = (time.perf_counter() - t0) * 1000.0

            return {
                "status": "healthy",
                "adapter": self.adapter_name,
                "connected": True,
                "is_connected": True,
                "mode": "live_postgres",
                "latency_ms": round(latency_ms, 2),
                "db_role": self._db_role,
                "record_counts": {
                    "pedidos": cnt_pedidos,
                    "tanques": cnt_tanques,
                    "bombas": cnt_bombas,
                    "fechamentos": cnt_fechamentos,
                    "produtos": cnt_produtos,
                },
                "error": None,
            }
        except (psycopg2.Error, RuntimeError, OSError, ValueError, KeyError) as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning("PostgresLocalERPAdapter check_health falhou (%s): modo offline.", exc)
            fallback_h = self._fallback_adapter.check_health()
            return {
                "status": "offline_fallback",
                "adapter": self.adapter_name,
                "connected": False,
                "is_connected": False,
                "mode": "offline_fallback",
                "latency_ms": round(latency_ms, 2),
                "db_role": self._db_role,
                "record_counts": _get_fallback_counts(fallback_h),
                "error": str(exc),
            }
