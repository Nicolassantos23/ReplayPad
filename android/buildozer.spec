[app]

title = ReplayPad
package.name = replaypad
package.domain = com.replaypad
version = 1.2.0
version.code = 1

# ── Entry point ──────────────────────────────────────────────────────
source.dir = ..
source.include_exts = py,png,jpg,jpeg,txt,json,html,css,js
source.exclude_dirs = .venv,__pycache__,node_modules,.git

# ── Dependências Python ──────────────────────────────────────────────
requirements = python3,opencv-python,fastapi,uvicorn,httpx,python-dotenv,numpy,sqlalchemy

# ── Bootstrap (webview = Android WebView nativo) ─────────────────────
bootstrap = webview

# ── Permissões Android ───────────────────────────────────────────────
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE
android.wakelock = 1

# ── Android API / NDK ────────────────────────────────────────────────
android.api = 34
android.minapi = 26
android.ndk = 27
android.sdk = 34
android.ndk_path =

# ── Arquiteturas ──────────────────────────────────────────────────────
android.archs = arm64-v8a

# ── Tela ──────────────────────────────────────────────────────────────
orientation = landscape
android.allow_backup = 0
android.window_soft_input_mode = adjustResize

# ── Ícone ─────────────────────────────────────────────────────────────
icon.filename = %(source.dir)s/android/icons/icon.png
presplash.filename = %(source.dir)s/android/icons/splash.png

# ── Storage ───────────────────────────────────────────────────────────
android.storage_path = /sdcard/ReplayPad

# ── Logging ──────────────────────────────────────────────────────────
log_level = 2
android.logcat_filters = *:S python:V

# ── Build ────────────────────────────────────────────────────────────
p4a.branch = develop
p4a.local_recipes = 
