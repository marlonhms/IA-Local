"""AURA Universal Domain Schema (AUDS) & AUPS: Dominio Canonico Universal.

Camada de Dominio Puro do Ecossistema AURA.
Desacoplada de drivers de banco de dados e schemas proprietarios de ERPs.
"""

from core.domain.base import (
    AUDSBaseModel,
    AUPSBaseModel,
    extract_first_present,
    parse_bool_safe,
    parse_date_safe,
    parse_datetime_safe,
    parse_float_safe,
    parse_str_safe,
    strip_accents,
)
from core.domain.cashier import (
    CashMovementType,
    UniversalCashMovement,
)
from core.domain.domain_pack_loader import (
    DomainPackConfig,
    SpecificIntentItem,
    get_active_domain_pack,
    list_available_packs,
    load_all_domain_packs,
    load_domain_pack,
    reset_active_domain_pack,
    set_active_domain_pack,
)
from core.domain.pumps import (
    UniversalPump,
)
from core.domain.sales import (
    PaymentType,
    UniversalPaymentMethod,
    UniversalSaleItem,
)
from core.domain.tanks import (
    UniversalTank,
)
from core.domain.universal_entities import (
    UniversalCashierSession,
    UniversalCashierShift,
    UniversalDispenserLog,
    UniversalEquipmentTelemetry,
    UniversalFinancialSettlement,
    UniversalInventoryNode,
    UniversalSaleReceipt,
    UniversalSaleTransaction,
    UniversalTankReading,
)

__all__ = [
    "AUDSBaseModel",
    "AUPSBaseModel",
    "CashMovementType",
    "DomainPackConfig",
    "PaymentType",
    "SpecificIntentItem",
    "UniversalCashMovement",
    "UniversalCashierSession",
    "UniversalCashierShift",
    "UniversalDispenserLog",
    "UniversalEquipmentTelemetry",
    "UniversalFinancialSettlement",
    "UniversalInventoryNode",
    "UniversalPaymentMethod",
    "UniversalPump",
    "UniversalSaleItem",
    "UniversalSaleReceipt",
    "UniversalSaleTransaction",
    "UniversalTank",
    "UniversalTankReading",
    "extract_first_present",
    "get_active_domain_pack",
    "list_available_packs",
    "load_all_domain_packs",
    "load_domain_pack",
    "parse_bool_safe",
    "parse_date_safe",
    "parse_datetime_safe",
    "parse_float_safe",
    "parse_str_safe",
    "reset_active_domain_pack",
    "set_active_domain_pack",
    "strip_accents",
]


