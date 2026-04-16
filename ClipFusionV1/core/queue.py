"""
ClipFusionV1.core.queue
=======================

Gerencia uma fila FIFO de projetos para processamento em lote.
O script lê a tabela de jobs no banco de dados, seleciona os
registrados como 'queued' e processa sequencialmente cada um
utilizando a classe ``Pipeline``.  Após o processamento de
cada projeto, o estado do job é atualizado.
"""

from __future__ import annotations

import logging
import time

from .database import get_next_job, get_project, update_job
from .pipeline import Pipeline


def run_queue(sleep_seconds: float = 5.0) -> None:
    """Processa continuamente jobs em estado 'queued'.

    Este loop infinito executa enquanto houver trabalhos a serem
    processados.  O parâmetro ``sleep_seconds`` define o tempo de
    espera entre verificações da fila.
    """
    pipeline = Pipeline()
    while True:
        job = get_next_job(db_path=pipeline.db_path)
        if job:
            job_id = job["id"]
            project = get_project(job["project_id"], db_path=pipeline.db_path)
            if project:
                logging.info(f"Processando job {job_id}")
                pipeline.process(project["video_path"], project["name"], protection_level=project.get("status", "basic"))
            else:
                update_job(job_id, state="error", error_message="Projeto não encontrado", db_path=pipeline.db_path)
        else:
            time.sleep(sleep_seconds)