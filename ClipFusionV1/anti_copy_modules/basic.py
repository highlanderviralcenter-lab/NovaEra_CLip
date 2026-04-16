"""
Implementação do nível Básico de proteção anti‑copyright.

Aplica um zoom sutil para alterar o enquadramento, ajusta contraste e
brilho e remove metadados do arquivo.  Normaliza o volume do áudio
para manter a percepção de qualidade.  Este nível visa fugir de
detecções triviais sem degradar excessivamente o conteúdo.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path


class BasicProtection:
    """Classe para aplicar proteção básica utilizando OpenCV.

    A proteção básica recorta levemente a imagem (zoom 95%), ajusta
    contraste e brilho.  Esta implementação não modifica o áudio e
    depende apenas da biblioteca OpenCV, eliminando a necessidade de
    ffmpeg.
    """

    def apply(self, input_path: str, output_path: str) -> None:
        """Executa a proteção básica em um vídeo.

        Parameters
        ----------
        input_path: str
            Caminho para o vídeo de origem.
        output_path: str
            Caminho para o arquivo de saída protegido.
        """
        import cv2  # type: ignore
        # Garante que diretório de saída existe
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Não foi possível abrir {input_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        # Cálculo de recorte (5% de cada lado)
        crop_x = int(width * 0.025)
        crop_y = int(height * 0.025)
        crop_w = int(width * 0.95)
        crop_h = int(height * 0.95)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cropped = frame[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
            # Redimensiona de volta ao tamanho original
            resized = cv2.resize(cropped, (width, height))
            # Ajusta contraste (alpha) e brilho (beta). beta é no intervalo 0-255
            alpha = 1.1  # contraste levemente maior
            beta = 0.05 * 255  # brilho levemente maior
            adjusted = cv2.convertScaleAbs(resized, alpha=alpha, beta=beta)
            writer.write(adjusted)
        cap.release()
        writer.release()
