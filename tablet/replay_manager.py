import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

from shared.config import settings
from shared.logger import setup_logger
from tablet.replay_engine import ReplayEngine, Segment

logger = setup_logger(__name__)


class ReplayManager:
    def __init__(self, engine: ReplayEngine, output_dir: str = "replays"):
        self._engine = engine
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._latest_replay: Optional[str] = None

    def get_last(self, seconds: int) -> Optional[str]:
        segments = self._engine.get_segments()
        if not segments:
            logger.warning("No segments available for replay")
            return None

        target_time = time.time() - seconds
        selected = [s for s in segments if s.end_time >= target_time]

        if not selected and segments:
            selected = [segments[-1]]
        elif not selected:
            return None

        if len(selected) == 1:
            return selected[0].path

        return self._concat_segments(selected)

    def save_replay(self, seconds: int) -> Optional[str]:
        replay_path = self.get_last(seconds)
        if replay_path is None:
            return None

        replay_id = uuid.uuid4().hex[:12]
        ext = Path(replay_path).suffix
        saved_name = f"replay_{replay_id}_{seconds}s{ext}"
        saved_path = str(self._output_dir / saved_name)

        import shutil
        shutil.copy2(replay_path, saved_path)

        self._latest_replay = saved_path
        size = os.path.getsize(saved_path)
        logger.info(f"Replay saved: {saved_name} ({size / 1024:.1f}KB)")
        return saved_path

    @property
    def latest_replay(self) -> Optional[str]:
        return self._latest_replay

    def _concat_segments(self, segments: list[Segment]) -> Optional[str]:
        concat_id = uuid.uuid4().hex[:8]
        output_path = str(self._output_dir / f"replay_{concat_id}.mp4")

        list_path = str(self._output_dir / f"concat_{concat_id}.txt")
        try:
            with open(list_path, "w") as f:
                for seg in segments:
                    abs_path = os.path.abspath(seg.path)
                    f.write(f"file '{abs_path}'\n")

            cmd = [
                settings.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",
                "-y",
                output_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg concat failed: {result.stderr}")
                return None

            self._latest_replay = output_path
            logger.info(f"Replay created: {os.path.basename(output_path)}")
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg concat timed out")
            return None
        except Exception as e:
            logger.error(f"Concat error: {e}")
            return None
        finally:
            try:
                if os.path.exists(list_path):
                    os.remove(list_path)
            except OSError:
                pass
