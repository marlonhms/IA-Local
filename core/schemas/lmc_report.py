"""
Contrato Estruturado Versionado para Livro de Movimentação de Combustíveis (LMC ANP) (AURA Precision Glass v1.0).
F5-06 & F5-07: Conciliação físico-contábil, abertura, vendas, descargas, escriturado vs físico em régua, tolerância de ±0.6%.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from core.schemas.reconciliation import PendingItem, DataSource, RecommendedAction


class LMCReportAssessment(BaseModel):
    """Diagnóstico da conformidade regulatória fiscal da Portaria ANP 26/1992."""
    model_config = ConfigDict(frozen=True)

    status_geral_anp: str = Field(..., description="CONFORME_ANP ou ALERTA_FORA_TOLERANCIA_ANP")
    severity: Literal["normal", "attention", "critical"] = Field(..., description="Severidade semântica")
    title: str = Field(..., description="Título executivo aprovado")
    limitation: Optional[str] = Field(None, description="Limitação técnica ou fiscal")
    badge_label: str = Field(..., description="Rótulo humano para o badge semântico")
    dentro_tolerancia_geral: bool = Field(..., description="True se a variação geral consolidada estiver dentro de ±0.6%")
    variacao_geral_pct: float = Field(..., description="Variação percentual consolidada sobre o total de vendas (%)")
    total_tanques_alerta: int = Field(default=0, description="Quantidade de tanques que violaram a tolerância da ANP")


class LMCReportMetrics(BaseModel):
    """Métricas físicas e contábeis consolidadas do LMC."""
    model_config = ConfigDict(frozen=True)

    total_tanques_analisados: int = Field(..., description="Total de tanques auditados no período")
    total_tanques_conformes: int = Field(..., description="Tanques operando dentro da margem legal de ±0.6%")
    total_tanques_alerta: int = Field(..., description="Tanques com variação fora da tolerância de ±0.6%")
    total_vendas_litros: float = Field(..., description="Volume total vendido através dos bicos (L)")
    total_recebimentos_litros: float = Field(..., description="Volume total recebido de descargas (L)")
    total_estoque_escriturado_litros: float = Field(..., description="Estoque contábil escriturado (abertura + descargas - vendas) (L)")
    total_estoque_fisico_litros: float = Field(..., description="Estoque físico medido por régua ou telemetria (L)")
    variacao_volumetrica_total_litros: float = Field(..., description="Variação volumétrica líquida apurada (físico - escriturado) (L)")
    variacao_volumetrica_geral_pct: float = Field(..., description="Variação percentual apurada (%)")
    tolerancia_oficial_pct: float = Field(default=0.6, description="Tolerância regulamentar oficial da ANP (±0.6%)")


class LMCTankAuditedItem(BaseModel):
    """Fechamento escriturado e físico individualizado de cada tanque no LMC."""
    model_config = ConfigDict(frozen=True)

    tanque: str = Field(..., description="Código do tanque")
    combustivel: str = Field(..., description="Nome do combustível")
    categoria_combustivel: str = Field(..., description="Categoria canônica")
    codlmc_anp: str = Field(..., description="Código oficial ANP do combustível")
    capacidade_litros: float = Field(..., description="Capacidade máxima do tanque (L)")
    bicos_vinculados: List[str] = Field(default_factory=list, description="Bicos conectados ao tanque")
    total_abastecimentos: int = Field(default=0, description="Quantidade de abastecimentos faturados")
    faturamento_vendas_reais: float = Field(default=0.0, description="Faturamento total das saídas do tanque (R$)")
    estoque_abertura_litros: float = Field(..., description="Estoque de abertura (L)")
    recebimentos_descargas_litros: float = Field(..., description="Descargas recebidas no período (L)")
    vendas_bicos_litros: float = Field(..., description="Volume total vendido nos bicos (L)")
    estoque_escriturado_litros: float = Field(..., description="Estoque contábil escriturado (L)")
    estoque_fisico_medido_litros: float = Field(..., description="Estoque físico medido em régua (L)")
    variacao_litros: float = Field(..., description="Variação em litros (físico - escriturado)")
    variacao_pct: float = Field(..., description="Variação percentual apurada (%)")
    tolerancia_pct: float = Field(default=0.6, description="Margem de tolerância da ANP (0.6%)")
    tolerancia_max_litros: float = Field(..., description="Volume máximo de tolerância em litros")
    dentro_tolerancia: bool = Field(..., description="True se dentro da tolerância legal de ±0.6%")
    status_anp: str = Field(..., description="CONFORME_ANP ou ALERTA_FORA_TOLERANCIA_ANP")
    tipo_variacao: str = Field(..., description="PERDA, SOBRA ou ZERO")
    nome_variacao: str = Field(..., description="Descrição técnica da variação")
    descricao_status: str = Field(..., description="Texto descritivo do status")
    diagnostico: str = Field(..., description="Diagnóstico operacional e recomendação fiscal")


class LMCTankAlertItem(BaseModel):
    """Tanque com quebra ou sobra volumétrica além do limite de tolerância."""
    model_config = ConfigDict(frozen=True)

    tanque: str = Field(..., description="Código do tanque em desconformidade")
    combustivel: str = Field(..., description="Combustível do tanque")
    variacao_litros: float = Field(..., description="Variação volumétrica em litros")
    variacao_pct: float = Field(..., description="Variação percentual apurada (%)")
    tolerancia_max_litros: float = Field(..., description="Tolerância legal permitida (L)")
    diagnostico: str = Field(..., description="Diagnóstico operacional de vazamento ou descarga")


class LMCReportContext(BaseModel):
    """Contexto da auditoria de LMC."""
    model_config = ConfigDict(frozen=True, extra="allow")

    unit_id: str = Field(default="posto_01", description="Unidade do posto")
    queried_at: str = Field(..., description="Timestamp ISO da consulta")
    data_lmc: str = Field(..., description="Data analisada do LMC")
    filtro_combustivel: Optional[str] = Field(None, description="Filtro de combustível")
    filtro_tanque: Optional[str] = Field(None, description="Filtro de tanque")


class LMCReportExplanation(BaseModel):
    """Explicação cognitiva isolada de dados numéricos oficiais."""
    model_config = ConfigDict(frozen=True, extra="allow")

    text: str = Field(..., description="Texto explicativo isolado")


class LMCReportContract(BaseModel):
    """Contrato oficial estruturado versionado para o Relatório LMC da ANP."""
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0", description="Versão do contrato")
    response_id: str = Field(..., description="ID único da resposta analítica")
    intent: str = Field(default="lmc_report", description="Intenção canônica")
    context: LMCReportContext = Field(...)
    assessment: LMCReportAssessment = Field(...)
    metrics: LMCReportMetrics = Field(...)
    tanks: List[LMCTankAuditedItem] = Field(default_factory=list)
    tanques_em_alerta: List[LMCTankAlertItem] = Field(default_factory=list)
    pending_items: List[PendingItem] = Field(default_factory=list)
    sources: List[DataSource] = Field(default_factory=list)
    recommended_action: RecommendedAction = Field(...)
    explanation: LMCReportExplanation = Field(...)
