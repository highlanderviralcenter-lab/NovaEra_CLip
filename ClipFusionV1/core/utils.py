"""
ClipFusionV1.core.utils
=======================

Utilitários gerais para o projeto.  Funções auxiliares para medir
duração de vídeos, executar comandos e verificar disponibilidade de
dependências externas.  Todas as chamadas de subprocess são
silenciosas para evitar poluição do terminal.
"""

import logging
import shutil
import subprocess


def get_video_duration(video_path: str) -> float:
    """Obtém a duração total do vídeo em segundos.

    A função tenta primeiro obter a duração com OpenCV (`cv2`).  Caso não
    esteja disponível ou o arquivo não possa ser aberto, tenta usar
    `ffprobe`.  Se nenhuma das ferramentas for encontrada, retorna ``0.0``.

    Parameters
    ----------
    video_path: str
        Caminho para o arquivo de vídeo.

    Returns
    -------
    float
        Duração em segundos.
    """
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            if fps > 0:
                return float(frame_count / fps)
    except Exception:
        pass
    # Fallback para ffprobe se disponível
    if shutil.which("ffprobe"):
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            logging.error(f"Falha ao obter duração via ffprobe: {e}")
    logging.warning("Nenhuma ferramenta disponível para obter duração; retornando 0.0.")
    return 0.0


def cut_video_segment_cv2(input_path: str, start: float, end: float, output_path: str) -> None:
    """Recorta um segmento de vídeo utilizando OpenCV.

    Parameters
    ----------
    input_path: str
        Caminho do vídeo de origem.
    start: float
        Tempo inicial do corte em segundos.
    end: float
        Tempo final do corte em segundos.
    output_path: str
        Caminho do vídeo de saída.
    """
    import cv2  # type: ignore
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Não foi possível abrir {input_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # Utiliza codec mp4v (compatível com .mp4) para maximizar suporte
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps if fps > 0 else 25.0, (width, height))
    start_frame = int(start * fps)
    end_frame = int(end * fps)
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret or frame_idx >= end_frame:
            break
        if frame_idx >= start_frame:
            writer.write(frame)
        frame_idx += 1
    cap.release()
    writer.release()


def command_exists(cmd: str) -> bool:
    """Verifica se um comando está disponível no PATH."""
    return shutil.which(cmd) is not None
