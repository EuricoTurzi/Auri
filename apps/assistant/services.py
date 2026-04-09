"""
Serviços do módulo assistant.

Responsabilidades:
- Transcrição de áudio via OpenAI Whisper API
"""

import openai
from django.conf import settings


class ServiceError(Exception):
    """Exceção base para erros de serviço do módulo assistant."""
    pass


def transcribe_audio(audio_file) -> str:
    """
    Recebe um arquivo de áudio (UploadedFile do Django), envia para a API
    OpenAI Whisper e retorna o texto transcrito.

    Args:
        audio_file: Objeto de arquivo compatível com o SDK OpenAI (UploadedFile,
                    arquivo aberto em modo binário ou tupla (nome, bytes, mime-type)).

    Returns:
        str: Texto transcrito pelo modelo Whisper.

    Raises:
        ServiceError: Quando a API do OpenAI retorna erro ou a chave está ausente.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ServiceError(
            "OPENAI_API_KEY não configurada. Defina a variável de ambiente no arquivo .env."
        )

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return response.text
    except openai.AuthenticationError as exc:
        raise ServiceError(f"Chave de API inválida ou expirada: {exc}") from exc
    except openai.RateLimitError as exc:
        raise ServiceError(f"Limite de requisições atingido na API OpenAI: {exc}") from exc
    except openai.APIConnectionError as exc:
        raise ServiceError(f"Falha de conexão com a API OpenAI: {exc}") from exc
    except openai.OpenAIError as exc:
        raise ServiceError(f"Erro inesperado ao chamar a API OpenAI Whisper: {exc}") from exc
