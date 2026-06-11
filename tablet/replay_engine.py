import os
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from shared.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Segment:
    path: str
    start_time: float
    end_time: float
    duration: float

    @property
    def filename(self) -> str:
        return os.path.basename(self.path)


class ReplayEngine:
    def __init__(
        self,
        output_dir: str = "segments",
        segment_duration: float = 5.0,
        max_segments: int = 6,
        fps: float = 30.0,
    ):
        self._output_dir = Path(output_dir)
        self._seg_duration = segment_duration
        self._max_segments = max_segments
        self._fps = fps

        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._running = False
        self._lock = threading.Lock()
        self._segments: list[Segment] = []

        self._current_writer: Optional[cv2.VideoWriter] = None
        self._current_path: Optional[str] = None
        self._current_start: float = 0.0
        self._frame_count: int = 0
        self._frame_w: int = 0
        self._frame_h: int = 0

        self._segment_index = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        self._running = True
        logger.info(
            f"ReplayEngine started: {self._seg_duration}s segments, "
            f"max {self._max_segments} ({self._max_segments * self._seg_duration}s buffer)"
        )

    def stop(self):
        self._running = False
        self._close_current()
        logger.info("ReplayEngine stopped")

    def feed(self, frame: np.ndarray, timestamp: float):
        if not self._running:
            return

        if self._current_writer is None:
            self._open_new_segment(frame, timestamp)

        elapsed = timestamp - self._current_start
        if elapsed >= self._seg_duration:
            self._finalize_segment()
            self._open_new_segment(frame, timestamp)

        self._current_writer.write(frame)
        self._frame_count += 1

    def get_segments(self) -> list[Segment]:
        with self._lock:
            return list(self._segments)

    def clear(self):
        self._close_current()
        with self._lock:
            for seg in self._segments:
                try:
                    os.remove(seg.path)
                except OSError:
                    pass
            self._segments.clear()
        self._segment_index = 0

    # ------------------------------------------------------------------
    # Segment management
    # ------------------------------------------------------------------

    def _open_new_segment(self, frame: np.ndarray, timestamp: float):
        self._frame_h, self._frame_w = frame.shape[:2]
        self._segment_index += 1
        self._current_start = timestamp
        self._frame_count = 0

        filename = f"seg_{self._segment_index:04d}.mp4"
        self._current_path = str(self._output_dir / filename)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._current_writer = cv2.VideoWriter(
            self._current_path, fourcc, self._fps, (self._frame_w, self._frame_h)
        )
        if not self._current_writer.isOpened():
            logger.error(f"Failed to create video writer: {self._current_path}")
            self._current_writer = None
            return

        logger.debug(f"New segment: {filename} @ {self._frame_w}x{self._frame_h}")

    def _finalize_segment(self):
        if self._current_writer is None:
            return

        self._current_writer.release()
        self._current_writer = None

        actual_duration = (
            self._frame_count / self._fps if self._frame_count > 0 else self._seg_duration
        )

        segment = Segment(
            path=self._current_path,
            start_time=self._current_start,
            end_time=self._current_start + actual_duration,
            duration=actual_duration,
        )

        with self._lock:
            self._segments.append(segment)
            while len(self._segments) > self._max_segments:
                oldest = self._segments.pop(0)
                try:
                    os.remove(oldest.path)
                    logger.debug(f"Removed old segment: {oldest.filename}")
                except OSError as e:
                    logger.warning(f"Failed to remove {oldest.filename}: {e}")

        self._current_path = None
        self._current_start = 0.0
        self._frame_count = 0

    def _close_current(self):
        if self._current_writer is not None:
            self._current_writer.release()
            self._current_writer = None
            if self._current_path and os.path.exists(self._current_path):
                if self._frame_count > 5:
                    self._finalize_segment()
                else:
                    try:
                        os.remove(self._current_path)
                    except OSError:
                        pass
