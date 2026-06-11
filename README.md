# ReplayPad v1.2

Sistema de replay esportivo distribuído:

**S20 FE** (câmera) → **Redmi Pad 2** (processamento) → **VPS** (armazenamento)

## Arquitetura

```
┌──────────┐   RTSP/HTTP    ┌──────────────┐   HTTP POST    ┌──────────┐
│  S20 FE  │───────────────▶│  Redmi Pad 2 │───────────────▶│  VPS     │
│ IP Webcam│                │               │  replay.mp4   │  Ubuntu  │
└──────────┘                │───────────────│               │──────────│
                            │• CameraReceiver              │• FastAPI │
                            │• ReplayEngine (segmentos)    │• PostgreSQL
                            │• ReplayManager (concat)      │• storage/│
                            │• Uploader                    │• Dashboard
                            └──────────────┘               └──────────┘
```

## Estrutura

```
replaypad/
├── tablet/          # Roda no Redmi Pad 2 (Termux)
│   ├── camera_receiver.py   # Captura RTSP/HTTP do S20 FE
│   ├── replay_engine.py     # Grava segmentos MP4 de 5s (ring de 6 = 30s)
│   ├── replay_manager.py    # Concatena segmentos via ffmpeg
│   ├── uploader.py          # Upload automático para VPS
│   ├── app.py               # Entry point do tablet
│   └── web/
│       ├── routes.py        # Endpoints do tablet
│       └── templates/
│           └── tablet.html  # Dashboard do tablet
├── server/          # Roda na VPS Ubuntu
│   ├── main.py              # Entry point da VPS
│   ├── config.py            # Configuração
│   ├── database.py          # SQLAlchemy + PostgreSQL
│   ├── storage.py           # Gerenciamento de arquivos
│   └── api/
│       └── replays.py       # Upload, listar, baixar, deletar
├── shared/          # Compartilhado
│   ├── config.py            # Constantes + env vars
│   └── logger.py            # Logging padronizado
├── requirements.txt
└── .env.example
```

## Instalação

### Tablet (Redmi Pad 2 via Termux)

```bash
pkg update && pkg upgrade
pkg install python ffmpeg opencv
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar STREAM_URL com IP da câmera

# Iniciar
python -m tablet.app
```

### Servidor (VPS Ubuntu)

```bash
# Dependências do sistema
apt install ffmpeg postgresql postgresql-contrib

# PostgreSQL
sudo -u postgres createuser replaypad -P
sudo -u postgres createdb replaypad -O replaypad

# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Iniciar
python -m server.main
```

## Endpoints

### Tablet (`http://tablet:8000`)

| Rota | Descrição |
|------|-----------|
| `GET /` | Dashboard do tablet |
| `GET /video` | Stream MJPEG ao vivo |
| `GET /status` | Status da câmera e buffer |
| `POST /replay/{10,20,30}` | Gera replay dos últimos N segundos |
| `GET /replay/latest` | Download do último replay |
| `POST /save/{10,20,30}` | Salva replay + enfileira upload |

### Servidor (`http://vps:8001`)

| Rota | Descrição |
|------|-----------|
| `GET /` | Health check |
| `GET /admin` | Dashboard admin |
| `POST /api/upload` | Upload de replay |
| `GET /api/replays` | Listar replays |
| `GET /api/replay/{id}` | Download |
| `DELETE /api/replay/{id}` | Excluir replay |
| `GET /api/health` | Health check |

## Funcionamento

1. **Captura**: `CameraReceiver` conecta ao S20 FE via RTSP/HTTP
2. **Segmentos**: `ReplayEngine` grava MP4 de 5s em disco, mantém ring de 6 (30s)
3. **Replay**: Ao clicar em 10s/20s/30s, `ffmpeg concat` junta os segmentos sem re-encode
4. **Salvar**: Cópia permanente é salva em `replays/`
5. **Upload**: `Uploader` envia automaticamente para VPS
6. **Servidor**: Armazena em disco + PostgreSQL, disponível no dashboard admin

## Requisitos

- Python 3.12+
- FFmpeg (tablet e servidor)
- PostgreSQL (apenas servidor)
- Rede local (Wi-Fi) entre S20 FE e tablet
- Acesso à internet do tablet para VPS
