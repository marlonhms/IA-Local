"""
Schema Pydantic de Conformidade, Titularidade de Dados e Opt-In Tecnico (LGPD & Clean Room).
Modelagem canonica para comprovacao juridica de autorizacao de leitura e interoperabilidade de postos.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComplianceOptInStatus(BaseModel):
    """
    Status canonico de opt-in de interoperabilidade e titularidade de dados.
    Comprova o consentimento formal do estabelecimento controlador conforme LGPD e Lei de Software.
    """
    model_config = ConfigDict(frozen=True)

    loja_cnpj: str = Field(..., min_length=1, description="CNPJ do estabelecimento comercial ou posto revendedor")
    razao_social: str = Field(..., min_length=1, description="Razao Social do estabelecimento controlador dos dados")
    aceite_interoperabilidade_em: str = Field(
        ...,
        description="Timestamp ISO-8601 da data e hora em que o aceite formal foi concedido"
    )
    versao_termo: str = Field(
        default="1.1",
        min_length=1,
        description="Versao do termo juridico de interoperabilidade aceito pelo lojista"
    )
    status: str = Field(
        default="active",
        description="Estado atual do opt-in: active, accepted, pending ou revoked"
    )
    assinado_por: str = Field(
        ...,
        min_length=1,
        description="Nome completo e qualificacao do representante legal que formalizou o opt-in"
    )
    hash_termo: str = Field(
        ...,
        min_length=1,
        description="Digest criptografico SHA-256 do conteudo do termo juridico no momento do aceite"
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Metadados complementares de auditoria, IP de origem e seguranca"
    )

    @field_validator("loja_cnpj", "razao_social", "assinado_por", "hash_termo", mode="before")
    @classmethod
    def _validate_non_empty(cls, v: Any) -> str:
        """Garante que strings obrigatorias nao sejam vazias ou compostas apenas de espacos."""
        s = str(v).strip()
        if not s:
            raise ValueError("Campo obrigatorio nao pode ser vazio ou conter apenas espacos em branco")
        return s

    @field_validator("aceite_interoperabilidade_em", mode="before")
    @classmethod
    def _coerce_datetime(cls, v: Any) -> str:
        """Converte instancias de datetime para string ISO-8601 canonicamente."""
        if isinstance(v, datetime):
            return v.isoformat()
        s = str(v).strip()
        if not s:
            raise ValueError("aceite_interoperabilidade_em nao pode ser vazio")
        return s

    @property
    def is_active(self) -> bool:
        """Retorna True se o consentimento do lojista estiver formalmente ativo."""
        return self.status.strip().lower() in ("active", "accepted", "ativo", "aceito")

    @property
    def cnpj_limpo(self) -> str:
        """Retorna apenas os digitos numericos do CNPJ para comparacoes uniformes."""
        return re.sub(r"\D", "", self.loja_cnpj)


class ComplianceVerificationResult(BaseModel):
    """
    Resultado detalhado da verificacao de conformidade e opt-in tecnico da AURA.
    Avalia integridade do termo, correspondencia de hash, modo read-only e isolamento AUPS.
    """
    model_config = ConfigDict(frozen=True)

    compliant: bool = Field(..., description="Indica se o estabelecimento esta 100% conforme")
    loja_cnpj: str = Field(..., description="CNPJ avaliado na verificacao")
    razao_social: str | None = Field(None, description="Razao social do estabelecimento registrado")
    versao_termo: str | None = Field(None, description="Versao do termo registrado")
    status: str = Field(..., description="Status do opt-in (active, pending, revoked, missing)")
    aceite_interoperabilidade_em: str | None = Field(None, description="Timestamp do aceite")
    assinado_por: str | None = Field(None, description="Nome do assinante formal")
    hash_termo: str | None = Field(None, description="Hash SHA-256 registrado no opt-in")
    hash_atual_termo: str = Field(..., description="Hash SHA-256 atual do arquivo fisico do termo")
    hash_confere: bool = Field(..., description="Se o hash assinado confere com o termo atual")
    garantia_leitura_exclusiva: bool = Field(
        default=True,
        description="Garantia de que a AURA opera exclusivamente com role aura_service_ro em READ ONLY"
    )
    isolamento_aups: bool = Field(
        default=True,
        description="Garantia de que o core opera exclusivamente com entidades universais AUPS"
    )
    driver_level_protection: bool = Field(
        default=True,
        description="Garantia de blindagem em nivel de driver (read_only, statement_timeout, lock_timeout)"
    )
    mensagem: str = Field(..., description="Mensagem executiva de status da conformidade")
