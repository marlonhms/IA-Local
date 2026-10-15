"""
Contrato Estruturado Versionado para Investigacao Forense de Causa-Raiz (RCA Forense v1.0).
Modela laudos consultivos Human-in-the-Loop (HITL) para quebras e divergencias de postos.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class RCAEvidenceItem(BaseModel):
    """Evidencia factual rastreavel identificada nas tabelas do ERP."""
    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(..., description="Identificador unico da evidencia (ex: EV-001)")
    pattern_type: str = Field(
        ...,
        description="Tipo do padrao: abastecimento_orfao, estorno_descompassado, afericao_inmetro_20l, inversao_pagamento, divergencia_encerrante"
    )
    source_table: Literal[
        "abastecimentos", "fechabomba", "fechacaixa", "pedido", "itemped", "tanques",
        "dispenser_logs", "cashier_shifts", "sales_receipts", "tank_readings",
        "encerrantes_pista", "caixas_turno", "vendas_pdv", "estoque_tanques"
    ] = Field(
        ...,
        description="Origem dos dados ou entidade canonica"
    )
    description: str = Field(..., description="Descricao factual detalhada da ocorrencia")
    occurred_at: Optional[str] = Field(None, description="Horario ou timestamp em que o fato ocorreu")
    amount_reais: float = Field(default=0.0, description="Impacto financeiro apurado em R$")
    volume_liters: Optional[float] = Field(None, description="Volume volumetrico associado em litros")
    bico: Optional[str] = Field(None, description="Bico fisico onde ocorreu o evento")
    tanque: Optional[str] = Field(None, description="Tanque fisico associado")
    combustivel: Optional[str] = Field(None, description="Nome do combustivel ou produto")
    operador: Optional[str] = Field(None, description="Nome ou matricula do operador/frentista envolvido")
    pdv: Optional[str] = Field(None, description="Terminal PDV do lancamento")
    cupom: Optional[str] = Field(None, description="Numero do cupom fiscal ou pedido vinculado")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais da evidencia")


class RCAHypothesis(BaseModel):
    """Hipotese de causa-raiz diagnosticada matematicamente pela IA."""
    model_config = ConfigDict(frozen=True)

    hypothesis_id: str = Field(..., description="Identificador unico da hipotese (ex: HYP-01)")
    pattern_code: Literal[
        "ABASTECIMENTO_ORFAO",
        "ESTORNO_DESCOMPASSADO",
        "AFERICAO_INMETRO_NAO_LANCADA",
        "INVERSAO_FORMA_PAGAMENTO",
        "DIVERGENCIA_OPERACIONAL_GENERICA"
    ] = Field(..., description="Codigo canonico do padrao matematico")
    title: str = Field(..., description="Titulo executivo da hipotese explicativa")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Grau de certeza matematica da hipotese (0.0 a 1.0)"
    )
    explained_amount_reais: float = Field(
        ...,
        description="Valor monetario explicado por esta hipotese em R$"
    )
    explained_volume_liters: Optional[float] = Field(
        None,
        description="Volume em litros explicado por esta hipotese"
    )
    severity: Literal["info", "low", "medium", "high", "critical"] = Field(
        default="medium",
        description="Severidade operacional da ocorrencia"
    )
    summary: str = Field(..., description="Explicacao direta e compreensivel para o gestor")
    evidences: List[RCAEvidenceItem] = Field(
        default_factory=list,
        description="Evidencias factuais que sustentam a hipotese"
    )
    recommended_action: str = Field(
        ...,
        description="Acao recomendada para o gestor verificar no posto"
    )


class RCARecommendation(BaseModel):
    """Recomendacao de verificacao ou procedimento operacional seguro (HITL)."""
    model_config = ConfigDict(frozen=True)

    action_type: Literal["human_audit", "voucher_action", "pos_check", "inmetro_check"] = Field(
        default="human_audit",
        description="Categoria da acao recomendada"
    )
    title: str = Field(..., description="Titulo da recomendacao")
    description: str = Field(..., description="Instrucao detalhada de procedimento no posto")
    required_role: str = Field(
        default="Gerente de Pista / Operador",
        description="Perfil de usuario responsavel pela verificacao"
    )
    action_button_label: Optional[str] = Field(None, description="Rotulo do botao de acao no GenUI")
    action_intent: Optional[str] = Field(None, description="Intencao chamada ao clicar no botao")
    action_params: Optional[Dict[str, Any]] = Field(None, description="Parametros da acao")


class RCAReport(BaseModel):
    """Laudo pericial forense completo de Causa-Raiz (RCA)."""
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default="1.0", description="Versao do schema do contrato")
    report_id: str = Field(..., description="Identificador unico do laudo RCA")
    intent: str = Field(default="investigar_causa_raiz", description="Intencao canonica")
    generated_at: str = Field(..., description="Timestamp ISO-8601 da geracao da pericia")
    unit_id: str = Field(default="posto_01", description="Identificador da unidade/filial auditada")
    target_date: str = Field(..., description="Data efetiva auditada (YYYY-MM-DD)")
    target_shift: Optional[str] = Field(None, description="Turno auditado ou None para todos")
    target_caixa_id: Optional[int] = Field(None, description="ID do caixa auditado ou None")
    target_bico: Optional[str] = Field(None, description="Bico auditado ou None")
    cash_tolerance_reais: float = Field(
        default=50.0,
        description="Tolerancia contratual de quebra antes de considerar anomalia"
    )
    total_divergence_reais: float = Field(
        ...,
        description="Diferenca total financeira apurada no fechamento em R$"
    )
    divergence_type: Literal["furo_caixa", "sobra_caixa", "divergencia_pista", "conforme"] = Field(
        ...,
        description="Classificacao da divergencia contabil"
    )
    total_explained_reais: float = Field(
        default=0.0,
        description="Soma dos valores financeiros explicados pelas hipoteses encontradas"
    )
    unexplained_reais: float = Field(
        default=0.0,
        description="Saldo remanescente de diferenca ainda nao explicado"
    )
    confidence_overall: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confianca global ponderada do diagnostico pericial (0.0 a 1.0)"
    )
    hypotheses: List[RCAHypothesis] = Field(
        default_factory=list,
        description="Lista de hipoteses explicativas detectadas pela IA"
    )
    recommendations: List[RCARecommendation] = Field(
        default_factory=list,
        description="Recomendacoes acionaveis para a equipe de gestao"
    )
    human_in_the_loop: bool = Field(
        default=True,
        description="Garante que este laudo e estritamente consultivo e requer validacao humana"
    )
    execution_mode: Literal["on_demand"] = Field(
        default="on_demand",
        description="Execucao sob demanda requisitada pelo gestor"
    )
    summary_markdown: str = Field(
        ...,
        description="Sintese executiva em Markdown para exibicao imediata no chat"
    )
