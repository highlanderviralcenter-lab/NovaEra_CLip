#!/bin/bash
# Inicializa e executa o ClipFusionV1 para um único projeto via CLI.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

python3 -m ClipFusionV1.app.main "$@"