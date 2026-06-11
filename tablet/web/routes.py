import asyncio
import os
import mimetypes

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

from shared.logger import setup_logger

logger = setup_logger(__name__)

BOUNDARY = "frame"
MJPEG_HEADER = f"multipart/x-mixed-replace; boundary={BOUNDARY}"


def create_router(camera, engine, manager, uploader):
    router = APIRouter()

    # ------------------------------------------------------------------
    # Live MJPEG
    # ------------------------------------------------------------------

    @router.get("/video")
    async def video():
        async def generate():
            while True:
                frame = camera.read_frame()
                if frame is not None:
                    import cv2
                    _, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    yield (
                        b"--" + BOUNDARY.encode() + b"\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
                    )
                await asyncio.sleep(0.033)

        return StreamingResponse(generate(), media_type=MJPEG_HEADER)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @router.get("/status")
    async def status():
        segments = engine.get_segments()
        return {
            "camera": "connected" if camera.is_connected else "disconnected",
            "recording": engine._running,
            "segments": len(segments),
            "buffer_duration": sum(s.duration for s in segments),
            "upload_queue": uploader.queue_size,
        }

    # ------------------------------------------------------------------
    # Replay endpoints
    # ------------------------------------------------------------------

    @router.post("/replay/{seconds}")
    async def create_replay(seconds: int):
        if seconds not in (10, 20, 30):
            raise HTTPException(400, "Supported: 10, 20, 30 seconds")
        path = manager.get_last(seconds)
        if path is None:
            raise HTTPException(503, "No segments available for replay")
        return {"path": path, "filename": os.path.basename(path)}

    @router.get("/replay/latest")
    async def latest_replay():
        path = manager.latest_replay
        if path is None or not os.path.isfile(path):
            raise HTTPException(404, "No replay available")
        mime, _ = mimetypes.guess_type(path)
        return FileResponse(path, media_type=mime or "video/mp4")

    # ------------------------------------------------------------------
    # Save and upload
    # ------------------------------------------------------------------

    @router.post("/save/{seconds}")
    async def save_replay(seconds: int):
        if seconds not in (10, 20, 30):
            raise HTTPException(400, "Supported: 10, 20, 30 seconds")
        path = manager.save_replay(seconds)
        if path is None:
            raise HTTPException(503, "Failed to save replay")
        uploader.enqueue(path)
        return {
            "path": path,
            "filename": os.path.basename(path),
            "upload_queued": True,
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    @router.get("/", response_class=HTMLResponse)
    async def dashboard():
        html_path = os.path.join(os.path.dirname(__file__), "templates", "tablet.html")
        try:
            with open(html_path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=404)

    return router
