"""
ClipFusionV1.core.asr
=====================

Módulo responsável pela transcrição de arquivos de áudio/vídeo.
Por padrão utiliza o ``openai-whisper`` quando disponível, mas
fornece um fallback simples para ambientes sem modelos de ASR
instalados.  O objetivo é garantir que a pipeline continue
funcionando em notebooks com recursos limitados sem travar.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path


def _extract_audio(video_path: str, output_wav: str) -> None:
    """Extrai a trilha de áudio de um vídeo usando ffmpeg.

    Parameters
    ----------
    video_path: str
        Caminho para o vídeo de entrada.
    output_wav: str
        Caminho para o arquivo .wav de saída.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        output_wav,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg não encontrado. Instale ffmpeg para extrair áudio."
        )


def transcribe(video_path: str) -> str:
    try:
        import whisper  # type: ignore
        model = whisper.load_model("base")
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "audio.wav")
            try:
                _extract_audio(video_path, wav_path)
            except subprocess.CalledProcessError:
                logging.warning("Falha ao extrair áudio; usando transcrição fictícia.")
                return "Transcrição fictícia: conte o conteúdo do vídeo manualmente."
            result = model.transcribe(wav_path)
        return result.get("text", "")
    except ImportError:
        logging.warning("Biblioteca whisper não encontrada. Usando transcrição fictícia.")
        return "Transcrição fictícia: conte o conteúdo do vídeo manualmente."
