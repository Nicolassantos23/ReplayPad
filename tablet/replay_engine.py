import os
import subprocess
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from shared.config import settings
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
    ):
        self._output_dir = Path(output_dir)
        self._seg_duration = segment_duration
        self._max_segments = max_segments

        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._running = False
        self._lock = threading.Lock()
        self._segments: list[Segment] = []
        self._frames: list[tuple[float, bytes]] = []
        self._segment_index = 0
        self._last_flush = 0.0

    def start(self):
        self._running = True
        self._last_flush = time.time()
        logger.info(
            f"ReplayEngine started: {self._seg_duration}s segments, "
            f"max {self._max_segments} ({self._max_segments * self._seg_duration}s buffer)"
        )

    def stop(self):
        self._running = False
        self._flush_segment(time.time())
        logger.info("ReplayEngine stopped")

    def feed(self, frame: bytes, timestamp: float):
        if not self._running:
            return

        self._frames.append((timestamp, frame))

        elapsed = timestamp - self._last_flush
        if elapsed >= self._seg_duration and len(self._frames) > 5:
            self._flush_segment(timestamp)

    def get_segments(self) -> list[Segment]:
        with self._lock:
            return list(self._segments)

    def clear(self):
        with self._lock:
            for seg in self._segments:
                try:
                    os.remove(seg.path)
                except OSError:
                    pass
            self._segments.clear()
        self._segment_index = 0
        self._frames.clear()

    def _flush_segment(self, current_time: float):
        if not self._frames:
            return

        window = [f for f in self._frames if f[0] >= self._last_flush]
        if len(window) < 5:
            return

        self._segment_index += 1
        filename = f"seg_{self._segment_index:04d}.mp4"
        output_path = str(self._output_dir / filename)

        fps = max(1, len(window) / (current_time - self._last_flush)) if (current_time - self._last_flush) > 0 else 30

        cmd = [
            settings.ffmpeg_path,
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-r", str(round(fps)),
            "-i", "pipe:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-y",
            output_path,
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            for _, jpeg_bytes in window:
                proc.stdin.write(jpeg_bytes)
            proc.stdin.close()
            proc.wait(timeout=30)

            if proc.returncode != 0:
                logger.error(f"ffmpeg segment creation failed for {filename}")
                return

            duration = current_time - self._last_flush
            segment = Segment(
                path=output_path,
                start_time=self._last_flush,
                end_time=current_time,
                duration=duration,
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

            self._frames = [f for f in self._frames if f[0] >= current_time - self._seg_duration]
            self._last_flush = current_time

        except subprocess.TimeoutExpired:
            proc.kill()
            logger.error(f"ffmpeg timed out for {filename}")
        except Exception as e:
            logger.error(f"Segment creation error: {e}")
