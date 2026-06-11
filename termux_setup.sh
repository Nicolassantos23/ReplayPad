#!/data/data/com.termux/files/usr/bin/bash
# termux_setup.sh — Instala e configura ReplayPad no Termux
# Uso: bash termux_setup.sh
set -e

echo "==> Atualizando pacotes..."
pkg update -y && pkg upgrade -y

echo "==> Instalando dependências do sistema..."
pkg install -y python ffmpeg git openssl

echo "==> Instalando OpenCV (pré-compilado para Termux)..."
pkg install -y opencv-python

echo "==> Instalando pacotes Python..."
pip install fastapi uvicorn httpx python-dotenv

echo "==> Clonando repositório..."
cd ~
if [ -d "ReplayPad" ]; then
    cd ReplayPad && git pull
else
    git clone https://github.com/Nicolassantos23/ReplayPad.git
    cd ReplayPad/replaypad
fi

echo "==> Configurando .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Edite o arquivo .env com a URL da câmera:"
    echo "  nano .env"
    echo "  -> Defina STREAM_URL=http://IP_DA_CAMERA:8080/video"
fi

echo ""
echo "==========================================="
echo "  ReplayPad instalado com sucesso!"
echo "==========================================="
echo ""
echo "Para iniciar:"
echo "  cd ~/ReplayPad/replaypad"
echo "  python -m tablet.app"
echo ""
echo "Dashboard: http://127.0.0.1:8000/"
