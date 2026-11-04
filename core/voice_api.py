"""
Rotas de Transcricao de Voz da AURA via Groq Whisper Cloud.
Oferece servico gratuito de alta velocidade (~200ms) e precisao maxima em portugues (pt-BR).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import os
import time
from typing import Any
import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from core.logger import logger

voice_router = APIRouter(prefix="/api/v1/aura/voice", tags=["AURA Voice Transcription"])


class VoiceTranscriptionResponse(BaseModel):
    status: str
    text: str
    duration_ms: float
    model: str


@voice_router.get("/status")
async def voice_service_status() -> dict[str, Any]:
    """Retorna o status do servico de transcricao de voz e presenca da chave Groq."""
    has_key = bool(os.getenv("GROQ_API_KEY", "").strip())
    return {
        "service": "Groq Whisper Cloud (Gratuito)",
        "model": os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo"),
        "has_api_key": has_key,
        "status": "ready" if has_key else "needs_api_key",
        "instructions": (
            "Obtenha sua chave gratuita em https://console.groq.com/keys e adicione GROQ_API_KEY no arquivo .env"
            if not has_key
            else "Servico pronto para transcricao em tempo real."
        ),
    }


@voice_router.post("/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_audio(request: Request) -> VoiceTranscriptionResponse:
    """
    Transcreve audio bruto enviado no corpo do request usando a API gratuita do Groq Whisper.
    Altissima velocidade (~200ms) e total precisao em portugues brasileiro com termos de postos e fiscal.
    Zero dependencias de pacotes multipart adicionais.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Chave GROQ_API_KEY nao configurada no arquivo .env. "
                "Crie sua chave gratuita em https://console.groq.com/keys e adicione no .env da AURA."
            ),
        )

    t0 = time.perf_counter()
    audio_bytes = await request.body()
    if not audio_bytes or len(audio_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buffer de audio vazio ou muito curto para transcricao.",
        )

    content_type = request.headers.get("content-type", "audio/webm").split(";")[0].strip()
    ext_map = {
        "audio/webm": "audio.webm",
        "audio/wav": "audio.wav",
        "audio/x-wav": "audio.wav",
        "audio/ogg": "audio.ogg",
        "audio/mp3": "audio.mp3",
        "audio/mpeg": "audio.mp3",
        "audio/m4a": "audio.m4a",
    }
    filename = ext_map.get(content_type, "audio.webm")

    model_name = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
    url = os.getenv("GROQ_AUDIO_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    files = {
        "file": (filename, audio_bytes, content_type),
    }
    data = {
        "model": model_name,
        "language": "pt",
        "temperature": "0.0",
        "response_format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)

        if resp.status_code != 200:
            logger.error(f"[AURA Voice] Falha na API Groq Whisper ({resp.status_code}): {resp.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erro no provedor Groq Whisper ({resp.status_code}): {resp.text[:200]}",
            )

        result_json = resp.json()
        transcribed_text = str(result_json.get("text", "")).strip()
        elapsed_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            f"[AURA Voice] Transcricao concluida em {elapsed_ms:.1f}ms: '{transcribed_text}'"
        )

        return VoiceTranscriptionResponse(
            status="success",
            text=transcribed_text,
            duration_ms=round(elapsed_ms, 2),
            model=model_name,
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo limite esgotado ao contatar o servico Groq Whisper.",
        )
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        logger.error(f"[AURA Voice] Erro inesperado na transcricao: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha interna ao processar audio: {exc}",
        )
