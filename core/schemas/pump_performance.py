"""
Contrato Estruturado Versionado para Auditoria de Pista, Vazão de Bicos & Desempenho de Frentistas (AURA Precision Glass v1.0).
F5-05: Bicos com vazão L/min (< 30 L/min alerta preventivo de filtro), ranking e conversão de aditivada.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from core.schemas.reconciliation import PendingItem, DataSource, RecommendedAction


class PumpPerformanceAssessment(BaseModel):
    """Diagnóstico executivo de pista, vazão e equipe."""
    model_config = ConfigDict(frozen=True)

    status_code: str = Field(..., description="Status geral da pista (ex: OPERACIONAL_NORMAL, ALERTA_PISTA, CRÍTICO_MANUTENÇÃO)")
    severity: Literal["normal", "attention", "critical"] = Field(..., description="Severidade semântica")
    title: str = Field(..., description="Título executivo aprovado")
    limitation: Optional[str] = Field(None, description="Limitação da telemetria ou base de dados")
    badge_label: str = Field(..., description="Rótulo humano para o badge semântico")
    total_bicos_lentos: int = Field(default=0, description="Quantidade de bicos com vazão lenta ou filtro obstruído (< 30 L/min)")
    total_anomalias: int = Field(default=0, description="Quantidade de anomalias detectadas na pista")
    melhor_frentista_nome: Optional[str] = Field(None, description="Nome do frentista com maior produtividade/faturamento")


class PumpPerformanceMetrics(BaseModel):
    """Métricas operacionais e comerciais consolidadas de pista."""
    model_config = ConfigDict(frozen=True)

    total_abastecimentos: int = Field(..., description="Total de abastecimentos auditados")
    total_litros: float = Field(..., description="Volume total comercializado na pista (L)")
    faturamento_total: float = Field(..., description="Faturamento total medido (R$)")
    faturamento_total_cents: int = Field(..., description="Faturamento total em centavos inteiros")
    ticket_medio: float = Field(..., description="Ticket médio da pista (R$)")
    volume_medio: float = Field(..., description="Volume médio por abastecimento (L)")
    taxa_conversao_aditivada_geral_pct: float = Field(..., description="Taxa de conversão de gasolina aditivada da pista (%)")
    classificacao_conversao_aditivada: str = Field(..., description="Classificação de desempenho comercial da aditivada")
    vazao_media_l_min: float = Field(default=35.0, description="Vazão média geral medida na pista (L/min)")
    total_gasolina_comum_litros: float = Field(default=0.0, description="Litros de gasolina comum")
    total_gasolina_aditivada_litros: float = Field(default=0.0, description="Litros de gasolina aditivada")
    total_diesel_litros: float = Field(default=0.0, description="Litros totais de diesel")
    taxa_conversao_diesel_s10_pct: float = Field(default=0.0, description="Percentual de Diesel S10 sobre o diesel total (%)")
    bicos_com_alerta_filtro: int = Field(default=0, description="Quantidade de bicos com alerta preventivo de filtro")
    total_anomalias_detectadas: int = Field(default=0, description="Quantidade de anomalias de pista")


class AttendantPerformanceItem(BaseModel):
    """Produtividade e métricas de desempenho de cada frentista."""
    model_config = ConfigDict(frozen=True)

    matricula: str = Field(..., description="Matrícula do frentista")
    nome: str = Field(..., description="Nome do colaborador")
    total_abastecimentos: int = Field(..., description="Total de abastecimentos realizados")
    total_litros: float = Field(..., description="Volume total abastecido (L)")
    faturamento_reais: float = Field(..., description="Faturamento total do frentista (R$)")
    ticket_medio_reais: float = Field(..., description="Ticket médio do frentista (R$)")
    volume_medio_litros: float = Field(..., description="Volume médio por atendimento (L)")
    conversao_aditivada_pct: float = Field(..., description="Taxa de conversão de aditivada (%)")
    classificacao_conversao: str = Field(..., description="Classificação do índice de aditivada")
    taxa_diesel_s10_pct: float = Field(default=0.0, description="Taxa de conversão de Diesel S10 (%)")
    identificado: bool = Field(default=True, description="True se colaborador autenticado no concentrador")


class NozzleAuditedItem(BaseModel):
    """Auditoria hidráulica individualizada de cada bico abastecedor."""
    model_config = ConfigDict(frozen=True)

    bico: str = Field(..., description="Número/código do bico físico")
    bomba_fisica: str = Field(..., description="Código da bomba física associada")
    tanque: str = Field(..., description="Código do tanque vinculado")
    combustivel: str = Field(..., description="Produto abastecido no bico")
    categoria: str = Field(..., description="Categoria do combustível")
    total_abastecimentos: int = Field(..., description="Total de abastecimentos no período")
    volume_total_litros: float = Field(..., description="Litros totais abastecidos pelo bico")
    vazao_media_l_min: float = Field(..., description="Vazão média medida ou estimada (L/min)")
    status_vazao: str = Field(..., description="Classificação da vazão")
    alerta_filtro_lento: bool = Field(..., description="True se vazão < 30 L/min sugerindo filtro sujo/obstruído")
    recomendacao: str = Field(..., description="Recomendação de manutenção preventiva")
    origem_vazao: str = Field(..., description="Origem da medição")


class PisteAnomalyItem(BaseModel):
    """Anomalia operacional detectada na pista."""
    model_config = ConfigDict(frozen=True)

    controle: str = Field(..., description="Número de controle do abastecimento")
    tipo: str = Field(..., description="Tipo de anomalia")
    gravidade: str = Field(..., description="Gravidade: ALTA, MEDIA, BAIXA")
    bico: str = Field(..., description="Bico do abastecimento")
    data_hora: str = Field(..., description="Data e hora do registro")
    litros: float = Field(..., description="Volume em litros")
    total_reais: float = Field(..., description="Valor total em R$")
    frentista: str = Field(..., description="Colaborador registrado")
    motivo: str = Field(..., description="Descrição e diagnóstico da anomalia")


class PumpPerformanceContext(BaseModel):
    """Contexto da auditoria de pista."""
    model_config = ConfigDict(frozen=True, extra="allow")

    unit_id: str = Field(default="posto_01", description="Unidade do posto")
    queried_at: str = Field(..., description="Timestamp ISO da consulta")
    data_filtro: Optional[str] = Field(None, description="Data auditada")
    turno_filtro: Optional[str] = Field(None, description="Turno auditado")
    frentista_filtro: Optional[str] = Field(None, description="Filtro de frentista aplicado")
    bico_filtro: Optional[str] = Field(None, description="Filtro de bico aplicado")


class PumpPerformanceExplanation(BaseModel):
    """Explicação cognitiva isolada de dados numéricos oficiais."""
    model_config = ConfigDict(frozen=True, extra="allow")

    text: str = Field(..., description="Texto explicativo isolado")


class PumpPerformanceContract(BaseModel):
    """Contrato oficial estruturado versionado para Desempenho de Pista, Vazão & Frentistas."""
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0", description="Versão do contrato")
    response_id: str = Field(..., description="ID único da resposta analítica")
    intent: str = Field(default="pump_performance", description="Intenção canônica")
    context: PumpPerformanceContext = Field(...)
    assessment: PumpPerformanceAssessment = Field(...)
    metrics: PumpPerformanceMetrics = Field(...)
    ranking: List[AttendantPerformanceItem] = Field(default_factory=list)
    nozzles: List[NozzleAuditedItem] = Field(default_factory=list)
    anomalies: List[PisteAnomalyItem] = Field(default_factory=list)
    pending_items: List[PendingItem] = Field(default_factory=list)
    sources: List[DataSource] = Field(default_factory=list)
    recommended_action: RecommendedAction = Field(...)
    explanation: PumpPerformanceExplanation = Field(...)
