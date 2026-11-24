"""Carregador de Cartuchos de Negocio: Domain Packs YAML (AUDS).

Permite carregar configuracoes verticais declarativas para transformar a AURA
em um motor horizontal desacoplado para postos, supermercados, farmacias e atacados.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import contextvars
import logging
import threading
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger("DomainPackLoader")

DEFAULT_DOMAIN_PACKS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "config" / "domain_packs"
)


class SpecificIntentItem(BaseModel):
    """Definicao de intencao especifica da vertical."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(description="Identificador da intencao especifica")
    descricao: str = Field(default="", description="Descricao operacional da intencao")
    keywords: list[str] = Field(default_factory=list, description="Palavras-chave e termos lexicos")


class DomainPackConfig(BaseModel):
    """Configuracao estruturada de um Domain Pack de vertical de negocio."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    pack_id: str = Field(description="Identificador unico do cartucho (ex: fuel_convenience)")
    pack_name: str = Field(description="Nome comercial amigavel do domain pack")
    vertical: str = Field(description="Vertical de mercado (fuel_retail, supermarket_retail, wholesale_distribution)")
    version: str = Field(default="1.0.0", description="Versao do domain pack")
    description: str = Field(default="", description="Descricao do dominio de aplicacao")
    vocabulary: dict[str, str] = Field(
        default_factory=dict,
        description="Terminologia e sinonimos especificos do nicho de atuacao",
    )
    tolerances: dict[str, float] = Field(
        default_factory=dict,
        description="Limiares operacionais, tolerancias regulamentares e parametros de lote",
    )
    intent_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Mapeamento de intencoes operacionais universais para intencoes verticais",
    )
    specific_intents: list[SpecificIntentItem] = Field(
        default_factory=list,
        description="Lista de intencoes operacionais especificas da vertical",
    )

    @field_validator("tolerances", mode="before")
    @classmethod
    def _validate_tolerances(cls, v: Any) -> dict[str, float]:
        if not isinstance(v, dict):
            return {}
        cleaned: dict[str, float] = {}
        for k, val in v.items():
            if isinstance(val, (int, float)):
                cleaned[str(k)] = float(val)
            elif isinstance(val, str):
                s = val.strip().replace("%", "").strip()
                if "," in s and "." in s:
                    s = s.replace(".", "").replace(",", ".")
                elif "," in s:
                    s = s.replace(",", ".")
                try:
                    cleaned[str(k)] = float(s)
                except ValueError:
                    cleaned[str(k)] = 0.0
            else:
                try:
                    cleaned[str(k)] = float(val)
                except (ValueError, TypeError):
                    cleaned[str(k)] = 0.0
        return cleaned

    def resolve_intent(self, universal_intent: str) -> str:
        """Retorna o nome especializado da intencao na vertical ou o proprio nome universal."""
        return self.intent_mappings.get(universal_intent, universal_intent)

    def get_tolerance(self, key: str, default: float = 0.0) -> float:
        """Retorna o valor de tolerancia configurado ou o default seguro."""
        return self.tolerances.get(key, default)

    def get_vocabulary_term(self, concept: str, default: str = "") -> str:
        """Retorna o termo contextualizado para o conceito pedido."""
        return self.vocabulary.get(concept, default or concept)


def _resolve_pack_path(pack_ref: str | Path, packs_dir: Path) -> Path:
    """Localiza o arquivo YAML a partir de um path direto ou identificador de pack."""
    candidate = Path(pack_ref)
    if candidate.is_file():
        return candidate

    # Tenta resolver dentro de packs_dir com ou sem prefixo 'pack_' e extensao .yaml
    clean_ref = str(pack_ref).strip()
    direct_in_dir = packs_dir / clean_ref
    if direct_in_dir.is_file():
        return direct_in_dir

    yaml_in_dir = packs_dir / f"{clean_ref}.yaml"
    if yaml_in_dir.is_file():
        return yaml_in_dir

    pack_prefix_yaml = packs_dir / f"pack_{clean_ref}.yaml"
    if pack_prefix_yaml.is_file():
        return pack_prefix_yaml

    raise FileNotFoundError(
        f"Domain Pack '{pack_ref}' nao localizado no diretorio {packs_dir}"
    )


def load_domain_pack(
    path_or_id: str | Path,
    packs_dir: str | Path | None = None,
) -> DomainPackConfig:
    """Carrega e valida um Domain Pack a partir de arquivo YAML."""
    base_dir = Path(packs_dir) if packs_dir else DEFAULT_DOMAIN_PACKS_DIR
    resolved_path = _resolve_pack_path(path_or_id, base_dir)

    raw_text = resolved_path.read_text(encoding="utf-8")
    data: Any = yaml.safe_load(raw_text)

    if not isinstance(data, dict):
        raise TypeError(
            f"Arquivo de Domain Pack invalido (deve ser dicionario YAML): {resolved_path}"
        )

    return DomainPackConfig.model_validate(data)


def list_available_packs(packs_dir: str | Path | None = None) -> list[str]:
    """Lista todos os identificadores de Domain Packs disponiveis no diretorio de configuracao."""
    base_dir = Path(packs_dir) if packs_dir else DEFAULT_DOMAIN_PACKS_DIR
    if not base_dir.exists() or not base_dir.is_dir():
        return []

    pack_ids: list[str] = []
    for yaml_path in sorted(base_dir.glob("*.yaml")):
        try:
            pack = load_domain_pack(yaml_path, packs_dir=base_dir)
            pack_ids.append(pack.pack_id)
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Falha ao carregar pack em %s: %s", yaml_path.name, exc)

    return pack_ids


def load_all_domain_packs(
    packs_dir: str | Path | None = None,
) -> dict[str, DomainPackConfig]:
    """Carrega todos os Domain Packs disponiveis em um dicionario indexado por pack_id."""
    base_dir = Path(packs_dir) if packs_dir else DEFAULT_DOMAIN_PACKS_DIR
    if not base_dir.exists() or not base_dir.is_dir():
        return {}

    loaded: dict[str, DomainPackConfig] = {}
    for yaml_path in sorted(base_dir.glob("*.yaml")):
        try:
            pack = load_domain_pack(yaml_path, packs_dir=base_dir)
            loaded[pack.pack_id] = pack
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Ignorando pack invalido em %s: %s", yaml_path.name, exc)

    return loaded


_PACK_CACHE_LOCK = threading.Lock()
_PACK_CACHE: dict[tuple[str, str], DomainPackConfig] = {}

_ACTIVE_PACK_VAR: contextvars.ContextVar[DomainPackConfig | None] = contextvars.ContextVar(
    "aura_active_domain_pack",
    default=None,
)


def _load_domain_pack_cached(
    pack_id: str,
    packs_dir: str | Path | None = None,
) -> DomainPackConfig:
    """Carrega Domain Pack imutavel com cache thread-safe por (packs_dir, pack_id)."""
    base_dir = Path(packs_dir).resolve() if packs_dir else DEFAULT_DOMAIN_PACKS_DIR.resolve()
    cache_key = (str(base_dir), str(pack_id).strip())
    with _PACK_CACHE_LOCK:
        cached = _PACK_CACHE.get(cache_key)
    if cached is not None:
        return cached
    loaded = load_domain_pack(pack_id, packs_dir=base_dir)
    with _PACK_CACHE_LOCK:
        _PACK_CACHE[cache_key] = loaded
    return loaded


def get_active_domain_pack(
    pack_id: str | None = None,
    packs_dir: str | Path | None = None,
) -> DomainPackConfig:
    """
    Retorna o Domain Pack ativo isolado por requisicao via ContextVar (Carbon Core P0.4).
    Nao muta _ACTIVE_PACK_VAR fora de DomainPackContext / set_active_domain_pack.
    Padrao retrocompativel: fuel_convenience.
    """
    current = _ACTIVE_PACK_VAR.get()
    if pack_id is None:
        if current is not None:
            return current
        return _load_domain_pack_cached("fuel_convenience", packs_dir=packs_dir)

    if current is not None and current.pack_id == pack_id and packs_dir is None:
        return current

    return _load_domain_pack_cached(pack_id, packs_dir=packs_dir)


def peek_active_domain_pack() -> DomainPackConfig | None:
    """Retorna o Domain Pack definido explicitamente no ContextVar atual, ou None."""
    return _ACTIVE_PACK_VAR.get()


def set_active_domain_pack(
    pack: DomainPackConfig | str,
    packs_dir: str | Path | None = None,
) -> contextvars.Token[DomainPackConfig | None]:
    """Define o Domain Pack ativo no ContextVar da coroutine/thread atual e retorna o Token."""
    resolved = pack if isinstance(pack, DomainPackConfig) else _load_domain_pack_cached(pack, packs_dir=packs_dir)
    return _ACTIVE_PACK_VAR.set(resolved)


def reset_active_domain_pack(
    token: contextvars.Token[DomainPackConfig | None] | None = None,
) -> None:
    """Reseta o Domain Pack ativo no ContextVar atual (via Token ou limpando para None)."""
    if token is not None:
        _ACTIVE_PACK_VAR.reset(token)
    else:
        _ACTIVE_PACK_VAR.set(None)


class DomainPackContext:
    """
    Gerenciador de contexto sync/async baseado em ContextVar para isolamento multi-tenant
    de Domain Packs sem race conditions entre requisicoes concorrentes (Carbon Core P0.4).
    """

    def __init__(
        self,
        pack: DomainPackConfig | str | None = None,
        packs_dir: str | Path | None = None,
    ) -> None:
        if pack is None:
            self.pack = get_active_domain_pack(packs_dir=packs_dir)
        elif isinstance(pack, DomainPackConfig):
            self.pack = pack
        else:
            self.pack = _load_domain_pack_cached(pack, packs_dir=packs_dir)
        self._token: contextvars.Token[DomainPackConfig | None] | None = None

    def __enter__(self) -> DomainPackConfig:
        self._token = _ACTIVE_PACK_VAR.set(self.pack)
        return self.pack

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._token is not None:
            _ACTIVE_PACK_VAR.reset(self._token)
            self._token = None

    async def __aenter__(self) -> DomainPackConfig:
        return self.__enter__()

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)


__all__ = [
    "DEFAULT_DOMAIN_PACKS_DIR",
    "DomainPackConfig",
    "DomainPackContext",
    "SpecificIntentItem",
    "get_active_domain_pack",
    "list_available_packs",
    "load_all_domain_packs",
    "load_domain_pack",
    "peek_active_domain_pack",
    "reset_active_domain_pack",
    "set_active_domain_pack",
]
