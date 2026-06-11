#!/usr/bin/env python3
import os
import sys
import threading

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from shared.config import settings
from shared.logger import setup_logger

from tablet.camera_receiver import CameraReceiver, CameraConfig
from tablet.replay_engine import ReplayEngine
from tablet.replay_manager import ReplayManager
from tablet.uploader import Uploader
from tablet.web.routes import create_router

logger = setup_logger("replaypad")


def main():
    load_dotenv()

    if not settings.stream_url:
        logger.error("STREAM_URL not set")
        sys.exit(1)

    # ── Engine ──────────────────────────────────────────────────────
    engine = ReplayEngine(
        output_dir="segments",
        segment_duration=settings.segment_duration,
        max_segments=settings.max_segments,
    )
    engine.start()

    # ── Camera ──────────────────────────────────────────────────────
    cam_config = CameraConfig(stream_url=settings.stream_url)
    camera = CameraReceiver(cam_config)
    camera.start()

    # ── Replay ──────────────────────────────────────────────────────
    manager = ReplayManager(engine)

    # ── Upload ──────────────────────────────────────────────────────
    uploader = Uploader(server_url=os.getenv("VPS_URL", ""))
    uploader.start()

    # ── Frame feeder (camera → engine) ──────────────────────────────
    import time as _time

    feeding = True

    def feed_loop():
        while feeding:
            frame = camera.read_frame()
            if frame is not None:
                engine.feed(frame, _time.time())
            _time.sleep(0.01)

    feed_thread = threading.Thread(target=feed_loop, daemon=True)
    feed_thread.start()

    # ── API ─────────────────────────────────────────────────────────
    app = FastAPI(title="ReplayPad — Tablet", version="1.2.0")
    router = create_router(camera, engine, manager, uploader)
    app.include_router(router)

    logger.info("─" * 45)
    logger.info(f"  ReplayPad v1.2 — Tablet")
    logger.info(f"  Stream URL: {settings.stream_url}")
    logger.info(f"  Dashboard:  http://{settings.tablet_host}:{settings.tablet_port}")
    logger.info(f"  Buffer:     {settings.max_segments}x{settings.segment_duration}s")
    logger.info("─" * 45)

    try:
        uvicorn.run(
            app,
            host=settings.tablet_host,
            port=settings.tablet_port,
            log_level="info",
        )
    finally:
        feeding = False
        camera.stop()
        engine.stop()
        uploader.stop()
        logger.info("ReplayPad stopped")


if __name__ == "__main__":
    main()
