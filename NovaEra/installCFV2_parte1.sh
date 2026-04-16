#!/bin/bash
# Script 1: Setup do Sistema e Estrutura de Pastas ClipFusion V2 (LIMPO)
set -euo pipefail

if [ "$EUID" -ne 0 ]; then echo "Erro: Execute como root (sudo bash script1.sh)"; exit 1; fi

REAL_USER=${SUDO_USER:-$(logname)}
REAL_HOME=$(eval echo "~$REAL_USER")
PROJETO_DIR="$REAL_HOME/ClipFusion_V2_FINAL"

echo "--- 1. TUNAGEM DO KERNEL (FIM DOS FREEZES) ---"
# Ativa aceleração total e evita congelamentos da Intel HD 520
GRUB_LINE='GRUB_CMDLINE_LINUX_DEFAULT="quiet splash i915.enable_guc=3 mitigations=off intel_idle.max_cstate=1"'
sed -i "s|GRUB_CMDLINE_LINUX_DEFAULT=.*|$GRUB_LINE|" /etc/default/grub
update-grub

echo "--- 2. HIERARQUIA DE MEMORIA (zRAM LZ4) ---"
# Configura 6GB de RAM extra via compressão para rodar o Whisper
apt update && apt install -y systemd-zram-generator
cat > /etc/systemd/zram-generator.conf << EOF
[zram0]
zram-size = 6144
compression-algorithm = lz4
swap-priority = 100
EOF
systemctl daemon-reload
systemctl start /dev/zram0 || true

echo "--- 3. INSTALACAO DE DEPENDENCIAS (MATE + TOOLS) ---"
# Instalando ambiente leve e ferramentas de renderização
apt install -y mate-desktop-environment-core mate-terminal ffmpeg python3-pip python3-venv build-essential vainfo intel-gpu-tools btop

echo "--- 4. CRIACAO DA ESTRUTURA CANONICA ---"
# Criação da hierarquia de 7 abas do Manual Master
mkdir -p "$PROJETO_DIR"/{src/{core,gui,utils,viral_engine,anti_copy_modules,config,locales},workspace/projects}
touch "$PROJETO_DIR"/src/{core,gui,utils,anti_copy_modules,viral_engine}/__init__.py
touch "$PROJETO_DIR"/{db.py,main.py,requirements.txt}

chown -R "$REAL_USER":"$REAL_USER" "$PROJETO_DIR"
echo "✅ Script 1 finalizado com sucesso. Reinicie para aplicar o Kernel."
