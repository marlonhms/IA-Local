"""Adaptador de Simulacao What-If para o Domain Pack fuel_convenience (Fase 1).

Implementa BaseDomainSimulator de forma 100% desacoplada de PostoTools e
sem acesso direto a tabelas proprietarias de combustivel.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from core.domain.domain_pack_loader import DomainPackConfig
from core.domain.simulator_contract import UniversalDomainSimulator
from core.simulation.models import BusinessRule


class FuelConvenienceSimulator(UniversalDomainSimulator):
    """Simulador What-If dedicado ao pack_id fuel_convenience."""

    pack_id: str = "fuel_convenience"

    def __init__(self) -> None:
        super().__init__(pack_id="fuel_convenience")

    def extract_yaml_rules(
        self,
        pack_config: DomainPackConfig | None,
        tenant_id: str,
    ) -> list[BusinessRule]:
        """Extrai hard_rules declaradas no YAML sem hardcoding de tabelas legadas."""
        rules = super().extract_yaml_rules(pack_config=pack_config, tenant_id=tenant_id)
        if pack_config is not None:
            vol_tol = pack_config.tolerances.get("regulatory_volume_tolerance_pct")
            if vol_tol is not None:
                rules.append(
                    BusinessRule(
                        rule_id="yaml:fuel_convenience:regulatory_volume_tolerance_pct",
                        tenant_id=tenant_id,
                        pack_id=pack_config.pack_id,
                        rule_key="regulatory_volume_tolerance_pct",
                        metric="volume_variance_pct",
                        operator="<=",
                        threshold_value=float(vol_tol),
                        severity="CRITICAL",
                        status="active",
                        source="yaml",
                        origin="domain_pack_yaml",
                        author="domain_pack",
                        description="Limite regulamentar ANP para variacao volumetrica (%)",
                    )
                )
        return rules


DomainSimulator = FuelConvenienceSimulator


def get_simulator() -> FuelConvenienceSimulator:
    """Factory padrao descoberta pelo DomainSimulatorRegistry."""
    return FuelConvenienceSimulator()


__all__ = ["DomainSimulator", "FuelConvenienceSimulator", "get_simulator"]
