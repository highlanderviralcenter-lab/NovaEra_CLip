"""
ClipFusionV1.core.pipeline
==========================

Este módulo orquestra o fluxo completo de processamento para um
projeto.  Ele é responsável por criar registros no banco de dados,
executar a transcrição do áudio, segmentar o vídeo, gerar pontuações e
ganchos, cortar trechos, aplicar proteção anti‑copyright e gravar
resultados.  Para fins didáticos, este pipeline é linear e
simplificado; adaptações podem ser feitas para adicionar paralelismo
ou processos assíncronos.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List
from datetime import datetime

from .database import (
    init_db,
    insert_project,
    insert_job,
    update_job,
    insert_clip,
    insert_schedule,
    get_project,
)
from .asr import transcribe
from .segmentation import segment
from .scoring import score_segments
from .utils import get_video_duration, cut_video_segment_cv2
from ..viral_engine.engine import ViralAnalyzer, Schedulyzer
from ..anti_copy_modules.basic import BasicProtection
from ..anti_copy_modules.anti_ia import AntiIAProtection
from ..anti_copy_modules.maximum import MaximumProtection


class Pipeline:
    """Classe de orquestração do pipeline."""

    def __init__(self, db_path: str = "clipfusion_v1.db") -> None:
        init_db(db_path)
        self.db_path = db_path
        self.analyzer = ViralAnalyzer()
        self.schedulyzer = Schedulyzer()

    def _get_protection_instance(self, level: str):
        level = level.lower()
        if level == "none":
            return None
        elif level == "basic":
            return BasicProtection()
        elif level in {"anti", "anti_ia", "anti-ia"}:
            return AntiIAProtection()
        elif level in {"max", "maximum", "maximo", "máximo"}:
            return MaximumProtection()
        else:
            raise ValueError(f"Nível de proteção desconhecido: {level}")

    def process(self, video_path: str, project_name: str, protection_level: str = "basic") -> dict:
        """Processa um vídeo completo.

        Parameters
        ----------
        video_path: str
            Caminho do arquivo de vídeo de entrada.
        project_name: str
            Nome descritivo do projeto.
        protection_level: str
            Nível de proteção: none, basic, anti_ia ou maximum.

        Returns
        -------
        dict
            Dicionário representando o projeto persistido.
        """
        logging.info(f"Iniciando processamento do projeto '{project_name}'")
        # Inserir projeto e job
        project_id = insert_project(project_name, video_path, status=protection_level, db_path=self.db_path)
        job_id = insert_job(project_id, state="running", db_path=self.db_path)
        try:
            # Transcrição
            transcription = transcribe(video_path)
            project = get_project(project_id, db_path=self.db_path)
            niche = self.analyzer.detect_niche(transcription)
            # Atualiza niche e status (não temos função, mas poderíamos fazer update; por simplicidade ignoramos)
            # Segmentação
            segments = segment(video_path)
            scores = score_segments(segments)
            # Selecionar top N segmentos (exemplo: 3)
            # Ordenar por score decrescente
            top_indices = sorted(range(len(segments)), key=lambda i: scores[i], reverse=True)[:3]
            protection_instance = self._get_protection_instance(protection_level)
            for idx in top_indices:
                start, end = segments[idx]
                score = scores[idx]
                duration = end - start
                # Gerar snippet do texto para hooks (recorta trecho proporcional)
                snippet_start = int(len(transcription) * (start / get_video_duration(video_path))) if get_video_duration(video_path) else 0
                snippet_end = int(len(transcription) * (end / get_video_duration(video_path))) if get_video_duration(video_path) else 0
                text_snippet = transcription[snippet_start:snippet_end] or transcription
                hooks = self.analyzer.generate_hooks(text_snippet)
                archetype = self.analyzer.pick_archetype(idx)
                # Cortar vídeo usando OpenCV para eliminar dependência de ffmpeg
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_cut:
                    tmp_cut_path = tmp_cut.name
                # Executa corte; captura exceções caso falhe
                try:
                    cut_video_segment_cv2(video_path, start, end, tmp_cut_path)
                except Exception as e:
                    logging.error(f"Erro ao cortar segmento {idx + 1}: {e}")
                    raise
                # Aplicar proteção
                # Define diretório de saída relativo à raiz do pacote (ClipFusionV1/output/videos)
                # parents[1] de pipeline.py é o diretório ClipFusionV1
                project_root = Path(__file__).resolve().parents[1]
                output_dir = project_root / "output" / "videos"
                output_dir.mkdir(parents=True, exist_ok=True)
                out_name = f"{Path(video_path).stem}_clip_{idx+1}_{protection_level}.mp4"
                protected_path = str(output_dir / out_name)
                if protection_instance:
                    protection_instance.apply(tmp_cut_path, protected_path)
                else:
                    # Sem proteção, apenas copia o arquivo temporário
                    os.rename(tmp_cut_path, protected_path)
                # Remover temporário se ainda existir
                if os.path.exists(tmp_cut_path):
                    os.remove(tmp_cut_path)
                # Registrar clip no banco
                clip_id = insert_clip(
                    project_id=project_id,
                    start_time=start,
                    end_time=end,
                    hook_text=hooks.get("hook_direct", ""),
                    viral_score=score,
                    archetype=archetype,
                    protection_level=protection_level,
                    output_path=protected_path,
                    db_path=self.db_path,
                )
                # Agendar postagem
                schedule_times = self.schedulyzer.generate_schedule(datetime.now().date())
                if schedule_times:
                    post_time_str = schedule_times[0]
                    # Constrói string datetime completa (ISO) para armazenamento
                    h, m, s = map(int, post_time_str.split(":"))
                    scheduled_dt = datetime.now().replace(hour=h, minute=m, second=s, microsecond=0)
                    insert_schedule(
                        clip_id,
                        scheduled_dt.isoformat(sep=" "),
                        self.schedulyzer.recommend_platform(niche or "geral", score),
                        db_path=self.db_path,
                    )
            update_job(job_id, state="done", db_path=self.db_path)
        except Exception as e:
            logging.exception(f"Erro durante o processamento: {e}")
            update_job(job_id, state="error", error_message=str(e), db_path=self.db_path)
        return get_project(project_id, db_path=self.db_path)
