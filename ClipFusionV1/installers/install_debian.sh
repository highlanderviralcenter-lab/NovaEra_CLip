#!/bin/bash
# Script de instalacao para ambientes Debian/Ubuntu

set -e

echo "[Install] Atualizando sistema e instalando dependencias..."

if command -v apt >/dev/null 2>&1; then
    echo "[Install] apt disponível, mas a instalação de pacotes foi omitida neste ambiente por falta de permissões."
    echo "         Instale python3, python3-pip, ffmpeg e libsqlite3-dev manualmente se necessário."
else
    echo "[Install] apt não encontrado. Pulando instalação de pacotes do sistema."
fi

echo "[Install] Instalando dependencias Python..."
# Nenhuma dependencia Python especifica e instalada via pip neste instalador,
# pois o projeto foi ajustado para usar apenas bibliotecas da
# biblioteca padrao (sqlite3, subprocess, etc.) e o utilitario ffmpeg.
echo "[Install] Nenhuma dependencia Python adicional a instalar."

echo "[Install] Instalacao concluida."
