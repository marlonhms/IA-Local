"""Cliente Unificado Singleton Google GenAI com Keep-Alive HTTP (Carbon Core P1.3).

Substitui o SDK depreciado google-generativeai pelo SDK oficial google-genai,
reutilizando conexoes HTTP/TLS persistentes via httpx para embeddings e geracao
em streaming, eliminando handshakes TLS repetidos e warnings de EOL.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, AsyncIterator

import httpx
from google import genai as google_genai
from google.genai import types as genai_types

logger = logging.getLogger("AuraLLMClient")

_CLIENT_LOCK = threading.Lock()
_CLIENTS_BY_KEY: dict[str, google_genai.Client] = {}
_SYNC_HTTP_CLIENTS: dict[str, httpx.Client] = {}
_ASYNC_HTTP_CLIENTS: dict[str, httpx.AsyncClient] = {}

_DEFAULT_LIMITS = httpx.Limits(
    max_connections=32,
    max_keepalive_connections=16,
    keepalive_expiry=60.0,
)

_TASK_TYPE_MAP: dict[str, str] = {
    "retrieval_query": "RETRIEVAL_QUERY",
    "retrieval_document": "RETRIEVAL_DOCUMENT",
    "semantic_similarity": "SEMANTIC_SIMILARITY",
    "classification": "CLASSIFICATION",
    "clustering": "CLUSTERING",
    "question_answering": "QUESTION_ANSWERING",
    "fact_verification": "FACT_VERIFICATION",
}


def _resolve_api_key(api_key: str | None = None) -> str:
    """Resolve a chave da API Gemini a partir de parametro explicito ou ambiente."""
    if api_key and str(api_key).strip():
        return str(api_key).strip()
    env_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if env_key:
        return env_key
    try:
        from config.settings import GEMINI_API_KEY

        if GEMINI_API_KEY:
            return str(GEMINI_API_KEY).strip()
    except Exception:
        pass
    return ""


def _normalize_task_type(task_type: str | None) -> str | None:
    """Normaliza task_type legado (snake_case minusculo) para enum google-genai."""
    if not task_type:
        return None
    raw = str(task_type).strip()
    if not raw:
        return None
    return _TASK_TYPE_MAP.get(raw.lower(), raw.upper())


def _normalize_model_name(model: str) -> str:
    """Normaliza identificador de modelo para o formato esperado pelo google-genai."""
    m = (model or "").strip()
    if not m:
        return "models/gemini-2.5-flash"
    return m


def get_genai_client(api_key: str | None = None) -> google_genai.Client:
    """Retorna cliente singleton google.genai.Client com pool httpx Keep-Alive."""
    resolved_key = _resolve_api_key(api_key)
    cache_key = resolved_key or "__default__"

    with _CLIENT_LOCK:
        existing = _CLIENTS_BY_KEY.get(cache_key)
        if existing is not None:
            return existing

        sync_http = httpx.Client(
            limits=_DEFAULT_LIMITS,
            timeout=httpx.Timeout(30.0, connect=5.0),
            http2=False,
        )
        async_http = httpx.AsyncClient(
            limits=_DEFAULT_LIMITS,
            timeout=httpx.Timeout(30.0, connect=5.0),
            http2=False,
        )
        http_opts = genai_types.HttpOptions(
            httpx_client=sync_http,
            httpx_async_client=async_http,
        )
        client = google_genai.Client(
            api_key=resolved_key or None,
            http_options=http_opts,
        )
        _SYNC_HTTP_CLIENTS[cache_key] = sync_http
        _ASYNC_HTTP_CLIENTS[cache_key] = async_http
        _CLIENTS_BY_KEY[cache_key] = client
        return client


def get_http_pool_stats() -> dict[str, Any]:
    """Retorna telemetria de reuso do pool HTTP persistente do cliente LLM."""
    with _CLIENT_LOCK:
        return {
            "active_clients": len(_CLIENTS_BY_KEY),
            "sync_pools": len(_SYNC_HTTP_CLIENTS),
            "async_pools": len(_ASYNC_HTTP_CLIENTS),
            "max_connections": _DEFAULT_LIMITS.max_connections,
            "max_keepalive_connections": _DEFAULT_LIMITS.max_keepalive_connections,
        }


def close_genai_clients() -> None:
    """Fecha pools HTTP persistentes e limpa o registro singleton."""
    with _CLIENT_LOCK:
        for http_c in _SYNC_HTTP_CLIENTS.values():
            try:
                http_c.close()
            except Exception:
                pass
        _SYNC_HTTP_CLIENTS.clear()
        _ASYNC_HTTP_CLIENTS.clear()
        _CLIENTS_BY_KEY.clear()


def embed_content(
    model: str,
    content: str | list[str],
    output_dimensionality: int = 768,
    task_type: str | None = None,
    timeout_sec: float | None = None,
    api_key: str | None = None,
) -> list[float] | list[list[float]]:
    """Gera embeddings usando o cliente unificado google-genai com Keep-Alive.

    Retorna list[float] quando content e str, ou list[list[float]] quando content e list[str].
    """
    client = get_genai_client(api_key=api_key)
    norm_task = _normalize_task_type(task_type)
    cfg_kwargs: dict[str, Any] = {}
    if output_dimensionality:
        cfg_kwargs["output_dimensionality"] = int(output_dimensionality)
    if norm_task:
        cfg_kwargs["task_type"] = norm_task
    if timeout_sec is not None and timeout_sec > 0:
        cfg_kwargs["http_options"] = genai_types.HttpOptions(
            timeout=int(max(1000, float(timeout_sec) * 1000))
        )

    config = genai_types.EmbedContentConfig(**cfg_kwargs) if cfg_kwargs else None
    response = client.models.embed_content(
        model=_normalize_model_name(model),
        contents=content,
        config=config,
    )

    embeddings = getattr(response, "embeddings", None) or []
    vectors = [list(getattr(emb, "values", []) or []) for emb in embeddings]
    if isinstance(content, str):
        return vectors[0] if vectors else []
    return vectors


async def generate_content_stream_async(
    model: str,
    contents: Any,
    timeout_sec: float = 25.0,
    api_key: str | None = None,
) -> AsyncIterator[Any]:
    """Executa geracao de conteudo em streaming assincrono via google-genai."""
    client = get_genai_client(api_key=api_key)
    cfg_kwargs: dict[str, Any] = {}
    if timeout_sec and timeout_sec > 0:
        cfg_kwargs["http_options"] = genai_types.HttpOptions(
            timeout=int(max(1000, float(timeout_sec) * 1000))
        )
    config = genai_types.GenerateContentConfig(**cfg_kwargs) if cfg_kwargs else None
    stream = await client.aio.models.generate_content_stream(
        model=_normalize_model_name(model),
        contents=contents,
        config=config,
    )
    async for chunk in stream:
        yield chunk


class CompatGenerativeModel:
    """Shim fino de compatibilidade com a interface legada GenerativeModel.

    Permite que testes unitarios que faziam monkeypatch em aura_engine.genai.GenerativeModel
    continuem operando integralmente sem importar google.generativeai.
    """

    def __init__(self, model_name: str, api_key: str | None = None) -> None:
        self.model_name = model_name
        self._api_key = api_key

    def generate_content(
        self,
        contents: Any,
        stream: bool = False,
        request_options: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> Any:
        timeout_sec = 25.0
        if isinstance(request_options, dict) and request_options.get("timeout"):
            timeout_sec = float(request_options["timeout"])
        client = get_genai_client(api_key=self._api_key)
        config = genai_types.GenerateContentConfig(
            http_options=genai_types.HttpOptions(timeout=int(max(1000, timeout_sec * 1000)))
        )
        model_name = _normalize_model_name(self.model_name)
        if stream:
            return client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config,
            )
        return client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

    async def generate_content_async(
        self,
        contents: Any,
        stream: bool = True,
        request_options: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> Any:
        timeout_sec = 25.0
        if isinstance(request_options, dict) and request_options.get("timeout"):
            timeout_sec = float(request_options["timeout"])

        if stream:
            return generate_content_stream_async(
                model=self.model_name,
                contents=contents,
                timeout_sec=timeout_sec,
                api_key=self._api_key,
            )

        client = get_genai_client(api_key=self._api_key)
        config = genai_types.GenerateContentConfig(
            http_options=genai_types.HttpOptions(timeout=int(max(1000, timeout_sec * 1000)))
        )
        return await client.aio.models.generate_content(
            model=_normalize_model_name(self.model_name),
            contents=contents,
            config=config,
        )


class CompatGenAIShim:
    """Fachada leve exposta como 'genai' nos modulos migrados para retrocompatibilidade."""

    GenerativeModel = CompatGenerativeModel

    def configure(self, api_key: str | None = None, **_kwargs: Any) -> None:
        if api_key:
            get_genai_client(api_key=api_key)

    def embed_content(
        self,
        model: str,
        content: str | list[str],
        output_dimensionality: int = 768,
        task_type: str | None = None,
        request_options: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        timeout_sec = None
        if isinstance(request_options, dict) and request_options.get("timeout"):
            timeout_sec = float(request_options["timeout"])
        vec = embed_content(
            model=model,
            content=content,
            output_dimensionality=output_dimensionality,
            task_type=task_type,
            timeout_sec=timeout_sec,
        )
        return {"embedding": vec}


__all__ = [
    "CompatGenAIShim",
    "CompatGenerativeModel",
    "close_genai_clients",
    "embed_content",
    "generate_content_stream_async",
    "get_genai_client",
    "get_http_pool_stats",
]
