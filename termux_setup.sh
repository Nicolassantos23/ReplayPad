#!/data/data/com.termux/files/usr/bin/bash
# termux_setup.sh — Instala e configura ReplayPad no Termux
# Uso: bash termux_setup.sh
set -e

REPO_DIR="$HOME/ReplayPad"
APP_DIR="$REPO_DIR/replaypad"

echo "==> Atualizando pacotes..."
pkg update -y && pkg upgrade -y

echo "==> Instalando dependências do sistema..."
pkg install -y python ffmpeg git

echo "==> Instalando pacotes Python..."
pip install fastapi uvicorn httpx python-dotenv

echo "==> Clonando/atualizando repositório..."
if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
    git pull
else
    git clone https://github.com/Nicolassantos23/ReplayPad.git "$REPO_DIR"
fi

cd "$APP_DIR"

echo "==> Configurando .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Edite o arquivo .env com a URL da câmera:"
    echo "  nano $APP_DIR/.env"
    echo "  -> Defina STREAM_URL=http://IP_DA_CAMERA:8080/video"
fi

echo ""
echo "==========================================="
echo "  ReplayPad instalado com sucesso!"
echo "==========================================="
echo ""
echo "Para iniciar:"
echo "  cd $APP_DIR"
echo "  python -m tablet.app"
echo ""
echo "Dashboard: http://127.0.0.1:8000/"
