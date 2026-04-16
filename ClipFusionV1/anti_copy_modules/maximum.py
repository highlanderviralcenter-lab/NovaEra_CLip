"""
Implementação do nível Máximo de proteção.

Combina todas as técnicas disponíveis para minimizar a chance de
detecção por algoritmos automáticos.  Aumenta a intensidade do
ruído e altera levemente a velocidade do áudio para quebrar hashes
digitais de conteúdo.  Essa proteção é mais agressiva e pode
impactar a qualidade percebida.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


class MaximumProtection:
    """Classe para proteção Máxima utilizando OpenCV.

    Aplica recorte mais agressivo, contraste/brilho intensificados,
    ruído mais forte e altera a saturação para reduzir a detecção.
    Não altera o áudio.
    """

    def apply(self, input_path: str, output_path: str) -> None:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Não foi possível abrir {input_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        # Recorte de 90%
        crop_x = int(width * 0.05)
        crop_y = int(height * 0.05)
        crop_w = int(width * 0.9)
        crop_h = int(height * 0.9)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cropped = frame[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
            resized = cv2.resize(cropped, (width, height))
            # Contraste/brilho mais fortes
            alpha = 1.2
            beta = 0.07 * 255
            adjusted = cv2.convertScaleAbs(resized, alpha=alpha, beta=beta)
            # Ruído mais forte
            noise = np.random.normal(0, 30, adjusted.shape).astype(np.int16)
            noisy = cv2.add(adjusted.astype(np.int16), noise, dtype=cv2.CV_16S)
            noisy = np.clip(noisy, 0, 255).astype(np.uint8)
            # Ajusta saturação (hue=s=0.8) – reduz saturação
            hsv = cv2.cvtColor(noisy, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = (hsv[:, :, 1] * 0.8).astype(hsv.dtype)
            final = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            writer.write(final)
        cap.release()
        writer.release()
