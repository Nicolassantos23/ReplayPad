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
        self._stop_event = threading.Event()
        self._frame_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._client: Optional[httpx.Client] = None
        self._response = None

        self._front: Optional[bytes] = None
        self._back: Optional[bytes] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Camera receiver started")

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._response:
            self._response.close()
        if self._client:
            self._client.close()
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
        while self._running and not self._stop_event.is_set():
            try:
                self._client = httpx.Client(timeout=httpx.Timeout(30.0))
                with self._client.stream("GET", self.config.stream_url, timeout=None) as response:
                    if response.status_code != 200:
                        logger.error(f"Stream returned HTTP {response.status_code}")
                        self._sleep_or_stop(delay)
                        delay = min(delay * 2, self.config.max_reconnect_delay)
                        continue

                    delay = self.config.reconnect_delay
                    self._connected = True
                    logger.info("Connected to stream")
                    self._response = response
                    self._parse_mjpeg(response)

            except httpx.ConnectError:
                logger.error(f"Connection failed, retrying in {delay:.0f}s...")
            except httpx.ReadError:
                logger.warning(f"Stream interrupted")
            except httpx.RemoteProtocolError:
                logger.warning("Stream protocol error")
            except Exception as e:
                if self._running:
                    logger.error(f"Stream error: {e}")

            self._connected = False
            self._response = None
            self._client = None
            if self._running and not self._stop_event.is_set():
                self._sleep_or_stop(delay)
                delay = min(delay * 2, self.config.max_reconnect_delay)

    def _sleep_or_stop(self, seconds: float):
        self._stop_event.wait(timeout=seconds)

    def _parse_mjpeg(self, response: httpx.Response):
        buffer = b""
        for chunk in response.iter_bytes():
            if not self._running or self._stop_event.is_set():
                break
            buffer += chunk

            while True:
                start = buffer.find(b"\xff\xd8")
                if start < 0:
                    if len(buffer) > 2 * 1024 * 1024:
                        buffer = buffer[-1024:]
                    break

                end = buffer.find(b"\xff\xd9", start)
                if end < 0:
                    if len(buffer) > 2 * 1024 * 1024:
                        buffer = buffer[-1024:]
                    break

                jpeg_bytes = buffer[start:end + 2]
                buffer = buffer[end + 2:]

                with self._frame_lock:
                    self._back = jpeg_bytes
                    self._front, self._back = self._back, self._front

                if not self._connected:
                    self._connected = True
                    logger.info("Receiving frames")
