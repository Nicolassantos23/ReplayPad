import time
import logging
import threading
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from shared.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class CameraConfig:
    stream_url: str
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0
    read_timeout_ms: float = 5000
    buffer_size: int = 1


class CameraReceiver:
    def __init__(self, config: CameraConfig):
        self.config = config
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._connected = False
        self._cap_lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

        self._front: Optional[np.ndarray] = None
        self._back: Optional[np.ndarray] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Camera receiver started")

    def stop(self):
        self._running = False
        with self._cap_lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
        self._connected = False
        logger.info("Camera receiver stopped")

    def read_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return self._front

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        with self._cap_lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

        logger.info(f"Connecting to stream: {self.config.stream_url}")
        cap = cv2.VideoCapture(self.config.stream_url, cv2.CAP_FFMPEG)

        if not cap.isOpened():
            logger.error("Failed to open stream — check URL and network")
            return False

        cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)

        with self._cap_lock:
            self._cap = cap

        self._connected = True
        logger.info("Connected successfully")
        return True

    def reconnect(self) -> bool:
        delay = self.config.reconnect_delay
        while self._running:
            logger.info(f"Reconnecting in {delay:.1f}s...")
            time.sleep(delay)
            if self.connect():
                return True
            delay = min(delay * 2, self.config.max_reconnect_delay)
        return False

    def _capture_loop(self):
        while self._running:
            with self._cap_lock:
                cap = self._cap

            if cap is None:
                if not self.connect():
                    self._connected = False
                    self.reconnect()
                continue

            ret, frame = cap.read()

            if not ret:
                logger.warning("Frame read failed — connection lost")
                with self._cap_lock:
                    if self._cap is not None:
                        self._cap.release()
                        self._cap = None
                self._connected = False
                self.reconnect()
                continue

            with self._frame_lock:
                self._back = frame
                self._front, self._back = self._back, self._front

            if not self._connected:
                self._connected = True
                logger.info("Receiving frames")
