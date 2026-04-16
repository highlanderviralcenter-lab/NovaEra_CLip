#!/bin/bash
# Script 1: Setup do Sistema e Estrutura de Pastas ClipFusion V2
set -euo pipefail

if [ "$EUID" -ne 0 ]; then echo "Erro: Execute como root (sudo bash script1.sh)"; exit 1; fi

REAL_USER=${SUDO_USER:-$(logname)}
REAL_HOME=$(eval echo "~$REAL_USER")
PROJETO_DIR="$REAL_HOME/ClipFusion_V2_FINAL"

echo "--- 1. TUNAGEM DO KERNEL (FIM DOS FREEZES) ---"
# Blindagem contra congelamentos na tomada e liberacao da VA-API
GRUB_LINE='GRUB_CMDLINE_LINUX_DEFAULT="quiet splash i915.enable_guc=3 mitigations=off intel_idle.max_cstate=1"'
sed -i "s|GRUB_CMDLINE_LINUX_DEFAULT=.*|$GRUB_LINE|" /etc/default/grub
update-grub [3, 4]

echo "--- 2. HIERARQUIA DE MEMORIA (zRAM LZ4) ---"
apt update && apt install -y systemd-zram-generator
cat > /etc/systemd/zram-generator.conf << EOF
[zram0]
zram-size = 6144
compression-algorithm = lz4
swap-priority = 100
EOF
systemctl daemon-reload
systemctl start /dev/zram0 || true [5]

echo "--- 3. INSTALACAO DE DEPENDENCIAS (MATE + TOOLS) ---"
apt install -y mate-desktop-environment-core mate-terminal ffmpeg python3-pip python3-venv build-essential vainfo intel-gpu-tools btop [6, 7]

echo "--- 4. CRIACAO DA ESTRUTURA CANONICA ---"
mkdir -p "$PROJETO_DIR"/{src/{core,gui,utils,viral_engine,anti_copy_modules,config,locales},workspace/projects}
touch "$PROJETO_DIR"/src/{core,gui,utils,anti_copy_modules,viral_engine}/__init__.py
touch "$PROJETO_DIR"/{db.py,main.py,requirements.txt} [2, 8]

chown -R "$REAL_USER":"$REAL_USER" "$PROJETO_DIR"
echo "✅ Script 1 finalizado. Recomenda-se reboot para aplicar ajustes de Kernel.
