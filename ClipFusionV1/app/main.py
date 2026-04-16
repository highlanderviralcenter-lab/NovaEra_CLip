"""
Entrada de linha de comando para o ClipFusionV1.

Permite processar um único vídeo imediatamente ou adicionar vários
arquivos à fila de processamento.  Também expõe comandos para
inicializar o banco de dados e listar projetos existentes.
"""

import argparse
import logging
import sys
from pathlib import Path

from ..core.pipeline import Pipeline
from ..core.database import (
    init_db,
    insert_project,
    insert_job,
    list_projects,
)
from ..core.queue import run_queue


def cmd_process(args: argparse.Namespace) -> None:
    pipeline = Pipeline()
    pipeline.process(args.input, args.name, args.protection)
    print("Processamento concluído.")


def cmd_enqueue(args: argparse.Namespace) -> None:
    for file_path in args.inputs:
        project_id = insert_project(Path(file_path).stem, file_path, status=args.protection)
        insert_job(project_id, state="queued")
        print(f"Arquivo {file_path} adicionado à fila com projeto id {project_id}.")


def cmd_list(args: argparse.Namespace) -> None:
    for proj in list_projects():
        print(f"{proj['id']}\t{proj['name']}\t{proj['status']}\t{proj['video_path']}")


def cmd_run_queue(args: argparse.Namespace) -> None:
    print("Executando fila... pressione Ctrl+C para parar.")
    try:
        run_queue(sleep_seconds=args.sleep)
    except KeyboardInterrupt:
        print("Interrompido pelo usuário.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ClipFusionV1 - Ferramenta de cortes virais")
    subparsers = parser.add_subparsers(dest="command", required=True)
    # Comando process
    p_process = subparsers.add_parser("process", help="Processa um único vídeo agora")
    p_process.add_argument("--input", required=True, help="Caminho para o vídeo")
    p_process.add_argument("--name", required=False, help="Nome do projeto", default="Projeto")
    p_process.add_argument("--protection", required=False, default="basic", help="Nível de proteção: none|basic|anti_ia|maximum")
    p_process.set_defaults(func=cmd_process)
    # Comando enqueue
    p_enqueue = subparsers.add_parser("enqueue", help="Adiciona vídeos à fila")
    p_enqueue.add_argument("inputs", nargs="+", help="Arquivos de vídeo a enfileirar")
    p_enqueue.add_argument("--protection", default="basic", help="Nível de proteção para os arquivos em lote")
    p_enqueue.set_defaults(func=cmd_enqueue)
    # Comando list
    p_list = subparsers.add_parser("list", help="Lista projetos existentes")
    p_list.set_defaults(func=cmd_list)
    # Comando run_queue
    p_runq = subparsers.add_parser("run_queue", help="Executa a fila de processamento")
    p_runq.add_argument("--sleep", type=float, default=5.0, help="Intervalo entre verificações da fila (segundos)")
    p_runq.set_defaults(func=cmd_run_queue)
    # Parse e executar
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    args.func(args)


if __name__ == "__main__":
    main()
