"""Interface Abstrata do Adaptador ERP (ERP Port).

AURA Universal Posto Schema (AUPS): Bloco 2 (Open Posto Architecture).
Define o contrato formal e imutavel que qualquer adaptador de ERP deve cumprir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from types import TracebackType
from typing import Any, Self

from core.domain.cashier import UniversalCashierShift
from core.domain.pumps import UniversalDispenserLog
from core.domain.sales import UniversalSaleItem, UniversalSaleReceipt
from core.domain.tanks import UniversalTankReading


class ERPAdapterError(Exception):
    """Excecao base para erros do adaptador ERP."""


class ERPConnectionError(ERPAdapterError):
    """Erro de conexao com o banco de dados ou servico ERP."""


class ERPQueryError(ERPAdapterError):
    """Erro durante a execucao de consulta ou transformacao de dados no ERP."""


def normalize_date_filter(val: str | date | datetime | None) -> date | None:
    """Normaliza parametro de data para objeto date padrao.

    Retorna None se o parametro for nulo ou vazio.
    Suporta date, datetime (com conversao de fuso horario local se houver tzinfo),
    e formatos textuais ISO (YYYY-MM-DD) ou brasileiros (DD/MM/YYYY).
    Lanca ValueError caso uma string informada nao represente uma data valida.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            return val.astimezone().date()
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        clean = val.strip()
        if not clean:
            return None
        # Tenta date ISO simples (YYYY-MM-DD)
        try:
            return date.fromisoformat(clean)
        except ValueError:
            pass
        # Tenta datetime ISO completo (com time ou timezone)
        try:
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is not None:
                return dt.astimezone().date()
            return dt.date()
        except ValueError:
            pass
        # Tenta formatos textuais comuns
        formats = (
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        )
        for fmt in formats:
            try:
                parsed_dt = datetime.strptime(clean, fmt)
                return parsed_dt.date()
            except ValueError:
                pass
        raise ValueError(f"Formato de data invalido para filtro ERP: '{val}'")
    raise ValueError(f"Tipo invalido para filtro de data: {type(val).__name__}")


class BaseERPAdapter(ABC):
    """Porta Abstrata do Adaptador ERP (Open Posto Architecture).

    Desacopla o cerebro da IA de fornecedores de software de posto.
    Qualquer ERP (WebPosto, Linx, Petros, XPert, LBC) e integrado implementando
    esta interface e retornando entidades canonicas universais de core/domain/.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Nome identificador do adaptador ERP."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Indica se a conexao com a fonte de dados esta ativa."""
        raise NotImplementedError

    @abstractmethod
    def get_recent_sales(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        limit: int = 100,
    ) -> list[UniversalSaleReceipt]:
        """Recupera lista de cupons de venda e itens faturados no periodo.

        Args:
            start_date: Data inicial para filtragem (opcional).
            end_date: Data final para filtragem (opcional).
            limit: Quantidade maxima de registros retornados.

        Returns:
            Lista de transacoes de venda no formato UniversalSaleReceipt.
        """
        raise NotImplementedError

    @abstractmethod
    def get_tank_inventory(self) -> list[UniversalTankReading]:
        """Recupera telemetria atual de estoque dos tanques de combustivel.

        Returns:
            Lista de medicoes no formato UniversalTankReading.
        """
        raise NotImplementedError

    @abstractmethod
    def get_pump_dispenses(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        limit: int = 100,
    ) -> list[UniversalDispenserLog]:
        """Recupera medicoes e diferencas de encerrantes dos bicos dispensadores.

        Args:
            start_date: Data inicial para filtragem (opcional).
            end_date: Data final para filtragem (opcional).
            limit: Quantidade maxima de registros retornados.

        Returns:
            Lista de registros de encerrantes no formato UniversalDispenserLog.
        """
        raise NotImplementedError

    @abstractmethod
    def get_cashier_shifts(
        self,
        target_date: str | date | None = None,
        limit: int = 50,
    ) -> list[UniversalCashierShift]:
        """Recupera fechamentos consolidados de turno de caixa e frentistas.

        Args:
            target_date: Data de referencia contabil (opcional).
            limit: Quantidade maxima de registros retornados.

        Returns:
            Lista de turnos no formato UniversalCashierShift.
        """
        raise NotImplementedError

    @abstractmethod
    def get_product_catalog(
        self,
        filter_term: str | None = None,
        category: str | None = None,
        limit: int = 100,
    ) -> list[UniversalSaleItem]:
        """Recupera catalogo de produtos e combustiveis cadastrados no ERP.

        Args:
            filter_term: Termo de busca por nome ou SKU (opcional).
            category: Categoria ou departamento comercial (opcional).
            limit: Quantidade maxima de registros retornados.

        Returns:
            Lista de itens cadastrais no formato UniversalSaleItem.
        """
        raise NotImplementedError

    @abstractmethod
    def check_health(self) -> dict[str, Any]:
        """Verifica conectividade, latencia e integridade do adaptador.

        Returns:
            Dicionario contendo status, latencia, conectividade e modo operacional.
        """
        raise NotImplementedError

    def connect(self) -> bool:
        """Estabelece conexao com a fonte de dados (implementacao padrao)."""
        return True

    def disconnect(self) -> None:
        """Finaliza recursos de conexao (implementacao padrao)."""

    def __enter__(self) -> Self:
        """Suporte ao gerenciador de contexto (with)."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Finalizacao no gerenciador de contexto."""
        self.disconnect()
