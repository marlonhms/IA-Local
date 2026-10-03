"""
Contratos Pydantic v2 para Arquitetura de Rede Multi-Filial (RAG Hierárquico & MapReduce).
Garante tipagem estrita, validação determinística e serialização ultracompacta (economia >85% de tokens).
"""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class BranchStatus(str, Enum):
    """Estado de conectividade do contêiner Docker da filial."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class MetricUrgency(str, Enum):
    """Grau de urgência operacional para ranqueamento gerencial da rede."""
    CRITICO = "Critico"
    ALERTA = "Alerta"
    REGULAR = "Regular"
    CONFORTAVEL = "Confortavel"


class BranchConfig(BaseModel):
    """Configuração de catálogo e roteamento de uma filial de borda."""
    model_config = ConfigDict(frozen=True)

    filial_id: str = Field(..., description="Identificador único da filial (ex: posto_centro_01)")
    filial_nome: str = Field(..., description="Nome de exibição da filial (ex: Posto Centro)")
    endpoint_url: str = Field(..., description="URL base da API do contêiner Docker local")
    ativo: bool = Field(default=True, description="Se a filial está ativa na esteira de monitoramento")
    timeout_segundos: float = Field(default=5.0, ge=0.5, le=30.0, description="SLA de timeout individual em segundos")


class NetworkQueryRequest(BaseModel):
    """Requisição enviada pelo usuário ao Maestro Central."""
    query: str = Field(..., min_length=2, description="Pergunta em linguagem natural do gestor")
    escopo: str = Field(default="global", description="'global' para toda a rede ou 'filial_id' para filial específica")
    combustivel: Optional[str] = Field(default=None, description="Filtro opcional de combustível (ex: Gasolina Comum)")
    timeout_global_s: float = Field(default=5.0, ge=1.0, le=30.0, description="Timeout máximo para Fan-Out")


class BranchProbeRequest(BaseModel):
    """Gatilho enxuto despachado via Fan-Out pelo Maestro para a borda."""
    query_id: str = Field(..., description="UUID da consulta de rede")
    tipo_metrica: str = Field(default="estoque_tanques", description="Tipo de métrica a auditar na borda")
    combustivel: Optional[str] = Field(default=None, description="Filtro opcional de combustível")
    filtro_data: Optional[str] = Field(default=None, description="Data da consulta no formato YYYY-MM-DD")


class BranchMetricPayload(BaseModel):
    """Payload estruturado retornado pelo Edge Worker ou pelo Fallback de Timeout."""
    filial_id: str = Field(..., description="Identificador da filial")
    filial_nome: str = Field(..., description="Nome amigável da filial")
    status_conexao: BranchStatus = Field(default=BranchStatus.ONLINE, description="Status de conectividade do nó")
    combustivel: Optional[str] = Field(default=None, description="Combustível auditado")
    saldo_litros: Optional[float] = Field(default=None, ge=0.0, description="Saldo atual volumétrico")
    capacidade_litros: Optional[float] = Field(default=None, ge=0.0, description="Capacidade máxima do tanque")
    status: MetricUrgency = Field(default=MetricUrgency.REGULAR, description="Grau de urgência operacional")
    autonomia_horas: Optional[float] = Field(default=None, ge=0.0, description="Autonomia estimada em horas")
    consumo_medio_dia: Optional[float] = Field(default=None, ge=0.0, description="Consumo médio diário em litros")
    alerta_fim_de_semana: bool = Field(default=False, description="Flag se o combustível acaba antes de segunda-feira")
    aviso: Optional[str] = Field(default=None, description="Mensagem de contingência se offline ou com falha")
    tempo_resposta_ms: float = Field(default=0.0, ge=0.0, description="Tempo de round-trip em milissegundos")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp UTC da resposta")

    @classmethod
    def criar_fallback_offline(cls, config: BranchConfig, aviso: Optional[str] = None, tempo_ms: float = 5000.0) -> BranchMetricPayload:
        """Cria payload de contingência para filial inacessível (Graceful Degradation)."""
        msg = aviso or f"Filial {config.filial_nome} offline (sem resposta em {config.timeout_segundos:.1f}s), dados não incluídos."
        return cls(
            filial_id=config.filial_id,
            filial_nome=config.filial_nome,
            status_conexao=BranchStatus.OFFLINE,
            status=MetricUrgency.ALERTA,
            aviso=msg,
            tempo_resposta_ms=tempo_ms,
        )


class NetworkConsolidatedReport(BaseModel):
    """Relatório final pós-Fan-In consolidado pelo Maestro e Agente Sintetizador."""
    total_filiais: int = Field(..., ge=0, description="Total de filiais consultadas")
    filiais_online: int = Field(..., ge=0, description="Total de filiais com resposta íntegra")
    filiais_offline: int = Field(..., ge=0, description="Total de filiais em contingência/offline")
    payloads: List[BranchMetricPayload] = Field(default_factory=list, description="Lista de payloads individuais")
    avisos_degradacao: List[str] = Field(default_factory=list, description="Lista de avisos de nós inacessíveis")
    ranking_criticidade: List[str] = Field(default_factory=list, description="IDs ordenados da mais crítica para mais estável")
    resumo_executivo: Optional[str] = Field(default=None, description="Texto de síntese executiva gerado via LLM")
    latencia_total_ms: float = Field(default=0.0, ge=0.0, description="Tempo total do Fan-Out e agregação")
    economia_tokens_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentual estimado de economia de tokens")
    gerado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def rank_branches_by_urgency(payloads: List[BranchMetricPayload]) -> List[str]:
    """
    Ranqueia filiais ordenando da maior urgência para maior estabilidade:
    1º Nós ONLINE com status CRITICO (menor autonomia_horas primeiro)
    2º Nós ONLINE com status ALERTA
    3º Nós OFFLINE / TIMEOUT
    4º Nós ONLINE com status REGULAR
    5º Nós ONLINE com status CONFORTAVEL
    """
    urgency_weights = {
        MetricUrgency.CRITICO: 0,
        MetricUrgency.ALERTA: 1,
        MetricUrgency.REGULAR: 3,
        MetricUrgency.CONFORTAVEL: 4,
    }

    def sort_key(p: BranchMetricPayload):
        if p.status_conexao != BranchStatus.ONLINE:
            # Nós offline ficam na faixa de prioridade de atenção (peso 2)
            return (2, 999999.0)
        weight = urgency_weights.get(p.status, 3)
        autonomia = p.autonomia_horas if p.autonomia_horas is not None else 999999.0
        return (weight, autonomia)

    sorted_payloads = sorted(payloads, key=sort_key)
    return [p.filial_id for p in sorted_payloads]


def calculate_token_savings(payloads: List[BranchMetricPayload], baseline_tokens_per_branch: int = 1000) -> float:
    """
    Calcula a economia real de tokens comparando o payload JSON compacto
    com o envio convencional de texto prolixo de cada nó.
    """
    if not payloads:
        return 0.0

    total_baseline_tokens = len(payloads) * baseline_tokens_per_branch
    # Cada 4 caracteres em JSON compacto equivalem aproximadamente a 1 token LLM
    json_chars = sum(len(p.model_dump_json(exclude_none=True)) for p in payloads)
    estimated_json_tokens = max(1, json_chars // 4)

    savings = max(0.0, (1.0 - (estimated_json_tokens / total_baseline_tokens)) * 100.0)
    return round(savings, 2)
