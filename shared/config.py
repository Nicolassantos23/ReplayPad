import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    # Tablet / Camera
    stream_url: str = os.getenv("STREAM_URL", "rtsp://192.168.1.100:554/stream")
    buffer_duration: int = int(os.getenv("BUFFER_DURATION", "30"))
    segment_duration: int = int(os.getenv("SEGMENT_DURATION", "5"))
    max_segments: int = int(os.getenv("MAX_SEGMENTS", "6"))
    jpeg_quality: int = int(os.getenv("JPEG_QUALITY", "50"))
    tablet_host: str = os.getenv("TABLET_HOST", "0.0.0.0")
    tablet_port: int = int(os.getenv("TABLET_PORT", "8000"))

    # VPS / Server
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", "8001"))
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://replaypad:replaypad@localhost/replaypad",
    )
    storage_path: Path = Path(os.getenv("STORAGE_PATH", "/app/storage"))
    upload_max_size: int = int(os.getenv("UPLOAD_MAX_SIZE", "500000000"))

    # FFmpeg
    ffmpeg_path: str = os.getenv("FFMPEG_PATH", "ffmpeg")

    # Shared
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
