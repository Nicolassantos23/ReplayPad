import os
import time
import threading
from pathlib import Path
from typing import Optional

import httpx

from shared.config import settings
from shared.logger import setup_logger

logger = setup_logger(__name__)


class Uploader:
    def __init__(self, server_url: Optional[str] = None):
        self._server_url = (server_url or "").rstrip("/")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._queue: list[str] = []
        self._lock = threading.Lock()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        logger.info(f"Uploader started (server: {self._server_url})")

    def stop(self):
        self._running = False

    def enqueue(self, file_path: str):
        with self._lock:
            self._queue.append(file_path)
        logger.info(f"Upload queued: {os.path.basename(file_path)}")

    @property
    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)

    def _worker(self):
        while self._running:
            file_path = None
            with self._lock:
                if self._queue:
                    file_path = self._queue.pop(0)

            if file_path is None:
                time.sleep(1)
                continue

            self._upload(file_path)

    def _upload(self, file_path: str):
        if not self._server_url:
            logger.warning("No server URL configured — skipping upload")
            return

        if not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            return

        url = f"{self._server_url}/api/upload"
        filename = os.path.basename(file_path)

        try:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "video/mp4")}
                with httpx.Client(timeout=120) as client:
                    response = client.post(url, files=files)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Upload successful: {filename} (id: {data.get('id', '?')})")
            else:
                logger.error(f"Upload failed ({response.status_code}): {response.text}")

        except httpx.ConnectError:
            logger.error(f"Upload failed — server unreachable: {self._server_url}")
        except httpx.TimeoutException:
            logger.error(f"Upload timeout — file too large or server busy")
        except Exception as e:
            logger.error(f"Upload error: {e}")
