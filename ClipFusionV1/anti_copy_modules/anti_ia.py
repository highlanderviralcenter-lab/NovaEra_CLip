"""
Implementação do nível Anti‑IA de proteção.

Extende a proteção básica adicionando injeção de ruído e alteração
de chroma.  O objetivo é perturbar o hash digital gerado por
algoritmos de detecção baseados em redes neurais sem degradar
significativamente a experiência do usuário.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


class AntiIAProtection:
    """Classe para proteção Anti‑IA utilizando OpenCV.

    Esta proteção recorta o quadro, ajusta contraste e brilho, injeta
    ruído e remove a saturação de cor (transformando em tom mais
    monocromático).  Não altera o áudio.
    """

    def apply(self, input_path: str, output_path: str) -> None:
        """Executa a proteção Anti‑IA em um vídeo.

        Parameters
        ----------
        input_path: str
            Caminho para o vídeo original.
        output_path: str
            Caminho do arquivo protegido.
        """
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
        crop_x = int(width * 0.025)
        crop_y = int(height * 0.025)
        crop_w = int(width * 0.95)
        crop_h = int(height * 0.95)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cropped = frame[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
            resized = cv2.resize(cropped, (width, height))
            # Ajusta contraste e brilho
            alpha = 1.1
            beta = 0.05 * 255
            adjusted = cv2.convertScaleAbs(resized, alpha=alpha, beta=beta)
            # Injeta ruído gaussiano
            noise = np.random.normal(0, 20, adjusted.shape).astype(np.int16)
            noisy = cv2.add(adjusted.astype(np.int16), noise, dtype=cv2.CV_16S)
            noisy = np.clip(noisy, 0, 255).astype(np.uint8)
            # Remove saturação de cor (hue=s=0) – converte para HSV e zera S
            hsv = cv2.cvtColor(noisy, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = (hsv[:, :, 1] * 0.3).astype(hsv.dtype)  # reduz saturação
            desaturated = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            writer.write(desaturated)
        cap.release()
        writer.release()
