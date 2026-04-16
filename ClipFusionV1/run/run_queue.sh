#!/bin/bash
# Executa a fila de processamento de projetos ClipFusionV1.

set -e

python3 -m ClipFusionV1.app.main run_queue "$@"
