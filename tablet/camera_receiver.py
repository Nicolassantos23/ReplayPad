import re
import time
import threading
from dataclasses import dataclass
from typing import Optional

import httpx

from shared.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class CameraConfig:
    stream_url: str
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0


class CameraReceiver:
    def __init__(self, config: CameraConfig):
        self.config = config
        self._running = False
        self._connected = False
        self._frame_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

        self._front: Optional[bytes] = None
        self._back: Optional[bytes] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Camera receiver started")

    def stop(self):
        self._running = False
        self._connected = False
        logger.info("Camera receiver stopped")

    def read_frame(self) -> Optional[bytes]:
        with self._frame_lock:
            return self._front

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _capture_loop(self):
        delay = self.config.reconnect_delay
        while self._running:
            try:
                with httpx.Client() as client:
                    with client.stream("GET", self.config.stream_url, timeout=None) as response:
                        if response.status_code != 200:
                            logger.error(f"Stream returned HTTP {response.status_code}")
                            time.sleep(delay)
                            delay = min(delay * 2, self.config.max_reconnect_delay)
                            continue

                        delay = self.config.reconnect_delay
                        self._connected = True
                        logger.info("Connected to stream")

                        self._parse_mjpeg(response)

            except httpx.ConnectError:
                logger.error(f"Connection failed, retrying in {delay:.0f}s...")
            except httpx.ReadError:
                logger.warning(f"Stream interrupted, retrying in {delay:.0f}s...")
            except Exception as e:
                logger.error(f"Stream error: {e}")

            self._connected = False
            time.sleep(delay)
            delay = min(delay * 2, self.config.max_reconnect_delay)

    def _parse_mjpeg(self, response: httpx.Response):
        buffer = b""
        for chunk in response.iter_bytes():
            if not self._running:
                break
            buffer += chunk

            while True:
                start = buffer.find(b"\xff\xd8")
                end = buffer.find(b"\xff\xd9")
                if start >= 0 and end > start:
                    jpeg_bytes = buffer[start:end + 2]
                    buffer = buffer[end + 2:]

                    with self._frame_lock:
                        self._back = jpeg_bytes
                        self._front, self._back = self._back, self._front

                    if not self._connected:
                        self._connected = True
                        logger.info("Receiving frames")
                else:
                    if len(buffer) > 1024 * 1024:
                        buffer = buffer[-512:]
                    break
