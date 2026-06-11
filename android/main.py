"""
ReplayPad — Android APK entry point

Empacota o tablet/app.py em um APK Android via Buildozer.
Inicia o servidor uvicorn em background e exibe o dashboard em um WebView.
"""
import os
import sys
import time
import threading
import json

# Caminho das libs do projeto
_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _PROJECT_ROOT)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def _load_config() -> dict:
    """Carrega config do dispositivo ou fallback para padrão."""
    defaults = {
        "stream_url": "http://192.168.1.100:8080/video",
        "vps_url": "",
        "buffer_duration": 30,
    }
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH) as f:
                return {**defaults, **json.load(f)}
        except (json.JSONDecodeError, OSError):
            pass
    return defaults


def _start_server():
    """Inicia FastAPI + câmera + engine em thread separada."""
    config = _load_config()

    os.environ["STREAM_URL"] = config["stream_url"]
    os.environ["VPS_URL"] = config.get("vps_url", "")
    os.environ["BUFFER_DURATION"] = str(config.get("buffer_duration", 30))
    os.environ["TABLET_HOST"] = "127.0.0.1"
    os.environ["TABLET_PORT"] = "8000"

    from tablet.app import create_app
    import uvicorn

    app, _, _, _, _ = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    """Chamado pelo Android ao iniciar o app."""

    # ── Servidor em background ────────────────────────────────────
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()

    # ── Aguarda servidor ficar pronto ─────────────────────────────
    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/status", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    # ── Abre WebView com dashboard ────────────────────────────────
    try:
        from android.webview import AndroidWebView

        webview = AndroidWebView()
        webview.load_url("http://127.0.0.1:8000/")
        webview.show()
    except ImportError:
        # Fallback se não for Android (modo dev)
        print("ReplayPad rodando em http://127.0.0.1:8000")
        threading.Event().wait()


if __name__ == "__main__":
    main()
