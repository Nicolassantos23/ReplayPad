import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from server.config import SERVER_CONFIG
from shared.logger import setup_logger

logger = setup_logger(__name__)


def get_storage_dir() -> Path:
    base = Path(SERVER_CONFIG["storage_path"])
    now = datetime.now()
    path = base / str(now.year) / f"{now.month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_file(filename: str, data: bytes) -> Optional[str]:
    try:
        dest_dir = get_storage_dir()
        dest_path = dest_dir / filename

        n = 1
        while dest_path.exists():
            stem = dest_path.stem
            suffix = dest_path.suffix
            dest_path = dest_dir / f"{stem}_{n}{suffix}"
            n += 1

        dest_path.write_bytes(data)
        logger.info(f"File saved: {dest_path} ({len(data) / 1024:.1f}KB)")
        return str(dest_path)

    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        return None


def get_file_path(storage_path: str) -> Optional[str]:
    path = Path(storage_path)
    if path.exists() and path.is_file():
        return str(path)
    logger.warning(f"File not found: {storage_path}")
    return None


def delete_file(storage_path: str) -> bool:
    try:
        path = Path(storage_path)
        if path.exists():
            path.unlink()
            logger.info(f"File deleted: {storage_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return False
