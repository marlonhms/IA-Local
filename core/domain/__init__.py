"""AURA Universal Posto Schema (AUPS): Dominio Canonico Universal.

Camada de Dominio Puro do Ecossistema AURA.
Desacoplada de drivers de banco de dados e schemas proprietarios de ERPs.
"""

from core.domain.base import (
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
    UniversalCashierShift,
    UniversalCashMovement,
)
from core.domain.pumps import (
    UniversalDispenserLog,
    UniversalPump,
)
from core.domain.sales import (
    PaymentType,
    UniversalPaymentMethod,
    UniversalSaleItem,
    UniversalSaleReceipt,
)
from core.domain.tanks import (
    UniversalTank,
    UniversalTankReading,
)

__all__ = [
    "AUPSBaseModel",
    "CashMovementType",
    "PaymentType",
    "UniversalCashMovement",
    "UniversalCashierShift",
    "UniversalDispenserLog",
    "UniversalPaymentMethod",
    "UniversalPump",
    "UniversalSaleItem",
    "UniversalSaleReceipt",
    "UniversalTank",
    "UniversalTankReading",
    "extract_first_present",
    "parse_bool_safe",
    "parse_date_safe",
    "parse_datetime_safe",
    "parse_float_safe",
    "parse_str_safe",
    "strip_accents",
]
