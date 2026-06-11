#!/bin/bash
# build_apk.sh — Compila o ReplayPad para APK Android
# Uso: bash build_apk.sh [debug|release]

set -e

MODE="${1:-debug}"
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "==> Instalando dependências do build..."
pip install buildozer cython 2>/dev/null || true

echo "==> Compilando APK ($MODE)..."
if [ "$MODE" = "release" ]; then
    buildozer android release
    echo "APK gerado: bin/ReplayPad-*-release.apk"
else
    buildozer android debug
    echo "APK gerado: bin/ReplayPad-*-debug.apk"
fi
