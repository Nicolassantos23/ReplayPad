import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from server.database import ReplayModel, get_session
from server.storage import delete_file, get_file_path, save_file
from shared.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api")


@router.post("/upload")
async def upload_replay(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    filepath = save_file(file.filename, data)
    if filepath is None:
        raise HTTPException(500, "Failed to save file")

    import cv2
    cap = cv2.VideoCapture(filepath)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    duration = frame_count / fps if fps > 0 else 0.0

    replay = ReplayModel(
        duration=round(duration, 2),
        filename=file.filename,
        size=len(data),
        storage_path=filepath,
    )
    db.add(replay)
    db.commit()
    db.refresh(replay)

    logger.info(f"Replay stored: {replay.id} — {file.filename}")
    return {
        "id": replay.id,
        "filename": replay.filename,
        "duration": replay.duration,
        "size": replay.size,
        "created_at": replay.created_at.isoformat(),
    }


@router.get("/replays")
async def list_replays(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
):
    total = db.query(ReplayModel).count()
    replays = (
        db.query(ReplayModel)
        .order_by(ReplayModel.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "replays": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "duration": r.duration,
                "filename": r.filename,
                "size": r.size,
            }
            for r in replays
        ],
    }


@router.get("/replay/{replay_id}")
async def download_replay(
    replay_id: str,
    db: Session = Depends(get_session),
):
    replay = db.query(ReplayModel).filter(ReplayModel.id == replay_id).first()
    if replay is None:
        raise HTTPException(404, "Replay not found")

    filepath = get_file_path(replay.storage_path)
    if filepath is None:
        raise HTTPException(404, "File not found on disk")

    return FileResponse(
        filepath,
        media_type="video/mp4",
        filename=replay.filename,
    )


@router.delete("/replay/{replay_id}")
async def delete_replay(
    replay_id: str,
    db: Session = Depends(get_session),
):
    replay = db.query(ReplayModel).filter(ReplayModel.id == replay_id).first()
    if replay is None:
        raise HTTPException(404, "Replay not found")

    delete_file(replay.storage_path)
    db.delete(replay)
    db.commit()

    return {"deleted": True, "id": replay_id}


@router.get("/health")
async def health():
    return {"status": "online"}
