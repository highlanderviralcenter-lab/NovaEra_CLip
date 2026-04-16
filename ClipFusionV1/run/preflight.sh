#!/bin/bash
# Verifica pre-requisitos para execucao do ClipFusionV1.

set -e

echo "[Preflight] Verificando requisitos de sistema..."

# Inicializa flag de erro
fail=0

# Funcao para checar a existencia de um comando no PATH
check_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "[ERRO] Comando '$cmd' nao encontrado. Instale-o antes de continuar."
        fail=1
    else
        echo "[OK]  $cmd encontrado."
    fi
}

# Verifica Python3
check_cmd python3
# Verifica ffmpeg (opcional)
if command -v ffmpeg >/dev/null 2>&1; then
    echo "[OK]  ffmpeg encontrado."
else
    echo "[AVISO] ffmpeg não encontrado; o pipeline utiliza OpenCV para corte de vídeos."
fi

# Verifica espaco em disco disponivel no diretorio atual (em kilobytes)
avail=$(df --output=avail . | tail -n1)
if [ "$avail" -lt 1048576 ]; then # 1GB = 1048576 KB
    echo "[ERRO] Espaco em disco insuficiente (menos de 1GB livre)."
    fail=1
else
    echo "[OK] Espaco em disco suficiente."
fi

# Verifica permissoes de escrita no diretorio atual
if ! touch .preflight_test 2>/dev/null; then
    echo "[ERRO] Sem permissao de escrita no diretorio atual"
    fail=1
else
    rm -f .preflight_test
fi

# Verifica disponibilidade da biblioteca Whisper (opcional)
python3 - <<'PY'
try:
    import whisper  # type: ignore
    print("[OK] Biblioteca whisper disponivel.")
except ImportError:
    print("[AVISO] Biblioteca whisper nao encontrada; sera usada transcricao ficticia.")
PY

# Se algum erro foi registrado, encerra com falha
if [ "$fail" -ne 0 ]; then
    echo "Preflight falhou. Corrija os erros acima e execute novamente."
    exit 1
fi

echo "Preflight concluido com sucesso."
